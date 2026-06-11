"""
backtest.py — Phase 3 point-in-time backtest harness for the Credit Warning System.

Measures whether the deterministic Formula-1 model catches credit stress *before* the
event, without look-ahead bias. For each historical scoring date it calls
extractor.extract(as_of=date), so only facts filed on or before that date are used —
the single most important correctness rule in backtesting (INTERN_PLAN.md Phase 3).

Distress signal (per the agreed calibration): an issuer is "flagged" on a date when ANY
non-suppressed metric reaches Stress or Critical. This avoids single-Flag false positives
(e.g. Apple's structurally low current ratio) while catching genuine distress. A softer
">=2 metrics at Flag+" view is reported alongside for tuning visibility, but the pass/fail
gate uses Stress+.

Targets (LEVERAGE.md backtest anchors):
  - Catch rate    >= 80% of scoreable distressed names flagged >= 2 quarters before event
  - False positives <= 20% of healthy controls flagged in any scored quarter
  - Lead time      median >= 2 quarters (informational)

Run:  python backtest.py            (full report; exit 0 = targets met, 1 = miss)
      python backtest.py --json out.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from extractor import SecClient, extract
from metrics import compute_metrics
from thresholds import classify, assign_alerts

# Alert severity ordinals (mirrors thresholds._LEVELS).
SEVERITY = {None: 0, "Watch": 1, "Flag": 2, "Stress": 3, "Critical": 4}
STRESS_ORDINAL = SEVERITY["Stress"]      # per-metric Stress+ threshold
FLAG_ORDINAL = SEVERITY["Flag"]          # softer secondary view

# Distress signal = CONFIRM_COUNT or more non-suppressed metrics at Stress+ on the same
# date. This generalises INTEREST_COVERAGE.md's "dual metric stress" trigger (leverage AND
# coverage flagging together) to any >=2 metrics at Stress+. The single-metric Stress+
# signal is still reported as a secondary column for comparison/tuning.
CONFIRM_COUNT = 2

LEAD_QUARTERS_REQUIRED = 2               # "early" = flagged >= 2 quarters pre-event
LEAD_DAYS_REQUIRED = LEAD_QUARTERS_REQUIRED * 91
MIN_PREEVENT_QUARTERS = 8                # below this -> insufficient_history

CATCH_RATE_TARGET = 0.80
FP_RATE_TARGET = 0.20


# --------------------------------------------------------------------------------------
# Case library
# --------------------------------------------------------------------------------------

@dataclass
class Case:
    name: str
    cik: str
    event_date: Optional[str]            # ISO; None for healthy controls + stressed survivors
    name_contains: tuple[str, ...]       # accepted entityName substrings (upper-cased)
    note: str = ""
    # Stressed-survivor window (ISO). The system should flag Stress+ *during* this period and
    # be clean before and after — the early-warning test for names that did NOT go bankrupt.
    stress_start: Optional[str] = None
    stress_end: Optional[str] = None


DISTRESSED: list[Case] = [
    Case("Rite Aid", "0000084129", "2023-10-15", ("RITE AID",), "primary anchor"),
    Case("Bed Bath & Beyond", "0000886158", "2023-04-23", ("BED BATH", "DK-BUTTERFLY")),
    Case("WeWork", "0001813756", "2023-11-06", ("WEWORK",),
         "SPAC listing — EDGAR history may be short; flagged if insufficient"),
    Case("Revlon", "0000887921", "2022-06-15", ("REVLON",)),
    Case("Party City", "0001592058", "2023-01-17", ("PARTY CITY", "PGHC", "PC NEXTCO")),
    Case("Yellow Corp", "0000716006", "2023-08-06", ("YELLOW", "YRC")),
    Case("iHeartMedia", "0001400891", "2018-03-14", ("IHEARTMEDIA", "IHEART"),
         "Chapter 11 March 2018"),
    Case("Chesapeake Energy", "0000895126", "2020-06-28", ("CHESAPEAKE", "EXPAND ENERGY"),
         "Chapter 11 June 2020; CIK renamed to Expand Energy post-emergence"),
    Case("JCPenney", "0001166126", "2020-05-15", ("PENNEY", "JC PENNEY", "OLD COPPER"),
         "Chapter 11 May 2020; CIK renamed to Old Copper Company post-bankruptcy"),
    Case("Hertz", "0001657853", "2020-05-22", ("HERTZ",), "Chapter 11 May 2020 (Hertz Global Holdings)"),
    Case("Sears Holdings", "0001310067", "2018-10-15", ("SEARS",), "Chapter 11 October 2018"),
]

HEALTHY: list[Case] = [
    Case("Apple", "0000320193", None, ("APPLE",)),
    Case("Microsoft", "0000789019", None, ("MICROSOFT",)),
    Case("Johnson & Johnson", "0000200406", None, ("JOHNSON",),
         "FY OperatingIncomeLoss gap — leverage/coverage path may be null (known limitation)"),
    Case("Waste Management", "0000823768", None, ("WASTE MANAGEMENT", "WASTE MGMT"),
         "acquisition-driven D/E event — Stericycle acquisition 2023; single leveraging "
         "transaction, not credit deterioration"),
    Case("Procter & Gamble", "0000080424", None, ("PROCTER",)),
    Case("Costco", "0000909832", None, ("COSTCO",)),
]

# Names that hit significant credit stress but did NOT go bankrupt. The early-warning test:
# flag Stress+ during the stress window, clean before and after. (No event_date — these
# survived; correctness is measured against the stress window, not a bankruptcy date.)
STRESSED_SURVIVOR: list[Case] = [
    Case("Macy's", "0000794367", None, ("MACY",), "retail stress 2019–2020, survived",
         stress_start="2019-01-01", stress_end="2020-12-31"),
    Case("Ford Motor", "0000037996", None, ("FORD MOTOR",),
         "downgraded to junk March 2020, recovered",
         stress_start="2020-01-01", stress_end="2020-12-31"),
    Case("Occidental Petroleum", "0000797468", None, ("OCCIDENTAL",),
         "severe oil-price stress 2020, recovered",
         stress_start="2020-01-01", stress_end="2020-12-31"),
]


# --------------------------------------------------------------------------------------
# Date helpers (no third-party deps)
# --------------------------------------------------------------------------------------

def _d(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the last valid day of the target month.
    for day in (d.day, 28, 29, 30, 31):
        try:
            return date(year, month, min(day, 31))
        except ValueError:
            continue
    return date(year, month, 28)


def _quarterly_dates(start: date, end: date) -> list[str]:
    """Quarterly scoring dates from start to end inclusive (step +3 months)."""
    out: list[str] = []
    cur = start
    while cur <= end:
        out.append(cur.isoformat())
        cur = _add_months(cur, 3)
    if not out or out[-1] != end.isoformat():
        out.append(end.isoformat())
    return out


# --------------------------------------------------------------------------------------
# Point-in-time scoring
# --------------------------------------------------------------------------------------

@dataclass
class ScorePoint:
    as_of: str
    ordinal: int                         # max non-suppressed metric severity
    level: Optional[str]
    stress_metrics: list[str]            # metrics at Stress+ (the distress drivers)
    flag_count: int                      # distinct metrics at Flag+ (softer view)
    latest_period: Optional[str]
    n_periods: int


def _score_at(cik: str, as_of: str, client: SecClient) -> Optional[ScorePoint]:
    """Score an issuer using only data filed on or before `as_of`. None if no data yet."""
    result = extract(cik, client=client, as_of=as_of)
    if result is None or not result.periods:
        return None
    cls = classify(result.metadata.sic_code)
    metrics = compute_metrics(result, cls.institution_type)
    assign_alerts(metrics, cls)

    # Stress is read off the most recent period available as of `as_of`. assign_alerts
    # has already folded trend (QoQ / multi-quarter) into that period's alert levels.
    latest_end = result.periods[-1].period_end
    max_ord, level = 0, None
    stress_metrics: list[str] = []
    flagged: set[str] = set()
    for m in metrics:
        if m.period_end != latest_end or m.suppressed or m.no_alert:
            continue
        o = SEVERITY.get(m.alert_level, 0)
        if o >= FLAG_ORDINAL:
            flagged.add(m.metric_name)
        if o >= STRESS_ORDINAL:
            stress_metrics.append(m.metric_name)
        if o > max_ord:
            max_ord, level = o, m.alert_level
    return ScorePoint(as_of, max_ord, level, sorted(stress_metrics), len(flagged),
                      latest_end, len(result.periods))


# --------------------------------------------------------------------------------------
# Case execution
# --------------------------------------------------------------------------------------

@dataclass
class CaseResult:
    case: Case
    status: str                          # caught | missed | flagged_late | clean |
                                         # false_positive | annotated |
                                         # detected_clean | detected_noisy | missed_stress |
                                         # insufficient_history | unresolved
    resolved_name: Optional[str] = None
    first_stress_date: Optional[str] = None      # first >=2-metric Stress+ (primary signal)
    lead_days: Optional[int] = None
    peak_level: Optional[str] = None
    peak_stress_metrics: list[str] = field(default_factory=list)
    single_first_date: Optional[str] = None      # first single-metric Stress+ (secondary)
    n_preevent_quarters: Optional[int] = None
    fp_dates: list[str] = field(default_factory=list)        # >=2-metric Stress+ dates
    single_fp_dates: list[str] = field(default_factory=list) # single-metric Stress+ (secondary)
    timeline: list[ScorePoint] = field(default_factory=list)
    note: str = ""
    # Stressed-survivor fields: confirmed (>=2-metric Stress+) dates by temporal bucket.
    stress_detected: bool = False
    clean_before: bool = False
    clean_after: bool = False
    during_dates: list[str] = field(default_factory=list)
    before_dates: list[str] = field(default_factory=list)
    after_dates: list[str] = field(default_factory=list)


def _confirmed(sp: ScorePoint) -> bool:
    """Distress signal: CONFIRM_COUNT+ non-suppressed metrics at Stress+ on this date."""
    return len(sp.stress_metrics) >= CONFIRM_COUNT


def _single(sp: ScorePoint) -> bool:
    """Secondary view: any single metric at Stress+ (the pre-confirmation rule)."""
    return sp.ordinal >= STRESS_ORDINAL


def _validate(case: Case, client: SecClient) -> tuple[bool, Optional[str]]:
    from extractor import fetch_issuer_metadata
    meta = fetch_issuer_metadata(client, case.cik)
    if meta is None or not meta.has_10k:
        return False, (meta.name if meta else None)
    if not any(s in meta.name.upper() for s in case.name_contains):
        return False, meta.name
    return True, meta.name


def _run_distressed(case: Case, client: SecClient) -> CaseResult:
    ok, name = _validate(case, client)
    if not ok:
        return CaseResult(case, "unresolved", resolved_name=name,
                          note="CIK did not resolve to expected issuer or lacks 10-K history")

    event = _d(case.event_date)  # type: ignore[arg-type]

    # History sufficiency: how many quarters were knowable as of the event date?
    at_event = extract(case.cik, client=client, as_of=case.event_date)
    n_pre = len(at_event.periods) if at_event else 0
    if n_pre < MIN_PREEVENT_QUARTERS:
        return CaseResult(case, "insufficient_history", resolved_name=name,
                          n_preevent_quarters=n_pre,
                          note=f"only {n_pre} pre-event quarters in EDGAR (< {MIN_PREEVENT_QUARTERS})")

    # Quarterly point-in-time scoring across the 3 years before the event.
    dates = _quarterly_dates(_add_months(event, -36), event)
    timeline = [sp for d in dates if (sp := _score_at(case.cik, d, client)) is not None]

    first_confirmed = next((sp for sp in timeline if _confirmed(sp)), None)  # primary
    first_single = next((sp for sp in timeline if _single(sp)), None)        # secondary
    peak = max(timeline, key=lambda s: s.ordinal, default=None)

    res = CaseResult(case, "missed", resolved_name=name, n_preevent_quarters=n_pre,
                     timeline=timeline,
                     single_first_date=first_single.as_of if first_single else None,
                     peak_level=peak.level if peak else None,
                     peak_stress_metrics=peak.stress_metrics if peak else [])
    if first_confirmed is not None:
        lead = (event - _d(first_confirmed.as_of)).days
        res.first_stress_date = first_confirmed.as_of
        res.lead_days = lead
        res.peak_stress_metrics = first_confirmed.stress_metrics or res.peak_stress_metrics
        res.status = "caught" if lead >= LEAD_DAYS_REQUIRED else "flagged_late"
    return res


def _run_healthy(case: Case, client: SecClient) -> CaseResult:
    ok, name = _validate(case, client)
    if not ok:
        return CaseResult(case, "unresolved", resolved_name=name)
    today = date.today()
    dates = _quarterly_dates(_add_months(today, -36), today)
    timeline = [sp for d in dates if (sp := _score_at(case.cik, d, client)) is not None]
    fp_dates = [sp.as_of for sp in timeline if _confirmed(sp)]            # primary (>=2 metric)
    single_fp_dates = [sp.as_of for sp in timeline if _single(sp)]        # secondary
    peak = max(timeline, key=lambda s: s.ordinal, default=None)
    # A control that fires the >=2-metric signal is a false positive; if the case carries a
    # note explaining a known one-off cause (e.g. WM's Stericycle acquisition), surface it as
    # "annotated" — it still counts in the FP rate (not removed from the control set).
    if fp_dates:
        status = "annotated" if case.note else "false_positive"
    else:
        status = "clean"
    return CaseResult(case, status, resolved_name=name, timeline=timeline, fp_dates=fp_dates,
                      single_fp_dates=single_fp_dates,
                      peak_level=peak.level if peak else None,
                      peak_stress_metrics=peak.stress_metrics if peak else [],
                      note=case.note)


def _run_stressed_survivor(case: Case, client: SecClient) -> CaseResult:
    """Early-warning test for names that hit stress but survived: did the system confirm
    Stress+ *during* the stress window, and stay clean before and after?"""
    ok, name = _validate(case, client)
    if not ok:
        return CaseResult(case, "unresolved", resolved_name=name,
                          note="CIK did not resolve to expected issuer or lacks 10-K history")

    s_start, s_end = _d(case.stress_start), _d(case.stress_end)  # type: ignore[arg-type]
    window_start = _add_months(s_start, -24)                      # 2 yrs before stress
    window_end = min(_add_months(s_end, 24), date.today())        # 2 yrs after stress, capped today

    # History sufficiency: how many quarters were knowable by the end of the stress window?
    at_end = extract(case.cik, client=client, as_of=case.stress_end)
    n_pre = len(at_end.periods) if at_end else 0
    if n_pre < MIN_PREEVENT_QUARTERS:
        return CaseResult(case, "insufficient_history", resolved_name=name,
                          n_preevent_quarters=n_pre,
                          note=f"only {n_pre} quarters knowable by stress end (< {MIN_PREEVENT_QUARTERS})")

    dates = _quarterly_dates(window_start, window_end)
    timeline = [sp for d in dates if (sp := _score_at(case.cik, d, client)) is not None]

    def _bucket(iso: str) -> str:
        d = _d(iso)
        if d < s_start:
            return "before"
        if d <= s_end:
            return "during"
        return "after"

    before_dates = [sp.as_of for sp in timeline if _bucket(sp.as_of) == "before" and _confirmed(sp)]
    during_dates = [sp.as_of for sp in timeline if _bucket(sp.as_of) == "during" and _confirmed(sp)]
    after_dates = [sp.as_of for sp in timeline if _bucket(sp.as_of) == "after" and _confirmed(sp)]

    stress_detected = len(during_dates) > 0
    clean_before = len(before_dates) == 0
    clean_after = len(after_dates) == 0
    peak = max(timeline, key=lambda s: s.ordinal, default=None)

    if not stress_detected:
        status = "missed_stress"
    elif clean_before and clean_after:
        status = "detected_clean"      # ideal: flagged during stress, clean either side
    else:
        status = "detected_noisy"      # detected, but also fired outside the stress window

    return CaseResult(case, status, resolved_name=name, timeline=timeline, n_preevent_quarters=n_pre,
                      stress_detected=stress_detected, clean_before=clean_before, clean_after=clean_after,
                      during_dates=during_dates, before_dates=before_dates, after_dates=after_dates,
                      first_stress_date=during_dates[0] if during_dates else None,
                      peak_level=peak.level if peak else None,
                      peak_stress_metrics=peak.stress_metrics if peak else [],
                      note=case.note)


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

def _months(days: Optional[int]) -> str:
    return "—" if days is None else f"{days / 30.44:.0f}mo"


def _q_label(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    d = _d(iso)
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


# Distressed status -> (icon, label).
_DIST_STATUS = {
    "caught": ("✅", "CAUGHT"), "flagged_late": ("⚠️", "FLAGGED LATE"),
    "missed": ("❌", "MISSED"), "insufficient_history": ("—", "INSUFFICIENT HIST"),
    "unresolved": ("—", "UNRESOLVED"),
}
_CTRL_STATUS = {
    "clean": ("✅", "CLEAN"), "annotated": ("⚠️", "ANNOTATED"),
    "false_positive": ("❌", "FALSE POSITIVE"), "unresolved": ("—", "UNRESOLVED"),
}
_SURVIVOR_STATUS = {
    "detected_clean": ("✅", "DETECTED+CLEAN"), "detected_noisy": ("⚠️", "DETECTED (NOISY)"),
    "missed_stress": ("❌", "MISSED STRESS"),
    "insufficient_history": ("—", "INSUFFICIENT HIST"), "unresolved": ("—", "UNRESOLVED"),
}


def _print_report(distressed: list[CaseResult], healthy: list[CaseResult],
                  survivors: list[CaseResult]) -> bool:
    line = "═" * 84
    print("\n" + line)
    print("  CREDIT WARNING SYSTEM — PHASE 3 BACKTEST  (point-in-time, no look-ahead)")
    print(f"  Distress signal: ≥{CONFIRM_COUNT} metrics at Stress+ (confirmation)."
          f"  Secondary: single-metric Stress+.")
    print(line)

    # ---- distressed scorecard ----
    print("\nDISTRESSED CASES")
    for r in distressed:
        icon, label = _DIST_STATUS.get(r.status, ("—", r.status.upper()))
        name = r.resolved_name and r.case.name or r.case.name
        if r.status in ("caught", "flagged_late"):
            detail = (f"first signal {_q_label(r.first_stress_date):<8} {_months(r.lead_days):>5} early"
                      f"   peak: {r.peak_level or '—'}")
        elif r.status == "missed":
            sec = f"single-metric first {_q_label(r.single_first_date)}" if r.single_first_date else "no Stress+ at all"
            detail = f"no ≥{CONFIRM_COUNT}-metric confirmation pre-event   (secondary: {sec})"
        else:
            detail = r.note or "—"
        print(f"  {icon} {label:<16} {r.case.name:<18} {detail}")

    scoreable = [r for r in distressed if r.status in ("caught", "flagged_late", "missed")]
    caught = [r for r in scoreable if r.status == "caught"]
    excluded = [r for r in distressed if r.status in ("insufficient_history", "unresolved")]
    catch_rate = (len(caught) / len(scoreable)) if scoreable else 0.0
    leads = sorted(r.lead_days for r in caught if r.lead_days is not None)
    median_lead = leads[len(leads) // 2] if leads else None

    # ---- healthy scorecard ----
    print("\nHEALTHY CONTROLS")
    for r in healthy:
        icon, label = _CTRL_STATUS.get(r.status, ("—", r.status.upper()))
        if r.status == "clean":
            sec = (f"   (secondary: {len(r.single_fp_dates)} single-metric Stress qtr"
                   f"{'s' if len(r.single_fp_dates) != 1 else ''})" if r.single_fp_dates else "")
            detail = f"no confirmed Stress+ in 3-year window{sec}"
        elif r.status == "annotated":
            detail = r.note
        elif r.status == "false_positive":
            mets = sorted({m for sp in r.timeline if _confirmed(sp) for m in sp.stress_metrics})
            detail = f"fired ≥{CONFIRM_COUNT}-metric Stress+ on {len(r.fp_dates)} qtr(s): {', '.join(mets)}"
        else:
            detail = "—"
        print(f"  {icon} {label:<16} {r.case.name:<18} {detail}")

    resolved = [r for r in healthy if r.status in ("clean", "annotated", "false_positive")]
    fired = [r for r in resolved if r.status in ("annotated", "false_positive")]
    fp_rate = (len(fired) / len(resolved)) if resolved else 0.0

    # ---- stressed-survivor scorecard (early-warning test) ----
    print("\nSTRESSED SURVIVORS  (flag Stress+ during the stress window; clean before & after)")
    for r in survivors:
        icon, label = _SURVIVOR_STATUS.get(r.status, ("—", r.status.upper()))
        win = f"{_q_label(r.case.stress_start)}→{_q_label(r.case.stress_end)}"
        if r.status in ("detected_clean", "detected_noisy"):
            bits = [f"flagged {len(r.during_dates)} qtr(s) during stress"]
            if not r.clean_before:
                bits.append(f"{len(r.before_dates)} pre-stress")
            if not r.clean_after:
                bits.append(f"{len(r.after_dates)} post-stress")
            detail = f"{win}: " + "; ".join(bits) + f"   peak {r.peak_level or '—'}"
        elif r.status == "missed_stress":
            detail = f"{win}: never confirmed Stress+ during window   peak {r.peak_level or '—'}"
        else:
            detail = r.note or "—"
        print(f"  {icon} {label:<18} {r.case.name:<22} {detail}")

    surv_scoreable = [r for r in survivors
                      if r.status in ("detected_clean", "detected_noisy", "missed_stress")]
    detected = [r for r in surv_scoreable if r.stress_detected]
    detected_clean = [r for r in surv_scoreable if r.status == "detected_clean"]
    stress_detect_rate = (len(detected) / len(surv_scoreable)) if surv_scoreable else 0.0
    surv_excluded = [r for r in survivors if r.status in ("insufficient_history", "unresolved")]

    # ---- secondary view (single-metric rule, pre-confirmation) ----
    single_caught = sum(1 for r in scoreable if r.single_first_date
                        and r.case.event_date
                        and (_d(r.case.event_date) - _d(r.single_first_date)).days >= LEAD_DAYS_REQUIRED)
    single_fired = sum(1 for r in resolved if r.single_fp_dates)
    print("\n" + "-" * 84)
    print(f"  SECONDARY (single-metric Stress+ rule): distressed caught {single_caught}/{len(scoreable)}"
          f"  ·  controls firing {single_fired}/{len(resolved)}"
          f"   → confirmation removes {single_fired - len(fired)} control false positive(s)")

    # ---- scorecard line + gate ----
    catch_pass = catch_rate >= CATCH_RATE_TARGET
    fp_pass = fp_rate <= FP_RATE_TARGET
    lead_pass = (median_lead or 0) >= LEAD_DAYS_REQUIRED
    overall = catch_pass and fp_pass and lead_pass

    print("\n" + line)
    print(f"  SCORECARD: {len(caught)}/{len(scoreable)} distressed caught ≥{LEAD_QUARTERS_REQUIRED} quarters early"
          f"  ·  catch rate {catch_rate:.0%}  ·  FP rate {fp_rate:.0%}"
          f"  ·  median lead {_months(median_lead)}")
    print(f"             stress detection {len(detected)}/{len(surv_scoreable)} survivors flagged during stress"
          f"  ·  rate {stress_detect_rate:.0%}"
          f"  ·  {len(detected_clean)}/{len(surv_scoreable)} also clean before & after")
    if excluded:
        for r in excluded:
            print(f"             (excluded: {r.case.name} — {r.status}: {r.note})")
    for r in surv_excluded:
        print(f"             (survivor excluded: {r.case.name} — {r.status}: {r.note})")
    print(f"  TARGETS:   catch ≥{CATCH_RATE_TARGET:.0%} {'✅' if catch_pass else '❌'}"
          f"   ·  FP ≤{FP_RATE_TARGET:.0%} {'✅' if fp_pass else '❌'}"
          f"   ·  median lead ≥{LEAD_QUARTERS_REQUIRED}Q {'✅' if lead_pass else '❌'}")
    print(f"\n  RESULT: {'✅ PASS' if overall else '❌ FAIL'}")
    print(line)
    return overall


def _to_json(distressed: list[CaseResult], healthy: list[CaseResult],
             survivors: list[CaseResult]) -> dict:
    def case_dict(r: CaseResult) -> dict:
        return {
            "name": r.case.name, "cik": r.case.cik, "event_date": r.case.event_date,
            "stress_start": r.case.stress_start, "stress_end": r.case.stress_end,
            "resolved_name": r.resolved_name, "status": r.status,
            "first_stress_date": r.first_stress_date, "lead_days": r.lead_days,
            "peak_level": r.peak_level, "peak_stress_metrics": r.peak_stress_metrics,
            "single_metric_first_date": r.single_first_date,
            "n_preevent_quarters": r.n_preevent_quarters, "fp_dates": r.fp_dates,
            "single_metric_fp_dates": r.single_fp_dates, "note": r.note,
            "stress_detected": r.stress_detected, "clean_before": r.clean_before,
            "clean_after": r.clean_after, "during_dates": r.during_dates,
            "before_dates": r.before_dates, "after_dates": r.after_dates,
            "timeline": [{"as_of": s.as_of, "level": s.level, "ordinal": s.ordinal,
                          "stress_metrics": s.stress_metrics, "flag_count": s.flag_count,
                          "latest_period": s.latest_period} for s in r.timeline],
        }
    return {"distressed": [case_dict(r) for r in distressed],
            "healthy": [case_dict(r) for r in healthy],
            "stressed_survivors": [case_dict(r) for r in survivors]}


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    json_path = None
    if "--json" in argv:
        i = argv.index("--json")
        json_path = argv[i + 1] if i + 1 < len(argv) else "backtest_report.json"

    client = SecClient()
    print("Running point-in-time backtest (network on cold cache; cached thereafter)…")

    distressed_results: list[CaseResult] = []
    for case in DISTRESSED:
        print(f"  · scoring {case.name} …")
        distressed_results.append(_run_distressed(case, client))

    healthy_results: list[CaseResult] = []
    for case in HEALTHY:
        print(f"  · scoring {case.name} (control) …")
        healthy_results.append(_run_healthy(case, client))

    survivor_results: list[CaseResult] = []
    for case in STRESSED_SURVIVOR:
        print(f"  · scoring {case.name} (stressed survivor) …")
        survivor_results.append(_run_stressed_survivor(case, client))

    overall = _print_report(distressed_results, healthy_results, survivor_results)

    if json_path:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(_to_json(distressed_results, healthy_results, survivor_results), fh, indent=2)
        print(f"\nJSON report written to {json_path}")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
