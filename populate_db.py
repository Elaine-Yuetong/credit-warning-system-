"""
populate_db.py — populate credit_warning.db with every backtest company.

Runs the same pipeline as cli.run() for each CIK (extract -> classify -> compute_metrics
-> assign_alerts -> upsert_issuer + write_metrics) so the dashboard's Company Monitor
dropdown shows all stored issuers. Uses one shared SecClient (on-disk cache + rate limiting).

Note vs. the originally-sketched snippet: db exposes `write_metrics` (not `upsert_metric_values`),
and cli.run() takes no client argument — so we call the pipeline directly here.

Run:  python populate_db.py   (20-30 min on a cold cache due to SEC rate limiting)
"""

from __future__ import annotations

from extractor import SecClient, extract
from metrics import compute_metrics, _load_llm_loss_provisions
from thresholds import classify, assign_alerts
from db import connect, upsert_issuer, write_metrics

CIKS = [
    # All distressed
    "0000084129", "0000886158", "0001166126", "0001310067", "0001592058",
    "0000278130", "0000884217", "0001008654", "0000895126", "0001255474",
    "0000945764", "0001437557", "0001655020", "0001528837", "0000014195",
    "0001400891", "0001058623", "0000887921", "0001657853", "0000716006",
    "0000020520", "0001567892", "0000057725", "0000003116", "0001282266",
    "0001813756", "0001735707", "0001525773", "0001677703", "0001024305",
    # All healthy controls
    "0000320193", "0000789019", "0000200406", "0000823768", "0000080424",
    "0000909832", "0000032604", "0000049826", "0000008670", "0000021665",
    "0000010795", "0000002969", "0000031462", "0000723254", "0000815556",
    "0000097476", "0001403161", "0000318154", "0001467373", "0000068505",
    "0000040704", "0000055785", "0000104169", "0000354950", "0001090727",
    "0000723531", "0000018230", "0000936468", "0000101829", "0000059478",
    "0000034088", "0000004977",
    # Stressed survivors
    "0000794367", "0000037996", "0000797468", "0000027904", "0000815097",
    "0000040545", "0001637459", "0000818686", "0000885639", "0000885590",
    "0000078003", "0000059478",
]


def process(cik: str, client: SecClient, conn) -> str:
    """Run the cli pipeline for one CIK and persist. Returns the stored issuer name."""
    result = extract(cik, client=client)
    if result is None:
        raise RuntimeError("extraction failed (CIK did not validate or companyfacts unavailable)")
    cls = classify(result.metadata.sic_code)
    metrics = compute_metrics(result, cls.institution_type)
    assign_alerts(metrics, cls, _load_llm_loss_provisions(result.metadata.cik))
    upsert_issuer(conn, result.metadata, cls)
    write_metrics(conn, result.metadata.cik, metrics)
    return result.metadata.name


if __name__ == "__main__":
    ciks = list(dict.fromkeys(CIKS))   # dedupe, preserve order
    client = SecClient()
    conn = connect()
    ok, fail, failures = 0, 0, []
    for i, cik in enumerate(ciks, 1):
        try:
            name = process(cik, client, conn)
            ok += 1
            print(f"[{i}/{len(ciks)}] {cik}  ->  {name}")
        except Exception as e:
            fail += 1
            failures.append((cik, str(e)))
            print(f"[{i}/{len(ciks)}] {cik}  ->  ERROR: {e}")
    conn.close()

    print("\n" + "=" * 60)
    print(f"  POPULATE COMPLETE: {ok} stored, {fail} failed, {len(ciks)} unique CIKs")
    if failures:
        print("  failures:")
        for cik, err in failures:
            print(f"    {cik}: {err}")
    print("=" * 60)
