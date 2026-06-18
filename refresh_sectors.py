"""refresh_sectors.py — one-time: update stored issuers.sector_group from the corrected classifier.

Re-derives sector_group from each issuer's SIC + EDGAR sicDescription via thresholds.classify(),
so the database reflects the spec-aligned, description-aware sector taxonomy. The description is
re-fetched from the submissions API (cache-served) since it is not stored in the issuers table.
Run after changing classify().
"""
import sqlite3

from extractor import SecClient, fetch_issuer_metadata
from thresholds import classify

conn = sqlite3.connect("credit_warning.db")
issuers = conn.execute("SELECT cik, sic_code FROM issuers").fetchall()
client = SecClient()
updated = 0
for cik, sic in issuers:
    if not sic:
        continue
    # Re-fetch metadata for sicDescription (cache-served). Fall back to SIC-only on failure.
    sic_desc = None
    try:
        m = fetch_issuer_metadata(client, cik)
        if m:
            sic_desc = m.sic_description
    except Exception:
        pass
    cls = classify(sic, sic_desc)
    conn.execute("UPDATE issuers SET sector_group=? WHERE cik=?", (cls.sector_group, cik))
    updated += 1
conn.commit()
conn.close()
print(f"Updated {updated} issuers")
