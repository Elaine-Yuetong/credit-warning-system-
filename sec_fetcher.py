"""
sec_fetcher.py — filing text fetcher for the (future) LLM extraction layer.

Step 1 of the LLM layer: locate and return the cleaned text of a company's Debt Footnote
from its most recent 10-K / 10-Q. This is the unstructured source for covenant thresholds,
maturity schedules, breach/waiver language, and revolver availability — none of which are
in XBRL (see spec/COVENANT_HEADROOM.md "Where it lives" and spec/DEBT_MATURITY_WALL.md
"Where it lives": the Debt Footnote is typically Note 5–9, titled "Debt", "Long-Term Debt",
"Borrowings", or "Credit Facilities").

This module does NO LLM calls — it only fetches and locates text ready for an LLM. It
reuses the SecClient from extractor.py for SEC-compliant rate limiting, backoff, and caching.

Pipeline:
  1. recent_filings()        — read submissions JSON (cached) → most recent 10-K / 10-Q ref
  2. filing_document_url()   — build the Archives URL for the primary document
  3. SecClient.get_text()    — fetch the filing HTML (cached)
  4. html_to_text()          — strip tags/entities to readable text
  5. locate_debt_footnote()  — find the Debt Footnote section by heading + keyword density
"""

from __future__ import annotations

import html as _html
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from extractor import SecClient, pad_cik

# Long cache TTL: filing HTML is immutable once accepted by EDGAR.
FILING_CACHE_TTL_S = 365 * 24 * 60 * 60

# Debt-footnote heading variants (spec: Note 5–9, "Debt"/"Long-Term Debt"/"Borrowings"/
# "Credit Facilities"/"Credit Agreement"). Ordered most-specific → least, lower-cased.
_HEADING_PATTERNS = [
    r"debt and credit facilities",
    r"long[\s\-]term debt and other borrowings",
    r"notes payable and long[\s\-]term debt",
    r"long[\s\-]term debt",
    r"credit facilities",
    r"credit agreement",
    r"notes payable",
    r"indebtedness",
    r"\bborrowings\b",
    r"\bdebt\b",
]

# Signal terms that distinguish the actual Debt Footnote from a passing mention in MD&A or
# the balance sheet. Density of these in the following window scores each candidate heading.
_SIGNAL_TERMS = [
    "covenant", "revolving", "senior notes", "maturit", "interest rate",
    "credit agreement", "term loan", "indenture", "waiver", "in compliance",
    "principal", "aggregate", "due 20", "borrowings", "secured", "unsecured",
]

_WINDOW = 30_000                                   # max chars to capture for the debt footnote
_SHORT_WINDOW = 10_000                              # going-concern / subsequent-events are shorter
_ASSET_WINDOW = 15_000                              # PP&E / intangibles category tables run long
_NOTE_BOUNDARY = re.compile(r"\bnote\s+\d{1,2}\b", re.I)   # next-note heading = section end

# Going-concern note headings (spec: covenant breach / waiver expiry language lives here).
_GOING_CONCERN_HEADINGS = [
    r"going concern",
    r"substantial doubt",
    r"ability to continue",
]
# Subsequent-events note headings (post-period-end waivers, defaults, Chapter 11 filings).
_SUBSEQUENT_EVENTS_HEADINGS = [
    r"subsequent events",
    r"events after",
    r"events subsequent",
]
# Distress vocabulary for scoring the going-concern / subsequent-events windows. Same
# keyword-density scoring as the debt footnote, but tuned to breach/waiver/restructuring
# language rather than instrument detail.
_DISTRESS_SIGNAL_TERMS = [
    "going concern", "substantial doubt", "waiver", "default", "covenant",
    "forbearance", "chapter 11", "bankruptcy", "maturit", "credit agreement",
    "refinanc", "liquidity", "amend", "restructur", "cross-default", "expire",
]

# Loss-contingency / litigation footnote (LOSS_PROVISIONS.md "Where it lives", Location 2).
_LOSS_CONTINGENCY_HEADINGS = [
    r"commitments and contingencies",
    r"loss contingencies",
    r"contingent liabilities",
    r"legal proceedings",
    r"litigation",
]
# Item 3 Legal Proceedings (10-K) / Part II Item 1 (10-Q). "legal proceedings" also catches
# the 10-Q's Part II Item 1 even though the function is named for the 10-K's Item 3.
_LEGAL_PROCEEDINGS_HEADINGS = [
    r"item\s*3",
    r"legal proceedings",
]
# ASC 450 / contingency vocabulary for scoring both windows.
_CONTINGENCY_SIGNAL_TERMS = [
    "probable", "reasonably possible", "remote", "accrued", "settlement",
    "legal proceedings", "contingency", "liability", "reserve", "insurance",
    "indemnification", "regulatory",
]
_CONTINGENCY_WINDOW = 20_000   # contingency notes can be long

# Asset-composition footnotes (Group 6 / ASSET_COVERAGE.md Formula 2). Each has its own
# headings + signal terms; same keyword-density scoring as the other locators.
_PPE_HEADINGS = [
    r"property,?\s+plant\s+and\s+equipment",
    r"property\s+and\s+equipment",
    r"fixed assets",
]
_PPE_SIGNAL_TERMS = [
    "land", "buildings", "building", "machinery", "equipment", "leasehold",
    "improvements", "construction in progress", "accumulated depreciation",
    "depreciation", "useful lives", "property",
]
_INVENTORY_HEADINGS = [
    r"\binventor",          # inventory / inventories
]
_INVENTORY_SIGNAL_TERMS = [
    "raw materials", "work in process", "work-in-process", "finished goods",
    "lifo", "fifo", "lower of cost", "net realizable", "reserve", "inventory",
]
_INTANGIBLES_HEADINGS = [
    r"goodwill and (?:other )?intangible",
    r"(?:other )?intangible assets",
    r"\bintangibles\b",
]
_INTANGIBLES_SIGNAL_TERMS = [
    "patents", "patent", "customer relationships", "customer lists", "trade names",
    "trademark", "developed technology", "capitalized software", "software",
    "amortization", "finite-lived", "indefinite-lived", "intangible",
]
# MD&A capital-expenditure discussion (Group 7a) — maintenance vs growth capex split.
_MDA_CAPEX_HEADINGS = [
    r"liquidity and capital resources",
    r"capital expenditures",
    r"capital resources",
]
_MDA_CAPEX_SIGNAL_TERMS = [
    "maintenance capex", "sustaining capex", "replacement capex", "growth capex",
    "expansion capex", "capital expenditures", "maintenance", "sustaining",
]


@dataclass
class FilingRef:
    form: str  # 10-K or 10-Q
    accession: str # SEC Document Number like "0000320193-23-000106"
    primary_document: str # main HTML Document name
    filing_date: Optional[str] # Submission Date
    report_date: Optional[str] # Report end date


@dataclass
class DebtFootnote:
    cik: str
    form: str
    accession: str
    source_url: str
    found: bool  #whether found the footnote
    # form_type mirrors `form` (10-K / 10-Q); kept so save_to_db() can read source.form_type.
    # Placed here (first defaulted field) because a dataclass requires defaulted fields to
    # follow the required ones above — it cannot sit immediately after `form`.
    form_type: str = ""  # The same form, retain compatibility
    heading: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    text: str = ""  # Debt Footnote main body
    full_text_len: int = 0
    signal_hits: dict = field(default_factory=dict)
    # Additional notes that often carry waiver / breach / restructuring language the 30k
    # debt window can miss. The LLM (Step 2) reads debt + going-concern + subsequent.
    going_concern_text: str = "" # Going Concern Note
    subsequent_events_text: str = ""  # Subsequent Events Note
    # Loss-provisions sources (Group 4): the contingency footnote + legal-proceedings item.
    loss_contingency_text: str = "" 
    legal_proceedings_text: str = ""
    # Asset-composition sources (Group 6): PP&E / inventory / intangibles footnotes.
    ppe_text: str = ""
    inventory_text: str = ""
    intangibles_text: str = ""
    # Capex-split source (Group 7a): MD&A Liquidity & Capital Resources discussion.
    mda_capex_text: str = ""


# --------------------------------------------------------------------------------------
# 1. Discover filings from the submissions JSON
# --------------------------------------------------------------------------------------

def recent_filings(client: SecClient, cik: str,
                   forms: tuple[str, ...] = ("10-K", "10-Q")) -> dict[str, FilingRef]:
    """Return the most recent filing of each requested form for a CIK.

    Reads the submissions JSON (cached by extractor as {cik}_submissions.json). The
    `filings.recent` arrays are parallel and ordered most-recent-first, so the first match
    per form is the latest. Amended forms (10-K/A) are normalised to their base form.
    """
    cik10 = pad_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    data = client.get_json(url, cache_name=f"{cik10}_submissions.json")
    recent = (data or {}).get("filings", {}).get("recent", {})
    accns = recent.get("accessionNumber") or []
    forms_arr = recent.get("form") or []
    docs = recent.get("primaryDocument") or []
    filed = recent.get("filingDate") or []
    reported = recent.get("reportDate") or []

    out: dict[str, FilingRef] = {}
    for i in range(len(accns)):
        base_form = (forms_arr[i] if i < len(forms_arr) else "").replace("/A", "")
        if base_form not in forms or base_form in out:
            continue
        out[base_form] = FilingRef(
            form=base_form,
            accession=accns[i],
            primary_document=docs[i] if i < len(docs) else "",
            filing_date=filed[i] if i < len(filed) else None,
            report_date=reported[i] if i < len(reported) else None,
        )
        if len(out) == len(forms):
            break
    return out


# --------------------------------------------------------------------------------------
# 2. Build the document URL
# --------------------------------------------------------------------------------------

def filing_document_url(cik: str, ref: FilingRef) -> str:
    """Construct the EDGAR Archives URL for a filing's primary document.

    Path form: /Archives/edgar/data/{cik-no-leading-zeros}/{accession-no-dashes}/{document}.
    Note: the folder uses the accession with dashes *removed* (EDGAR convention).
    """
    cik_int = str(int(pad_cik(cik)))                 # strip leading zeros
    acc_nodash = ref.accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{ref.primary_document}"


# --------------------------------------------------------------------------------------
# 3 + 4. Fetch + clean HTML
# --------------------------------------------------------------------------------------

def html_to_text(raw: str) -> str:
    """Reduce filing HTML (incl. inline XBRL) to readable text.

    Block-level closers become newlines first so section headings survive on their own
    lines; remaining tags are stripped, HTML entities decoded, and whitespace collapsed.
    """
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    # Preserve structure: block-level boundaries -> newline.
    s = re.sub(r"(?i)<(?:/p|/div|/tr|/h[1-6]|/li|br\s*/?|/table)\s*>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)               # strip all remaining tags
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]*\n+", "\n\n", s)
    return s.strip()


def fetch_filing_text(client: SecClient, cik: str, ref: FilingRef) -> tuple[str, str]:
    """Fetch a filing's primary document and return (cleaned_text, source_url).
    Returns ("", url) if the document could not be fetched."""
    url = filing_document_url(cik, ref)
    cik10 = pad_cik(cik)
    cache_name = f"{cik10}_{ref.accession.replace('-', '')}.html"
    raw = client.get_text(url, cache_name=cache_name, ttl_s=FILING_CACHE_TTL_S)
    if not raw:
        return "", url
    return html_to_text(raw), url


# --------------------------------------------------------------------------------------
# 5. Locate the Debt Footnote
# --------------------------------------------------------------------------------------

def _candidate_positions(low: str, patterns: list[str]) -> list[tuple[int, str]]:
    """All heading-phrase positions for `patterns`, de-duplicated to one per ~1000 chars."""
    raw: list[tuple[int, str]] = []
    for pat in patterns:
        for m in re.finditer(pat, low):
            raw.append((m.start(), m.group()))
    raw.sort()
    deduped: list[tuple[int, str]] = []
    for pos, phrase in raw:
        if deduped and pos - deduped[-1][0] < 1000:
            continue
        deduped.append((pos, phrase))
    return deduped


def _locate_section(text: str, headings: list[str], signal_terms: list[str],
                    window: int, min_distinct: int = 3,
                    strict: bool = False) -> tuple[bool, Optional[str], int, int, dict]:
    """Generic footnote locator: pick the heading candidate whose following `window` has the
    highest density of `signal_terms`, with a heading-position bonus, trimmed at the next
    "Note N" boundary. Shared by all three locators. Returns
    (found, heading, char_start, char_end, signal_hits).

    `min_distinct` is a SOFT preference by default: every heading match is scored, candidates
    meeting min_distinct get a +5 bonus (so they win over thin ones), but thin candidates are
    still eligible — found=False only when there are zero heading matches. Pass strict=True to
    restore the old hard filter (thin candidates excluded outright); no caller needs it today."""
    low = text.lower()
    best_score = -1
    best: Optional[tuple[int, str, int, dict]] = None  # (start, phrase, end, hits)

    for pos, phrase in _candidate_positions(low, headings):
        win = low[pos:pos + window]
        hits = {term: win.count(term) for term in signal_terms}
        distinct = sum(1 for c in hits.values() if c > 0)
        score = sum(min(c, 5) for c in hits.values())   # cap each term's contribution
        # Hard filter only when strict=True; otherwise min_distinct is a soft preference.
        if strict and distinct < min_distinct:
            continue
        if distinct >= min_distinct:
            score += 5   # soft preference: reward meeting the density threshold
        # Heading bonus: a real footnote title sits at the start of a short line, not
        # mid-sentence. Reward that and back the start up to the heading line.
        line_start = low.rfind("\n", 0, pos) + 1
        heading_like = len(low[line_start:pos].strip()) <= 60
        if heading_like:
            score += 8
        start = line_start if heading_like else pos
        # Tie-break toward later positions (footnotes sit after MD&A).
        if score > best_score or (score == best_score and best and start > best[0]):
            boundary = _NOTE_BOUNDARY.search(low, pos + 2000)
            end = min(boundary.start(), pos + window) if boundary else min(pos + window, len(text))
            best = (start, phrase, end, {k: v for k, v in hits.items() if v})
            best_score = score

    if best is None:
        return False, None, 0, 0, {}
    start, phrase, end, hits = best
    return True, phrase, start, end, hits


def locate_debt_footnote(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Debt Footnote (Note 5–9) by debt-keyword density. 30k-char window."""
    return _locate_section(text, _HEADING_PATTERNS, _SIGNAL_TERMS, _WINDOW, min_distinct=3)


def locate_going_concern_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the going-concern note (waiver/breach/restructuring language). 10k window.
    min_distinct=2 — these notes are short and a single breach event may carry few terms."""
    return _locate_section(text, _GOING_CONCERN_HEADINGS, _DISTRESS_SIGNAL_TERMS,
                           _SHORT_WINDOW, min_distinct=2)


def locate_subsequent_events_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the subsequent-events note (post-period-end waivers, defaults, Chapter 11). 10k."""
    return _locate_section(text, _SUBSEQUENT_EVENTS_HEADINGS, _DISTRESS_SIGNAL_TERMS,
                           _SHORT_WINDOW, min_distinct=2)


def locate_loss_contingency_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Loss Contingency / Commitments & Contingencies footnote. 20k window."""
    return _locate_section(text, _LOSS_CONTINGENCY_HEADINGS, _CONTINGENCY_SIGNAL_TERMS,
                           _CONTINGENCY_WINDOW, min_distinct=3)


def locate_legal_proceedings_item3(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Legal Proceedings item (10-K Item 3 / 10-Q Part II Item 1). 10k window."""
    return _locate_section(text, _LEGAL_PROCEEDINGS_HEADINGS, _CONTINGENCY_SIGNAL_TERMS,
                           _SHORT_WINDOW, min_distinct=2)


def locate_ppe_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Property, Plant & Equipment footnote (category table). 15k window — the
    gross/net category table can be large and was being truncated at 10k."""
    return _locate_section(text, _PPE_HEADINGS, _PPE_SIGNAL_TERMS, _ASSET_WINDOW, min_distinct=3)


def locate_inventory_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Inventory footnote (raw materials / WIP / finished goods). 10k window."""
    return _locate_section(text, _INVENTORY_HEADINGS, _INVENTORY_SIGNAL_TERMS, _SHORT_WINDOW, min_distinct=2)


def locate_intangibles_note(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the Goodwill & Intangibles footnote (intangibles by type). 15k window — the
    intangibles-by-class table can be large and was being truncated at 10k."""
    return _locate_section(text, _INTANGIBLES_HEADINGS, _INTANGIBLES_SIGNAL_TERMS, _ASSET_WINDOW, min_distinct=2)


def locate_mda_capex_section(text: str) -> tuple[bool, Optional[str], int, int, dict]:
    """Find the MD&A capital-expenditures discussion (Liquidity and Capital Resources). 15k window
    — used by Group 7a to detect a disclosed maintenance vs growth capex split. min_distinct=1:
    the heading ("liquidity and capital resources") is a strong, specific anchor, so a single capex
    signal term suffices — companies that disclose a split may use sparse keyword density."""
    return _locate_section(text, _MDA_CAPEX_HEADINGS, _MDA_CAPEX_SIGNAL_TERMS, _ASSET_WINDOW, min_distinct=1)


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def get_debt_footnote(client: SecClient, cik: str, form: str = "10-K") -> Optional[DebtFootnote]:
    """Fetch the most recent `form` filing for `cik` and return its Debt Footnote text.

    Returns None if the filing cannot be located/fetched. Returns a DebtFootnote with
    found=False (and empty text) if the document was fetched but no debt section matched.
    """
    cik10 = pad_cik(cik)
    refs = recent_filings(client, cik, (form,))
    ref = refs.get(form)
    if ref is None or not ref.primary_document:
        return None

    text, url = fetch_filing_text(client, cik, ref)
    if not text:
        return DebtFootnote(cik10, form, ref.accession, url, found=False, form_type=form)

    found, heading, start, end, hits = locate_debt_footnote(text)
    gc_found, _gc_h, gc_s, gc_e, _gc_hits = locate_going_concern_note(text)
    se_found, _se_h, se_s, se_e, _se_hits = locate_subsequent_events_note(text)
    lc_found, _lc_h, lc_s, lc_e, _lc_hits = locate_loss_contingency_note(text)
    lp_found, _lp_h, lp_s, lp_e, _lp_hits = locate_legal_proceedings_item3(text)
    pp_found, _pp_h, pp_s, pp_e, _pp_hits = locate_ppe_note(text)
    iv_found, _iv_h, iv_s, iv_e, _iv_hits = locate_inventory_note(text)
    it_found, _it_h, it_s, it_e, _it_hits = locate_intangibles_note(text)
    mc_found, _mc_h, mc_s, mc_e, _mc_hits = locate_mda_capex_section(text)
    return DebtFootnote(
        cik=cik10, form=form, form_type=form, accession=ref.accession, source_url=url,
        found=found, heading=heading, char_start=start, char_end=end,
        text=text[start:end] if found else "",
        full_text_len=len(text), signal_hits=hits,
        going_concern_text=text[gc_s:gc_e] if gc_found else "",
        subsequent_events_text=text[se_s:se_e] if se_found else "",
        loss_contingency_text=text[lc_s:lc_e] if lc_found else "",
        legal_proceedings_text=text[lp_s:lp_e] if lp_found else "",
        ppe_text=text[pp_s:pp_e] if pp_found else "",
        inventory_text=text[iv_s:iv_e] if iv_found else "",
        intangibles_text=text[it_s:it_e] if it_found else "",
        mda_capex_text=text[mc_s:mc_e] if mc_found else "",
    )


# --------------------------------------------------------------------------------------
# Manual test — Rite Aid (covenant breach + waiver disclosures expected)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "0000084129"  # Rite Aid
    client = SecClient()

    print(f"Debt Footnote fetch — CIK {target}\n" + "=" * 78)
    refs = recent_filings(client, target, ("10-K", "10-Q"))
    if not refs:
        print("No 10-K/10-Q found in submissions.")
        sys.exit(1)
    for form, ref in refs.items():
        print(f"  most recent {form}: accession {ref.accession}  filed {ref.filing_date}  "
              f"doc {ref.primary_document}")

    for form in ("10-K", "10-Q"):
        if form not in refs:
            continue
        print("\n" + "=" * 78)
        print(f"  {form}")
        print("=" * 78)
        fn = get_debt_footnote(client, target, form)
        if fn is None:
            print("  could not locate/fetch filing")
            continue
        print(f"  source: {fn.source_url}")
        print(f"  full cleaned text length: {fn.full_text_len:,} chars")
        print(f"  debt footnote found: {fn.found}")
        if not fn.found:
            print("  (no debt section matched heading + keyword-density test)")
            continue
        print(f"  heading matched: {fn.heading!r}   chars [{fn.char_start:,}–{fn.char_end:,}]  "
              f"({fn.char_end - fn.char_start:,} chars extracted)")
        print(f"  signal hits: {fn.signal_hits}")
        print(f"  going-concern note: {len(fn.going_concern_text):,} chars   "
              f"subsequent-events note: {len(fn.subsequent_events_text):,} chars")

        # Combined text the LLM (Step 2) will receive.
        combined = (fn.text + "\n\n" + fn.going_concern_text + "\n\n"
                    + fn.subsequent_events_text).lower()
        print("  breach/waiver keyword presence across combined text "
              "(debt + going-concern + subsequent):")
        for kw in ("covenant", "waiver", "not in compliance", "in compliance",
                   "event of default", "expire", "forbearance", "chapter 11",
                   "going concern", "substantial doubt"):
            print(f"    {'✓' if kw in combined else '·'} {kw!r}")

        if fn.going_concern_text:
            print("\n  --- first 1200 chars of GOING-CONCERN note ---")
            print("  " + fn.going_concern_text[:1200].replace("\n", "\n  "))
        if fn.subsequent_events_text:
            print("\n  --- first 1000 chars of SUBSEQUENT-EVENTS note ---")
            print("  " + fn.subsequent_events_text[:1000].replace("\n", "\n  "))
