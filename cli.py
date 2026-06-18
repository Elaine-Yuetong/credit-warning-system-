"""
cli.py — Credit Warning System Phase-2 MVP entry point.

Usage:
    python cli.py <CIK>          e.g.  python cli.py 0000320193

Pipeline: fetch + extract (extractor) -> classify + compute (metrics) -> alert
(thresholds) -> persist to SQLite (db) -> print the §6.5 terminal table.
"""









from __future__ import annotations

import sys
from datetime import datetime, timezone

import db
from extractor import SecClient, extract
from metrics import compute_metrics, MetricResult, _load_llm_loss_provisions
from thresholds import assign_alerts, classify

# Alert icons — canonical legend (§6.5): 🔴 Critical, 🟠 Stress, 🟡 Flag, 🔵 Watch, ✅ None.
ICONS = {"Critical": "🔴", "Stress": "🟠", "Flag": "🟡", "Watch": "🔵", None: "✅"}

# Display rows: (metric_name, label, formatter-key). Order follows the spec table.
DISPLAY_ROWS = [
    ("leverage", "Leverage (F1)", "x"),
    ("interest_coverage", "Interest Coverage", "x"),
    ("free_cash_flow", "FCF ($M)", "m"),
    ("fcf_margin", "FCF Margin", "pct"),
    ("moody_adjusted_fcf", "Moody FCF ($M)", "m"),
    ("rcf_net_debt", "RCF/Net Debt", "x"),
    ("ocf_ebitda_conversion", "OCF/EBITDA Conv", "x"),
    ("current_ratio", "Current Ratio", "x"),
    ("quick_ratio", "Quick Ratio", "x"),
    ("ebitda_margin", "EBITDA Margin", "pct"),
    ("revenue_yoy_growth", "Revenue YoY", "pct"),
    ("debt_to_equity", "D/E Ratio", "x"),
    ("asset_coverage", "Asset Coverage", "x"),
    ("tangible_asset_coverage", "Tangible Asset Cov", "x"),
    ("liquidation_asset_coverage", "Liquidation Cov", "x"),
    ("maturity_coverage_near_term", "Maturity Cov (NT)", "x"),
    ("covenant_headroom_leverage", "Covenant Lev (px)", "x"),
    ("covenant_headroom_coverage", "Covenant Cov (px)", "x"),
    ("loss_provisions_balance", "Loss Prov ($M)", "m"),
]

# Table column width settings for aligned output.
COL_W = 9          # width of each period column
LABEL_W = 19       # width of the metric label column
ALERT_W = 14       # width of the alert column


def _fmt_value(m: MetricResult, kind: str) -> str:
    if m.suppressed:
        return "—"
    if m.value is None:
        # Distinguish negative-EBITDA leverage from a plain extraction failure.
        if m.metric_name == "leverage" and (m.extra.get("ebitda") or 0) <= 0 and m.extra.get("ebitda") is not None:
            return "neg"
        return "n/a"
        # Leverage = Net Debt / EBITDA. If EBITDA is negative, the ratio is meaningless (negative "x" doesn't make sense).
        # The system shows "neg" instead of an invalid number.
    if kind == "x":
        return f"{m.value:.2f}x"
    if kind == "pct":
        return f"{m.value:.1f}%"
    if kind == "m":
        return f"{m.value:,.0f}"
    return f"{m.value:.2f}"


def _period_label(period_end: str) -> str:
    try:
        d = datetime.strptime(period_end[:10], "%Y-%m-%d")
        return d.strftime("%b %y")
    except ValueError:
        return period_end[:7]


def _alert_cell(level) -> str:
    icon = ICONS.get(level, "✅")
    return icon if level is None else f"{icon} {level.upper()}"


def print_table(meta, cls, metrics: list[MetricResult], period_ends: list[str]) -> None:
    # Index: metric_name -> {period_end -> MetricResult}
    idx: dict[str, dict[str, MetricResult]] = {}
    for m in metrics:
        idx.setdefault(m.metric_name, {})[m.period_end] = m

    ticker = meta.tickers[0] if meta.tickers else "—"
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    width = LABEL_W + COL_W * len(period_ends) + ALERT_W + 2

    print(f"\nCredit Warning System — {meta.name} ({ticker}) — CIK {meta.cik}")
    print(f"Sector: {cls.sector_group} | Volatility: {cls.volatility_cat} | "
          f"Type: {cls.institution_type} | Last updated: {updated}")
    print("═" * width)
    '''
    Output Example:
    Credit Warning System — APPLE INC (AAPL) — CIK 0000320193
    Sector: Manufacturing / Industrials | Volatility: Standard | Type: corporate
    '''

    # Header row.
    header = "METRIC".ljust(LABEL_W)
    for pe in period_ends:
        header += _period_label(pe).rjust(COL_W)
    header += "  " + "ALERT".ljust(ALERT_W)
    '''
    METRIC            Mar 22  Jun 22  Sep 22  Dec 22    ALERT
    '''
    print(header)
    print("─" * width)

    # Metric rows.
    for metric_name, label, kind in DISPLAY_ROWS:
        per_period = idx.get(metric_name, {})
        row = label.ljust(LABEL_W)
        for pe in period_ends:
            m = per_period.get(pe)
            row += (_fmt_value(m, kind) if m else "·").rjust(COL_W)  ## If a metric has no data for a given period (e.g., the company hasn't disclosed it yet), display "·" as a placeholder.
        # Alert = most-recent period's level.
        latest = per_period.get(period_ends[-1]) if period_ends else None
        row += "  " + _alert_cell(latest.alert_level if latest else None).ljust(ALERT_W)
        print(row)

    print("─" * width)

    # Flags section — notable flags from the most recent period, deduped. Routine
    # period-derivation provenance is kept in the DB audit trail but not shown here.
    # ==================================================================
    # FLAGS SECTION - Display only risk signals, hide data processing traces
    # ==================================================================
    # During data extraction, the system adds flags to track how values were derived.
    # Some flags are just data processing traces (e.g., "Q2 derived: H1 YTD minus Q1").
    # Users don't need to see these - they only care about actual risk signals.
    #
    # routine_prefixes: flags starting with these strings are data processing traces
    #                   → filtered out (not shown to users)
    # Non-routine flags: actual risk signals (e.g., "EBITDA <= 0", "debt extraction failed")
    #                   → displayed to users
    # ==================================================================
    routine_prefixes = ("Q2 derived", "Q3 derived", "Q4 derived",
                        "H1 YTD stored", "9M YTD stored")
    latest_end = period_ends[-1] if period_ends else None
    flag_lines: list[str] = []
    seen: set[str] = set()
    for metric_name, label, _ in DISPLAY_ROWS:
        m = idx.get(metric_name, {}).get(latest_end)
        if not m or not m.flags:
            continue
        for fl in m.flags:
            # Skip data processing traces - users don't need to see these
            if fl.startswith(routine_prefixes):
                continue
            # Deduplicate: same flag might appear for multiple metrics
            key = f"{label}:{fl}"
            if key in seen: #DEDUP： Why seen dedup? The same flag may appear on multiple metrics (e.g., "EBITDA negative" affects both leverage and coverage). Show it only once.
                continue
            seen.add(key)
            flag_lines.append(f"  ⚠ {label}: {fl}")
    if flag_lines:
        print("FLAGS (latest period):")
        for line in flag_lines:
            print(line)
        print("─" * width)
    print(f"Legend: {ICONS['Critical']} Critical  {ICONS['Stress']} Stress  "
          f"{ICONS['Flag']} Flag  {ICONS['Watch']} Watch  {ICONS[None]} No alert")
    print("═" * width)


'''
run() function
    │
    ├── SecClient() ────────────────────► from extractor import SecClient
    │                                      (SEC HTTP client with rate limiting & caching)
    │
    ├── extract(cik, client) ───────────► from extractor import extract
    │                                      (Core extraction: fetches XBRL → parses → organizes into periods)
    │
    ├── classify(sic_code) ─────────────► from thresholds import classify
    │                                      (Maps SIC code → sector group, volatility category, institution type)
    │
    ├── compute_metrics(result, type) ──► from metrics import compute_metrics
    │                                      (Calculates 16 financial metrics × 8 quarters)
    │
    ├── assign_alerts(metrics, cls) ────► from thresholds import assign_alerts
    │                                      (Assigns Watch/Flag/Stress/Critical levels based on thresholds)
    │
    ├── db.connect() ───────────────────► from db import connect
    │                                      (Creates SQLite connection, creates tables if not exist)
    │
    ├── db.upsert_issuer(...) ──────────► from db import upsert_issuer
    │                                      (Insert or update issuer metadata in issuers table)
    │
    ├── db.write_metrics(...) ──────────► from db import write_metrics
    │                                      (Batch insert all MetricResult rows into metric_values table)
    │
    └── print_table(...) ───────────────► Defined in same file (line 90)
                                          (Formats and prints terminal table with alerts)
'''



def run(cik: str) -> int:
    # 1. Extract data
    client = SecClient()
    print(f"Fetching EDGAR data for CIK {cik} …")
    result = extract(cik, client=client)
    if result is None:
        print(f"✗ Extraction failed — CIK {cik} did not validate or companyfacts unavailable.")
        return 1

    #2. Field classfication
    cls = classify(result.metadata.sic_code, result.metadata.sic_description)

    #3. Calculate
    metrics = compute_metrics(result, cls.institution_type)

    #4. Distribute the alert level (loss-provisions tier alert uses the LLM extraction row)
    assign_alerts(metrics, cls, _load_llm_loss_provisions(result.metadata.cik))

    #5. Store into database
    conn = db.connect()
    db.upsert_issuer(conn, result.metadata, cls)
    db.write_metrics(conn, result.metadata.cik, metrics)
    conn.close()


    #6. print
    period_ends = [p.period_end for p in result.periods]
    print_table(result.metadata, cls, metrics, period_ends)
    print(f"Stored {len(metrics)} metric rows in {db.DB_PATH}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli.py <CIK>")
        sys.exit(2)
    sys.exit(run(sys.argv[1]))



