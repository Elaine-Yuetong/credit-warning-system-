"""
llm_extractor.py — Step 2 of the LLM layer: extract unstructured debt-footnote terms
that cannot be sourced from XBRL — covenant thresholds, debt maturity schedule, covenant
breach / waiver / going-concern language, and revolving-credit availability.

Input is the cleaned footnote text produced by sec_fetcher.get_debt_footnote() (debt
footnote + going-concern note + subsequent-events note). The model is asked for a single
JSON object, which is parsed and validated against the Pydantic schema below.

RELAY COMPATIBILITY: This version works with APIYI and other Claude API relay services.
thinking parameter removed. messages.parse() replaced with messages.create() + manual
JSON parsing. Set ANTHROPIC_BASE_URL=https://api.apiyi.com for APIYI.

Model / API choices (per the claude-api reference):
  - Anthropic Python SDK (matches the project language).
  - Model: claude-opus-4-8 (default; override via `model=`).
  - API key resolved from the environment (ANTHROPIC_API_KEY) — never hardcoded.
  - Base URL overridable via ANTHROPIC_BASE_URL (for relay services).

These outputs feed Phase-3 covenant headroom (replacing the Phase-2 leverage>5.5x proxy),
the full maturity wall, and the revolver component of Available Liquidity Coverage.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    import anthropic
    from pydantic import BaseModel, Field, ValidationError
except ModuleNotFoundError as e:  # pragma: no cover
    raise SystemExit(f"missing dependency: {e}. Run: pip install -r requirements.txt")

from sec_fetcher import DebtFootnote, get_debt_footnote
from extractor import SecClient

DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000

# --------------------------------------------------------------------------------------
# Extraction schema (structured output)
# --------------------------------------------------------------------------------------

class Covenant(BaseModel):
    """One financial maintenance or incurrence covenant disclosed in the footnote."""
    covenant_type: str = Field(
        description="One of: leverage | interest_coverage | fixed_charge_coverage | "
                    "minimum_liquidity | minimum_cash | capex | incurrence | other")
    ratio_name: Optional[str] = Field(
        default=None, description="Exact name as written, e.g. 'Consolidated Net Leverage Ratio'")
    threshold_value: Optional[float] = Field(
        default=None, description="Numeric threshold, e.g. 5.5 or 1.0. Null if not stated numerically.")
    direction: Optional[str] = Field(
        default=None, description="'maximum' (ceiling, e.g. max leverage) or 'minimum' (floor, e.g. min coverage)")
    unit: Optional[str] = Field(
        default=None, description="e.g. 'x' (ratio to 1.00), 'USD millions'")
    testing_frequency: Optional[str] = Field(
        default=None, description="e.g. 'quarterly', 'at all times', 'when availability < $X'")
    is_springing: Optional[bool] = Field(
        default=None, description="True if it is a springing covenant (only tested when a trigger is hit)")
    step_down: Optional[str] = Field(
        default=None, description="Step-down/step-up schedule if disclosed, else null")
    is_maintenance: Optional[bool] = Field(
        default=None, description="True if maintenance covenant (breach can trigger default); "
                                  "False if incurrence-only (limits new debt, no acceleration)")
    evidence: Optional[str] = Field(
        default=None, description="Verbatim sentence from the filing supporting this covenant. Do not paraphrase.")


class MaturityYear(BaseModel):
    """One row of the debt maturity schedule (Maturities of Long-Term Debt table)."""
    year_label: str = Field(description="As labelled, e.g. 'Year 1' / '2025' / 'Less than 1 year' / 'Thereafter'")
    amount_millions: Optional[float] = Field(default=None, description="Principal maturing, in USD millions")


class Revolver(BaseModel):
    """Revolving credit facility availability (LIQUIDITY.md Formula 2 input)."""
    exists: bool = Field(description="True if a revolving credit facility is disclosed")
    total_commitment_millions: Optional[float] = Field(default=None)
    drawn_amount_millions: Optional[float] = Field(default=None, description="Amount currently borrowed/drawn")
    undrawn_availability_millions: Optional[float] = Field(
        default=None, description="Available (undrawn) capacity, net of letters of credit if stated")
    maturity_date: Optional[str] = Field(default=None, description="Facility maturity date as stated")
    evidence: Optional[str] = Field(default=None, description="Verbatim supporting sentence")


class Compliance(BaseModel):
    """Covenant-compliance / going-concern status (the binary breach signal)."""
    status: str = Field(
        description="One of: in_compliance | breach | waiver_obtained | going_concern_doubt | not_disclosed")
    going_concern_flag: bool = Field(
        description="True if the filing expresses substantial doubt about ability to continue as a going concern")
    description: Optional[str] = Field(default=None, description="One-sentence summary of the status")
    evidence: Optional[str] = Field(default=None, description="Verbatim supporting sentence(s). Do not paraphrase.")


class DebtFootnoteExtraction(BaseModel):
    """Complete structured extraction from a company's debt-related footnotes."""
    covenants: list[Covenant] = Field(description="All financial covenants found; empty list if none disclosed")
    maturity_schedule: list[MaturityYear] = Field(
        description="Rows of the maturities-of-long-term-debt table; empty list if not disclosed")
    revolver: Revolver
    compliance: Compliance
    notes: Optional[str] = Field(default=None, description="Anything material not captured above")


SYSTEM_PROMPT = (
    "You are a credit analyst extracting structured facts from the debt-related footnotes of "
    "an SEC 10-K/10-Q filing. Extract ONLY what is explicitly stated in the provided text.\n\n"
    "Rules:\n"
    "- Never infer, estimate, or fill in values that are not in the text. If a field is not "
    "stated, leave it null (or an empty list).\n"
    "- For every covenant, revolver, and the compliance status, copy a short VERBATIM sentence "
    "from the text into the `evidence` field — do not paraphrase. If you cannot find a verbatim "
    "sentence, the item is not really present; omit it.\n"
    "- Distinguish maintenance covenants (breach can trigger default/acceleration) from "
    "incurrence covenants (only limit new debt). Note springing covenants explicitly.\n"
    "- threshold_value is the numeric limit only (e.g. 5.5 for '5.50 to 1.00'); put units in `unit`.\n"
    "- For compliance.status: use 'breach' only if non-compliance is stated; 'waiver_obtained' if a "
    "waiver/forbearance is described; 'going_concern_doubt' if substantial-doubt language is present; "
    "'in_compliance' only if the filing affirms compliance; otherwise 'not_disclosed'.\n"
    "- Maturity amounts are principal in USD millions; convert thousands/billions to millions.\n"
    "- maturity_schedule: If a standard Year 1–5 aggregate table is present, extract those "
    "totals. If only individual instrument maturity dates are disclosed (e.g. '$500M due 2025, "
    "$400M due 2026'), compute the year-by-year totals by summing all instruments maturing in "
    "each fiscal year and populate year1 through year5 accordingly. Use the filing's fiscal "
    "year end date to determine which calendar year maps to year1, year2 etc. If the fiscal "
    "year end is in early calendar year N, year1 = amounts maturing in year N, year2 = year "
    "N+1, etc. Emit one maturity_schedule row per year (year_label 'Year 1', 'Year 2', … and "
    "amount_millions = that year's summed total); do NOT leave maturity_schedule empty when "
    "instrument-level maturities are disclosed."
)

# Output-format directive — the replacement for the removed structured-output mechanic
# (messages.parse/output_format). Appended to SYSTEM_PROMPT at call time so the model
# returns a single JSON object we parse manually. SYSTEM_PROMPT itself is left unchanged.
JSON_OUTPUT_INSTRUCTION = (
    "\n\nRespond with ONLY a single JSON object and nothing else — no prose, no commentary, "
    "no markdown code fences. The JSON object must conform to this JSON Schema:\n"
    + json.dumps(DebtFootnoteExtraction.model_json_schema())
)


# --------------------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------------------

def _extract_json(text: str) -> Optional[dict]:
    """Best-effort parse of a JSON object from model output (relay-safe).

    1. Strips a leading ```json / ``` fence and trailing ``` if present.
    2. Tries json.loads on the whole string.
    3. Falls back to the substring from the first '{' to the last '}'.
    Returns None if every attempt fails.
    """
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    # 1/2. direct parse
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        pass
    # 3. first '{' ... last '}'
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _combine(footnote: DebtFootnote) -> str:
    """Concatenate the debt footnote + going-concern + subsequent-events notes for the LLM."""
    parts = []
    if footnote.text:
        parts.append("=== DEBT FOOTNOTE ===\n" + footnote.text)
    if footnote.going_concern_text:
        parts.append("=== GOING CONCERN NOTE ===\n" + footnote.going_concern_text)
    if footnote.subsequent_events_text:
        parts.append("=== SUBSEQUENT EVENTS NOTE ===\n" + footnote.subsequent_events_text)
    return "\n\n".join(parts)


def extract_debt_terms(source: DebtFootnote | str, *, client: Optional["anthropic.Anthropic"] = None,
                       model: str = DEFAULT_MODEL) -> Optional[DebtFootnoteExtraction]:
    """Run the structured LLM extraction over footnote text.

    `source` may be a DebtFootnote (from sec_fetcher) or a raw combined-text string.
    Returns a validated DebtFootnoteExtraction, or None if there is no text to extract.
    Raises anthropic.AuthenticationError if no/invalid API key (caller handles).
    """
    text = _combine(source) if isinstance(source, DebtFootnote) else source
    if not text or not text.strip():
        return None

    # Support ANTHROPIC_BASE_URL for relay services (e.g. APIYI). The API key resolves
    # from ANTHROPIC_API_KEY in the environment.
    if client is None:
        client_kwargs: dict = {}
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url:
            client_kwargs["base_url"] = base_url
        client = anthropic.Anthropic(**client_kwargs)

    # thinking parameter omitted — not supported by relay services (APIYI)
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT + JSON_OUTPUT_INSTRUCTION,
        messages=[{
            "role": "user",
            "content": "Extract the debt covenants, maturity schedule, revolver availability, "
                       "and covenant/going-concern compliance status from the following filing "
                       "footnote text:\n\n" + text,
        }],
    )
    # Manual JSON parsing (relay-safe) — concatenate text blocks, parse, validate.
    raw = "".join(getattr(b, "text", "") for b in response.content if hasattr(b, "text"))
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        result = DebtFootnoteExtraction.model_validate(data)
    except ValidationError:
        return None

    # Persist to SQLite when we have filing metadata (DebtFootnote source). Best-effort —
    # a DB error must never lose the extraction.
    if isinstance(source, DebtFootnote):
        try:
            save_to_db(result, source.cik, source.accession, source.form_type, model)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not persist extraction to SQLite: {exc}", file=sys.stderr)
    return result


# --------------------------------------------------------------------------------------
# Persistence — flatten DebtFootnoteExtraction into the llm_extractions table (db.py §6.3)
# --------------------------------------------------------------------------------------

def _first(covenants: list[Covenant], predicate) -> Optional[Covenant]:
    return next((c for c in covenants if predicate(c)), None)


def _year_bucket(label: Optional[str]) -> Optional[str]:
    """Map a maturity-row label to 'year1'..'year5' or 'thereafter' (or None).

    Handles relative labels ('Year 1', 'Less than 1 year') and calendar-year labels
    ('2026', '2027') — the latter resolved to Year N relative to the current year.
    """
    s = (label or "").lower()
    if "thereafter" in s or "after year" in s or "beyond" in s:
        return "thereafter"
    # Existing: "Year 1", "Year 2" etc.
    m = re.search(r"(?:year|yr)\s*([1-5])\b", s)
    if m:
        return f"year{m.group(1)}"
    # New: calendar year labels e.g. "2026", "2027"
    m = re.search(r"\b(20\d{2})\b", s)
    if m:
        cal_year = int(m.group(1))
        current_year = datetime.now().year
        offset = cal_year - current_year + 1
        if 1 <= offset <= 5:
            return f"year{offset}"
        elif offset > 5:
            return "thereafter"
    if "less than 1" in s or "within 1" in s or "next 12" in s:
        return "year1"
    m = re.search(r"\b([1-5])\b", s)
    return f"year{m.group(1)}" if m else None


def save_to_db(result: DebtFootnoteExtraction, cik: str, accession: Optional[str],
               form_type: Optional[str], model: str, db_path: Optional[str] = None) -> None:
    """Flatten `result` into one llm_extractions row and write it (ON CONFLICT REPLACE)."""
    import db as _db  # lazy import to avoid any import cycle

    lev = _first(result.covenants, lambda c: (c.covenant_type or "") == "leverage")
    cov = _first(result.covenants, lambda c: "coverage" in (c.covenant_type or ""))

    years: dict[str, float] = {}
    for row in result.maturity_schedule:
        bucket = _year_bucket(row.year_label)
        if bucket and row.amount_millions is not None and bucket not in years:
            years[bucket] = row.amount_millions

    comp = result.compliance
    blob = f"{comp.description or ''} {comp.evidence or ''}".lower()
    chapter_11 = 1 if ("chapter 11" in blob or "chapter11" in blob) else 0
    going_concern = 1 if (comp.going_concern_flag or comp.status == "going_concern_doubt") else 0
    breach = 1 if comp.status in ("breach", "waiver_obtained") else 0
    in_compliance = 1 if comp.status == "in_compliance" else 0
    springing = 1 if any(c.is_springing for c in result.covenants) else 0
    rev = result.revolver

    conn = _db.connect(db_path or _db.DB_PATH)
    conn.execute(
        """
        INSERT INTO llm_extractions (
            cik, accession, form_type, extracted_at, model_used,
            in_compliance, breach_disclosed, going_concern_doubt, chapter_11_filed, compliance_evidence,
            leverage_covenant_threshold, leverage_covenant_direction,
            coverage_covenant_threshold, coverage_covenant_direction, covenant_springing,
            maturity_year1, maturity_year2, maturity_year3, maturity_year4, maturity_year5, maturity_thereafter,
            revolver_commitment, revolver_drawn, revolver_net_available, revolver_maturity_date, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cik, accession, form_type, datetime.now(timezone.utc).isoformat(), model,
         in_compliance, breach, going_concern, chapter_11, comp.evidence,
         (lev.threshold_value if lev else None), (lev.direction if lev else None),
         (cov.threshold_value if cov else None), (cov.direction if cov else None), springing,
         years.get("year1"), years.get("year2"), years.get("year3"),
         years.get("year4"), years.get("year5"), years.get("thereafter"),
         (rev.total_commitment_millions if rev.exists else None),
         (rev.drawn_amount_millions if rev.exists else None),
         (rev.undrawn_availability_millions if rev.exists else None),
         (rev.maturity_date if rev.exists else None),
         result.model_dump_json()),
    )
    conn.commit()
    conn.close()


def extract_from_filing(cik: str, form: str = "10-K", *,
                        client: Optional["anthropic.Anthropic"] = None,
                        model: str = DEFAULT_MODEL) -> tuple[Optional[DebtFootnote], Optional[DebtFootnoteExtraction]]:
    """Fetch the most recent `form` filing's debt footnotes (sec_fetcher) and extract terms.
    Returns (DebtFootnote, DebtFootnoteExtraction). Either may be None on failure.
    `client` is the Anthropic client for the LLM call; SEC fetching uses its own SecClient."""
    fetcher_client = SecClient()
    footnote = get_debt_footnote(fetcher_client, cik, form)
    if footnote is None or not footnote.found:
        return footnote, None
    extraction = extract_debt_terms(footnote, client=client, model=model)
    return footnote, extraction


# --------------------------------------------------------------------------------------
# Manual test — Rite Aid (requires ANTHROPIC_API_KEY)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    cik = sys.argv[1] if len(sys.argv) > 1 else "0000084129"  # Rite Aid
    form = sys.argv[2] if len(sys.argv) > 2 else "10-Q"        # 10-Q has the going-concern note

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Export it and re-run:\n"
              "  export ANTHROPIC_API_KEY=sk-ant-...\n"
              f"  python llm_extractor.py {cik} {form}")
        sys.exit(2)

    print(f"Fetching + extracting debt terms — CIK {cik} {form} …")
    footnote, result = extract_from_filing(cik, form)
    if footnote is None or not footnote.found:
        print("Could not locate a debt footnote to extract from.")
        sys.exit(1)
    print(f"Source: {footnote.source_url}")
    print(f"Footnote text fed to LLM: {len(_combine(footnote)):,} chars "
          f"(debt {len(footnote.text):,} + GC {len(footnote.going_concern_text):,} "
          f"+ subsequent {len(footnote.subsequent_events_text):,})\n")

    if result is None:
        print("No extraction produced.")
        sys.exit(1)

    print("═" * 78)
    print("  EXTRACTED DEBT TERMS")
    print("═" * 78)
    print(f"\nCOMPLIANCE: {result.compliance.status}  (going concern: {result.compliance.going_concern_flag})")
    if result.compliance.description:
        print(f"  {result.compliance.description}")
    if result.compliance.evidence:
        print(f"  evidence: “{result.compliance.evidence[:240]}”")

    print(f"\nCOVENANTS ({len(result.covenants)}):")
    for c in result.covenants:
        thr = f"{c.threshold_value}{c.unit or ''}" if c.threshold_value is not None else "—"
        print(f"  • [{c.covenant_type}] {c.ratio_name or ''} {c.direction or ''} {thr}"
              f"  freq={c.testing_frequency or '—'}"
              f"{'  SPRINGING' if c.is_springing else ''}"
              f"{'  (maintenance)' if c.is_maintenance else '  (incurrence)' if c.is_maintenance is False else ''}")
        if c.evidence:
            print(f"      “{c.evidence[:200]}”")

    print(f"\nMATURITY SCHEDULE ({len(result.maturity_schedule)} rows):")
    for m in result.maturity_schedule:
        print(f"  {m.year_label:<18} {m.amount_millions if m.amount_millions is not None else '—'}")

    r = result.revolver
    print(f"\nREVOLVER: exists={r.exists}")
    if r.exists:
        print(f"  commitment={r.total_commitment_millions}  drawn={r.drawn_amount_millions}  "
              f"undrawn={r.undrawn_availability_millions}  matures={r.maturity_date}")
    if result.notes:
        print(f"\nNOTES: {result.notes}")
    print("═" * 78)
