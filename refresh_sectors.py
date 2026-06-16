"""refresh_sectors.py — one-time: update stored issuers.sector_group from the corrected classifier.

Re-derives sector_group from each issuer's (unchanged) SIC via thresholds.classify(), so the
database reflects the spec-aligned sector taxonomy. Run after changing classify().
"""
import sqlite3

from thresholds import classify

conn = sqlite3.connect("credit_warning.db")
issuers = conn.execute("SELECT cik, sic_code FROM issuers").fetchall()
updated = 0
for cik, sic in issuers:
    if sic:
        cls = classify(int(sic))
        conn.execute("UPDATE issuers SET sector_group=? WHERE cik=?", (cls.sector_group, cik))
        updated += 1
conn.commit()
conn.close()
print(f"Updated {updated} issuers")
