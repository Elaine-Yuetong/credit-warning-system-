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
    oi = _v(p.quarterly.get("operating_income"))
    da = _v(p.quarterly.get("dep_amort"))
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


def _interest_coverage(p: PeriodInputs, has_interest_tag: bool, has_net_tag: bool) -> MetricResult:
    ebitda, ebsrc, ebflags = _ebitda_ttm(p)
    oi_ttm = _v(p.ttm.get("operating_income"))
    int_rv = p.ttm.get("interest_expense")
    interest = _v(int_rv)
    src: dict[str, str] = dict(ebsrc)
    flags: list[str] = list(ebflags)
    base = dict(metric_name="interest_coverage", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="ratio", source_tags=src)

    # Explicit net-interest netting detection (no silent net substitution).
    if not has_interest_tag and has_net_tag:
        flags.append("net interest only — LLM required per spec")
        return MetricResult(**base, value=None, flags=flags,
                            audit_log={"reason": "net_interest_only"}, extraction_path="none")

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


def _maturity_coverage(p: PeriodInputs) -> MetricResult:
    cur_ltd = _v(p.instant.get("current_ltd"))
    st = _v(p.instant.get("short_term_debt"))
    cash = _v(p.instant.get("cash"))
    sti = _v(p.instant.get("short_term_investments")) or 0.0
    base = dict(metric_name="maturity_coverage_near_term", period_end=p.period_end,
                form_type=p.form_type, filing_date=p.filing_date, value_unit="ratio")
    flags = ["revolver excluded — Phase 2; available liquidity may be understated"]

    near_term = (cur_ltd or 0.0) + (st or 0.0)
    if cur_ltd is None:
        flags.append("current portion of LT debt not found — near-term maturity may be understated")
    if near_term == 0:
        return MetricResult(**base, value=None, flags=flags + ["no near-term maturities identified"],
                            extraction_path="none")
    if cash is None:
        return MetricResult(**base, value=None, flags=flags + ["cash unavailable"], extraction_path="none")
    avail = cash + sti
    return MetricResult(**base, value=avail / near_term, flags=flags,
                        audit_log={"available_liquidity": avail, "near_term_maturity": near_term,
                                   "cash": cash, "short_term_investments": sti})


def _covenant_proxies(leverage: MetricResult, coverage: MetricResult, p: PeriodInputs) -> list[MetricResult]:
    """Phase-2 proxy: no covenant threshold is XBRL-extractable, so flag when the leverage
    or coverage ratio crosses the leveraged-finance proxy levels (>5.5x, <2.0x) (§ COVENANT_HEADROOM)."""
    base = dict(period_end=p.period_end, form_type=p.form_type, filing_date=p.filing_date, value_unit="ratio")
    proxy_note = "Phase 2 proxy — covenant threshold not XBRL-extractable (Phase 3 LLM); leveraged-finance proxy level"

    lev = MetricResult(metric_name="covenant_headroom_leverage", value=leverage.value,
                       flags=[proxy_note], extraction_path="derived",
                       extra={"breached": (leverage.value is not None and leverage.value > 5.5)}, **base)
    cov = MetricResult(metric_name="covenant_headroom_coverage", value=coverage.value,
                       flags=[proxy_note], extraction_path="derived",
                       extra={"breached": (coverage.value is not None and coverage.value < 2.0)}, **base)
    return [lev, cov]


def _loss_provisions(p: PeriodInputs) -> MetricResult:
    cur = _v(p.instant.get("loss_contingency_current"))
    nc = _v(p.instant.get("loss_contingency_noncurrent"))
    env = _v(p.instant.get("environmental_accrual"))
    base = dict(metric_name="loss_provisions_balance", period_end=p.period_end, form_type=p.form_type,
                filing_date=p.filing_date, value_unit="millions_usd")
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
        out.append(_maturity_coverage(p))
        out.extend(_covenant_proxies(leverage, coverage, p))
        out.append(_loss_provisions(p))

    if institution_type == "financial":
        for m in out:
            _apply_financial_rules(m)
    return out
