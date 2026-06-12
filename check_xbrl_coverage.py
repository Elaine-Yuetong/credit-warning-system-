"""check_xbrl_coverage.py — diagnose XBRL tag gaps for a company.

For each concept in extractor.CONCEPTS, reports whether any configured us-gaap tag is
present in the company's EDGAR facts. For concepts with NO matching tag, scans the full
tag list for candidates containing the same keywords (derived from the concept name),
ranked by how many periods of data they carry — i.e. suggested fallback tags.

Standalone diagnostic — modifies nothing. Stdlib only (json/collections via extractor reuse).

Usage:  python check_xbrl_coverage.py 0000318154
"""

import sys

from extractor import CONCEPTS, SecClient, fetch_company_facts, pad_cik

LINE = "═" * 70
THIN = "─" * 70


def _usgaap(facts: dict) -> dict:
    return (facts or {}).get("facts", {}).get("us-gaap", {})


def _periods(usgaap: dict, tag: str) -> int:
    """Total data points across all units for a tag (proxy for 'periods of data')."""
    node = usgaap.get(tag)
    if not node:
        return 0
    return sum(len(points) for points in node.get("units", {}).values())


def _keywords(concept_key: str) -> list[str]:
    """Significant keyword tokens from the concept name, e.g. 'interest_expense' -> [interest, expense]."""
    return [t for t in concept_key.lower().split("_") if len(t) >= 3]


def _candidates(usgaap: dict, keywords: list[str]) -> list[tuple[str, int]]:
    """Tags whose lowercased name contains ALL keywords; fall back to the longest single
    keyword if the conjunction matches nothing. Sorted by period count descending."""
    def matching(req: list[str]) -> list[tuple[str, int]]:
        out = [(tag, _periods(usgaap, tag)) for tag in usgaap
               if all(k in tag.lower() for k in req)]
        return sorted(out, key=lambda x: -x[1])

    hits = matching(keywords)
    if not hits and len(keywords) > 1:
        longest = max(keywords, key=len)
        hits = matching([longest])
    return hits


def analyze(cik_arg: str):
    """Return (name, usgaap, rows, missing) for a CIK, or None if facts unavailable.
    rows = [(key, concept, found_tags)]; missing = [(key, concept, candidates)]
    where candidates = [(tag, period_count)] sorted desc. Importable for batch use."""
    cik = pad_cik(cik_arg)
    client = SecClient()
    facts = fetch_company_facts(client, cik)
    if facts is None:
        return None
    usgaap = _usgaap(facts)
    name = facts.get("entityName", "?")
    rows, missing = [], []
    for key, concept in CONCEPTS.items():
        found = [t for t in concept.tags if t in usgaap]
        rows.append((key, concept, found))
        if not found:
            cands = [(t, n) for (t, n) in _candidates(usgaap, _keywords(key))
                     if t not in concept.tags and n > 0]
            missing.append((key, concept, cands))
    return name, usgaap, rows, missing


def main(cik_arg: str, gaps_only: bool = False) -> int:
    res = analyze(cik_arg)
    if res is None:
        print(f"Could not fetch companyfacts for CIK {pad_cik(cik_arg)}.")
        return 1
    name, usgaap, rows, missing = res
    cik = pad_cik(cik_arg)

    if not gaps_only:
        print(f"\nXBRL TAG COVERAGE — {name} ({cik})")
        print(LINE)
        if not usgaap:
            print("No us-gaap facts in this filing (foreign/IFRS filer?) — all concepts unmatched.")
        print(f"{'CONCEPT':<26}{'CONFIGURED TAGS':<34}STATUS")
        print(THIN)
        for key, concept, found in rows:
            cfg = ", ".join(concept.tags)
            cfg_disp = cfg if len(cfg) <= 32 else cfg[:31] + "…"
            if found:
                via = "" if found[0] == concept.tags[0] else f": {found[0]}"
                status = f"✅ found{via}"
            else:
                status = "❌ MISSING"
            print(f"{key:<26}{cfg_disp:<34}{status}")
        print("\n" + LINE)

    print(f"GAP REPORT — {name} ({cik}) — {len(missing)} concept(s) with no matching tag")
    print(LINE)
    if not missing:
        print("None — every concept has at least one configured tag present. ✅")
        return 0
    for key, concept, cands in missing:
        kws = _keywords(key)
        print(f"\n{key}:")
        print(f"  Configured: {', '.join(concept.tags)}")
        print("  Not found in filing.")
        if not cands:
            print(f"  Candidate alternatives (tags containing {' + '.join(repr(k) for k in kws)}): none")
            continue
        print(f"  Candidate alternatives (tags containing {' + '.join(repr(k) for k in kws)}):")
        for i, (tag, n) in enumerate(cands[:8]):
            tail = "  ← RECOMMENDED" if i == 0 else ""
            print(f"    {tag:<48} — {n:>3} periods of data{tail}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python check_xbrl_coverage.py <CIK> [--gaps-only]")
        sys.exit(2)
    sys.exit(main(args[0], gaps_only=("--gaps-only" in sys.argv)))
