"""
benchmarks.py — sector × size percentile benchmark table (SEGMENT_BENCHMARK_SPEC.md §3).

Computes, for every (sector_group, size_category, sub_sector) cell, the p25/p50/p75
distribution of each benchmarked metric across the company database — the reference layer
for peer-relative comparison. Pure stdlib (sqlite3, statistics); reuses extractor for the
us-gaap:Assets size classification.

Public API:
    recompute_all_benchmarks(db_path="credit_warning.db") -> dict
    get_benchmark(db_path, cik, metric_name) -> dict | None
    classify_quartile(value, p25, p50, p75, metric_name) -> str

CLI:
    python benchmarks.py --recompute
    python benchmarks.py --company <CIK> --metric <metric_name>

DEVIATION FROM SPEC (§3 Step-1 SQL): the spec's selection query includes
`AND alert_level IS NOT NULL  -- exclude suppressed metrics`. That filter is incorrect:
healthy, non-alerting metric values also have alert_level NULL (62% of all non-null values
in this DB), so applying it would discard the bulk of the healthy peer distribution and
bias every benchmark toward stressed/alerting values. Suppressed metrics already have
value=NULL, so `value IS NOT NULL` alone correctly excludes them. We therefore select on
`value IS NOT NULL` and drop the alert_level condition.

DISTRESSED EXCLUSION: peer distributions are computed from healthy companies only — the 30
distressed case-library firms are flagged `benchmark_exclude=1` and omitted from p25/p50/p75
(they are counted per cell as `distressed_count`). This is the spec's Limitation-2 fix
(§3): a distressed firm should be benchmarked against healthy peers, not against other
distressed firms. (The spec nominally defers this to Phase 5; enabled here by request.)
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from statistics import quantiles

DB_DEFAULT = "credit_warning.db"

# Metric polarity (SEGMENT_BENCHMARK_SPEC.md §3 "Metric Polarity").
HIGHER_IS_BETTER = {
    "interest_coverage", "free_cash_flow", "fcf_margin",
    "moody_adjusted_fcf", "rcf_net_debt", "ocf_ebitda_conversion",
    "current_ratio", "quick_ratio", "ebitda_margin",
    "revenue_yoy_growth", "asset_coverage", "tangible_asset_coverage",
    "liquidation_asset_coverage", "maturity_coverage_near_term",
}
LOWER_IS_BETTER = {"leverage", "debt_to_equity"}

# The 16 benchmarked metrics (the 19 metrics minus the 3 excluded per §3).
BENCHMARK_METRICS = HIGHER_IS_BETTER | LOWER_IS_BETTER
EXCLUDED_METRICS = {
    "covenant_headroom_leverage", "covenant_headroom_coverage", "loss_provisions_balance",
}

# Size breakpoints (Section 1).
LARGE_MIN = 10_000_000_000
MID_MIN = 1_000_000_000


# --------------------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------------------

def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Add issuer columns + sector_benchmarks table (idempotent)."""
    for col, decl in (("size_category", "TEXT DEFAULT 'Unknown'"),
                      ("sub_sector", "TEXT DEFAULT NULL"),
                      ("benchmark_exclude", "INTEGER DEFAULT 0")):
        try:
            conn.execute(f"ALTER TABLE issuers ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sector_benchmarks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_group    TEXT NOT NULL,
            size_category   TEXT NOT NULL,
            sub_sector      TEXT,
            metric_name     TEXT NOT NULL,
            p25             REAL,
            p50             REAL,
            p75             REAL,
            company_count   INTEGER NOT NULL,
            distressed_count INTEGER DEFAULT 0,
            fallback_level  TEXT NOT NULL,
            outliers_excluded INTEGER DEFAULT 0,
            computed_at     TEXT NOT NULL,
            UNIQUE (sector_group, size_category, sub_sector, metric_name)
        )
    """)
    conn.commit()


# --------------------------------------------------------------------------------------
# Size classification (Section 1) — us-gaap:Assets direct fetch (canonical, ~100% coverage)
# --------------------------------------------------------------------------------------

def _latest_instant(usgaap: dict, tag: str):
    node = usgaap.get(tag)
    if not node:
        return None
    best_end, best_val = None, None
    for points in node.get("units", {}).values():
        for p in points:
            end = p.get("end")
            if end and (best_end is None or end > best_end) and p.get("val") is not None:
                best_end, best_val = end, p["val"]
    return best_val


def _size_from_assets(client, cik: str) -> str:
    """Size tier from us-gaap:Assets (Section 1), with AssetsCurrent+Noncurrent fallback."""
    from extractor import fetch_company_facts
    facts = fetch_company_facts(client, cik)
    usgaap = (facts or {}).get("facts", {}).get("us-gaap", {})
    assets = _latest_instant(usgaap, "Assets")
    if assets is None:
        cur = _latest_instant(usgaap, "AssetsCurrent")
        non = _latest_instant(usgaap, "AssetsNoncurrent")
        assets = (cur + non) if (cur is not None and non is not None) else None
    if assets is None:
        return "Unknown"
    if assets >= LARGE_MIN:
        return "Large"
    if assets >= MID_MIN:
        return "Mid"
    return "Small"


def _populate_sizes(conn: sqlite3.Connection) -> dict:
    """Compute & store size_category for issuers where it's missing/Unknown. Returns {cik: size}."""
    from extractor import SecClient
    client = SecClient()
    sizes = {}
    rows = conn.execute("SELECT cik, size_category FROM issuers").fetchall()
    for cik, cur in rows:
        if cur and cur not in ("Unknown", None):
            sizes[cik] = cur
            continue
        size = _size_from_assets(client, cik)
        conn.execute("UPDATE issuers SET size_category=? WHERE cik=?", (size, cik))
        sizes[cik] = size
    conn.commit()
    return sizes


def _distressed_ciks() -> set:
    """Authoritative distressed set from the backtest case library."""
    try:
        from backtest import DISTRESSED
        from extractor import pad_cik
        return {pad_cik(c.cik) for c in DISTRESSED}
    except Exception:
        return set()


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------

def _exclude_outliers(pairs: list) -> tuple:
    """Winsorise (cik, value) pairs at ±3 std (§3 Step 5). Returns (kept_pairs, n_excluded)."""
    if len(pairs) < 4:
        return pairs, 0
    vals = [v for _c, v in pairs]
    mean = sum(vals) / len(vals)
    std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    if std == 0:
        return pairs, 0
    kept = [(c, v) for c, v in pairs if abs(v - mean) <= 3 * std]
    return kept, len(pairs) - len(kept)


def _percentiles(values: list):
    """(p25, p50, p75) via statistics.quantiles(n=4). Requires len >= 3."""
    if len(values) < 3:
        return None, None, None
    qs = quantiles(values, n=4)
    return qs[0], qs[1], qs[2]


# --------------------------------------------------------------------------------------
# Recompute
# --------------------------------------------------------------------------------------

def recompute_all_benchmarks(db_path: str = DB_DEFAULT) -> dict:
    """Recompute all sector_benchmarks rows from current metric_values data.
    Stores cells at three granularities (full / no_subsector / sector_only) so get_benchmark
    can pick the most specific available. Returns {(sector,size,sub,metric): company_count}."""
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    _populate_sizes(conn)

    # Mark distressed case-library companies benchmark_exclude=1 so peer distributions are
    # healthy-company-only (SEGMENT_BENCHMARK_SPEC.md Limitation 2 fix): a distressed firm is
    # benchmarked against healthy peers, not against other distressed firms.
    distressed = _distressed_ciks()
    if distressed:
        qs = ",".join("?" * len(distressed))
        conn.execute(f"UPDATE issuers SET benchmark_exclude=1 WHERE cik IN ({qs})",
                     tuple(distressed))
        conn.commit()

    # Issuer attributes (incl. benchmark_exclude flag).
    issuers = {}
    for cik, sector, size, sub, exc in conn.execute(
            "SELECT cik, sector_group, size_category, sub_sector, benchmark_exclude FROM issuers"):
        issuers[cik] = (sector or "Unknown", size or "Unknown", sub, bool(exc))

    # Latest non-null value per (cik, metric) for the 16 benchmarked metrics.
    placeholders = ",".join("?" * len(BENCHMARK_METRICS))
    rows = conn.execute(
        f"SELECT cik, metric_name, value, period_end_date FROM metric_values "
        f"WHERE value IS NOT NULL AND metric_name IN ({placeholders})",
        tuple(BENCHMARK_METRICS),
    )
    latest = {}  # (cik, metric) -> (period_end, value)
    for cik, metric, value, pe in rows:
        key = (cik, metric)
        if key not in latest or pe > latest[key][0]:
            latest[key] = (pe, value)

    # Build cell -> metric -> [(cik, value)] at three granularities.
    # level 'full' keyed by (sector,size,sub); 'no_subsector' by (sector,size); 'sector_only' by (sector,)
    from collections import defaultdict
    full = defaultdict(lambda: defaultdict(list))
    nosub = defaultdict(lambda: defaultdict(list))
    sectoronly = defaultdict(lambda: defaultdict(list))
    for (cik, metric), (_pe, value) in latest.items():
        if cik not in issuers:
            continue
        sector, size, sub, exc = issuers[cik]
        if sub:
            full[(sector, size, sub)][metric].append((cik, value, exc))
        nosub[(sector, size)][metric].append((cik, value, exc))
        sectoronly[(sector,)][metric].append((cik, value, exc))

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("DELETE FROM sector_benchmarks")
    summary = {}

    def store(sector, size_store, sub_store, metric, members, level):
        # Healthy peers feed the distribution; distressed (excluded) peers are only counted.
        healthy = [(c, v) for c, v, ex in members if not ex]
        excluded = [(c, v) for c, v, ex in members if ex]
        kept, n_out = _exclude_outliers(healthy)
        if len(kept) < 3:
            return
        vals = [v for _c, v in kept]
        p25, p50, p75 = _percentiles(vals)
        dcount = len(excluded)   # distressed peers excluded from this cell's distribution
        conn.execute(
            "INSERT OR REPLACE INTO sector_benchmarks "
            "(sector_group,size_category,sub_sector,metric_name,p25,p50,p75,"
            " company_count,distressed_count,fallback_level,outliers_excluded,computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (sector, size_store, sub_store, metric, p25, p50, p75,
             len(kept), dcount, level, n_out, now),
        )
        summary[(sector, size_store, sub_store, metric)] = len(kept)

    for (sector, size, sub), metrics in full.items():
        for metric, pairs in metrics.items():
            store(sector, size, sub, metric, pairs, "full")
    for (sector, size), metrics in nosub.items():
        for metric, pairs in metrics.items():
            store(sector, size, None, metric, pairs, "no_subsector")
    for (sector,), metrics in sectoronly.items():
        for metric, pairs in metrics.items():
            store(sector, "ALL", None, metric, pairs, "sector_only")

    conn.commit()
    conn.close()
    return summary


# --------------------------------------------------------------------------------------
# Lookup with fallback cascade
# --------------------------------------------------------------------------------------

def get_benchmark(db_path: str, cik: str, metric_name: str) -> dict | None:
    """Most-specific available benchmark for a company+metric via the fallback cascade."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    iss = conn.execute(
        "SELECT sector_group, size_category, sub_sector FROM issuers WHERE cik=?", (cik,)
    ).fetchone()
    if iss is None:
        conn.close()
        return None
    sector, size, sub = iss["sector_group"], iss["size_category"], iss["sub_sector"]
    row = conn.execute(
        """
        SELECT sector_group, size_category, sub_sector, p25, p50, p75,
               company_count, distressed_count, fallback_level
        FROM sector_benchmarks
        WHERE metric_name = :metric
          AND sector_group = :sector
          AND (
              (size_category = :size AND sub_sector IS :sub)
           OR (size_category = :size AND sub_sector IS NULL)
           OR (size_category = 'ALL' AND sub_sector IS NULL)
          )
        ORDER BY CASE fallback_level
            WHEN 'full' THEN 1 WHEN 'no_subsector' THEN 2 WHEN 'sector_only' THEN 3 END
        LIMIT 1
        """,
        {"metric": metric_name, "sector": sector, "size": size, "sub": sub},
    ).fetchone()
    conn.close()
    if row is None:
        return None
    size_label = row["size_category"] if row["size_category"] != "ALL" else "all sizes"
    sub_label = f" — {row['sub_sector']}" if row["sub_sector"] else ""
    desc = (f"{size_label} {row['sector_group']}{sub_label} "
            f"({row['company_count']} companies, level={row['fallback_level']})")
    return {
        "p25": row["p25"], "p50": row["p50"], "p75": row["p75"],
        "company_count": row["company_count"], "distressed_count": row["distressed_count"],
        "fallback_level": row["fallback_level"], "cell_description": desc,
    }


# --------------------------------------------------------------------------------------
# Quartile classification (polarity-adjusted, §3)
# --------------------------------------------------------------------------------------

def classify_quartile(value, p25, p50, p75, metric_name) -> str:
    """'top' / 'upper_middle' / 'lower_middle' / 'bottom' / 'no_data'."""
    if value is None or p25 is None or p50 is None or p75 is None:
        return "no_data"
    if metric_name in LOWER_IS_BETTER:
        if value <= p25:
            return "top"
        if value <= p50:
            return "upper_middle"
        if value <= p75:
            return "lower_middle"
        return "bottom"
    # higher-is-better (default)
    if value >= p75:
        return "top"
    if value >= p50:
        return "upper_middle"
    if value >= p25:
        return "lower_middle"
    return "bottom"


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def _company_latest_value(db_path: str, cik: str, metric: str):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT value FROM metric_values WHERE cik=? AND metric_name=? AND value IS NOT NULL "
        "ORDER BY period_end_date DESC LIMIT 1", (cik, metric)).fetchone()
    conn.close()
    return row[0] if row else None


def main(argv: list[str]) -> int:
    db = DB_DEFAULT
    if "--recompute" in argv:
        summary = recompute_all_benchmarks(db)
        cells = {(s, sz, sub) for (s, sz, sub, _m) in summary}
        print(f"Recomputed sector_benchmarks: {len(summary)} (cell × metric) rows across "
              f"{len(cells)} cells.")
        by_level = {}
        conn = sqlite3.connect(db)
        for lvl, n in conn.execute("SELECT fallback_level, COUNT(*) FROM sector_benchmarks GROUP BY fallback_level"):
            by_level[lvl] = n
        conn.close()
        print(f"  rows by fallback_level: {by_level}")
        return 0

    if "--company" in argv and "--metric" in argv:
        cik = argv[argv.index("--company") + 1]
        metric = argv[argv.index("--metric") + 1]
        bm = get_benchmark(db, cik, metric)
        value = _company_latest_value(db, cik, metric)
        print(f"\nBenchmark — CIK {cik} · {metric}")
        if bm is None:
            print("  No benchmark available (no peer cell met the 3-company minimum).")
            return 0
        q = classify_quartile(value, bm["p25"], bm["p50"], bm["p75"], metric)
        polarity = "lower-is-better" if metric in LOWER_IS_BETTER else "higher-is-better"
        vstr = "n/a" if value is None else f"{value:.3f}"
        print(f"  company value : {vstr}")
        print(f"  peer cell     : {bm['cell_description']}")
        print(f"  peers: {bm['company_count']} healthy · {bm['distressed_count']} distressed excluded")
        print(f"  p25 / p50 / p75: {bm['p25']:.3f} / {bm['p50']:.3f} / {bm['p75']:.3f}  ({polarity})")
        print(f"  QUARTILE      : {q.upper().replace('_', ' ')}")
        return 0

    print("Usage:\n  python benchmarks.py --recompute\n"
          "  python benchmarks.py --company <CIK> --metric <metric_name>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
