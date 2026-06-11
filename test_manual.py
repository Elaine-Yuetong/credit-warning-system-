"""
test_manual.py — interactive smoke-test harness for the Credit Warning System.

Exercises every major function individually, prints what each returned, and labels
PASS/FAIL wherever the expected value is known. Network sections hit SEC EDGAR live
(cached after the first run via the 24 h TTL cache).

Run:  python test_manual.py
"""

from __future__ import annotations

import sqlite3
import traceback

import db
import extractor as ex
import metrics as mx
import thresholds as th

# CIKs used throughout.
APPLE = "0000320193"
JPM = "0000019617"
RITE_AID = "0000084129"

# ---------------------------------------------------------------------------
# tiny test framework
# ---------------------------------------------------------------------------
_passed = 0
_failed = 0
_results: dict = {}  # cik -> ExtractionResult (reused across sections)


def header(title: str) -> None:
    print("\n" + "═" * 78)
    print(f"  {title}")
    print("═" * 78)


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed, _failed
    tag = "✅ PASS" if condition else "❌ FAIL"
    if condition:
        _passed += 1
    else:
        _failed += 1
    line = f"  [{tag}] {label}"
    if detail:
        line += f"  ·  {detail}"
    print(line)


def info(label: str, value) -> None:
    print(f"         {label}: {value}")


# Shared client (reuses cache + rate limiter across all sections).
CLIENT = ex.SecClient()
# Apple companyfacts reused by several sections.
_apple_facts: dict | None = None


# ===========================================================================
# 1. pad_cik
# ===========================================================================
def test_pad_cik() -> None:
    header("1. pad_cik — valid string / int / already-padded / invalid")
    cases = [
        ("valid string '320193'", lambda: ex.pad_cik("320193"), "0000320193"),
        ("valid int 320193", lambda: ex.pad_cik(320193), "0000320193"),
        ("already-padded '0000320193'", lambda: ex.pad_cik("0000320193"), "0000320193"),
        ("prefixed 'CIK0000320193'", lambda: ex.pad_cik("CIK0000320193"), "0000320193"),
    ]
    for label, fn, expected in cases:
        got = fn()
        info(label, f"-> {got!r}")
        check(label, got == expected, f"expected {expected!r}")

    # Invalid input must raise ValueError.
    try:
        ex.pad_cik("abc")
        check("invalid 'abc' raises ValueError", False, "no exception raised")
    except ValueError as e:
        info("invalid 'abc'", f"raised ValueError: {e}")
        check("invalid 'abc' raises ValueError", True)


# ===========================================================================
# 2. fetch_issuer_metadata
# ===========================================================================
def test_fetch_issuer_metadata() -> None:
    header("2. fetch_issuer_metadata — Apple / JPMorgan / Rite Aid")
    # Note: EDGAR reports JPMorgan as SIC 6021 (National Commercial Banks), not 6020.
    # Both are in the 6000-6499 financial range and classify identically.
    expected_sic = {APPLE: "3571", JPM: "6021", RITE_AID: "5912"}
    expected_name = {APPLE: "APPLE", JPM: "JPMORGAN", RITE_AID: "RITE AID"}
    for cik in (APPLE, JPM, RITE_AID):
        meta = ex.fetch_issuer_metadata(CLIENT, cik)
        print(f"\n   CIK {cik}:")
        if meta is None:
            check(f"{cik} metadata fetched", False, "returned None")
            continue
        info("name", meta.name)
        info("SIC", meta.sic_code)
        info("tickers", meta.tickers)
        info("fiscal_year_end", meta.fiscal_year_end)
        info("has_10k", meta.has_10k)
        check(f"{cik} name matches", expected_name[cik] in meta.name.upper(),
              f"expected contains {expected_name[cik]!r}")
        check(f"{cik} SIC matches", meta.sic_code == expected_sic[cik],
              f"expected {expected_sic[cik]}")
        check(f"{cik} has 10-K history", meta.has_10k is True)


# ===========================================================================
# 3. fetch_company_facts
# ===========================================================================
def test_fetch_company_facts() -> None:
    global _apple_facts
    header("3. fetch_company_facts — Apple — count us-gaap tags")
    facts = ex.fetch_company_facts(CLIENT, APPLE)
    _apple_facts = facts
    if not facts:
        check("Apple companyfacts fetched", False, "returned None/empty")
        return
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    info("entityName", facts.get("entityName"))
    info("us-gaap tag count", len(usgaap))
    check("Apple companyfacts returned", facts is not None)
    check("us-gaap tag count is substantial", len(usgaap) > 100, f"got {len(usgaap)}")


# ===========================================================================
# 4. _classify_span
# ===========================================================================
def test_classify_span() -> None:
    header("4. _classify_span — Q / H1 / 9M / FY / instant / unclassifiable")
    cases = [
        ("Q  (2023-01-01 -> 2023-03-31)", "2023-01-01", "2023-03-31", "Q"),
        ("H1 (2023-01-01 -> 2023-06-30)", "2023-01-01", "2023-06-30", "H1"),
        ("9M (2023-01-01 -> 2023-09-30)", "2023-01-01", "2023-09-30", "9M"),
        ("FY (2023-01-01 -> 2023-12-31)", "2023-01-01", "2023-12-31", "FY"),
        ("instant (no start)", None, "2023-12-31", None),
        ("unclassifiable (~2 months)", "2023-01-01", "2023-02-28", None),
    ]
    for label, start, end, expected in cases:
        days, bucket = ex._classify_span(start, end)
        info(label, f"days={days}, bucket={bucket}")
        check(label, bucket == expected, f"expected bucket {expected}")


# ===========================================================================
# 5. _resolve_instant
# ===========================================================================
def test_resolve_instant() -> None:
    header("5. _resolve_instant — cash & long_term_debt for Apple at a known period end")
    if not _apple_facts:
        check("Apple facts available", False, "section 3 did not load facts")
        return
    ends = ex._quarter_end_universe(_apple_facts)
    if not ends:
        check("Apple period ends found", False)
        return
    end = ends[-1]  # most recent balance-sheet date
    info("period end tested", end)
    for concept_key in ("cash", "long_term_debt"):
        rv = ex._resolve_instant(_apple_facts, ex.CONCEPTS[concept_key], end)
        print(f"\n   {concept_key} @ {end}:")
        info("value", rv.value)
        info("tags", rv.tags)
        info("path", rv.path)
        check(f"{concept_key} resolved (non-null)", rv.value is not None)


# ===========================================================================
# 6. _derive_quarterly_series
# ===========================================================================
def test_derive_quarterly_series() -> None:
    header("6. _derive_quarterly_series — operating_income for Apple")
    if not _apple_facts:
        check("Apple facts available", False, "section 3 did not load facts")
        return
    series = ex._derive_quarterly_series(_apple_facts, ex.CONCEPTS["operating_income"])
    if not series:
        check("series produced", False, "empty series")
        return
    print(f"   {len(series)} period-ends derived (showing most recent 8):")
    paths_seen = set()
    for end in sorted(series.keys())[-8:]:
        rv = series[end]
        paths_seen.add(rv.path)
        val = f"{rv.value:,.0f}" if rv.value is not None else "None"
        info(end, f"value={val}  path={rv.path}")
    check("series non-empty", len(series) > 0)
    check("derivation paths present", bool(paths_seen & {"primary", "reported_quarterly", "derived_quarterly"}),
          f"paths seen: {sorted(paths_seen)}")


# ===========================================================================
# 7. _ttm
# ===========================================================================
def test_ttm() -> None:
    header("7. _ttm — TTM sum equals 4 trailing quarters for a known series")
    ends = ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"]
    vals = {"2023-03-31": 10.0, "2023-06-30": 20.0, "2023-09-30": 30.0,
            "2023-12-31": 40.0, "2024-03-31": 50.0}
    series = {e: ex.ResolvedValue(vals[e], ["TestTag"], [], "derived_quarterly") for e in ends}
    ttm = ex._ttm(series, ends)

    # First three lack 4 trailing quarters -> None.
    info("TTM @ 2023-09-30 (only 3 quarters)", ttm["2023-09-30"].value)
    check("TTM null before 4 quarters", ttm["2023-09-30"].value is None)

    expected_q4 = 10 + 20 + 30 + 40
    info("TTM @ 2023-12-31", f"{ttm['2023-12-31'].value} (expected {expected_q4})")
    check("TTM @ 2023-12-31 = sum of 4 trailing", ttm["2023-12-31"].value == expected_q4)

    expected_q5 = 20 + 30 + 40 + 50  # rolling window drops oldest
    info("TTM @ 2024-03-31", f"{ttm['2024-03-31'].value} (expected {expected_q5})")
    check("TTM @ 2024-03-31 rolls forward (drops oldest)", ttm["2024-03-31"].value == expected_q5)


# ===========================================================================
# 8. extract
# ===========================================================================
def test_extract() -> None:
    header("8. extract — full extraction for Apple / JPMorgan / Rite Aid")
    for cik in (APPLE, JPM, RITE_AID):
        result = ex.extract(cik, client=CLIENT)
        print(f"\n   CIK {cik}:")
        if result is None:
            check(f"{cik} extraction succeeded", False, "returned None")
            continue
        _results[cik] = result
        info("issuer", result.metadata.name)
        info("period count", len(result.periods))
        if result.periods:
            p = result.periods[-1]
            info("most recent period", p.period_end)
            info("  form / filed", f"{p.form_type} / {p.filing_date}")
            info("  long_term_debt", ex_v(p.instant.get("long_term_debt")))
            info("  cash", ex_v(p.instant.get("cash")))
            info("  operating_income (qtr)", ex_v(p.quarterly.get("operating_income")))
            info("  TTM dep_amort", ex_v(p.ttm.get("dep_amort")))
        check(f"{cik} extraction returned periods", len(result.periods) > 0,
              f"{len(result.periods)} periods")


def ex_v(rv) -> str:
    if rv is None or rv.value is None:
        return "None"
    return f"{rv.value:,.0f}"


# ===========================================================================
# 9. compute_metrics (all 19 metrics)
# ===========================================================================
def test_compute_metrics() -> None:
    header("9. compute_metrics — all 19 metrics for Rite Aid (with alert levels)")
    result = _results.get(RITE_AID)
    if result is None:
        check("Rite Aid extraction available", False, "section 8 did not populate")
        return
    cls = th.classify(result.metadata.sic_code)
    metrics = mx.compute_metrics(result, cls.institution_type)
    th.assign_alerts(metrics, cls)

    # Show the most-recent-period value + alert for each distinct metric.
    latest_end = result.periods[-1].period_end
    by_name: dict[str, mx.MetricResult] = {}
    for m in metrics:
        if m.period_end == latest_end:
            by_name[m.metric_name] = m
    print(f"   Most recent period: {latest_end}\n")
    print(f"   {'metric_name':<28}{'value':>14}   {'alert':<10}{'unit'}")
    print("   " + "-" * 64)
    for name in sorted(by_name):
        m = by_name[name]
        val = "None" if m.value is None else f"{m.value:,.3f}"
        alert = m.alert_level or "—"
        print(f"   {name:<28}{val:>14}   {alert:<10}{m.value_unit}")

    distinct = {m.metric_name for m in metrics}
    info("\n   distinct metric_names", len(distinct))
    check("all 19 metric_names computed", len(distinct) == 19, f"got {len(distinct)}")


# ===========================================================================
# 10. SIC classification
# ===========================================================================
def test_classification() -> None:
    header("10. SIC classification — Apple(3571) / JPMorgan(6020) / Rite Aid(5912)")
    expected = {
        "3571": ("Standard", "corporate"),
        "6020": ("NA", "financial"),
        "5912": ("Medial", "corporate"),
    }
    for sic, (exp_vol, exp_type) in expected.items():
        cls = th.classify(sic)
        print(f"\n   SIC {sic}:")
        info("sector_group", cls.sector_group)
        info("volatility_cat", cls.volatility_cat)
        info("institution_type", cls.institution_type)
        info("liquidity_sector / de_group", f"{cls.liquidity_sector} / {cls.de_group}")
        check(f"SIC {sic} volatility = {exp_vol}", cls.volatility_cat == exp_vol)
        check(f"SIC {sic} institution = {exp_type}", cls.institution_type == exp_type)


# ===========================================================================
# 11. Database integrity
# ===========================================================================
def test_database() -> None:
    header("11. Database integrity — store 3 issuers, count tables, sample Rite Aid")
    conn = db.connect()
    # Persist whatever extractions succeeded in section 8.
    stored = 0
    for cik, result in _results.items():
        cls = th.classify(result.metadata.sic_code)
        metrics = mx.compute_metrics(result, cls.institution_type)
        th.assign_alerts(metrics, cls)
        db.upsert_issuer(conn, result.metadata, cls)
        db.write_metrics(conn, result.metadata.cik, metrics)
        stored += 1
    info("issuers stored this run", stored)

    tables = ["issuers", "filings", "metric_values", "time_series", "maturity_schedule", "alerts"]
    print("\n   Row counts:")
    counts = {}
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        counts[t] = n
        info(t, n)
    check("issuers table populated", counts["issuers"] >= 1)
    check("metric_values populated", counts["metric_values"] > 0)
    check("all 6 tables exist", len(counts) == 6)

    print("\n   5 sample metric_values rows for Rite Aid:")
    rows = conn.execute(
        """SELECT metric_name, period_end_date, value, alert_level, extraction_path
           FROM metric_values WHERE cik = ?
           ORDER BY period_end_date DESC, metric_name LIMIT 5""",
        (RITE_AID,),
    ).fetchall()
    print(f"   {'metric_name':<26}{'period':<12}{'value':>14}  {'alert':<10}{'path'}")
    print("   " + "-" * 70)
    for mn, pe, val, al, path in rows:
        v = "None" if val is None else f"{val:,.3f}"
        print(f"   {mn:<26}{pe:<12}{v:>14}  {str(al or '—'):<10}{path}")
    check("Rite Aid sample rows returned", len(rows) > 0, f"{len(rows)} rows")

    ra_count = conn.execute("SELECT COUNT(*) FROM metric_values WHERE cik = ?", (RITE_AID,)).fetchone()[0]
    info("\n   Rite Aid total metric_values rows", ra_count)
    check("Rite Aid has 19 metrics × 8 quarters = 152 rows", ra_count == 152, f"got {ra_count}")
    conn.close()


# ===========================================================================
# main
# ===========================================================================
def main() -> None:
    print("\n" + "#" * 78)
    print("#  CREDIT WARNING SYSTEM — MANUAL FUNCTION TEST HARNESS")
    print("#  (network sections hit SEC EDGAR; cached after first run)")
    print("#" * 78)

    sections = [
        test_pad_cik,
        test_fetch_issuer_metadata,
        test_fetch_company_facts,
        test_classify_span,
        test_resolve_instant,
        test_derive_quarterly_series,
        test_ttm,
        test_extract,
        test_compute_metrics,
        test_classification,
        test_database,
    ]
    for section in sections:
        try:
            section()
        except Exception as e:  # a crashing section is itself a failure, not a halt
            global _failed
            _failed += 1
            print(f"\n   ❌ SECTION CRASHED: {section.__name__}: {e}")
            traceback.print_exc()

    header(f"SUMMARY — {_passed} passed, {_failed} failed")


if __name__ == "__main__":
    main()
