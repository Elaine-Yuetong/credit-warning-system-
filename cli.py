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
from metrics import compute_metrics, MetricResult
from thresholds import assign_alerts, classify

# Alert icons — canonical legend (§6.5): 🔴 Critical, 🟠 Stress, 🟡 Flag, 🔵 Watch, ✅ None.
ICONS = {"Critical": "🔴", "Stress": "🟠", "Flag": "🟡", "Watch": "🔵", None: "✅"}

# Display rows: (metric_name, label, formatter-key). Order follows the spec table.
DISPLAY_ROWS = [
    ("leverage", "Leverage (F1)", "x"),
    ("interest_coverage", "Interest Coverage", "x"),
    ("free_cash_flow", "FCF ($M)", "m"),
    ("fcf_margin", "FCF Margin", "pct"),
    ("ocf_ebitda_conversion", "OCF/EBITDA Conv", "x"),
    ("current_ratio", "Current Ratio", "x"),
    ("quick_ratio", "Quick Ratio", "x"),
    ("ebitda_margin", "EBITDA Margin", "pct"),
    ("revenue_yoy_growth", "Revenue YoY", "pct"),
    ("debt_to_equity", "D/E Ratio", "x"),
    ("asset_coverage", "Asset Coverage", "x"),
    ("tangible_asset_coverage", "Tangible Asset Cov", "x"),
    ("maturity_coverage_near_term", "Maturity Cov (NT)", "x"),
    ("covenant_headroom_leverage", "Covenant Lev (px)", "x"),
    ("covenant_headroom_coverage", "Covenant Cov (px)", "x"),
    ("loss_provisions_balance", "Loss Prov ($M)", "m"),
]

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

    # Header row.
    header = "METRIC".ljust(LABEL_W)
    for pe in period_ends:
        header += _period_label(pe).rjust(COL_W)
    header += "  " + "ALERT".ljust(ALERT_W)
    print(header)
    print("─" * width)

    # Metric rows.
    for metric_name, label, kind in DISPLAY_ROWS:
        per_period = idx.get(metric_name, {})
        row = label.ljust(LABEL_W)
        for pe in period_ends:
            m = per_period.get(pe)
            row += (_fmt_value(m, kind) if m else "·").rjust(COL_W)
        # Alert = most-recent period's level.
        latest = per_period.get(period_ends[-1]) if period_ends else None
        row += "  " + _alert_cell(latest.alert_level if latest else None).ljust(ALERT_W)
        print(row)

    print("─" * width)

    # Flags section — notable flags from the most recent period, deduped. Routine
    # period-derivation provenance is kept in the DB audit trail but not shown here.
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
            if fl.startswith(routine_prefixes):
                continue
            key = f"{label}:{fl}"
            if key in seen:
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


def run(cik: str) -> int:
    client = SecClient()
    print(f"Fetching EDGAR data for CIK {cik} …")
    result = extract(cik, client=client)
    if result is None:
        print(f"✗ Extraction failed — CIK {cik} did not validate or companyfacts unavailable.")
        return 1

    cls = classify(result.metadata.sic_code)
    metrics = compute_metrics(result, cls.institution_type)
    assign_alerts(metrics, cls)

    conn = db.connect()
    db.upsert_issuer(conn, result.metadata, cls)
    db.write_metrics(conn, result.metadata.cik, metrics)
    conn.close()

    period_ends = [p.period_end for p in result.periods]
    print_table(result.metadata, cls, metrics, period_ends)
    print(f"Stored {len(metrics)} metric rows in {db.DB_PATH}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli.py <CIK>")
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
