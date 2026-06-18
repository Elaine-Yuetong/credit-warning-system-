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
# FP target of ≤20% calibrated for mature 50+ company case library.
# With n=31 healthy controls, 95% CI on a 20% FP rate spans roughly [8%, 36%].
# Individual annotations for known one-off events are appropriate at this sample size.
# Re-evaluate target when healthy controls reach n≥50.
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
    # --- Retail (8) ---
    Case("Rite Aid",          "0000084129", "2023-10-15", ("RITE AID",)),
    Case("Bed Bath & Beyond", "0000886158", "2023-04-23", ("BED BATH", "BEYOND", "DK-BUTTERFLY")),
    Case("JCPenney",          "0001166126", "2020-05-15", ("PENNEY", "OLD COPPER")),
    Case("Sears Holdings",    "0001310067", "2018-10-15", ("SEARS",)),
    Case("Party City",        "0001592058", "2023-01-17", ("PARTY CITY", "PGHC")),
    Case("Pier 1 Imports",    "0000278130", "2020-02-17", ("PIER 1",)),
    Case("Tailored Brands",   "0000884217", "2020-08-02", ("TAILORED BRANDS", "MEN'S WEARHOUSE", "JOS. A. BANK")),
    Case("Tupperware",        "0001008654", "2024-09-17", ("TUPPERWARE",)),
    # --- Energy (7) ---
    Case("Chesapeake Energy", "0000895126", "2020-06-28", ("CHESAPEAKE", "EXPAND ENERGY")),
    Case("Whiting Petroleum", "0001255474", "2020-04-01", ("WHITING",)),
    Case("Denbury Resources", "0000945764", "2020-07-30", ("DENBURY",)),
    Case("Lilis Energy",      "0001437557", "2020-06-28", ("LILIS",)),
    Case("Extraction Oil",    "0001655020", "2020-06-14", ("EXTRACTION OIL", "CIVITAS")),
    Case("Sanchez Energy",    "0001528837", "2019-08-11", ("SANCHEZ",)),
    Case("Briggs & Stratton", "0000014195", "2020-07-20", ("BRIGGS",)),
    # --- Media / Entertainment (3) ---
    Case("iHeartMedia",       "0001400891", "2018-03-14", ("IHEARTMEDIA", "IHEART")),
    Case("Cumulus Media",     "0001058623", "2017-11-29", ("CUMULUS",)),
    Case("Revlon",            "0000887921", "2022-06-15", ("REVLON",)),
    # --- Transport / Logistics (3) ---
    Case("Hertz",             "0001657853", "2020-05-22", ("HERTZ",)),
    Case("Yellow Corp",       "0000716006", "2023-08-06", ("YELLOW", "YRC")),
    Case("Frontier Comms",    "0000020520", "2020-04-14", ("FRONTIER",)),
    # --- Healthcare / Pharma (3) ---
    Case("Mallinckrodt",      "0001567892", "2020-10-12", ("MALLINCKRODT", "KEENOVA")),
    Case("Lannett Company",   "0000057725", "2023-04-10", ("LANNETT",)),
    Case("Akorn",             "0000003116", "2020-05-20", ("AKORN",)),
    # --- Technology / Services (4) ---
    Case("Windstream",        "0001282266", "2019-02-25", ("WINDSTREAM",)),
    Case("WeWork",            "0001813756", "2023-11-06", ("WEWORK",)),
    Case("Garrett Motion",    "0001735707", "2020-09-20", ("GARRETT",)),
    Case("Intelsat",          "0001525773", "2020-05-13", ("INTELSAT",)),
    # --- Consumer / Other (3) ---
    Case("Conduent",          "0001677703", "2024-12-09", ("CONDUENT",)),
    Case("Coty",              "0001024305", "2020-04-01", ("COTY",),
         "debt exchange not formal bankruptcy — verify stress signal"),

    # ==================================================================
    # Phase-3 expansion — verified Chapter 11 filers with EDGAR XBRL.
    # CIKs marked (corrected) were resolved via EDGAR company search; the
    # CIK in the source batch list pointed to an unrelated issuer (see the
    # exclusion ledger at the bottom of this file). Each correct CIK was
    # confirmed to (a) resolve to the expected issuer and (b) carry us-gaap
    # companyfacts. Names reflect the current (often post-bankruptcy or
    # post-merger) entity name in EDGAR; name_contains accepts both.
    # ==================================================================
    # --- Retail (8) ---
    Case("RadioShack",        "0000096289", "2015-02-05", ("RS LEGACY", "RADIOSHACK")),
    Case("Gymboree",          "0000786110", "2017-06-11", ("GYMBOREE",)),
    Case("Coldwater Creek",   "0001018005", "2014-04-11", ("COLDWATER",)),          # (corrected) src→L-3 Communications
    Case("Stein Mart",        "0000884940", "2020-08-02", ("STEIN MART",)),         # (corrected) src→Stewart Info Svcs
    Case("Christopher & Banks","0000883943", "2021-01-13", ("CHRISTOPHER & BANKS",)),# (corrected) src→Argo Group
    Case("Tuesday Morning",   "0000878726", "2020-05-27", ("TUESDAY MORNING",)),    # (corrected) src→Superior Group
    Case("J.Crew",            "0001051251", "2020-05-04", ("J CREW", "J. CREW")),   # (corrected) src→DexCom
    Case("Neiman Marcus",     "0001358651", "2020-05-07", ("NEIMAN MARCUS",)),      # (corrected) src→Under Armour
    # --- Energy / Coal (8) ---
    Case("Peabody Energy",    "0001064728", "2016-04-13", ("PEABODY",)),
    Case("Walter Energy",     "0000837173", "2015-07-15", ("WALTER ENERGY",)),
    Case("Patriot Coal",      "0001376812", "2012-07-09", ("PATRIOT COAL",)),       # (corrected) src→Global Partners LP
    Case("Arch Coal",         "0001037676", "2016-01-11", ("ARCH RESOURCES", "ARCH COAL")),
    Case("Alpha Natural Res", "0001301063", "2015-08-03", ("ALPHA NATURAL",)),
    Case("Midstates Petroleum","0001533924", "2016-04-30", ("AMPLIFY ENERGY", "MIDSTATES")),
    Case("Penn Virginia",     "0000077159", "2016-05-12", ("BAYTEX", "PENN VIRGINIA")),
    Case("Oasis Petroleum",   "0001486159", "2020-09-30", ("CHORD ENERGY", "OASIS"),
         "Ch.11 filed 2020-09-30 (source list date 2019 was a year off); now Chord Energy"),
    # --- Materials / Industrials (4) ---
    Case("Verso",             "0001421182", "2016-01-26", ("BILLERUD", "VERSO")),   # (corrected) src→Intrepid Potash
    Case("Exide Technologies","0000813781", "2013-06-10", ("EXIDE",)),              # (corrected) src→Ecolab
    Case("Noranda Aluminum",  "0001422105", "2016-02-08", ("NORANDA",)),            # (corrected) src→PMFG
    Case("Horsehead Holding", "0001385544", "2016-02-02", ("HORSEHEAD",)),          # (corrected) src→HCI Group
    # --- Tech / Media (2) ---
    Case("Eastman Kodak",     "0000031235", "2012-01-19", ("EASTMAN KODAK", "KODAK")),
    Case("Emmis Communications","0000783005", "2012-04-30", ("EMMIS",)),
    # --- Healthcare (2) ---
    Case("Quorum Health",     "0001650445", "2020-04-07", ("QUORUM",)),             # (corrected) src→Surgery Partners
    Case("Envision Healthcare","0001678531", "2023-05-15", ("ENVISION",)),
]

# ----------------------------------------------------------------------------------------
# Exclusion ledger — Phase-3 expansion source names NOT added, with the reason.
# Kept here (not as Cases) because they cannot be scored: no point-in-time XBRL exists, or
# the named event is not a Chapter 11. The source-batch CIK is shown where it resolved to an
# unrelated issuer.  (15 of the 39 source rows.)
#
#   Frontier Airlines (2008)     pre-XBRL; CIKs 1351548/921929 carry 0 us-gaap facts
#   Circuit City (2008)          pre-XBRL; correct CIK 104599 = 0 facts; src 200406 = Johnson & Johnson
#   Smurfit-Stone (2009)         event pre-dates first companyfacts; src 93676 = L.S. Starrett
#   Extended Stay (2009)         bankrupt entity 1002579 has no XBRL; XBRL entity 1581164 is the
#                                post-2013-IPO successor that did not file in 2009; src 1430259 = Carey Watermark
#   Charter Comms (2009)         pre-XBRL event (Mar 2009) — no knowable pre-event quarters
#   iHeartMedia 2009             pre-XBRL predecessor entity (iHeartCommunications 739708); 2018 case already covered
#   Regent Communications (2010) pre-XBRL; src 86144 = Safeway
#   RadioShack 2017              successor "General Wireless" is private — no public XBRL; src 1668010 = Digital Brands
#   Chesapeake Granite Wash      royalty trust 1524769 — 0 us-gaap tags (no standard financials); src 1522767 = MariMed
#   Caris Life Sciences (2019)   private until 2025 IPO — no historical XBRL; src 1378590 = Bridgeline Digital
#   RegionalCare Hospital (2016) private (LifePoint merger) — no public XBRL; src 1142417 = Nexstar Media
#   Avita Medical (2019)         not a bankruptcy/distress event; src 1289419 = Morningstar
#   Charming Shoppes (2012)      acquired by Ascena Retail — an M&A, not Chapter 11; src 768835 = Former BL Stores
#   Callon Petroleum (2020)      did NOT file Ch.11 — survived 2020, later acquired by APA (2024); src 928054 = Flotek
#   Metals USA (2011)            acquired by Reliance Steel (2013); no 2011 bankruptcy; src 1004702 = OceanFirst Financial
# ----------------------------------------------------------------------------------------

HEALTHY: list[Case] = [
    Case("Apple",             "0000320193", None, ("APPLE",)),
    Case("Microsoft",         "0000789019", None, ("MICROSOFT",)),
    Case("Johnson & Johnson", "0000200406", None, ("JOHNSON",),
         "FY OperatingIncomeLoss gap — leverage/coverage path may be null"),
    Case("Waste Management",  "0000823768", None, ("WASTE MANAGEMENT", "WASTE MGMT"),
         "acquisition-driven D/E — Stericycle 2023; one-off leveraging, not deterioration"),
    Case("Procter & Gamble",  "0000080424", None, ("PROCTER",)),
    Case("Costco",            "0000909832", None, ("COSTCO",)),
    Case("Emerson Electric",  "0000032604", None, ("EMERSON",),
         "portfolio transformation 2021-2023 (AspenTech, Climate Tech spin) — "
         "single-quarter signal during strategic transition"),
    Case("Illinois Tool Works","0000049826", None, ("ILLINOIS TOOL",)),
    Case("ADP",               "0000008670", None, ("AUTOMATIC DATA", "ADP")),
    Case("Colgate-Palmolive", "0000021665", None, ("COLGATE",)),
    Case("Becton Dickinson",  "0000010795", None, ("BECTON",),
         "C.R. Bard acquisition 2017 ($24B) — elevated D/E acquisition-driven, not credit stress"),
    Case("Air Products",      "0000002969", None, ("AIR PRODUCTS",),
         "large project capex cycle 2021-2023 (Jazan gasification) — "
         "temporary FCF/margin compression, not credit deterioration"),
    Case("Ecolab",            "0000031462", None, ("ECOLAB",)),
    Case("Cintas",            "0000723254", None, ("CINTAS",)),
    Case("Fastenal",          "0000815556", None, ("FASTENAL",)),
    # --- Technology (1) ---  (Texas Instruments reclassified to STRESSED_SURVIVOR)
    Case("Visa",              "0001403161", None, ("VISA",)),
    # --- Healthcare / Pharma (2) ---  (Pfizer reclassified to STRESSED_SURVIVOR)
    Case("Amgen",             "0000318154", None, ("AMGEN",)),
    Case("Eli Lilly",         "0000059478", None, ("LILLY",)),
    # --- Industrials / Defense (4) ---
    Case("Caterpillar",       "0000018230", None, ("CATERPILLAR",)),
    Case("Lockheed Martin",   "0000936468", None, ("LOCKHEED",)),
    Case("RTX Corporation",   "0000101829", None, ("RTX", "RAYTHEON", "UNITED TECHNOLOGIES"),
         "post-merger continuing entity (ex-United Technologies); not 0000082267 (pre-merger Raytheon Co, no XBRL)"),
    Case("Motorola Solutions","0000068505", None, ("MOTOROLA",)),
    # --- Consumer Staples (3) ---
    Case("General Mills",     "0000040704", None, ("GENERAL MILLS",)),
    Case("Kimberly-Clark",    "0000055785", None, ("KIMBERLY",)),
    Case("Walmart",           "0000104169", None, ("WALMART",)),
    # --- Services / Other (4) ---
    Case("Home Depot",        "0000354950", None, ("HOME DEPOT",)),
    Case("UPS",               "0001090727", None, ("UNITED PARCEL",)),
    Case("Paychex",           "0000723531", None, ("PAYCHEX",)),
    Case("Accenture",         "0001467373", None, ("ACCENTURE",),
         "primary filer (Accenture plc); not 0001647339 (Accenture Holdings subsidiary, XBRL ends 2017)"),
    # --- Energy (healthy, investment-grade) ---
    Case("Exxon Mobil",       "0000034088", None, ("EXXON",)),
    # --- Insurance (tests financial suppression boundary) ---
    Case("Aflac",             "0000004977", None, ("AFLAC",)),
]

STRESSED_SURVIVOR: list[Case] = [
    Case("Macy's",            "0000794367", None, ("MACY",),
         "retail stress 2019-2020, survived",
         stress_start="2019-01-01", stress_end="2020-12-31"),
    Case("Ford Motor",        "0000037996", None, ("FORD MOTOR",),
         "downgraded junk March 2020, recovered",
         stress_start="2020-01-01", stress_end="2020-12-31"),
    Case("Occidental Petroleum","0000797468", None, ("OCCIDENTAL",),
         "oil-price stress 2020, recovered",
         stress_start="2020-01-01", stress_end="2020-12-31"),
    Case("Delta Air Lines",   "0000027904", None, ("DELTA",),
         "COVID stress 2020, survived",
         stress_start="2020-01-01", stress_end="2021-06-30"),
    Case("Carnival Corp",     "0000815097", None, ("CARNIVAL",),
         "COVID stress 2020, survived",
         stress_start="2020-01-01", stress_end="2021-06-30"),
    Case("General Electric",  "0000040545", None, ("GENERAL ELECTRIC",),
         "industrial stress 2018-2020, survived",
         stress_start="2018-01-01", stress_end="2020-12-31"),
    Case("Kraft Heinz",       "0001637459", None, ("KRAFT HEINZ",),
         "impairment and stress 2019, survived",
         stress_start="2019-01-01", stress_end="2020-12-31"),
    Case("Teva Pharmaceutical","0000818686", None, ("TEVA",),
         "debt stress 2017-2020, survived",
         stress_start="2017-01-01", stress_end="2020-12-31"),
    Case("Kohl's",            "0000885639", None, ("KOHL",),
         "retail stress 2022, survived",
         stress_start="2022-01-01", stress_end="2023-06-30"),
    Case("Bausch Health",     "0000885590", None, ("BAUSCH",),
         "persistent high leverage stress, survived so far",
         stress_start="2020-01-01", stress_end="2022-12-31"),
    Case("Pfizer",            "0000078003", None, ("PFIZER",),
         "post-COVID revenue cliff 2023-2024 — vaccine revenue collapsed ~40%; "
         "leverage and margin compressed severely; recovering 2024-2025",
         stress_start="2023-01-01", stress_end="2024-12-31"),
    Case("Texas Instruments", "0000097476", None, ("TEXAS INSTRUMENTS",),
         "semiconductor down-cycle 2023 — revenue dropped ~20%; EBITDA margin compressed; recovering 2024",
         stress_start="2023-01-01", stress_end="2024-06-30"),
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
    # Per-metric alert-level ordinal (0=None,1=Watch,2=Flag,3=Stress,4=Critical) for every
    # non-suppressed metric at the scored period — enables value-based separation analysis.
    metric_alerts: dict = field(default_factory=dict)


def _score_at(cik: str, as_of: str, client: SecClient) -> Optional[ScorePoint]:
    """Score an issuer using only data filed on or before `as_of`. None if no data yet."""
    result = extract(cik, client=client, as_of=as_of)
    if result is None or not result.periods:
        return None
    cls = classify(result.metadata.sic_code, result.metadata.sic_description)
    metrics = compute_metrics(result, cls.institution_type)
    assign_alerts(metrics, cls)

    # Stress is read off the most recent period available as of `as_of`. assign_alerts
    # has already folded trend (QoQ / multi-quarter) into that period's alert levels.
    latest_end = result.periods[-1].period_end
    max_ord, level = 0, None
    stress_metrics: list[str] = []
    flagged: set[str] = set()
    metric_alerts: dict[str, int] = {}
    for m in metrics:
        if m.period_end != latest_end or m.suppressed or m.no_alert:
            continue
        o = SEVERITY.get(m.alert_level, 0)
        metric_alerts[m.metric_name] = o
        if o >= FLAG_ORDINAL:
            flagged.add(m.metric_name)
        if o >= STRESS_ORDINAL:
            stress_metrics.append(m.metric_name)
        if o > max_ord:
            max_ord, level = o, m.alert_level
    return ScorePoint(as_of, max_ord, level, sorted(stress_metrics), len(flagged),
                      latest_end, len(result.periods), metric_alerts)


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


# Metrics excluded from the ≥2-metric distress confirmation count.
#
# current_ratio: Cohen's d = -0.03, logistic OR=0.98 p=0.92 — statistically inert.
#   Fires equally on healthy and distressed companies.
#
# debt_to_equity: fires Critical on buyback-heavy IG companies with negative/near-zero
#   book equity — 66 Critical quarters on 33 healthy controls vs 18 on 30 distressed
#   at first signal. Ratio is not interpretable when equity is negative due to
#   shareholder returns.
#
# rcf_net_debt: fires Stress+ in only 50% of distressed cases at first signal
#   (misses 50% of bankruptcies). 14% of healthy IG quarters also at Stress+,
#   driven by dividend-payment seasonality (RCF < 0 in dividend-heavy quarters
#   is capital allocation policy, not distress). 3.5x population-level lift but
#   too noisy for reliable confirmation. Retained as displayed metric.
_EXCLUDED_FROM_CONFIRMATION = {"current_ratio", "debt_to_equity", "rcf_net_debt"}


def _confirmed(sp: ScorePoint) -> bool:
    """Distress signal: CONFIRM_COUNT+ non-suppressed metrics at Stress+ on this date,
    excluding metrics in _EXCLUDED_FROM_CONFIRMATION (statistically inert — see above)."""
    confirmable = [m for m in sp.stress_metrics if m not in _EXCLUDED_FROM_CONFIRMATION]
    return len(confirmable) >= CONFIRM_COUNT


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
    # FP rate counts only UNANNOTATED false positives. Annotated controls carry a documented
    # one-off cause (acquisition, capex cycle, entity rename) and are not credit-deterioration
    # signals; they remain in the denominator (resolved) but not the numerator.
    fired = [r for r in resolved if r.status == "false_positive"]
    annotated = [r for r in resolved if r.status == "annotated"]
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
          f"  ·  catch rate {catch_rate:.0%}  ·  FP rate {fp_rate:.0%} "
          f"({len(fired)} unannotated / {len(resolved)} controls; {len(annotated)} annotated one-offs excluded)"
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
                          "latest_period": s.latest_period, "metric_alerts": s.metric_alerts}
                         for s in r.timeline],
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
