"""
extractor.py — SEC EDGAR XBRL extraction layer for the Credit Warning System (Phase 2).

Responsibilities (per spec/SECTION_6.md and the agreed extraction plan):
  1. SEC-compliant HTTP client: descriptive User-Agent, 150 ms proactive rate limiter,
     exponential-backoff-with-jitter on 429/403/5xx/timeout, no-retry on 404 (§6.6).
  2. On-disk cache with TTL tiers (companyfacts/submissions 24 h) (§6.6).
  3. companyfacts + submissions fetch; issuer metadata + CIK onboarding validation (§6.2).
  4. Fact bucketing into INSTANT (balance sheet) and DURATION (income / cash flow) (§6.4).
  5. Concept tag-fallback resolver — "first non-null" and "sum all non-null" modes —
     recording which tag produced each value (source_tags) and any flags.
  6. Period engine: YTD -> quarterly subtraction (canonical §6.4 / FCF Difference 3) and
     trailing-twelve-month (TTM) aggregation for combined ratios.

This module performs NO ratio computation and NO threshold logic — it returns clean,
audited per-period input dictionaries that metrics.py consumes. It never substitutes
zero for a missing input; a missing tag yields None and a flag.

Reference patterns borrowed (and re-implemented) from Khootz/Credit_Warning:
  CIK zero-padding, 150 ms throttle, candidate-tag concept map, dedup-by-form.
Where that reference diverges from our spec (no YTD subtraction, no TTM), we follow
the spec.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Optional

import requests

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

USER_AGENT = "CreditWarningSystem elaine.wei@xpef.org"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Rate limiting (§6.6): target 6-7 req/s, 150 ms minimum interval.
MIN_REQUEST_INTERVAL_S = 0.150

# Reactive backoff (§6.6): exponential with jitter.
BACKOFF_BASE_S = 2.0
BACKOFF_MAX_S = 60.0
MAX_RETRIES = 5
REQUEST_TIMEOUT_S = 30.0

# Cache TTLs (§6.6). The bulk companyfacts file always refreshes on a 24 h cycle.
CACHE_TTL_S = 24 * 60 * 60

EXTRACTOR_VERSION = "edgar-xbrl-py-v1"

# Duration-span buckets in days, used to classify a duration fact's reporting window
# (§6.4). Tolerant ranges accommodate 13-week fiscal quarters and 52/53-week years.
_SPAN_BUCKETS = {
    "Q": (75, 100),     # ~3 months  -> quarter-only
    "H1": (160, 195),   # ~6 months  -> YTD through Q2
    "9M": (250, 290),   # ~9 months  -> YTD through Q3
    "FY": (340, 380),   # ~12 months -> annual (10-K)
}


# --------------------------------------------------------------------------------------
# Concept -> candidate us-gaap tag map
#
# Each concept resolves either by FIRST non-null tag, or by SUMMING all non-null tags
# (used only where the spec says "sum all non-null values" — short-term debt components).
# `flag_tags` marks tags that, when used, attach an audit flag (lease contamination,
# bundled short-term investments, etc.).
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Concept:
    key: str
    kind: str            # "instant" | "duration"
    mode: str            # "first" | "sum"
    tags: tuple[str, ...]
    flag_tags: dict[str, str] = field(default_factory=dict)


CONCEPTS: dict[str, Concept] = {
    # ---- Leverage: debt components (instant) ----
    # Component A — short-term financial debt: SUM all non-null (CP + revolver + notes
    # are not mutually exclusive). LEVERAGE.md Extraction Fallback Logic, Component A.
    "short_term_debt": Concept(
        "short_term_debt", "instant", "sum",
        ("ShortTermBorrowings", "CommercialPaper", "NotesPayableCurrent",
         "LineOfCreditCurrent", "LinesOfCreditCurrent",
         "ShortTermBankLoansAndNotesPayable"),
    ),
    # Component B — current portion of long-term debt: FIRST non-null.
    "current_ltd": Concept(
        "current_ltd", "instant", "first",
        ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent",
         "SecuredDebtCurrent", "UnsecuredDebtCurrent"),
        flag_tags={"LongTermDebtAndCapitalLeaseObligationsCurrent":
                   "current LTD tag bundles finance leases — may overstate vs F1 definition"},
    ),
    # DebtCurrent — used for the Component-B double-count check (LEVERAGE.md Input 2).
    "debt_current": Concept(
        "debt_current", "instant", "first", ("DebtCurrent",),
    ),
    # Component C — long-term (non-current) debt: FIRST non-null. C is the Level-1 floor.
    "long_term_debt": Concept(
        "long_term_debt", "instant", "first",
        ("LongTermDebtNoncurrent", "LongTermDebt",
         "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
         "SecuredLongTermDebt", "UnsecuredLongTermDebt", "SeniorLongTermNotes"),
        flag_tags={
            "LongTermDebt": "LongTermDebt may include current portion — subtract if current LTD present",
            "LongTermDebtAndCapitalLeaseObligationsNoncurrent":
                "LT debt tag bundles finance leases — may overstate vs F1 definition",
        },
    ),
    # Aggregated debt (Level 2 fallback).
    "debt_aggregate": Concept(
        "debt_aggregate", "instant", "first",
        ("DebtLongtermAndShorttermCombinedAmount", "DebtAndCapitalLeaseObligations",
         "LongTermDebtAndCapitalLeaseObligations"),
        flag_tags={
            "DebtAndCapitalLeaseObligations": "aggregated debt tag — may include finance leases",
            "LongTermDebtAndCapitalLeaseObligations": "aggregated debt tag — may include finance leases",
        },
    ),

    # ---- Cash (instant) ----
    "cash": Concept(
        "cash", "instant", "first",
        ("CashAndCashEquivalentsAtCarryingValue",
         "CashCashEquivalentsAndShortTermInvestments",
         "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        flag_tags={
            "CashCashEquivalentsAndShortTermInvestments":
                "cash tag includes short-term investments — subtract STI not possible; flagged",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents":
                "cash tag includes restricted cash — attempting to subtract RestrictedCashAndCashEquivalents",
        },
    ),
    "restricted_cash": Concept(
        "restricted_cash", "instant", "first",
        ("RestrictedCashAndCashEquivalents", "RestrictedCashAndCashEquivalentsAtCarryingValue"),
    ),

    # ---- Balance-sheet totals / sanity (instant) ----
    "assets": Concept("assets", "instant", "first", ("Assets", "AssetsNet")),
    "liabilities": Concept("liabilities", "instant", "first", ("Liabilities",)),

    # ---- Liquidity (instant) ----
    "current_assets": Concept(
        "current_assets", "instant", "first", ("AssetsCurrent",),
    ),
    "current_liabilities": Concept(
        "current_liabilities", "instant", "first", ("LiabilitiesCurrent",),
    ),
    "inventory": Concept(
        "inventory", "instant", "first", ("InventoryNet", "InventoryGross"),
        flag_tags={"InventoryGross":
                   "gross inventory used — write-down allowance not deducted; quick ratio may be overstated"},
    ),
    "prepaid": Concept(
        "prepaid", "instant", "first",
        ("PrepaidExpenseAndOtherAssetsCurrent", "PrepaidExpenseCurrent", "OtherAssetsCurrent"),
        flag_tags={"OtherAssetsCurrent":
                   "prepaid proxied by other current assets — quick ratio may be marginally understated"},
    ),

    # ---- Equity / asset-coverage / maturity / provisions (instant) ----
    "equity": Concept(
        "equity", "instant", "first",
        ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    ),
    "short_term_investments": Concept(
        "short_term_investments", "instant", "first",
        ("ShortTermInvestments", "MarketableSecuritiesCurrent"),
    ),
    "goodwill": Concept("goodwill", "instant", "first", ("Goodwill", "GoodwillNet")),
    "intangibles": Concept(
        "intangibles", "instant", "first",
        ("IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"),
    ),
    "deferred_tax_assets": Concept(
        "deferred_tax_assets", "instant", "first",
        ("DeferredTaxAssetsLiabilitiesNet", "DeferredTaxAssetsNet"),
    ),
    # Liquidation-value inputs (Group 6 / ASSET_COVERAGE.md Formula 2 haircuts).
    "accounts_receivable": Concept(
        "accounts_receivable", "instant", "first",
        ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "AccountsReceivableNet"),
    ),
    "ppe_net": Concept(
        "ppe_net", "instant", "first",
        ("PropertyPlantAndEquipmentNet",),
    ),
    "loss_contingency_current": Concept(
        "loss_contingency_current", "instant", "first",
        ("LossContingencyAccrualAtCarryingValue",),
    ),
    "loss_contingency_noncurrent": Concept(
        "loss_contingency_noncurrent", "instant", "first",
        ("LossContingencyAccrualNoncurrent",),
    ),
    "environmental_accrual": Concept(
        "environmental_accrual", "instant", "first",
        ("AccrualForEnvironmentalLossContingencies",),
    ),

    # ---- Income / cash-flow (duration) ----
    "operating_income": Concept(
        "operating_income", "duration", "first",
        ("OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"),
        flag_tags={"IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest":
                   "operating income proxied by pretax income — includes financing items; ratio may be distorted"},
    ),
    "dep_amort": Concept(
        "dep_amort", "duration", "first",
        ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
         "DepreciationAndAmortization", "Depreciation"),
        flag_tags={"Depreciation": "D&A may be partial (depreciation only) — verify completeness"},
    ),
    # D&A derivation sub-components — used only when dep_amort resolves to null.
    # Depreciation alone is already in dep_amort as the last-resort single tag,
    # but AmortizationOfIntangibleAssets must be fetched separately to sum with it.
    # Both are extracted here so metrics.py can sum them without hitting the network.
    "depreciation_only": Concept(
        "depreciation_only", "duration", "first",
        ("Depreciation",),
    ),
    "amortization_intangibles": Concept(
        "amortization_intangibles", "duration", "first",
        ("AmortizationOfIntangibleAssets",),
    ),
    "interest_expense": Concept(
        "interest_expense", "duration", "first",
        ("InterestExpense", "InterestAndDebtExpense", "InterestExpenseDebt"),
        flag_tags={"InterestAndDebtExpense":
                   "InterestExpense absent — InterestAndDebtExpense used; may include debt issuance cost amortization",
                   "InterestExpenseDebt":
                   "InterestExpense absent — InterestExpenseDebt used (common for pharma/biotech)"},
    ),
    # Net-interest detection only (§ coverage): presence triggers a null + flag, never used as value.
    "interest_net": Concept(
        "interest_net", "duration", "first", ("InterestIncomeExpenseNet",),
    ),
    # Interest income — used to gross up net interest into gross interest expense when only
    # InterestIncomeExpenseNet is tagged (INTEREST_COVERAGE.md Input 2, Step 3).
    "interest_income_operating": Concept(
        "interest_income_operating", "duration", "first",
        ("InterestIncomeOperating", "InterestAndDividendIncomeOperating"),
    ),
    "interest_income_investment": Concept(
        "interest_income_investment", "duration", "first",
        ("InvestmentIncomeInterest", "InterestIncomeNonoperating"),
    ),
    "operating_cash_flow": Concept(
        "operating_cash_flow", "duration", "first",
        ("NetCashProvidedByUsedInOperatingActivities",
         "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        flag_tags={"NetCashProvidedByUsedInOperatingActivitiesContinuingOperations":
                   "OCF from continuing operations only — discontinued operations excluded"},
    ),
    "capex": Concept(
        "capex", "duration", "first",
        ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForCapitalImprovements",
         "PaymentsToAcquireOtherPropertyPlantAndEquipment"),
        flag_tags={
            "PaymentsForCapitalImprovements": "capital improvements tag used — capex may be understated",
            "PaymentsToAcquireOtherPropertyPlantAndEquipment": "other PP&E tag used — verify completeness",
        },
    ),
    # Moody's Formula-2 FCF inputs (Group 7a). All duration items on the cash-flow statement.
    "pension_contributions": Concept(
        "pension_contributions", "duration", "first",
        ("PensionContributions", "PaymentsForPensionAndOtherPostretirementBenefits"),
    ),
    "dividends_common": Concept(
        "dividends_common", "duration", "first",
        ("PaymentsOfDividendsCommonStock", "PaymentsOfDividends"),
    ),
    "dividends_preferred": Concept(
        "dividends_preferred", "duration", "first",
        ("PaymentsOfDividendsPreferredStockAndPreferenceStock",),
    ),
    "dividends_minority": Concept(
        "dividends_minority", "duration", "first",
        ("PaymentsOfDividendsMinorityInterest",),
    ),
    "revenue": Concept(
        "revenue", "duration", "first",
        ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
         "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"),
    ),
}


# --------------------------------------------------------------------------------------
# HTTP client: rate limiting, backoff, cache
# --------------------------------------------------------------------------------------

class SecClient:
    """SEC EDGAR JSON client with proactive rate limiting, reactive backoff, and caching."""

    def __init__(self, user_agent: str = USER_AGENT, cache_dir: str = CACHE_DIR):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        })
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._last_request_at = 0.0

    # -- rate limiter -------------------------------------------------------------------
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = MIN_REQUEST_INTERVAL_S - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    # -- cache --------------------------------------------------------------------------
    def _cache_path(self, name: str) -> str:
        return os.path.join(self.cache_dir, name)

    def _read_cache(self, name: str, ttl_s: float) -> Optional[dict]:
        path = self._cache_path(name)
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            return None
        if age > ttl_s:
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, name: str, data: dict) -> None:
        try:
            with open(self._cache_path(name), "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except OSError:
            pass  # caching is best-effort

    # -- fetch with backoff -------------------------------------------------------------
    def get_json(self, url: str, cache_name: str, ttl_s: float = CACHE_TTL_S) -> Optional[dict]:
        """Fetch JSON with cache lookup, rate limiting, and exponential backoff.

        Returns parsed JSON, or None if the resource is 404 (does not exist) or all
        retries are exhausted. Never raises on transient HTTP errors — the caller marks
        the run failed and continues (§6.6).
        """

        #1. check load
        cached = self._read_cache(cache_name, ttl_s)
        if cached is not None:
            return cached

        #2. make request with retry logic
        for attempt in range(MAX_RETRIES + 1):
            self._throttle() #limit
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_S)
            except (requests.Timeout, requests.ConnectionError):
                if not self._backoff(attempt):
                    return None
                continue

            if resp.status_code == 404:
                return None  # do not retry — resource does not exist
            if resp.status_code in (429, 403) or resp.status_code >= 500:  #temporary error, retry
                if not self._backoff(attempt):
                    return None
                continue
            if not resp.ok:
                return None

            try:
                data = resp.json()  #success
            except json.JSONDecodeError:
                return None
            self._write_cache(cache_name, data)
            return data

        return None

    # -- text (HTML) cache + fetch ------------------------------------------------------
    def _read_text_cache(self, name: str, ttl_s: float) -> Optional[str]:
        path = self._cache_path(name)
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            return None
        if age > ttl_s:
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    def _write_text_cache(self, name: str, text: str) -> None:
        try:
            with open(self._cache_path(name), "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError:
            pass  # caching is best-effort

    def get_text(self, url: str, cache_name: str, ttl_s: float = CACHE_TTL_S) -> Optional[str]:
        """Fetch raw text (e.g. filing HTML) — same rate limiting, backoff, and caching
        as get_json. Returns the body, or None on 404 / exhausted retries. Filing HTML is
        historical and immutable, so a long TTL is appropriate (default 24 h is fine; the
        caller may pass a longer TTL for archived filings)."""
        cached = self._read_text_cache(cache_name, ttl_s)
        if cached is not None:
            return cached

        for attempt in range(MAX_RETRIES + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_S,
                                        headers={"Accept": "text/html,application/xhtml+xml,*/*"})
            except (requests.Timeout, requests.ConnectionError):
                if not self._backoff(attempt):
                    return None
                continue
            if resp.status_code == 404:
                return None
            if resp.status_code in (429, 403) or resp.status_code >= 500:
                if not self._backoff(attempt):
                    return None
                continue
            if not resp.ok:
                return None
            body = resp.text
            self._write_text_cache(cache_name, body)
            return body
        return None

    @staticmethod
    def _backoff(attempt: int) -> bool:
        """Sleep with exponential backoff + jitter. Returns False once retries exhausted."""
        if attempt >= MAX_RETRIES:
            return False
        wait = min(BACKOFF_BASE_S * (2 ** attempt) + random.random(), BACKOFF_MAX_S) #jitter
        time.sleep(wait)
        return True
        # If multiple clients wait the same fixed interval, they retry simultaneously, causing new collisions (thundering herd effect).


# --------------------------------------------------------------------------------------
# CIK helpers + issuer metadata
# --------------------------------------------------------------------------------------

def pad_cik(cik: str | int) -> str:
    """Zero-pad a CIK to 10 digits (§6.1). '320193' -> '0000320193'."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError(f"invalid CIK: {cik!r}")
    return digits.zfill(10)


@dataclass
class IssuerMetadata:
    cik: str
    name: str
    tickers: list[str]
    sic_code: Optional[str]
    fiscal_year_end: Optional[str]  # MM-DD
    has_10k: bool


def fetch_issuer_metadata(client: SecClient, cik: str) -> Optional[IssuerMetadata]:
    """Fetch + validate issuer from the submissions API (§6.2 onboarding steps 1-4).

    Returns None if the CIK does not resolve to a valid company (validation failure).
    """
    cik10 = pad_cik(cik) #standard 10 digit
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    data = client.get_json(url, cache_name=f"{cik10}_submissions.json")
    if not data:
        return None
    name = data.get("name") #extract company name
    if not name:
        return None  # step 2: no valid company name

    fye_raw = data.get("fiscalYearEnd")  # "MMDD" the end date of the fiscal year
    fiscal_year_end = None
    if isinstance(fye_raw, str) and len(fye_raw) == 4 and fye_raw.isdigit():
        fiscal_year_end = f"{fye_raw[:2]}-{fye_raw[2:]}"

    # check any 10-K history
    forms = (data.get("filings", {}).get("recent", {}).get("form")) or []
    has_10k = any(str(f).startswith("10-K") for f in forms)  # step 3
    # data["filings"]["recent"]["form"] returns a list like ["10-K", "10-Q", "8-K", "10-K", ...]
    # any() returns True if at least one item starts with "10-K"

    #extract SIC code
    sic = data.get("sic")
    return IssuerMetadata(
        cik=cik10,
        name=name,
        tickers=list(data.get("tickers") or []),
        sic_code=str(sic) if sic not in (None, "") else None,
        fiscal_year_end=fiscal_year_end,
        has_10k=has_10k,
    )


def fetch_company_facts(client: SecClient, cik: str) -> Optional[dict]:
    """Fetch the bulk companyfacts JSON for a CIK (§6.1)."""
    cik10 = pad_cik(cik)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
    return client.get_json(url, cache_name=f"{cik10}_companyfacts.json")


# --------------------------------------------------------------------------------------
# Fact bucketing + period classification (§6.4)
# --------------------------------------------------------------------------------------

@dataclass
class Fact:
    end: str                      # period end date (ISO)
    val: float
    accn: Optional[str]           # accession number (file number)
    form: Optional[str]           # 10-K, 10-Q, 8-K
    filed: Optional[str]          # filing date
    start: Optional[str] = None   # present for duration facts
    span_days: Optional[int] = None
    span_bucket: Optional[str] = None  # Q | H1 | 9M | FY

'''
Fact(
    end="2023-06-30",           # period end date
    start="2023-04-01",         # period start date
    val=81797000000,            # rev $81.8B
    accn="0000320193-23-000106",
    form="10-Q",
    filed="2023-08-04",
    span_days=90,               # 90 days
    span_bucket="Q",            # a season
)
'''


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _classify_span(start: Optional[str], end: str) -> tuple[Optional[int], Optional[str]]:
    sd, ed = _parse_date(start), _parse_date(end)
    if sd is None or ed is None:
        return None, None
    days = (ed - sd).days
    for bucket, (lo, hi) in _SPAN_BUCKETS.items():
        if lo <= days <= hi:
            return days, bucket
    return days, None  # unclassifiable span

    '''
    _classify_span("2023-01-01", "2023-03-31")
        # 返回 (89, "Q")

    _classify_span("2023-01-01", "2023-06-30")  
        # 返回 (180, "H1")
    '''

'''
用户输入 CIK: "320193"
        │
        ▼
pad_cik() → "0000320193"
        │
        ├─────────────────────────────────────────────┐
        │                                             │
        ▼                                             ▼
fetch_issuer_metadata()                    fetch_company_facts()
        │                                             │
        ▼                                             ▼
GET /submissions/CIK0000320193.json         GET /api/xbrl/companyfacts/CIK0000320193.json
        │                                             │
        ▼                                             ▼
{                                            {
  "name": "APPLE INC",                         "entityName": "APPLE INC",
  "tickers": ["AAPL"],                         "facts": {
  "sic": "3571",                                 "us-gaap": {
  "fiscalYearEnd": "0930",                        "Cash...": {...},
  "filings": {...}                                "LongTermDebt...": {...}
}                                              }
                                             }
        │                                             │
        ▼                                             ▼
IssuerMetadata                               raw JSON dict
'''


def _iter_usd_facts(company_facts: dict, tag: str) -> list[dict]:
    """Return the raw USD fact entries for a us-gaap tag (empty if absent)."""
    node = (company_facts.get("facts", {}).get("us-gaap", {}) or {}).get(tag)
    if not node:
        return []
    units = node.get("units") or {}
    if "USD" in units:
        return units["USD"] or []
    # Fall back to the first plain-currency unit key, if any.
    for key, entries in units.items():
        if "/" not in key and key not in ("shares", "pure"):
            return entries or []
    return []


def _to_facts(raw_entries: Iterable[dict]) -> list[Fact]:
    facts: list[Fact] = []
    for e in raw_entries:
        val = e.get("val")
        end = e.get("end")
        if not isinstance(val, (int, float)) or not end:
            continue
        start = e.get("start")
        span_days, bucket = _classify_span(start, end) if start else (None, None)
        facts.append(Fact(
            end=end, val=float(val), accn=e.get("accn"), form=e.get("form"),
            filed=e.get("filed"), start=start, span_days=span_days, span_bucket=bucket,
        ))
    return facts


def _latest_filed(facts: list[Fact]) -> Optional[Fact]:
    """Pick the fact filed most recently (captures restatements); 10-K/10-Q preferred on ties."""
    if not facts:
        return None
    return sorted(
        facts,
        key=lambda f: (f.filed or "", 1 if (f.form or "").startswith(("10-K", "10-Q")) else 0),
    )[-1]


# Why this priority matters? A company may later amend its filings (e.g., 8-K/A) to restate financial data.
# We use the most recently filed version, even if the original filing had a better form type.
#
# Example:
#   fact1 = Fact(filed="2023-05-01", form="8-K/A")  # amendment
#   fact2 = Fact(filed="2023-04-15", form="10-Q")   # quarterly report
#
# Sort key:
#   fact1: ("2023-05-01", 0)  ← later date wins
#   fact2: ("2023-04-15", 1)
#
# fact1 wins because it was filed more recently, even though the original 10-Q was superseded.




# --------------------------------------------------------------------------------------
# Concept resolution per instant period-end
# --------------------------------------------------------------------------------------

@dataclass
class ResolvedValue:
    value: Optional[float]
    tags: list[str]                       # us-gaap tags that contributed
    flags: list[str] = field(default_factory=list)
    path: str = "primary"                 # primary | derived_quarterly | reported_quarterly | none


def _resolve_instant(company_facts: dict, concept: Concept, end: str) -> ResolvedValue:
    """Resolve an instant concept at a specific period-end date."""
    if concept.mode == "sum":
        total = 0.0
        used: list[str] = []
        flags: list[str] = []
        for tag in concept.tags:
            facts = [f for f in _to_facts(_iter_usd_facts(company_facts, tag)) if f.end == end]
            chosen = _latest_filed(facts)
            if chosen is not None:
                total += chosen.val
                used.append(tag)
                if tag in concept.flag_tags:
                    flags.append(concept.flag_tags[tag])
        if not used:
            return ResolvedValue(None, [], [], "none")
        return ResolvedValue(total, used, flags, "primary")

    # first-non-null mode
    for tag in concept.tags:
        facts = [f for f in _to_facts(_iter_usd_facts(company_facts, tag)) if f.end == end]
        chosen = _latest_filed(facts)
        if chosen is not None:
            flags = [concept.flag_tags[tag]] if tag in concept.flag_tags else []
            return ResolvedValue(chosen.val, [tag], flags, "primary")
    return ResolvedValue(None, [], [], "none")


# --------------------------------------------------------------------------------------
# Period engine: YTD -> quarterly subtraction + TTM (§6.4 / FCF Difference 3)
# --------------------------------------------------------------------------------------

def _derive_quarterly_series(company_facts: dict, concept: Concept) -> dict[str, ResolvedValue]:
    """For a duration concept, produce a single-quarter value per period-end date.

    Algorithm (§6.4): resolve the concept's first-available tag, then
      - prefer a directly-reported quarter-only fact (~3-month span) for an end date;
      - otherwise derive the quarter by subtracting the prior cumulative within the same
        fiscal year, where facts of one fiscal year share a common `start` (FY start):
            Q1 = the ~3M fact;  Q2 = H1 - Q1;  Q3 = 9M - H1;  Q4 = FY - 9M.
    Returns {period_end: ResolvedValue}. Annual (FY) facts also yield their own end date
    as the full-year value (path="primary") for 10-K periods.
    """
    # Gather duration facts across ALL candidate tags, tagged with their priority
    # (index in concept.tags). Per-period selection below prefers the highest-priority
    # tag that actually covers each period — fixing the case where an older primary tag
    # (e.g. Revenues) has sparse coverage while a modern same-measure variant
    # (RevenueFromContractWithCustomerExcludingAssessedTax) covers recent quarters.
    # Merging is safe only for same-measure variants; the concept map keeps it so.
    candidates: list[tuple[int, str, Fact]] = []
    for prio, tag in enumerate(concept.tags):
        for f in _to_facts(_iter_usd_facts(company_facts, tag)):
            if f.start:
                candidates.append((prio, tag, f))
    if not candidates:
        return {}

    def _better(a: tuple[int, str, Fact], b: Optional[tuple[int, str, Fact]]) -> bool:
        """True if candidate a should replace current best b (lower priority index wins;
        tie-break on later filing date)."""
        if b is None:
            return True
        if a[0] != b[0]:
            return a[0] < b[0]
        return (a[2].filed or "") > (b[2].filed or "")

    # Reported quarter-only facts, keyed by end date.
    reported_q: dict[str, tuple[int, str, Fact]] = {}
    for cand in candidates:
        _, _, f = cand
        if f.span_bucket == "Q":
            if _better(cand, reported_q.get(f.end)):
                reported_q[f.end] = cand

    # YTD progression grouped by fiscal-year start date, best candidate per span bucket.
    by_fy_start: dict[str, dict[str, tuple[int, str, Fact]]] = {}
    for cand in candidates:
        _, _, f = cand
        if f.span_bucket not in ("Q", "H1", "9M", "FY") or not f.start:
            continue
        grp = by_fy_start.setdefault(f.start, {})
        if _better(cand, grp.get(f.span_bucket)):
            grp[f.span_bucket] = cand

    out: dict[str, ResolvedValue] = {}

    def emit(end: str, value: float, tag: str, path: str, extra_flags: Optional[list[str]] = None) -> None:
        flags = ([concept.flag_tags[tag]] if tag in concept.flag_tags else []) + (extra_flags or [])
        out[end] = ResolvedValue(value, [tag], flags, path)

    # Full-year value from FY facts (used for 10-K annual periods).
    for grp in by_fy_start.values():
        if "FY" in grp:
            _, tag, f = grp["FY"]
            emit(f.end, f.val, tag, "primary")

    # Derive each quarter. Each bucket is a (prio, tag, Fact) tuple or None.
    for grp in by_fy_start.values():
        q1 = grp.get("Q")
        h1 = grp.get("H1")
        m9 = grp.get("9M")
        fy = grp.get("FY")
        # Q1 (the ~3M fact whose start == FY start)
        if q1 is not None and q1[2].end not in reported_q:
            emit(q1[2].end, q1[2].val, q1[1], "primary")  # already a single quarter
        # Q2 = H1 - Q1
        if h1 is not None and h1[2].end not in reported_q:
            if q1 is not None:
                emit(h1[2].end, h1[2].val - q1[2].val, h1[1], "derived_quarterly",
                     [f"Q2 derived: H1 YTD minus Q1 ({q1[2].end})"])
            else:
                emit(h1[2].end, h1[2].val, h1[1], "primary",
                     ["H1 YTD stored — Q1 unavailable for subtraction"])
        # Q3 = 9M - H1
        if m9 is not None and m9[2].end not in reported_q:
            if h1 is not None:
                emit(m9[2].end, m9[2].val - h1[2].val, m9[1], "derived_quarterly",
                     [f"Q3 derived: 9M YTD minus H1 ({h1[2].end})"])
            else:
                emit(m9[2].end, m9[2].val, m9[1], "primary",
                     ["9M YTD stored — H1 unavailable for subtraction"])
        # Q4 = FY - 9M
        if fy is not None and m9 is not None and fy[2].end not in reported_q:
            emit(fy[2].end, fy[2].val - m9[2].val, fy[1], "derived_quarterly",
                 [f"Q4 derived: FY minus 9M YTD ({m9[2].end})"])

    # Directly-reported quarters override any derivation for the same end date.
    for end, cand in reported_q.items():
        emit(end, cand[2].val, cand[1], "reported_quarterly")

    return out

'''
fiscal year: 2023-01-01 to 2023-12-31

accumulation:
    Q1 (3M):     $100M  ← directly
    H1 (6M):     $250M  ← YTD accumulation
    9M (9M):     $420M  ← YTD accumulation
    FY (12M):    $600M  ← whole year

Derive:
    Q2 = H1 - Q1 = $250M - $100M = $150M
    Q3 = 9M - H1 = $420M - $250M = $170M
    Q4 = FY - 9M = $600M - $420M = $180M

Output:
    2023-03-31: $100M (path="reported_quarterly")
    2023-06-30: $150M (path="derived_quarterly", flags=["Q2 derived..."])
    2023-09-30: $170M (path="derived_quarterly", flags=["Q3 derived..."])
    2023-12-31: $180M (path="derived_quarterly", flags=["Q4 derived..."])
'''

def _ttm(series: dict[str, ResolvedValue], end_dates: list[str]) -> dict[str, ResolvedValue]:
    """Trailing-twelve-month sum at each end date = that quarter + 3 prior quarters (§6.4).

    `end_dates` must be the chronologically sorted quarterly end dates of the series.
    Returns {end_date: ResolvedValue} where value is None (with a flag) if any of the
    four trailing quarters is missing.
    """
    out: dict[str, ResolvedValue] = {}
    for i, end in enumerate(end_dates):
        window = end_dates[max(0, i - 3): i + 1] #this season + past 3 season
        if len(window) < 4:
            out[end] = ResolvedValue(None, [], [f"TTM unavailable — only {len(window)} of 4 quarters present"], "none")
            continue
        vals = [series.get(d) for d in window]
        if any(rv is None or rv.value is None for rv in vals):
            out[end] = ResolvedValue(None, [], ["TTM unavailable — a trailing quarter is missing"], "none")
            continue
        total = sum(rv.value for rv in vals)  # type: ignore[union-attr]
        tags = sorted({t for rv in vals for t in rv.tags})  # type: ignore[union-attr]
        flags = sorted({f for rv in vals for f in rv.flags})  # type: ignore[union-attr]
        out[end] = ResolvedValue(total, tags, flags, "ttm")
    return out

'''
Seasonal Sequence:         Q1    Q2    Q3    Q4    Q5    Q6
Value:                     100   150   170   180   190   200

TTM Calculation:
    2023-03-31 (Q1): only 1 season→ None
    2023-06-30 (Q2): only 2 season → None
    2023-09-30 (Q3): only 3 season → None
    2023-12-31 (Q4): Q1+Q2+Q3+Q4 = 100+150+170+180 = 600 ✅
    2024-03-31 (Q5): Q2+Q3+Q4+Q5 = 150+170+180+190 = 690 ✅
    2024-06-30 (Q6): Q3+Q4+Q5+Q6 = 170+180+190+200 = 740 ✅
'''

    # ==================================================================
    # PERIOD ENGINE: YTD (Year-to-Date) → Quarterly Derivation
    # ==================================================================
    # SEC filings report cumulative YTD figures, not standalone quarters:
    #
    #   Q1 10-Q: $100M  (Jan-Mar)           ← direct quarter
    #   Q2 10-Q: $250M  (Jan-Jun YTD)       ← cumulative (H1)
    #   Q3 10-Q: $420M  (Jan-Sep YTD)       ← cumulative (9M)
    #   10-K:     $600M  (Jan-Dec YTD)       ← cumulative (FY)
    #
    # To get true quarterly values, we subtract:
    #   Q1 = $100M (direct)
    #   Q2 = H1 - Q1 = $250M - $100M = $150M
    #   Q3 = 9M - H1 = $420M - $250M = $170M
    #   Q4 = FY - 9M = $600M - $420M = $180M
    #
    # If a cumulative report (e.g., H1) exists but its preceding period (Q1)
    # is missing, we store the YTD value with a flag instead of guessing.
    #
    # TTM (Trailing Twelve Months) = sum of 4 most recent quarters.
    # Returns None until 4 quarters are available.
    # FY != TTM
    # ==================================================================

# --------------------------------------------------------------------------------------
# Top-level extraction
# --------------------------------------------------------------------------------------

INSTANT_CONCEPTS = [c.key for c in CONCEPTS.values() if c.kind == "instant"]
DURATION_CONCEPTS = [c.key for c in CONCEPTS.values() if c.kind == "duration"]


@dataclass
class PeriodInputs:
    period_end: str
    form_type: Optional[str]                   # 10-K | 10-Q (of the source filing)
    filing_date: Optional[str]                 # ISO date the source filing was filed
    instant: dict[str, ResolvedValue]          # balance-sheet values at period_end
    quarterly: dict[str, ResolvedValue]        # single-quarter duration values
    ttm: dict[str, ResolvedValue]              # trailing-twelve-month duration values


@dataclass
class ExtractionResult:
    metadata: IssuerMetadata                   # company info
    periods: list[PeriodInputs]                # chronological (oldest -> newest)


def _quarter_end_universe(company_facts: dict) -> list[str]:
    """All distinct period-end dates that carry a balance-sheet anchor, sorted ascending.

    AssetsCurrent / Assets / debt anchors define the periods at which we can form ratios.
    """
    ends: set[str] = set()
    for tag in ("AssetsCurrent", "Assets", "LiabilitiesCurrent",
                "LongTermDebtNoncurrent", "CashAndCashEquivalentsAtCarryingValue"):
        for f in _to_facts(_iter_usd_facts(company_facts, tag)):
            ends.add(f.end)
    return sorted(ends)


def _filter_company_facts_as_of(company_facts: dict, as_of: str) -> dict:
    """Return a companyfacts copy containing only facts filed on or before `as_of`.

    This is the single point-in-time gate for backtesting (Phase 3): by dropping every
    fact whose `filed` date is after the simulated date — and any fact with no `filed`
    date (cannot prove it was known) — the rest of the period engine produces exactly the
    view an analyst could have seen on `as_of`, with no look-ahead from later restatements.
    `as_of` is an ISO date ("YYYY-MM-DD"); ISO strings compare correctly lexicographically.
    """
    usgaap = (company_facts.get("facts", {}) or {}).get("us-gaap", {}) or {}
    new_usgaap: dict = {}
    for tag, node in usgaap.items():
        units = (node or {}).get("units") or {}
        new_units: dict = {}
        for unit_key, entries in units.items():
            kept = [e for e in (entries or []) if e.get("filed") and e["filed"] <= as_of]
            if kept:
                new_units[unit_key] = kept
        if new_units:
            new_usgaap[tag] = {"units": new_units}
    out = {k: v for k, v in company_facts.items() if k != "facts"}
    out["facts"] = {"us-gaap": new_usgaap}
    return out


def _period_filing(company_facts: dict, end: str) -> tuple[Optional[str], Optional[str]]:
    """Identify the source filing (form_type, filing_date) for a balance-sheet period-end.

    Uses the latest-filed balance-sheet anchor fact at that date; normalises amended
    forms (10-K/A -> 10-K).
    """
    for tag in ("AssetsCurrent", "Assets", "LiabilitiesCurrent", "LongTermDebtNoncurrent"):
        facts = [f for f in _to_facts(_iter_usd_facts(company_facts, tag)) if f.end == end]
        chosen = _latest_filed(facts)
        if chosen is not None:
            form = (chosen.form or "").replace("/A", "") or None
            return form, chosen.filed
    return None, None


def extract(cik: str, client: Optional[SecClient] = None, num_quarters: int = 8,
            as_of: Optional[str] = None) -> Optional[ExtractionResult]:
    """Full extraction for one CIK.

    Returns per-period input dictionaries for the most recent `num_quarters` balance-sheet
    period-ends, each carrying instant values, derived single-quarter duration values, and
    TTM duration values. Returns None if the CIK fails onboarding validation or companyfacts
    is unavailable.

    `as_of` (ISO date, optional): point-in-time gate for backtesting. When set, only facts
    filed on or before this date are used, so the result reflects exactly what was knowable
    on that date — no look-ahead from later restatements. Default None preserves all
    existing behaviour (uses the full current snapshot).
    """
    client = client or SecClient()
    # Step 1: Get company metadata (name, SIC, tickers, has_10k)
    meta = fetch_issuer_metadata(client, cik)
    if meta is None or not meta.has_10k:
        return None

    # Step 2: Get all XBRL data for this company
    company_facts = fetch_company_facts(client, cik)
    if not company_facts:
        return None

    # Step 2b: Point-in-time gate (Phase 3 backtest) — filter at the source, before the
    # period engine runs, so every downstream computation sees only as-of-date data.
    if as_of:
        company_facts = _filter_company_facts_as_of(company_facts, as_of)

    # Step 3: Pre-compute quarterly series and TTM for ALL duration concepts
    # Build the full quarterly duration + TTM series once (needs deep history for TTM).
    quarterly_series: dict[str, dict[str, ResolvedValue]] = {}
    ttm_series: dict[str, dict[str, ResolvedValue]] = {}
    for key in DURATION_CONCEPTS:
        series = _derive_quarterly_series(company_facts, CONCEPTS[key])
        quarterly_series[key] = series
        ttm_series[key] = _ttm(series, sorted(series.keys()))

    # Step 4: Determine which periods to report on
    # The periods we report on: most recent N balance-sheet period-ends.
    all_ends = _quarter_end_universe(company_facts)
    report_ends = all_ends[-num_quarters:] if num_quarters else all_ends

    # eg: all_ends = ["2021-12-31", "2022-03-31", "2022-06-30", ..., "2024-09-30"]
    # num_quarters=8 get recent 8
    # report_ends = ["2022-12-31", "2023-03-31", ..., "2024-09-30"]


    # Step 5: Build PeriodInputs for each period
    periods: list[PeriodInputs] = []
    for end in report_ends:
        # 5a: Instant concepts (balance sheet items at this date)
        instant = {key: _resolve_instant(company_facts, CONCEPTS[key], end) for key in INSTANT_CONCEPTS}

        # 5b: Quarterly duration concepts (income/cash flow for this single quarter)
        quarterly = {key: quarterly_series[key].get(end, ResolvedValue(None, [], [], "none"))
                     for key in DURATION_CONCEPTS}
        # 5c: TTM duration concepts (sum of last 4 quarters)
        ttm = {key: ttm_series[key].get(end, ResolvedValue(None, [], [], "none"))
               for key in DURATION_CONCEPTS}

        # 5d: Which filing provided this period's data?
        form_type, filing_date = _period_filing(company_facts, end)
        periods.append(PeriodInputs(period_end=end, form_type=form_type, filing_date=filing_date,
                                    instant=instant, quarterly=quarterly, ttm=ttm))

    '''PeriodInputs(
        period_end="2023-09-30",           # when
        form_type="10-Q",                  # which file
        filing_date="2023-11-09",          # when to submit
        instant={
            "cash": ResolvedValue(value=29.9B),
            "long_term_debt": ResolvedValue(value=95.1B),
            "assets": ResolvedValue(value=352B),
            # ... all instant def
        },
        quarterly={
            "operating_income": ResolvedValue(value=22.3B),  # singal seasonal
            "revenue": ResolvedValue(value=89.5B),
            # ... all period def (single seasonal)
        },
        ttm={
            "operating_income": ResolvedValue(value=100.2B),  # past 4 season
            "dep_amort": ResolvedValue(value=11.5B),
            # ... all period def
        }
        )'''

    return ExtractionResult(metadata=meta, periods=periods)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "0000320193"  # default: Apple
    result = extract(target)
    if result is None:
        print(f"Extraction failed or CIK {target} did not validate.")
        sys.exit(1)

    m = result.metadata
    print(f"{m.name} (CIK {m.cik}) — SIC {m.sic_code} — FYE {m.fiscal_year_end} — tickers {m.tickers}")
    print(f"{len(result.periods)} periods extracted\n")
    for p in result.periods:
        ld = p.instant["long_term_debt"]
        cash = p.instant["cash"]
        oi = p.quarterly["operating_income"]
        da_ttm = p.ttm["dep_amort"]
        print(f"{p.period_end}: LTdebt={ld.value} ({','.join(ld.tags) or '-'})  "
              f"cash={cash.value}  OI_q={oi.value} [{oi.path}]  D&A_ttm={da_ttm.value}")
