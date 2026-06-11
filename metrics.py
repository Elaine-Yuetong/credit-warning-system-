"""
metrics.py — Formula 1 (deterministic, no-LLM) metric computation for Phase 2.

Consumes extractor.ExtractionResult and produces one MetricResult per metric per period
using the canonical metric_name strings from spec/SECTION_6.md §6.3:

  leverage              Net Debt / TTM EBITDA            (LEVERAGE.md F1)
  interest_coverage     TTM EBITDA / TTM Interest        (INTEREST_COVERAGE.md F1, EBITDA-based)
  free_cash_flow        quarterly OCF - Capex            (FREE_CASH_FLOW.md F1, millions USD)
  fcf_margin            quarterly FCF / Revenue          (FREE_CASH_FLOW.md F1)
  ocf_ebitda_conversion quarterly OCF / quarterly EBITDA (FREE_CASH_FLOW.md F1)
  current_ratio         Current Assets / Current Liab.   (LIQUIDITY.md Output 1A)
  quick_ratio           (CA - Inv - Prepaid) / CL        (LIQUIDITY.md Output 1B)

Rules enforced here (shared design principles across the metric files):
  - Never substitute zero for a missing input; missing -> value None + flag.
  - Debt: 3-component sum with the LEVERAGE.md 4-level fallback hierarchy + cross-checks.
  - Interest coverage: explicit net-interest netting detection — if InterestIncomeExpenseNet
    is the only interest tag available, value is None + flag (no silent net substitution).
  - EBIT coverage (the 1.0x floor) and EBITDA value are stashed in `extra` for thresholds.py.
  - Financial-institution suppression (SIC 6000-6499): leverage / interest_coverage /
    current_ratio / quick_ratio suppressed to null + flag; FCF computed with an FI flag.

Threshold/alert assignment is NOT done here — see thresholds.py. This module only
produces audited numeric values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from extractor import ExtractionResult, PeriodInputs, ResolvedValue

FORMULA_VERSION = "F1"

# Cash tag whose value bundles restricted cash and must have restricted cash subtracted.
_RESTRICTED_INCLUSIVE_CASH_TAG = "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"

SUPPRESSED_FOR_FINANCIAL = {"leverage", "interest_coverage", "current_ratio", "quick_ratio"}

FINANCIAL_SUPPRESSION_FLAG = (
    "financial institution — standard ratio not applicable; regulatory capital framework "
    "governs; manual assessment required"
)
FINANCIAL_FCF_FLAG = (
    "financial institution — FCF interpretation differs; capex excludes loan originations "
    "and investment portfolio activity"
)


@dataclass
class MetricResult:
    metric_name: str
    period_end: str
    form_type: Optional[str]
    filing_date: Optional[str]
    value: Optional[float]
    value_unit: str                       # ratio | percent | millions_usd
    formula_version: str = FORMULA_VERSION
    alert_level: Optional[str] = None     # None | Watch | Flag | Stress | Critical (set by thresholds.py)
    flags: list[str] = field(default_factory=list)
    source_tags: dict[str, str] = field(default_factory=dict)
    audit_log: dict = field(default_factory=dict)
    extraction_path: str = "primary"      # primary | derived_quarterly | ttm | none | derived
    suppressed: bool = False
    no_alert: bool = False                # computed-with-flag but thresholds N/A (financials)
    extra: dict = field(default_factory=dict)  # alert inputs (ebitda, ebit_coverage, ...)


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------

def _v(rv: Optional[ResolvedValue]) -> Optional[float]:
    return rv.value if rv is not None else None


def _tags(rv: Optional[ResolvedValue]) -> list[str]:
    return list(rv.tags) if rv is not None else []


def _flags(rv: Optional[ResolvedValue]) -> list[str]:
    return list(rv.flags) if rv is not None else []


def _issuer_has_concept(result: ExtractionResult, concept: str) -> bool:
    """True if any reported period carries a non-null quarterly value for a duration concept."""
    for p in result.periods:
        rv = p.quarterly.get(concept)
        if rv is not None and rv.value is not None:
            return True
    return False


# --------------------------------------------------------------------------------------
# Debt extraction (LEVERAGE.md fallback hierarchy + cross-checks)
# --------------------------------------------------------------------------------------

def _total_debt(p: PeriodInputs) -> tuple[Optional[float], dict, list[str], str]:
    """Return (total_debt, source_tags, flags, level). Never zero-substitutes.

    Level 1: Component A (short-term, summed) + B (current LTD) + C (LT non-current).
             C non-null is the minimum bar.
    Level 2: aggregated debt tag, used if Level 1 fails (C null) or if it exceeds a
             partial Level-1 result.
    Level 4: failure -> None.
    (Level 3 — derive from total liabilities minus non-debt — requires non-debt line
     items not extracted in Phase 2; treated as unavailable, falls through to failure.)
    """
    a = p.instant.get("short_term_debt")
    b = p.instant.get("current_ltd")
    c = p.instant.get("long_term_debt")
    dc = p.instant.get("debt_current")
    agg = p.instant.get("debt_aggregate")

    flags: list[str] = []
    src: dict[str, str] = {}

    a_val, b_val, c_val = _v(a), _v(b), _v(c)

    # Component B fallback: if no LongTermDebtCurrent-style tag, use DebtCurrent.
    if b_val is None and _v(dc) is not None:
        b_val = _v(dc)
        flags.append("current LTD proxied by DebtCurrent — verify no overlap with short-term debt")
        if dc is not None:
            src["current_ltd"] = ",".join(_tags(dc))
    elif b is not None and b.tags:
        src["current_ltd"] = ",".join(b.tags)

    # Level 1 requires Component C.
    if c_val is not None:
        # ── ADDED: LongTermDebt double-count protection ───────────────────────
        # LongTermDebt (unlike LongTermDebtNoncurrent) is ambiguous in XBRL —
        # many companies use it to mean total long-term debt including the current
        # portion already captured in Component B. Subtract b_val to avoid
        # double-counting. Only applies when the exact tag "LongTermDebt" was used;
        # does NOT apply to LongTermDebtNoncurrent or
        # LongTermDebtAndCapitalLeaseObligationsNoncurrent.
        c_tags = c.tags if c is not None else []
        if "LongTermDebt" in c_tags:
            b_subtract = b_val if b_val is not None else 0.0
            if b_subtract > 0:
                original_c = c_val
                c_val = c_val - b_subtract
                flags.append(
                    f"LongTermDebt tag used (raw={original_c:,.0f}) — current LTD "
                    f"({b_subtract:,.0f}) subtracted to avoid double-count; "
                    f"adjusted non-current LT debt = {c_val:,.0f}"
                )
        # ── END ADDED ─────────────────────────────────────────────────────────
        total = (a_val or 0.0) + (b_val or 0.0) + c_val
        if a is not None and a.tags:
            src["short_term_debt"] = ",".join(a.tags)
        if c is not None:
            src["long_term_debt"] = ",".join(c.tags)
        flags += _flags(a) + _flags(b) + _flags(c)
        if a_val is None:
            flags.append("short-term debt components missing — Total Debt may be understated")

        # Level-2 override check: if an aggregated tag exceeds the disaggregated sum, prefer it.
        agg_val = _v(agg)
        if agg_val is not None and agg_val > total:
            flags += _flags(agg) + ["aggregated debt tag exceeded component sum — Level 2 figure used"]
            if agg is not None:
                src = {"debt_aggregate": ",".join(agg.tags)}
            return agg_val, src, flags, "2"
        return total, src, flags, "1"

    # Level 2: aggregated tag alone.
    if _v(agg) is not None:
        flags += _flags(agg) + ["Component C (long-term debt) absent — aggregated debt tag used (Level 2)"]
        if agg is not None:
            src["debt_aggregate"] = ",".join(agg.tags)
        return _v(agg), src, flags, "2"

    # Level 4: failure.
    return None, src, ["debt extraction failed — no long-term or aggregated debt tag (Level 4)"], "4"


def _net_debt(p: PeriodInputs) -> tuple[Optional[float], Optional[float], dict, list[str], str]:
    """Net Debt = Total Debt - Unrestricted Cash. Returns (net_debt, total_debt, src, flags, level)."""
    total, src, flags, level = _total_debt(p)
    if total is None:
        return None, None, src, flags, level

    # Cross-checks on Total Debt (LEVERAGE.md).
    if total < 0:
        return None, None, src, flags + ["negative Total Debt — likely tagging error; ratio nulled"], level
    assets = _v(p.instant.get("assets"))
    if assets and total < 0.01 * assets:
        flags.append("Total Debt < 1% of assets — verify extraction completeness")

    cash_rv = p.instant.get("cash")
    cash = _v(cash_rv)
    if cash is None:
        flags.append("unrestricted cash not found — Net Debt assumes zero cash; flagged")
        net = total
    else:
        net = total - cash
        if cash_rv is not None:
            src["cash"] = ",".join(cash_rv.tags)
            flags += _flags(cash_rv)
            # If the cash tag bundles restricted cash, subtract it where available.
            if _RESTRICTED_INCLUSIVE_CASH_TAG in cash_rv.tags:
                rc = _v(p.instant.get("restricted_cash"))
                if rc is not None:
                    net += rc  # add back restricted (it was included in cash, must be removed)
                    flags.append("restricted cash subtracted from cash figure")
    return net, total, src, flags, level


def _ebitda_ttm(p: PeriodInputs) -> tuple[Optional[float], dict, list[str]]:
    """TTM EBITDA = TTM OperatingIncome + TTM D&A. None if either input is null."""
    oi = p.ttm.get("operating_income")
    da = p.ttm.get("dep_amort")
    src: dict[str, str] = {}
    flags: list[str] = []
    # ── D&A fallback: Depreciation + AmortizationOfIntangibleAssets ──────────
    if _v(da) is None:
        dep = p.ttm.get("depreciation_only")
        amort = p.ttm.get("amortization_intangibles")
        dep_val = _v(dep)
        amort_val = _v(amort)
        if dep_val is not None:
            derived_da = dep_val + (amort_val or 0.0)
            derived_tags = _tags(dep) + (_tags(amort) if amort_val is not None else [])
            derived_flags = [
                "D&A derived from Depreciation + AmortizationOfIntangibleAssets — may be partial"
            ]
            if amort_val is None:
                derived_flags.append(
                    "AmortizationOfIntangibleAssets absent — D&A is depreciation-only; EBITDA may be understated"
                )
            # Wrap as a ResolvedValue-like object for consistent downstream handling
            from extractor import ResolvedValue
            da = ResolvedValue(
                value=derived_da,
                tags=derived_tags,
                flags=derived_flags,
                path="derived",
            )
    # ── END D&A fallback ──────────────────────────────────────────────────────
    if _v(oi) is None or _v(da) is None:
        missing = "operating income" if _v(oi) is None else "D&A"
        return None, src, [f"TTM EBITDA null — {missing} unavailable (insufficient quarters or tag absent)"]
    if oi is not None:
        src["operating_income"] = ",".join(oi.tags)
        flags += _flags(oi)
    if da is not None:
        src["dep_amort"] = ",".join(da.tags)
        flags += _flags(da)
    return _v(oi) + _v(da), src, flags


def _ebitda_quarterly(p: PeriodInputs) -> Optional[float]:
    """Single-quarter EBITDA = Operating Income + D&A.

    D&A fallback (spec LEVERAGE.md line 201 Fallback 2): if dep_amort quarterly is null,
    attempt to derive D&A from Depreciation + AmortizationOfIntangibleAssets.
    """
    oi = _v(p.quarterly.get("operating_income"))

    da_rv = p.quarterly.get("dep_amort")
    da = _v(da_rv)

    # ── D&A fallback: Depreciation + AmortizationOfIntangibleAssets ──────────
    if da is None:
        dep_val = _v(p.quarterly.get("depreciation_only"))
        amort_val = _v(p.quarterly.get("amortization_intangibles"))
        if dep_val is not None:
            da = dep_val + (amort_val or 0.0)
    # ── END D&A fallback ──────────────────────────────────────────────────────

    if oi is None or da is None:
        return None
    return oi + da


# --------------------------------------------------------------------------------------
# Per-metric computation
# --------------------------------------------------------------------------------------

def _leverage(p: PeriodInputs) -> MetricResult:
    net, total, src, flags, level = _net_debt(p)
    ebitda, ebsrc, ebflags = _ebitda_ttm(p)
    src.update(ebsrc)
    flags += ebflags
    base = dict(metric_name="leverage", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    audit = {"net_debt": net, "total_debt": total, "ttm_ebitda": ebitda, "debt_level": level}
    extra = {"ebitda": ebitda}

    if net is None or ebitda is None:
        return MetricResult(**base, value=None, flags=flags, audit_log=audit, extra=extra,
                            extraction_path="none")
    if ebitda <= 0:
        flags.append("EBITDA <= 0 — leverage ratio not meaningful; critical stress signal")
        return MetricResult(**base, value=None, flags=flags, audit_log=audit, extra=extra,
                            extraction_path="ttm")
    value = net / ebitda
    audit["leverage"] = value
    return MetricResult(**base, value=value, flags=flags, audit_log=audit, extra=extra,
                        extraction_path="ttm")



# ── LOCATION: metrics.py, inside _interest_coverage(), lines 258–262 ────────
#
# CURRENT CODE (Phase 2 — correct as-is):
#
#     # Explicit net-interest netting detection (no silent net substitution).
#     if not has_interest_tag and has_net_tag:
#         flags.append("net interest only — LLM required per spec")
#         return MetricResult(**base, value=None, flags=flags,
#                             audit_log={"reason": "net_interest_only"}, extraction_path="none")
#
# REPLACE the comment block above with this comment-enhanced version:
# ─────────────────────────────────────────────────────────────────────────────
 
    # Explicit net-interest netting detection (no silent net substitution).
    # Phase 2: when InterestExpense tag is absent but InterestIncomeExpenseNet is
    # present, we cannot isolate gross interest expense from structured data alone.
    # Return null + flag immediately. This is correct Phase 2 behaviour.
    #
    # ── PHASE 3 TODO: net interest reconstruction ─────────────────────────────
    # When this condition fires, Phase 3 should attempt reconstruction before
    # returning null. The spec defines this in INTEREST_COVERAGE.md →
    # Section "Extraction Fallback Logic" → Input 2 (Interest Expense), Steps 3–4:
    #
    # Step 3 — If InterestIncomeExpenseNet is negative (net expense):
    #   Attempt reconstruction:
    #     gross_interest = abs(InterestIncomeExpenseNet)
    #                    + (InterestIncomeOperating or InvestmentIncomeInterest or 0)
    #   Flag: "interest expense reconstructed from net interest plus interest income;
    #          gross figure approximate — verify against interest footnote"
    #   Proceed with reconstructed gross_interest if reconstruction succeeds.
    #
    # Step 4 — If InterestIncomeExpenseNet is positive (net income > expense):
    #   Company earns more interest than it pays. Coverage ratio is not meaningful.
    #   Return null + flag: "net interest income (not expense) — coverage not applicable"
    #
    # Step 5 — If reconstruction fails (interest income tags also absent):
    #   Return null as Phase 2 does now.
    #   Flag: "net interest only — gross reconstruction failed; LLM required per spec"
    #
    # New concepts needed in extractor.py for Phase 3:
    #   "interest_income_operating": Concept(..., ("InterestIncomeOperating",))
    #   "interest_income_investment": Concept(..., ("InvestmentIncomeInterest",))
    # Both are duration concepts. Fetch alongside interest_net in the CONCEPTS dict.
    #
    # Implied rate sanity check (also Phase 3, INTEREST_COVERAGE.md §Extraction):
    #   After any interest expense is resolved (gross or reconstructed):
    #   implied_rate = gross_interest / total_debt
    #   If implied_rate < 0.01 (< 1%) or > 0.20 (> 20%) for non-distressed issuers:
    #   Flag: "implied interest rate {implied_rate:.1%} appears anomalous —
    #          verify interest expense extraction is gross and covers all obligations"
    #   This catches silent netting errors and missing debt components simultaneously.
    # ── END PHASE 3 TODO ──────────────────────────────────────────────────────
    # if not has_interest-tag and has net_tag this line before

def _interest_coverage(p: PeriodInputs, has_interest_tag: bool, has_net_tag: bool) -> MetricResult:
    ebitda, ebsrc, ebflags = _ebitda_ttm(p)
    oi_ttm = _v(p.ttm.get("operating_income"))
    int_rv = p.ttm.get("interest_expense")
    interest = _v(int_rv)
    src: dict[str, str] = dict(ebsrc)
    flags: list[str] = list(ebflags)
    base = dict(metric_name="interest_coverage", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    # Net-interest reconstruction (INTEREST_COVERAGE.md Input 2, Steps 3-4). Fires ONLY when the
    # issuer has neither InterestExpense nor InterestAndDebtExpense tagged but does tag
    # InterestIncomeExpenseNet — never for companies with a gross interest tag.
    if not has_interest_tag and has_net_tag:
        net_rv = p.ttm.get("interest_net")
        net_interest = _v(net_rv)
        if net_interest is None:
            flags.append("net interest only — insufficient quarters for TTM reconstruction")
            return MetricResult(**base, value=None, flags=flags,
                                audit_log={"reason": "net_interest_no_ttm"}, extraction_path="none")
        if net_interest < 0:
            # Net interest EXPENSE presented net -> gross up by adding back BOTH interest income
            # tags (spec Step 3 sums them; abs(net) + operating + investment).
            inc_op_rv = p.ttm.get("interest_income_operating")
            inc_inv_rv = p.ttm.get("interest_income_investment")
            inc_op, inc_inv = _v(inc_op_rv), _v(inc_inv_rv)
            gross = abs(net_interest) + (inc_op or 0.0) + (inc_inv or 0.0)
            if gross > 0:
                interest = gross  # use reconstructed gross; fall through to normal computation
                src["interest_net"] = ",".join(net_rv.tags) if net_rv else ""
                if inc_op is not None and inc_op_rv:
                    src["interest_income_operating"] = ",".join(inc_op_rv.tags)
                if inc_inv is not None and inc_inv_rv:
                    src["interest_income_investment"] = ",".join(inc_inv_rv.tags)
                flags.append("interest expense reconstructed from InterestIncomeExpenseNet + "
                             "interest income tags; approximate — verify against interest footnote")
            else:
                flags.append("net interest only — reconstruction failed; LLM required")
                return MetricResult(**base, value=None, flags=flags,
                                    audit_log={"reason": "reconstruction_failed",
                                               "net_interest": net_interest}, extraction_path="none")
        elif net_interest > 0:
            flags.append("net interest income (not expense) — coverage ratio not applicable")
            return MetricResult(**base, value=None, flags=flags,
                                audit_log={"net_interest": net_interest}, extraction_path="none")
        else:  # net_interest == 0
            flags.append("net interest zero — coverage ratio not applicable")
            return MetricResult(**base, value=None, flags=flags,
                                audit_log={"net_interest": 0}, extraction_path="none")

    if interest is None:
        flags.append("interest expense unavailable (tag absent or insufficient quarters for TTM)")
        return MetricResult(**base, value=None, flags=flags,
                            audit_log={"ttm_ebitda": ebitda}, extraction_path="none")
    if int_rv is not None:
        src["interest_expense"] = ",".join(int_rv.tags)
        flags += _flags(int_rv)

    gross_interest = abs(interest)
    if gross_interest == 0:
        total_debt = _net_debt(p)[1]
        flags.append("interest expense zero — ratio undefined; verify company carries no debt"
                     if not total_debt else "interest expense zero but debt exists — possible netting/tag error")
        return MetricResult(**base, value=None, flags=flags,
                            audit_log={"interest_expense": 0}, extraction_path="none")

    ebit_coverage = (oi_ttm / gross_interest) if oi_ttm is not None else None
    extra = {"ebit_coverage": ebit_coverage, "ebitda": ebitda, "ttm_ebit": oi_ttm}
    audit = {"ttm_ebitda": ebitda, "ttm_interest_expense": gross_interest,
             "ebit_coverage": ebit_coverage}

    if ebitda is None:
        flags.append("TTM EBITDA null — EBITDA coverage not computed")
        return MetricResult(**base, value=None, flags=flags, audit_log=audit, extra=extra,
                            extraction_path="none")

    value = ebitda / gross_interest  # EBITDA coverage (primary, matches S&P tables)
    audit["ebitda_coverage"] = value
    return MetricResult(**base, value=value, flags=flags, audit_log=audit, extra=extra,
                        extraction_path="ttm")


def _free_cash_flow(p: PeriodInputs, institution_type: str) -> list[MetricResult]:
    """Compute free_cash_flow (millions), fcf_margin (%), ocf_ebitda_conversion (ratio)."""
    ocf_rv = p.quarterly.get("operating_cash_flow")
    capex_rv = p.quarterly.get("capex")
    rev_rv = p.quarterly.get("revenue")
    ocf, capex, revenue = _v(ocf_rv), _v(capex_rv), _v(rev_rv)

    fi_flag = [FINANCIAL_FCF_FLAG] if institution_type == "financial" else []

    src: dict[str, str] = {}
    flags: list[str] = list(fi_flag)
    if ocf_rv is not None and ocf_rv.tags:
        src["operating_cash_flow"] = ",".join(ocf_rv.tags)
        flags += _flags(ocf_rv)
    base = dict(period_end=p.period_end, form_type=p.form_type, filing_date=p.filing_date)

    # --- free_cash_flow (absolute, millions USD) ---
    fcf: Optional[float] = None
    if ocf is None:
        fcf_flags = flags + ["OCF unavailable — FCF null"]
        fcf_res = MetricResult(metric_name="free_cash_flow", value=None, value_unit="millions_usd",
                               flags=fcf_flags, source_tags=src, audit_log={}, extraction_path="none", **base)
    elif capex is None:
        # Partial: OCF known, capex missing — never treat missing capex as zero.
        fcf_flags = flags + ["capex missing — FCF null; OCF reported as partial signal"]
        fcf_res = MetricResult(metric_name="free_cash_flow", value=None, value_unit="millions_usd",
                               flags=fcf_flags, source_tags=src,
                               audit_log={"partial_ocf_millions": ocf / 1e6}, extraction_path="none",
                               extra={"partial_ocf": ocf}, **base)
    else:
        if capex_rv is not None:
            src["capex"] = ",".join(capex_rv.tags)
            flags += _flags(capex_rv)
        if capex < 0:
            flags.append("capex tag returned negative value — possible sign convention error")
        fcf = ocf - abs(capex)
        fcf_res = MetricResult(metric_name="free_cash_flow", value=fcf / 1e6, value_unit="millions_usd",
                               flags=flags, source_tags=dict(src),
                               audit_log={"ocf": ocf, "capex": abs(capex), "fcf": fcf},
                               extraction_path=ocf_rv.path if ocf_rv else "primary", extra={"fcf": fcf}, **base)

    results = [fcf_res]

    # --- fcf_margin (%) ---
    margin_flags = list(fi_flag)
    if fcf is None or revenue is None:
        margin_val = None
        margin_flags.append("FCF or revenue unavailable — margin null")
        margin_path = "none"
    elif revenue == 0:
        margin_val = None
        margin_flags.append("zero revenue — FCF margin undefined")
        margin_path = "none"
    else:
        margin_val = fcf / revenue * 100.0
        margin_path = "derived"
    msrc = dict(src)
    if rev_rv is not None and rev_rv.tags:
        msrc["revenue"] = ",".join(rev_rv.tags)
    results.append(MetricResult(metric_name="fcf_margin", value=margin_val, value_unit="percent",
                                flags=margin_flags, source_tags=msrc,
                                audit_log={"fcf": fcf, "revenue": revenue}, extraction_path=margin_path, **base))

    # --- ocf_ebitda_conversion (ratio) ---
    # Suppressed for financial institutions — depends on EBITDA, which is not meaningful
    # for deposit-funded institutions (§6.2 suppression table).
    if institution_type == "financial":
        results.append(MetricResult(metric_name="ocf_ebitda_conversion", value=None,
                                    value_unit="ratio", flags=[FINANCIAL_SUPPRESSION_FLAG],
                                    source_tags={}, audit_log={}, extraction_path="none",
                                    suppressed=True, **base))
        return results

    conv_flags = list(fi_flag)
    ebitda_q = _ebitda_quarterly(p)
    if ocf is None or ebitda_q is None:
        conv_val = None
        conv_flags.append("OCF or quarterly EBITDA unavailable — conversion null")
        conv_path = "none"
    elif ebitda_q <= 0:
        conv_val = None
        conv_flags.append("EBITDA <= 0 — OCF/EBITDA conversion not meaningful")
        conv_path = "none"
    else:
        conv_val = ocf / ebitda_q
        conv_path = "derived"
    results.append(MetricResult(metric_name="ocf_ebitda_conversion", value=conv_val, value_unit="ratio",
                                flags=conv_flags, source_tags=dict(src),
                                audit_log={"ocf": ocf, "quarterly_ebitda": ebitda_q},
                                extraction_path=conv_path, **base))
    return results


def _current_ratio(p: PeriodInputs) -> MetricResult:
    ca_rv = p.instant.get("current_assets")
    cl_rv = p.instant.get("current_liabilities")
    ca, cl = _v(ca_rv), _v(cl_rv)
    src: dict[str, str] = {}
    flags: list[str] = []
    if ca_rv is not None and ca_rv.tags:
        src["current_assets"] = ",".join(ca_rv.tags)
    if cl_rv is not None and cl_rv.tags:
        src["current_liabilities"] = ",".join(cl_rv.tags)
    base = dict(metric_name="current_ratio", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    if ca is None:
        return MetricResult(**base, value=None, flags=flags + ["current assets unavailable"], extraction_path="none")
    if cl is None:
        return MetricResult(**base, value=None, flags=flags + ["current liabilities unavailable"], extraction_path="none")
    if cl == 0:
        return MetricResult(**base, value=None, flags=flags + ["zero current liabilities — extraction failure"], extraction_path="none")
    assets = _v(p.instant.get("assets"))
    if assets and cl < 0.01 * assets:
        flags.append("current liabilities < 1% of assets — verify extraction completeness")
    return MetricResult(**base, value=ca / cl, flags=flags,
                        audit_log={"current_assets": ca, "current_liabilities": cl})


def _quick_ratio(p: PeriodInputs) -> MetricResult:
    ca_rv = p.instant.get("current_assets")
    cl_rv = p.instant.get("current_liabilities")
    inv_rv = p.instant.get("inventory")
    pre_rv = p.instant.get("prepaid")
    ca, cl, inv, pre = _v(ca_rv), _v(cl_rv), _v(inv_rv), _v(pre_rv)
    src: dict[str, str] = {}
    flags: list[str] = []
    for name, rv in (("current_assets", ca_rv), ("current_liabilities", cl_rv),
                     ("inventory", inv_rv), ("prepaid", pre_rv)):
        if rv is not None and rv.tags:
            src[name] = ",".join(rv.tags)
            flags += _flags(rv)
    base = dict(metric_name="quick_ratio", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    if ca is None:
        return MetricResult(**base, value=None, flags=flags + ["current assets unavailable"], extraction_path="none")
    if cl is None or cl == 0:
        return MetricResult(**base, value=None, flags=flags + ["current liabilities unavailable or zero"], extraction_path="none")
    # Inventory: None means a genuine extraction failure for an inventory business -> null.
    # The extractor leaves inventory absent when the tag is missing; for the quick ratio we
    # treat missing inventory as 0 only when prepaid logic allows. Here: missing -> 0 with flag.
    if inv is None:
        inv = 0.0
        flags.append("inventory not found — treated as zero for quick ratio")
    if pre is None:
        pre = 0.0  # prepaid is the one acceptable zero-substitution (LIQUIDITY.md Input 4)
    value = (ca - inv - pre) / cl
    return MetricResult(**base, value=value, flags=flags,
                        audit_log={"current_assets": ca, "inventory": inv, "prepaid": pre,
                                   "current_liabilities": cl})


# --------------------------------------------------------------------------------------
# Group A / B / C metrics
# --------------------------------------------------------------------------------------

def _debt_to_equity(p: PeriodInputs) -> MetricResult:
    total, _src, dflags, level = _total_debt(p)
    eq_rv = p.instant.get("equity")
    equity = _v(eq_rv)
    src: dict[str, str] = dict(_src)
    flags = list(dflags)
    if eq_rv is not None and eq_rv.tags:
        src["equity"] = ",".join(eq_rv.tags)
    base = dict(metric_name="debt_to_equity", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    if total is None or equity is None:
        return MetricResult(**base, value=None, flags=flags + (["equity unavailable"] if equity is None else []),
                            extraction_path="none", extra={"equity": equity})
    if equity < 0:
        flags.append("NEGATIVE EQUITY — book value insolvent; ratio not meaningful; condition is the signal")
        return MetricResult(**base, value=None, flags=flags, extra={"equity": equity, "negative_equity": True},
                            audit_log={"total_debt": total, "equity": equity})
    if equity == 0:
        return MetricResult(**base, value=None, flags=flags + ["zero equity — D/E undefined"],
                            extra={"equity": 0}, extraction_path="none")
    return MetricResult(**base, value=total / equity, flags=flags,
                        audit_log={"total_debt": total, "equity": equity}, extra={"equity": equity})


def _asset_coverage(p: PeriodInputs) -> list[MetricResult]:
    total, _src, dflags, _level = _total_debt(p)
    assets = _v(p.instant.get("assets"))
    goodwill = _v(p.instant.get("goodwill")) or 0.0
    intangibles = _v(p.instant.get("intangibles")) or 0.0
    dta = _v(p.instant.get("deferred_tax_assets"))
    dta = dta if (dta is not None and dta > 0) else 0.0  # ignore net DTL
    base = dict(period_end=p.period_end, form_type=p.form_type, filing_date=p.filing_date,
                value_unit="ratio")

    src = {"assets": ",".join(p.instant["assets"].tags)} if _v(p.instant.get("assets")) is not None else {}

    # Total asset coverage.
    if assets is None or total is None or total == 0:
        ac = MetricResult(metric_name="asset_coverage", value=None, flags=dflags + ["assets or total debt unavailable"],
                          source_tags=src, extraction_path="none", **base)
    else:
        ac = MetricResult(metric_name="asset_coverage", value=assets / total, flags=list(dflags),
                          source_tags=src, audit_log={"assets": assets, "total_debt": total}, **base)

    # Tangible asset coverage.
    tang_flags = list(dflags)
    if assets is None or total is None or total == 0:
        tac = MetricResult(metric_name="tangible_asset_coverage", value=None,
                           flags=tang_flags + ["assets or total debt unavailable"],
                           source_tags=src, extraction_path="none", **base)
    else:
        tangible = assets - goodwill - intangibles - dta
        tac = MetricResult(metric_name="tangible_asset_coverage", value=tangible / total, flags=tang_flags,
                           source_tags=src,
                           audit_log={"tangible_assets": tangible, "goodwill": goodwill,
                                      "intangibles": intangibles, "dta": dta, "total_debt": total}, **base)
    return [ac, tac]


# Liquidation recovery-rate ranges (low, mid) per ASSET_COVERAGE.md Formula 2. mid = midpoint
# of the spec range; conservative scenario uses low, base scenario uses mid. Do NOT alter.
_HAIRCUTS = {
    "cash":                        (1.00, 1.00),    # 100%
    "sti":                         (1.00, 1.00),    # 100%
    "ar":                          (0.70, 0.775),   # 70%-85%
    "inventory":                   (0.40, 0.50),    # 40%-60%
    "ppe_real_estate":             (0.60, 0.70),    # 60%-80%
    "ppe_equipment":               (0.30, 0.40),    # 30%-50%
    "ppe_specialised":             (0.10, 0.20),    # 10%-30%
    "ppe_leasehold":               (0.00, 0.05),    # 0%-10%
    "ppe_fallback":                (0.30, 0.45),    # 30%-60% (composition unknown)
    "goodwill":                    (0.00, 0.00),    # 0%
    "intangibles_patents":         (0.10, 0.15),    # 10%-20%
    "intangibles_customer_lists":  (0.00, 0.05),    # 0%-10%
    "intangibles_software":        (0.00, 0.025),   # 0%-5%
    "intangibles_fallback":        (0.00, 0.10),    # 0%-20% (composition unknown)
}
_M = 1_000_000.0  # LLM composition amounts are USD millions; structured values are raw USD


def _liq_value(idx: int, cash, sti, ar, inventory, ppe_net, intangibles, comp: Optional[dict]) -> float:
    """Liquidation value of assets for scenario idx (0=conservative/low, 1=base/mid). All in raw USD."""
    def h(key):
        return _HAIRCUTS[key][idx]
    v = (cash or 0.0) + (sti or 0.0)                      # cash + STI at 100%
    v += (ar or 0.0) * h("ar")
    v += (inventory or 0.0) * h("inventory")

    # PP&E: per-type haircuts when LLM composition exists; residual + uncomposed at blanket.
    ppe_keys = ("ppe_real_estate", "ppe_equipment", "ppe_specialised", "ppe_leasehold")
    if comp and any(comp.get(k) is not None for k in ppe_keys):
        categorised = 0.0
        for k in ppe_keys:
            amt = (comp.get(k) or 0.0) * _M
            v += amt * h(k)
            categorised += amt
        residual = max((ppe_net or 0.0) - categorised, 0.0)
        v += residual * h("ppe_fallback")
    else:
        v += (ppe_net or 0.0) * h("ppe_fallback")

    # Goodwill recovers 0% (omitted). Intangibles: per-type when composition exists.
    intan_keys = ("intangibles_patents", "intangibles_customer_lists", "intangibles_software")
    if comp and any(comp.get(k) is not None for k in intan_keys):
        categorised = 0.0
        for k in intan_keys:
            amt = (comp.get(k) or 0.0) * _M
            v += amt * h(k)
            categorised += amt
        residual = max((intangibles or 0.0) - categorised, 0.0)
        v += residual * h("intangibles_fallback")
    else:
        v += (intangibles or 0.0) * h("intangibles_fallback")
    return v


def _liquidation_coverage(p: PeriodInputs, comp: Optional[dict] = None) -> MetricResult:
    """Liquidation-adjusted asset coverage (ASSET_COVERAGE.md Formula 2). Stores the base-scenario
    value; the conservative-base range goes in the flag + extra (for the Dimension 3 alert).
    Uses LLM asset composition when present; otherwise blanket PP&E/intangibles haircuts."""
    total, _src, dflags, _level = _total_debt(p)
    base_d = dict(metric_name="liquidation_asset_coverage", period_end=p.period_end,
                  form_type=p.form_type, filing_date=p.filing_date, value_unit="ratio",
                  formula_version="F2")
    if total is None or total == 0:
        return MetricResult(**base_d, value=None, flags=dflags + ["total debt unavailable"],
                            extraction_path="none")
    cash = _v(p.instant.get("cash"))
    sti = _v(p.instant.get("short_term_investments"))
    ar = _v(p.instant.get("accounts_receivable"))
    inventory = _v(p.instant.get("inventory"))
    ppe_net = _v(p.instant.get("ppe_net"))
    intangibles = _v(p.instant.get("intangibles"))
    if all(x is None for x in (cash, sti, ar, inventory, ppe_net, intangibles)):
        return MetricResult(**base_d, value=None,
                            flags=["no asset inputs available for liquidation value"], extraction_path="none")

    recon_flags: list[str] = []
    _ppe_keys = ("ppe_real_estate", "ppe_equipment", "ppe_specialised", "ppe_leasehold")
    # Reconciliation guard A — UNDERSTATEMENT: if the LLM ppe_total is less than 10% of XBRL
    # net PP&E, it likely grabbed a sub-component (a depreciation line / single asset class).
    # Discard the LLM PP&E entirely and apply the blanket haircut to the balance-sheet value.
    if comp and ppe_net and comp.get("ppe_total") is not None:
        llm_total = comp["ppe_total"] * _M
        if llm_total < ppe_net * 0.10:
            recon_flags.append(
                f"LLM PP&E total ({llm_total / _M:,.0f}m) is less than 10% of balance sheet net "
                f"PP&E ({ppe_net / _M:,.0f}m) — likely extracted a sub-component; blanket haircut "
                f"applied to balance sheet value")
            comp = {k: v for k, v in comp.items() if k not in _ppe_keys and k != "ppe_total"}

    # Reconciliation guard B — OVERSTATEMENT: if the LLM PP&E components sum to >120% of XBRL
    # net PP&E, the LLM likely picked up GROSS values — drop the components, blanket the net value.
    if comp and ppe_net and any(comp.get(k) is not None for k in _ppe_keys):
        comp_sum = sum((comp.get(k) or 0.0) for k in _ppe_keys) * _M
        if comp_sum > ppe_net * 1.20:
            recon_flags.append(
                f"PP&E component sum ({comp_sum / _M:,.0f}m) exceeds balance sheet net PP&E "
                f"({ppe_net / _M:,.0f}m) by >20% — likely gross values extracted; blanket "
                f"haircut applied to balance sheet net value")
            comp = {k: v for k, v in comp.items() if k not in _ppe_keys}

    cons = _liq_value(0, cash, sti, ar, inventory, ppe_net, intangibles, comp) / total
    base_v = _liq_value(1, cash, sti, ar, inventory, ppe_net, intangibles, comp) / total
    flags = [f"liquidation coverage range: {cons:.2f}x to {base_v:.2f}x"]
    flags.extend(recon_flags)
    if comp is None:
        flags.append("no LLM asset composition — blanket PP&E (30-60%) / intangibles (0-20%) "
                     "haircuts applied; coarse estimate")
        path = "derived"
    else:
        path = "llm"
    return MetricResult(**base_d, value=base_v, flags=flags, extraction_path=path,
                        extra={"conservative_coverage": cons, "base_coverage": base_v},
                        audit_log={"total_debt": total, "conservative": cons, "base": base_v,
                                   "has_llm_composition": comp is not None})


def _ebitda_margin(p: PeriodInputs) -> MetricResult:
    ebitda_q = _ebitda_quarterly(p)
    rev = _v(p.quarterly.get("revenue"))
    base = dict(metric_name="ebitda_margin", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="percent")
    if ebitda_q is None or rev is None or rev == 0:
        return MetricResult(**base, value=None, flags=["EBITDA or revenue unavailable for margin"],
                            extraction_path="none")
    return MetricResult(**base, value=ebitda_q / rev * 100.0,
                        audit_log={"quarterly_ebitda": ebitda_q, "revenue": rev}, extraction_path="derived")


def _revenue_yoy(p: PeriodInputs, prior_year: Optional[PeriodInputs]) -> MetricResult:
    rev = _v(p.quarterly.get("revenue"))
    base = dict(metric_name="revenue_yoy_growth", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="percent")
    rev_rv = p.quarterly.get("revenue")
    src = {"revenue": ",".join(rev_rv.tags)} if (rev_rv and rev_rv.tags) else {}
    if rev is None:
        return MetricResult(**base, value=None, flags=["current revenue unavailable"],
                            source_tags=src, extraction_path="none")
    prior_rev = _v(prior_year.quarterly.get("revenue")) if prior_year is not None else None
    if prior_rev is None or prior_rev == 0:
        return MetricResult(**base, value=None,
                            flags=["YoY growth null — prior-year same-quarter revenue unavailable"],
                            source_tags=src, extraction_path="none")
    yoy = (rev - prior_rev) / prior_rev * 100.0
    return MetricResult(**base, value=yoy, source_tags=src,
                        audit_log={"revenue": rev, "prior_year_revenue": prior_rev}, extraction_path="derived")


def _load_llm_extraction(cik: str) -> Optional[dict]:
    """Most recent llm_extractions row for an issuer (Phase-3 footnote terms), or None.

    Returns None if the table doesn't exist yet or has no row for this CIK — callers then
    fall back to the Phase-2 proxy / current-portion behaviour. Read-only; no I/O on the
    pure metric functions beyond this single lookup per issuer.
    """
    import sqlite3
    try:
        from db import DB_PATH
    except Exception:
        DB_PATH = "credit_warning.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM llm_extractions WHERE cik = ? ORDER BY extracted_at DESC LIMIT 1",
            (cik,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None  # table not created yet


def _load_llm_loss_provisions(cik: str) -> Optional[dict]:
    """Most recent llm_loss_provisions row for an issuer (Group 4), or None / missing-table."""
    import sqlite3
    try:
        from db import DB_PATH
    except Exception:
        DB_PATH = "credit_warning.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM llm_loss_provisions WHERE cik = ? ORDER BY extracted_at DESC LIMIT 1",
            (cik,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def _load_llm_asset_composition(cik: str) -> Optional[dict]:
    """Most recent llm_asset_composition row for an issuer (Group 6), or None / missing-table."""
    import sqlite3
    try:
        from db import DB_PATH
    except Exception:
        DB_PATH = "credit_warning.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM llm_asset_composition WHERE cik = ? ORDER BY extracted_at DESC LIMIT 1",
            (cik,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def _maturity_coverage(p: PeriodInputs, llm: Optional[dict] = None) -> MetricResult:
    cur_ltd = _v(p.instant.get("current_ltd"))
    st = _v(p.instant.get("short_term_debt"))
    cash = _v(p.instant.get("cash"))
    sti = _v(p.instant.get("short_term_investments")) or 0.0
    base = dict(metric_name="maturity_coverage_near_term", period_end=p.period_end,
                form_type=p.form_type, filing_date=p.filing_date, value_unit="ratio")
    flags: list[str] = []

    # Near-term maturity: prefer the LLM Year-1 full schedule (captures bullet maturities not
    # yet reclassified to the balance-sheet current portion) over the XBRL current portion.
    near_term_from_llm = llm is not None and llm.get("maturity_year1") is not None
    if near_term_from_llm:
        near_term = float(llm["maturity_year1"]) * 1e6  # schedule is in USD millions
        flags.append("near-term maturity from LLM Year 1 schedule (full bullet maturities)")
    else:
        near_term = (cur_ltd or 0.0) + (st or 0.0)
        if cur_ltd is None:
            flags.append("current portion of LT debt not found — near-term maturity may be understated")

    if near_term == 0:
        return MetricResult(**base, value=None, flags=flags + ["no near-term maturities identified"],
                            extraction_path="none")
    if cash is None:
        return MetricResult(**base, value=None, flags=flags + ["cash unavailable"], extraction_path="none")

    # Available liquidity: cash + STI, plus the revolver's undrawn capacity when the LLM
    # extraction provides it (replaces the Phase-2 "revolver excluded" understatement).
    avail = cash + sti
    revolver_added = False
    if llm is not None and llm.get("revolver_net_available") is not None:
        avail += float(llm["revolver_net_available"]) * 1e6
        flags.append("revolver included from LLM extraction")
        revolver_added = True
    else:
        flags.append("revolver excluded — not available; available liquidity may be understated")

    path = "llm" if (near_term_from_llm or revolver_added) else "primary"
    return MetricResult(**base, value=avail / near_term, flags=flags, extraction_path=path,
                        audit_log={"available_liquidity": avail, "near_term_maturity": near_term,
                                   "cash": cash, "short_term_investments": sti,
                                   "revolver_net_available": (llm or {}).get("revolver_net_available")})


def _covenant_headroom(leverage: MetricResult, coverage: MetricResult, p: PeriodInputs,
                       llm: Optional[dict] = None) -> list[MetricResult]:
    """Covenant headroom. With an LLM extraction (real covenant thresholds + compliance
    status), compute actual headroom and apply compliance overrides. Without one, fall back
    to the Phase-2 leveraged-finance proxy (leverage > 5.5x, coverage < 2.0x)."""
    base = dict(period_end=p.period_end, form_type=p.form_type, filing_date=p.filing_date, value_unit="ratio")

    # ---- Fallback: Phase-2 proxy (unchanged) ----
    if llm is None:
        proxy_note = ("Phase 2 proxy — no LLM covenant extraction; leveraged-finance proxy level")
        lev = MetricResult(metric_name="covenant_headroom_leverage", value=leverage.value,
                           flags=[proxy_note], extraction_path="derived",
                           extra={"breached": (leverage.value is not None and leverage.value > 5.5)}, **base)
        cov = MetricResult(metric_name="covenant_headroom_coverage", value=coverage.value,
                           flags=[proxy_note], extraction_path="derived",
                           extra={"breached": (coverage.value is not None and coverage.value < 2.0)}, **base)
        return [lev, cov]

    # ---- LLM path: real thresholds + compliance overrides ----
    # Compliance-level overrides apply to both covenant metrics.
    override, override_flag = None, None
    if llm.get("breach_disclosed") or llm.get("chapter_11_filed"):
        override = "Critical"
        override_flag = "covenant breach / Chapter 11 disclosed (LLM extraction)"
    elif llm.get("going_concern_doubt"):
        override = "Stress"
        override_flag = "going-concern doubt disclosed (LLM extraction)"

    def headroom_alert(h: Optional[float]) -> Optional[str]:
        if h is None:
            return None
        if h < 0:
            return "Critical"          # already in breach
        if h < 0.10:
            return "Stress"
        if h < 0.20:
            return "Flag"              # <15-20% headroom is a negative factor (S&P)
        if h < 0.30:
            return "Watch"
        return None

    # Leverage covenant is a maximum: headroom = (threshold - current) / threshold.
    lev_thr = llm.get("leverage_covenant_threshold")
    lev_val = leverage.value
    lev_head, lev_flags = None, []
    if lev_thr and lev_val is not None:
        lev_head = (lev_thr - lev_val) / lev_thr
        lev_flags.append(f"covenant max leverage {lev_thr}x (LLM); current {lev_val:.2f}x; "
                         f"headroom {lev_head * 100:.0f}%")
    elif override is None:
        lev_flags.append("no leverage covenant threshold extracted")
    if override_flag:
        lev_flags.append(override_flag)
    lev = MetricResult(metric_name="covenant_headroom_leverage", value=lev_head, flags=lev_flags,
                       extraction_path="llm", extra={"llm_alert": override or headroom_alert(lev_head)},
                       audit_log={"covenant_threshold": lev_thr, "current_leverage": lev_val}, **base)

    # Coverage covenant is a minimum: headroom = (current - threshold) / threshold.
    cov_thr = llm.get("coverage_covenant_threshold")
    cov_val = coverage.value
    cov_head, cov_flags = None, []
    if cov_thr and cov_val is not None:
        cov_head = (cov_val - cov_thr) / cov_thr
        cov_flags.append(f"covenant min coverage {cov_thr}x (LLM); current {cov_val:.2f}x; "
                         f"headroom {cov_head * 100:.0f}%")
    elif override is None:
        cov_flags.append("no coverage covenant threshold extracted")
    if override_flag:
        cov_flags.append(override_flag)
    cov = MetricResult(metric_name="covenant_headroom_coverage", value=cov_head, flags=cov_flags,
                       extraction_path="llm", extra={"llm_alert": override or headroom_alert(cov_head)},
                       audit_log={"covenant_threshold": cov_thr, "current_coverage": cov_val}, **base)
    return [lev, cov]


def _loss_provisions(p: PeriodInputs, llm_lp: Optional[dict] = None) -> MetricResult:
    base = dict(metric_name="loss_provisions_balance", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="millions_usd")

    # Prefer the LLM contingency-footnote extraction (Group 4) when present — the XBRL tag
    # LossContingencyAccrual is rarely populated, so this is where most issuers get a value.
    if llm_lp is not None and llm_lp.get("total_accrued") is not None:
        flags = ["loss provisions from LLM contingency-footnote extraction"]
        if llm_lp.get("total_maximum_exposure") is not None:
            flags.append(f"reasonably-possible max exposure (unrecorded) ${llm_lp['total_maximum_exposure']:,.0f}M")
        if llm_lp.get("regulatory_investigation"):
            flags.append("regulatory investigation disclosed")
        return MetricResult(**base, value=llm_lp["total_accrued"], extraction_path="llm", flags=flags,
                            audit_log={"total_accrued": llm_lp.get("total_accrued"),
                                       "total_maximum_exposure": llm_lp.get("total_maximum_exposure"),
                                       "regulatory_investigation": llm_lp.get("regulatory_investigation")})

    # LLM ran but disclosed no accrued provisions — report null with matter context (Apple
    # case: matters extracted but nothing accrued). Do NOT fall through to the XBRL path.
    if llm_lp is not None:
        try:
            matters = json.loads(llm_lp.get("matters_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            matters = []
        n = len(matters)
        tiers = [mt.get("tier") for mt in matters if isinstance(mt, dict) and mt.get("tier") is not None]
        highest = max(tiers) if tiers else None
        return MetricResult(**base, value=None, extraction_path="llm",
                            flags=[f"LLM extraction complete — no accrued provisions disclosed; "
                                   f"matters extracted: {n} (highest tier: {highest})"],
                            audit_log={"matters": n, "highest_tier": highest,
                                       "total_maximum_exposure": llm_lp.get("total_maximum_exposure"),
                                       "regulatory_investigation": llm_lp.get("regulatory_investigation")})

    cur = _v(p.instant.get("loss_contingency_current"))
    nc = _v(p.instant.get("loss_contingency_noncurrent"))
    env = _v(p.instant.get("environmental_accrual"))
    src: dict[str, str] = {}
    for name in ("loss_contingency_current", "loss_contingency_noncurrent", "environmental_accrual"):
        rv = p.instant.get(name)
        if rv is not None and rv.tags:
            src[name] = ",".join(rv.tags)

    if cur is None and nc is None and env is None:
        return MetricResult(**base, value=None,
                            flags=["provision balance not extractable from XBRL — Phase 3 LLM required; "
                                   "do not interpret as zero exposure"],
                            source_tags=src, extraction_path="none")
    total = (cur or 0.0) + (nc or 0.0) + (env or 0.0)
    return MetricResult(**base, value=total / 1e6, source_tags=src,
                        flags=["XBRL provision balance only — footnote contingencies (Phase 3 LLM) not included"],
                        audit_log={"current": cur, "noncurrent": nc, "environmental": env})


# --------------------------------------------------------------------------------------
# Financial-institution post-processing (§6.2 suppression table)
# --------------------------------------------------------------------------------------

# Metrics suppressed entirely for financial institutions (EBITDA-based or balance-structure ratios).
_FI_SUPPRESS = {"leverage", "interest_coverage", "current_ratio", "quick_ratio",
                "ebitda_margin", "ocf_ebitda_conversion",
                "covenant_headroom_leverage", "covenant_headroom_coverage"}
# Computed-with-flag but absolute thresholds not applicable (no alert).
_FI_FLAG_NO_ALERT = {
    "debt_to_equity": "financial institution — D/E thresholds not applicable; regulatory capital "
                      "ratios (CET1, Tier 1) govern; use for trend monitoring only",
    "asset_coverage": "financial institution — Formula 1 book value coverage only; liquidation "
                      "haircuts not applicable without bank-specific asset quality data",
    "tangible_asset_coverage": "financial institution — Formula 1 book value coverage only; "
                               "liquidation haircuts not applicable",
    "liquidation_asset_coverage": "financial institution — liquidation haircuts not applicable "
                                  "without bank-specific asset quality data",
}
# Computed-with-flag, alerts retained.
_FI_FLAG = {
    "free_cash_flow": FINANCIAL_FCF_FLAG,
    "fcf_margin": FINANCIAL_FCF_FLAG,
    "revenue_yoy_growth": "financial institution — revenue = net interest income + non-interest "
                          "income; GAAP revenue line used as proxy; verify composition",
}


def _apply_financial_rules(m: MetricResult) -> None:
    """Mutate a MetricResult in place per the §6.2 financial-institution suppression table."""
    if m.metric_name in _FI_SUPPRESS:
        m.value = None
        m.suppressed = True
        m.extraction_path = "none"
        m.flags = [FINANCIAL_SUPPRESSION_FLAG]
        m.extra = {}
    elif m.metric_name in _FI_FLAG_NO_ALERT:
        m.no_alert = True
        if _FI_FLAG_NO_ALERT[m.metric_name] not in m.flags:
            m.flags.append(_FI_FLAG_NO_ALERT[m.metric_name])
    elif m.metric_name in _FI_FLAG:
        if _FI_FLAG[m.metric_name] not in m.flags:
            m.flags.append(_FI_FLAG[m.metric_name])


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def compute_metrics(result: ExtractionResult, institution_type: str) -> list[MetricResult]:
    """Compute all Phase-2 Formula-1 metrics across all reported periods.

    Metrics are computed normally first; financial-institution rules (§6.2) are then
    applied as a post-processing pass so suppressed metrics still appear as null rows with
    the suppression flag (downstream can distinguish suppressed from failed extractions).
    """
    has_interest_tag = _issuer_has_concept(result, "interest_expense")
    has_net_tag = _issuer_has_concept(result, "interest_net")
    periods = result.periods
    # Phase-3 LLM footnote terms (covenant thresholds, maturity schedule, revolver), loaded
    # once per issuer. None when no extraction has been persisted -> proxy/current-portion fallback.
    llm = _load_llm_extraction(result.metadata.cik)
    llm_lp = _load_llm_loss_provisions(result.metadata.cik)
    llm_ac = _load_llm_asset_composition(result.metadata.cik)

    out: list[MetricResult] = []
    for i, p in enumerate(periods):
        leverage = _leverage(p)
        coverage = _interest_coverage(p, has_interest_tag, has_net_tag)
        prior_year = periods[i - 4] if i >= 4 else None

        out.append(leverage)
        out.append(coverage)
        out.extend(_free_cash_flow(p, institution_type))
        out.append(_current_ratio(p))
        out.append(_quick_ratio(p))
        out.append(_ebitda_margin(p))
        out.append(_revenue_yoy(p, prior_year))
        out.append(_debt_to_equity(p))
        out.extend(_asset_coverage(p))
        out.append(_liquidation_coverage(p, llm_ac))
        out.append(_maturity_coverage(p, llm))
        out.extend(_covenant_headroom(leverage, coverage, p, llm))
        out.append(_loss_provisions(p, llm_lp))

    if institution_type == "financial":
        for m in out:
            _apply_financial_rules(m)
    return out
