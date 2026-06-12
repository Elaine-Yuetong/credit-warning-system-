"""run_coverage_check.py — run check_xbrl_coverage across all DB issuers + frequency report.

Step 1: per-company gap reports (via check_xbrl_coverage --gaps-only).
Step 2: consolidated frequency table — which concepts are missing in the most companies,
        with the most common top-candidate tag (computed in-process via analyze()).

Run: python run_coverage_check.py
"""
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict

from check_xbrl_coverage import analyze

conn = sqlite3.connect("credit_warning.db")
ISSUERS = [(r[0], r[1]) for r in conn.execute("SELECT cik, name FROM issuers ORDER BY name")]
conn.close()
CIKS = [c for c, _ in ISSUERS]

# ---- Step 1: per-company gap reports (subprocess, --gaps-only) ----
print("=" * 70)
print(f"  PER-COMPANY GAP REPORTS — {len(CIKS)} issuers")
print("=" * 70)
for cik in CIKS:
    result = subprocess.run(
        [sys.executable, "check_xbrl_coverage.py", cik, "--gaps-only"],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
        print()

# ---- Step 2: frequency analysis (in-process via analyze()) ----
missing_count = Counter()                 # concept -> # companies missing it
candidate_votes = defaultdict(Counter)    # concept -> Counter(top_candidate_tag)
candidate_periods = defaultdict(dict)     # concept -> {tag: max periods seen}
analyzed = 0
for cik, name in ISSUERS:
    res = analyze(cik)
    if res is None:
        continue
    analyzed += 1
    _name, _usgaap, _rows, missing = res
    for key, _concept, cands in missing:
        missing_count[key] += 1
        if cands:
            top_tag, top_n = cands[0]
            candidate_votes[key][top_tag] += 1
            for tag, n in cands:
                candidate_periods[key][tag] = max(candidate_periods[key].get(tag, 0), n)

print("=" * 70)
print(f"  GAP FREQUENCY — across {analyzed} issuers")
print("=" * 70)
print(f"{'CONCEPT':<28}{'MISSING IN':<12}TOP CANDIDATE TAG (periods)")
print("-" * 70)
for concept, n in missing_count.most_common():
    votes = candidate_votes.get(concept)
    if votes:
        tag, _v = votes.most_common(1)[0]
        periods = candidate_periods[concept].get(tag, 0)
        cand = f"{tag} ({periods}p)"
    else:
        cand = "— (no candidate)"
    print(f"{concept:<28}{n:<12}{cand}")
