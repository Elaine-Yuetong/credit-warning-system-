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
    "interest_expense": Concept(
        "interest_expense", "duration", "first",
        ("InterestExpense", "InterestAndDebtExpense"),
        flag_tags={"InterestAndDebtExpense":
                   "InterestExpense absent — InterestAndDebtExpense used; may include debt issuance cost amortization"},
    ),
    # Net-interest detection only (§ coverage): presence triggers a null + flag, never used as value.
    "interest_net": Concept(
        "interest_net", "duration", "first", ("InterestIncomeExpenseNet",),
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
        cached = self._read_cache(cache_name, ttl_s)
        if cached is not None:
            return cached

        for attempt in range(MAX_RETRIES + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_S)
            except (requests.Timeout, requests.ConnectionError):
                if not self._backoff(attempt):
                    return None
                continue

            if resp.status_code == 404:
                return None  # do not retry — resource does not exist
            if resp.status_code in (429, 403) or resp.status_code >= 500:
                if not self._backoff(attempt):
                    return None
                continue
            if not resp.ok:
                return None

            try:
                data = resp.json()
            except json.JSONDecodeError:
                return None
            self._write_cache(cache_name, data)
            return data

        return None

    @staticmethod
    def _backoff(attempt: int) -> bool:
        """Sleep with exponential backoff + jitter. Returns False once retries exhausted."""
        if attempt >= MAX_RETRIES:
            return False
        wait = min(BACKOFF_BASE_S * (2 ** attempt) + random.random(), BACKOFF_MAX_S)
        time.sleep(wait)
        return True


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
    cik10 = pad_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    data = client.get_json(url, cache_name=f"{cik10}_submissions.json")
    if not data:
        return None
    name = data.get("name")
    if not name:
        return None  # step 2: no valid company name

    fye_raw = data.get("fiscalYearEnd")  # "MMDD"
    fiscal_year_end = None
    if isinstance(fye_raw, str) and len(fye_raw) == 4 and fye_raw.isdigit():
        fiscal_year_end = f"{fye_raw[:2]}-{fye_raw[2:]}"

    forms = (data.get("filings", {}).get("recent", {}).get("form")) or []
    has_10k = any(str(f).startswith("10-K") for f in forms)  # step 3

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
    accn: Optional[str]
    form: Optional[str]
    filed: Optional[str]
    start: Optional[str] = None   # present for duration facts
    span_days: Optional[int] = None
    span_bucket: Optional[str] = None  # Q | H1 | 9M | FY


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


def _ttm(series: dict[str, ResolvedValue], end_dates: list[str]) -> dict[str, ResolvedValue]:
    """Trailing-twelve-month sum at each end date = that quarter + 3 prior quarters (§6.4).

    `end_dates` must be the chronologically sorted quarterly end dates of the series.
    Returns {end_date: ResolvedValue} where value is None (with a flag) if any of the
    four trailing quarters is missing.
    """
    out: dict[str, ResolvedValue] = {}
    for i, end in enumerate(end_dates):
        window = end_dates[max(0, i - 3): i + 1]
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
    metadata: IssuerMetadata
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


def extract(cik: str, client: Optional[SecClient] = None, num_quarters: int = 8) -> Optional[ExtractionResult]:
    """Full extraction for one CIK.

    Returns per-period input dictionaries for the most recent `num_quarters` balance-sheet
    period-ends, each carrying instant values, derived single-quarter duration values, and
    TTM duration values. Returns None if the CIK fails onboarding validation or companyfacts
    is unavailable.
    """
    client = client or SecClient()
    meta = fetch_issuer_metadata(client, cik)
    if meta is None or not meta.has_10k:
        return None

    company_facts = fetch_company_facts(client, cik)
    if not company_facts:
        return None

    # Build the full quarterly duration + TTM series once (needs deep history for TTM).
    quarterly_series: dict[str, dict[str, ResolvedValue]] = {}
    ttm_series: dict[str, dict[str, ResolvedValue]] = {}
    for key in DURATION_CONCEPTS:
        series = _derive_quarterly_series(company_facts, CONCEPTS[key])
        quarterly_series[key] = series
        ttm_series[key] = _ttm(series, sorted(series.keys()))

    # The periods we report on: most recent N balance-sheet period-ends.
    all_ends = _quarter_end_universe(company_facts)
    report_ends = all_ends[-num_quarters:] if num_quarters else all_ends

    periods: list[PeriodInputs] = []
    for end in report_ends:
        instant = {key: _resolve_instant(company_facts, CONCEPTS[key], end) for key in INSTANT_CONCEPTS}
        quarterly = {key: quarterly_series[key].get(end, ResolvedValue(None, [], [], "none"))
                     for key in DURATION_CONCEPTS}
        ttm = {key: ttm_series[key].get(end, ResolvedValue(None, [], [], "none"))
               for key in DURATION_CONCEPTS}
        form_type, filing_date = _period_filing(company_facts, end)
        periods.append(PeriodInputs(period_end=end, form_type=form_type, filing_date=filing_date,
                                    instant=instant, quarterly=quarterly, ttm=ttm))

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
