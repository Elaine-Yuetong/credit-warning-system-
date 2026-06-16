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
            save_to_db(result, source.cik, source.accession, source.form_type, model,
                       footnote_text=source.text, footnote_gc_text=source.going_concern_text)
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
               form_type: Optional[str], model: str, db_path: Optional[str] = None,
               footnote_text: str = "", footnote_gc_text: str = "") -> None:
    """Flatten `result` into one llm_extractions row and write it (ON CONFLICT REPLACE).
    The raw debt-footnote text (footnote_text) and going-concern text (footnote_gc_text) fed to
    the LLM are embedded into raw_json so the source is recoverable (Streamlit raw-footnote view)."""
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

    # raw_json = the structured extraction plus the verbatim source text fed to the LLM.
    raw = result.model_dump()
    raw["footnote_text"] = footnote_text or None
    raw["footnote_gc_text"] = footnote_gc_text or None
    raw_json = json.dumps(raw, default=str)

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
         raw_json),
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


# ======================================================================================
# Group 4 — Loss Provisions / Litigation Contingencies (LOSS_PROVISIONS.md)
# ======================================================================================

class ContingencyMatter(BaseModel):
    """One material legal/regulatory/environmental matter disclosed in the contingency note."""
    matter_description: str = Field(description="Brief description / name of the matter (1-2 sentences)")
    tier: Optional[int] = Field(
        default=None,
        description="ASC 450 language tier per LOSS_PROVISIONS.md (severity rises with tier): "
                    "1 = Remote (no financial impact expected); "
                    "2 = Reasonably possible, quantified range disclosed; "
                    "3 = Reasonably possible, no range given but described as potentially material; "
                    "4 = Probable, amount not yet estimable; "
                    "5 = Probable, amount estimable — provision recorded. "
                    "Generic 'ordinary course of business' boilerplate maps to Tier 1.")
    accrued_amount: Optional[float] = Field(default=None, description="Recorded provision for this matter, USD millions")
    maximum_exposure: Optional[float] = Field(
        default=None, description="Disclosed reasonably-possible maximum loss in excess of accrual, USD millions")
    insurance_offset: Optional[float] = Field(default=None, description="Expected insurance recovery, USD millions")
    settlement_reached: Optional[bool] = Field(default=None, description="True if a settlement has been reached")
    verbatim_quote: Optional[str] = Field(
        default=None, description="Verbatim ASC 450 sentence/phrase that determines the tier. Do not paraphrase. "
                                  "For boilerplate Tier 1, quote the generic statement.")


class ProvisionRollForward(BaseModel):
    """Provision roll-forward table (USD millions), when disclosed."""
    beginning_balance: Optional[float] = None
    additions: Optional[float] = None
    payments: Optional[float] = None
    reversals: Optional[float] = None
    ending_balance: Optional[float] = None


class LossProvisionsExtraction(BaseModel):
    """Complete structured extraction of loss provisions / litigation contingencies."""
    roll_forward: Optional[ProvisionRollForward] = None
    matters: list[ContingencyMatter] = Field(description="All material matters; empty list if none disclosed")
    total_accrued: Optional[float] = Field(
        default=None, description="Total recorded provision balance, USD millions (roll-forward ending balance "
                                  "if present, else sum of per-matter accrued amounts)")
    total_maximum_exposure: Optional[float] = Field(
        default=None, description="Aggregate disclosed reasonably-possible maximum loss in excess of accruals, USD millions")
    new_matters_detected: Optional[bool] = Field(
        default=None, description="True if the filing describes any matter as newly arising/first disclosed this period")
    regulatory_investigation: Optional[bool] = Field(
        default=None, description="True if any investigation/enforcement by DOJ, SEC, CFTC, FTC, a state AG, or an "
                                  "equivalent regulator is disclosed")
    notes: Optional[str] = Field(default=None, description="Anything material not captured above")


LOSS_PROVISIONS_SYSTEM_PROMPT = (
    "You are a credit analyst extracting loss provisions and litigation contingencies from the "
    "Loss Contingency / Commitments & Contingencies footnote and Legal Proceedings item of an SEC "
    "filing. Extract ONLY what is explicitly stated.\n\n"
    "Rules:\n"
    "- For each material legal, regulatory, or environmental matter, create a ContingencyMatter and "
    "classify its ASC 450 language tier (1-5) using these definitions EXACTLY (severity rises with tier):\n"
    "    Tier 1 = Remote — no financial impact expected (also: generic 'ordinary course of business' boilerplate)\n"
    "    Tier 2 = Reasonably possible, with a quantified range disclosed\n"
    "    Tier 3 = Reasonably possible, no range given but described as potentially material\n"
    "    Tier 4 = Probable, amount not yet estimable\n"
    "    Tier 5 = Probable, amount estimable — a provision has been recorded\n"
    "- Put the verbatim ASC 450 sentence/phrase that determines the tier into `verbatim_quote` — do not "
    "paraphrase. If you cannot find a verbatim sentence, do not invent the matter.\n"
    "- Never infer amounts not stated; leave nulls. All amounts are USD millions (convert thousands/billions).\n"
    "- accrued_amount = recorded provision for that matter; maximum_exposure = disclosed reasonably-possible "
    "loss in EXCESS of the accrual; insurance_offset = expected insurance recovery.\n"
    "- roll_forward: populate only if a beginning/additions/payments/reversals/ending table is present.\n"
    "- total_accrued = the roll-forward ending balance if present, otherwise the sum of per-matter accrued amounts.\n"
    "- total_maximum_exposure = aggregate reasonably-possible maximum loss in excess of accruals.\n"
    "- regulatory_investigation = true only if a named regulator's investigation/enforcement is disclosed.\n"
    "- new_matters_detected = true if the text describes a matter as newly arising or first disclosed this period.\n"
    "- If the footnote is only generic boilerplate ('subject to legal proceedings in the ordinary course'), "
    "emit a single Tier 1 matter quoting that statement; do not fabricate specific matters."
)

LOSS_JSON_INSTRUCTION = (
    "\n\nRespond with ONLY a single JSON object and nothing else — no prose, no commentary, no markdown "
    "code fences. The JSON object must conform to this JSON Schema:\n"
    + json.dumps(LossProvisionsExtraction.model_json_schema())
)


def _combine_loss(footnote: DebtFootnote) -> str:
    """Concatenate the loss-contingency note + legal-proceedings item for the LLM."""
    parts = []
    if footnote.loss_contingency_text:
        parts.append("=== LOSS CONTINGENCY / COMMITMENTS & CONTINGENCIES FOOTNOTE ===\n"
                     + footnote.loss_contingency_text)
    if footnote.legal_proceedings_text:
        parts.append("=== LEGAL PROCEEDINGS ITEM ===\n" + footnote.legal_proceedings_text)
    return "\n\n".join(parts)


def extract_loss_provisions(source: DebtFootnote | str, *,
                            client: Optional["anthropic.Anthropic"] = None,
                            model: str = DEFAULT_MODEL) -> Optional[LossProvisionsExtraction]:
    """Structured LLM extraction of loss provisions / litigation contingencies.

    `source` may be a DebtFootnote (uses loss_contingency_text + legal_proceedings_text) or a raw
    string. Returns a validated LossProvisionsExtraction, or None if there is no text/parse fails.
    Persists to llm_loss_provisions when given a DebtFootnote (best-effort)."""
    text = _combine_loss(source) if isinstance(source, DebtFootnote) else source
    if not text or not text.strip():
        return None

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
        system=LOSS_PROVISIONS_SYSTEM_PROMPT + LOSS_JSON_INSTRUCTION,
        messages=[{
            "role": "user",
            "content": "Extract the loss provisions and litigation contingencies (per-matter tier "
                       "classification, roll-forward, totals, regulatory investigations) from the "
                       "following filing text:\n\n" + text,
        }],
    )
    raw = "".join(getattr(b, "text", "") for b in response.content if hasattr(b, "text"))
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        result = LossProvisionsExtraction.model_validate(data)
    except ValidationError:
        return None

    if isinstance(source, DebtFootnote):
        try:
            save_loss_provisions_to_db(result, source.cik, source.accession, source.form_type, model)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not persist loss provisions to SQLite: {exc}", file=sys.stderr)
    return result


def save_loss_provisions_to_db(result: LossProvisionsExtraction, cik: str, accession: Optional[str],
                               form_type: Optional[str], model: str, db_path: Optional[str] = None) -> None:
    """Write one llm_loss_provisions row (ON CONFLICT REPLACE)."""
    import db as _db  # lazy import to avoid any import cycle
    reg = None if result.regulatory_investigation is None else (1 if result.regulatory_investigation else 0)
    roll_json = result.roll_forward.model_dump_json() if result.roll_forward else None
    matters_json = json.dumps([m.model_dump() for m in result.matters])

    conn = _db.connect(db_path or _db.DB_PATH)
    conn.execute(
        """
        INSERT INTO llm_loss_provisions (
            cik, accession, form_type, total_accrued, total_maximum_exposure,
            regulatory_investigation, roll_forward_json, matters_json, extracted_at, model_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cik, accession, form_type, result.total_accrued, result.total_maximum_exposure,
         reg, roll_json, matters_json, datetime.now(timezone.utc).isoformat(), model),
    )
    conn.commit()
    conn.close()


# ======================================================================================
# Group 6 — Asset Composition for Liquidation Coverage (ASSET_COVERAGE.md Formula 2)
# ======================================================================================

class PPEComposition(BaseModel):
    """PP&E (net) split by liquidation-recovery type, USD millions."""
    total: Optional[float] = Field(default=None, description="Total PP&E, net (should reconcile to balance sheet)")
    real_estate: Optional[float] = Field(default=None, description="Land and buildings")
    equipment: Optional[float] = Field(default=None, description="General manufacturing / office equipment")
    specialised: Optional[float] = Field(default=None, description="Specialised industrial equipment")
    leasehold: Optional[float] = Field(default=None, description="Leasehold improvements")


class InventoryComposition(BaseModel):
    """Inventory split by stage, USD millions."""
    raw_materials: Optional[float] = None
    wip: Optional[float] = Field(default=None, description="Work in process")
    finished_goods: Optional[float] = None


class IntangiblesComposition(BaseModel):
    """Intangible assets split by liquidation-recovery type, USD millions."""
    patents: Optional[float] = Field(default=None, description="Patents / IP with licensing value")
    customer_lists: Optional[float] = Field(default=None, description="Customer relationships / lists / trade names")
    software: Optional[float] = Field(default=None, description="Capitalised software")


class AssetCompositionExtraction(BaseModel):
    """Asset composition for liquidation-adjusted coverage (Formula 2 inputs)."""
    ppe: PPEComposition
    inventory: InventoryComposition
    intangibles: IntangiblesComposition
    collateral_description: Optional[str] = Field(
        default=None, description="Verbatim description of assets pledged as collateral for secured debt")
    collateral_type: Optional[str] = Field(
        default=None, description="One of: substantially_all | specific | none")
    notes: Optional[str] = None


# The haircut (recovery-rate) table is reproduced EXACTLY from ASSET_COVERAGE.md Formula 2.
# It is included so the model buckets each asset into the correct recovery tier; the system
# applies the haircuts deterministically — the model must NOT apply haircuts or compute coverage.
ASSET_COMPOSITION_SYSTEM_PROMPT = (
    "You are a credit analyst extracting ASSET COMPOSITION (not ratios) from the PP&E, "
    "Inventory, and Intangibles footnotes and the Debt footnote of an SEC filing, to support a "
    "liquidation-coverage calculation. Extract ONLY amounts explicitly stated; leave nulls "
    "otherwise. All amounts in USD millions.\n\n"
    "Categorise assets into these recovery-tier buckets (the system applies the haircuts; you "
    "only assign amounts to the right bucket). For reference, the recovery-rate ranges are:\n"
    "  Cash & short-term investments: 100%\n"
    "  Accounts receivable: 70%–85%\n"
    "  Inventory: 40%–60%\n"
    "  PP&E — real estate (land/buildings): 60%–80%\n"
    "  PP&E — general manufacturing equipment: 30%–50%\n"
    "  PP&E — specialised industrial equipment: 10%–30%\n"
    "  PP&E — leasehold improvements: 0%–10%\n"
    "  Goodwill: 0%\n"
    "  Intangibles — patents / IP with licensing value: 10%–20%\n"
    "  Intangibles — customer lists / trade names: 0%–10%\n"
    "  Intangibles — capitalised software: 0%–5%\n\n"
    "Rules:\n"
    "- ppe: extract NET BOOK VALUES (after accumulated depreciation), NOT gross/cost. PP&E "
    "footnotes typically show a gross column, an accumulated-depreciation row, and a net total — "
    "use the NET column only. The PP&E net total (ppe.total) is the SINGLE bottom-line figure in "
    "the table, typically labelled 'Property and equipment, net' or 'Total property and equipment, "
    "net'. It should be the LARGEST single number in the PP&E table and typically in the hundreds "
    "of millions or billions for any company with significant physical assets. Do NOT extract "
    "depreciation expense, accumulated depreciation, or any individual asset-class sub-total as the "
    "total. Split net PP&E into real_estate (land+buildings), equipment "
    "(general), specialised (specialised industrial), leasehold (leasehold improvements). Put the "
    "net PP&E total in `total`. SANITY CHECK: the component amounts should sum to approximately "
    "`total`, and `total` should match the balance-sheet net PP&E. If the footnote only breaks out "
    "categories on a GROSS basis, do NOT report those gross category amounts as net — instead leave "
    "the category buckets null and report only the net `total`.\n"
    "- inventory: split into raw_materials / wip / finished_goods if disclosed.\n"
    "- intangibles: report net carrying amounts (after accumulated amortisation). Split into patents "
    "(incl. developed technology/IP), customer_lists (incl. customer relationships and trade "
    "names/trademarks), software (capitalised internal-use software).\n"
    "- collateral_description: verbatim sentence describing assets pledged for secured debt, from the "
    "Debt footnote, if any. collateral_type = 'substantially_all' if 'substantially all assets' is "
    "pledged, 'specific' if particular assets are named, 'none' if no secured debt / no pledge.\n"
    "- PARTIAL RESULTS: if footnote text is present but you cannot break out every bucket, return "
    "whatever amounts ARE stated — never refuse, never return an all-null object. At minimum populate "
    "the net totals (ppe.total, inventory stages, intangible classes) that the filing discloses.\n"
    "- Do NOT invent haircut values, do NOT apply haircuts, do NOT compute any coverage ratio — "
    "amounts only. Leave a bucket null only if the filing does not disclose it."
)

ASSET_JSON_INSTRUCTION = (
    "\n\nRespond with ONLY a single JSON object and nothing else — no prose, no markdown fences. "
    "The JSON object must conform to this JSON Schema:\n"
    + json.dumps(AssetCompositionExtraction.model_json_schema())
)


def _combine_assets(footnote: DebtFootnote) -> str:
    """Concatenate PP&E + inventory + intangibles footnotes + the debt footnote (for collateral)."""
    parts = []
    if footnote.ppe_text:
        parts.append("=== PROPERTY, PLANT & EQUIPMENT FOOTNOTE ===\n" + footnote.ppe_text)
    if footnote.inventory_text:
        parts.append("=== INVENTORY FOOTNOTE ===\n" + footnote.inventory_text)
    if footnote.intangibles_text:
        parts.append("=== GOODWILL & INTANGIBLES FOOTNOTE ===\n" + footnote.intangibles_text)
    if footnote.text:
        parts.append("=== DEBT FOOTNOTE (for collateral description) ===\n" + footnote.text)
    return "\n\n".join(parts)


def extract_asset_composition(source: DebtFootnote | str, *,
                              client: Optional["anthropic.Anthropic"] = None,
                              model: str = DEFAULT_MODEL) -> Optional[AssetCompositionExtraction]:
    """Structured LLM extraction of asset composition for Formula 2. Persists to
    llm_asset_composition when given a DebtFootnote (best-effort)."""
    text = _combine_assets(source) if isinstance(source, DebtFootnote) else source
    if not text or not text.strip():
        return None

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
        system=ASSET_COMPOSITION_SYSTEM_PROMPT + ASSET_JSON_INSTRUCTION,
        messages=[{
            "role": "user",
            "content": "Extract the PP&E / inventory / intangibles composition and secured-debt "
                       "collateral description from the following filing footnote text:\n\n" + text,
        }],
    )
    raw = "".join(getattr(b, "text", "") for b in response.content if hasattr(b, "text"))
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        result = AssetCompositionExtraction.model_validate(data)
    except ValidationError:
        return None

    if isinstance(source, DebtFootnote):
        try:
            save_asset_composition_to_db(result, source.cik, source.accession, source.form_type, model)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not persist asset composition to SQLite: {exc}", file=sys.stderr)
    return result


def save_asset_composition_to_db(result: AssetCompositionExtraction, cik: str, accession: Optional[str],
                                 form_type: Optional[str], model: str, db_path: Optional[str] = None) -> None:
    """Flatten AssetCompositionExtraction into one llm_asset_composition row (ON CONFLICT REPLACE)."""
    import db as _db  # lazy import to avoid any import cycle
    p, inv, it = result.ppe, result.inventory, result.intangibles
    conn = _db.connect(db_path or _db.DB_PATH)
    conn.execute(
        """
        INSERT INTO llm_asset_composition (
            cik, accession, form_type, ppe_total, ppe_real_estate, ppe_equipment, ppe_specialised,
            ppe_leasehold, inventory_raw_materials, inventory_wip, inventory_finished_goods,
            intangibles_patents, intangibles_customer_lists, intangibles_software,
            collateral_description, collateral_type, extracted_at, model_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cik, accession, form_type, p.total, p.real_estate, p.equipment, p.specialised, p.leasehold,
         inv.raw_materials, inv.wip, inv.finished_goods,
         it.patents, it.customer_lists, it.software,
         result.collateral_description, result.collateral_type,
         datetime.now(timezone.utc).isoformat(), model),
    )
    conn.commit()
    conn.close()


# ======================================================================================
# Group 7a — Maintenance vs Growth Capex Split (FREE_CASH_FLOW.md Formula 2, Item 2b)
# ======================================================================================

class CapexSplitExtraction(BaseModel):
    """Maintenance vs growth capex split disclosed in MD&A (USD millions)."""
    split_disclosed: bool = Field(
        description="True only if the filing explicitly distinguishes maintenance/sustaining "
                    "capex from growth/expansion capex. False if it reports a single capex figure.")
    maintenance_capex: Optional[float] = Field(
        default=None, description="Maintenance / sustaining / replacement capex, USD millions")
    growth_capex: Optional[float] = Field(
        default=None, description="Growth / expansion capex, USD millions")
    total_capex_disclosed: Optional[float] = Field(
        default=None, description="Total capex stated in MD&A, USD millions (for sum verification)")
    notes: Optional[str] = None


CAPEX_SPLIT_SYSTEM_PROMPT = (
    "You are a credit analyst reading the MD&A 'Liquidity and Capital Resources' / capital-"
    "expenditures discussion of an SEC filing. Your only task is to determine whether the company "
    "discloses a split between MAINTENANCE capex (also called sustaining, replacement, or "
    "keep-the-lights-on capex — spending to keep existing assets functioning) and GROWTH capex "
    "(also called expansion capex — spending to add capacity). All amounts in USD millions.\n\n"
    "Rules:\n"
    "- split_disclosed = true ONLY if the text explicitly separates maintenance/sustaining capex "
    "from growth/expansion capex with distinct amounts or clearly attributable language. A single "
    "total capex figure with no breakdown is NOT a split — set split_disclosed = false.\n"
    "- maintenance_capex / growth_capex: the disclosed amounts if split_disclosed is true; null "
    "otherwise. total_capex_disclosed: the total capex figure stated in MD&A if present.\n"
    "- Do NOT invent or estimate a split. Do NOT apply the D&A proxy — that is the system's job "
    "when no split is disclosed. If not disclosed, set split_disclosed=false and leave amounts null, "
    "with notes='maintenance vs growth capex split not disclosed'."
)

CAPEX_SPLIT_JSON_INSTRUCTION = (
    "\n\nRespond with ONLY a single JSON object and nothing else — no prose, no markdown fences. "
    "The JSON object must conform to this JSON Schema:\n"
    + json.dumps(CapexSplitExtraction.model_json_schema())
)


def extract_capex_split(source: DebtFootnote | str, *,
                        client: Optional["anthropic.Anthropic"] = None,
                        model: str = DEFAULT_MODEL) -> Optional[CapexSplitExtraction]:
    """Structured LLM extraction of the maintenance vs growth capex split from MD&A. Persists to
    llm_capex_split when given a DebtFootnote (best-effort)."""
    text = (source.mda_capex_text if isinstance(source, DebtFootnote) else source)
    if not text or not text.strip():
        return None

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
        system=CAPEX_SPLIT_SYSTEM_PROMPT + CAPEX_SPLIT_JSON_INSTRUCTION,
        messages=[{
            "role": "user",
            "content": "Determine the maintenance vs growth capex split from the following MD&A "
                       "capital-expenditures discussion:\n\n" + text,
        }],
    )
    raw = "".join(getattr(b, "text", "") for b in response.content if hasattr(b, "text"))
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        result = CapexSplitExtraction.model_validate(data)
    except ValidationError:
        return None

    if isinstance(source, DebtFootnote):
        try:
            save_capex_split_to_db(result, source.cik, source.accession, source.form_type, model)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not persist capex split to SQLite: {exc}", file=sys.stderr)
    return result


def save_capex_split_to_db(result: CapexSplitExtraction, cik: str, accession: Optional[str],
                           form_type: Optional[str], model: str, db_path: Optional[str] = None) -> None:
    """Write one llm_capex_split row (ON CONFLICT REPLACE)."""
    import db as _db  # lazy import to avoid any import cycle
    conn = _db.connect(db_path or _db.DB_PATH)
    conn.execute(
        """
        INSERT INTO llm_capex_split (
            cik, accession, form_type, maintenance_capex, growth_capex, total_capex_disclosed,
            split_disclosed, extracted_at, model_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cik, accession, form_type, result.maintenance_capex, result.growth_capex,
         result.total_capex_disclosed, 1 if result.split_disclosed else 0,
         datetime.now(timezone.utc).isoformat(), model),
    )
    conn.commit()
    conn.close()


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

    # ---- Group 4: Loss provisions / litigation contingencies ----
    print(f"\nExtracting loss provisions — contingency note {len(footnote.loss_contingency_text):,} chars "
          f"+ legal proceedings {len(footnote.legal_proceedings_text):,} chars …")
    lp = extract_loss_provisions(footnote)
    if lp is None:
        print("No loss-provisions extraction produced (no contingency text or parse failed).")
    else:
        print("═" * 78)
        print("  EXTRACTED LOSS PROVISIONS / CONTINGENCIES")
        print("═" * 78)
        print(f"\nTOTALS: accrued=${lp.total_accrued}M  max_exposure=${lp.total_maximum_exposure}M  "
              f"regulatory_investigation={lp.regulatory_investigation}  new_matters={lp.new_matters_detected}")
        if lp.roll_forward:
            rf = lp.roll_forward
            print(f"ROLL-FORWARD: begin={rf.beginning_balance} +adds={rf.additions} "
                  f"-pmts={rf.payments} -rev={rf.reversals} = end={rf.ending_balance}")
        print(f"\nMATTERS ({len(lp.matters)}):")
        for m in lp.matters:
            print(f"  • [Tier {m.tier}] {m.matter_description[:90]}"
                  f"  accrued={m.accrued_amount} max={m.maximum_exposure}"
                  f"{'  SETTLED' if m.settlement_reached else ''}")
            if m.verbatim_quote:
                print(f"      “{m.verbatim_quote[:200]}”")
        if lp.notes:
            print(f"\nNOTES: {lp.notes}")
        print("═" * 78)

    # ---- Group 6: Asset composition for liquidation coverage ----
    print(f"\nExtracting asset composition — PP&E {len(footnote.ppe_text):,} + inventory "
          f"{len(footnote.inventory_text):,} + intangibles {len(footnote.intangibles_text):,} chars …")
    ac = extract_asset_composition(footnote)
    if ac is None:
        print("No asset-composition extraction produced.")
    else:
        print("═" * 78)
        print("  EXTRACTED ASSET COMPOSITION (Formula 2 inputs)")
        print("═" * 78)
        print(f"  PP&E: total={ac.ppe.total} real_estate={ac.ppe.real_estate} equipment={ac.ppe.equipment} "
              f"specialised={ac.ppe.specialised} leasehold={ac.ppe.leasehold}")
        print(f"  Inventory: raw={ac.inventory.raw_materials} wip={ac.inventory.wip} "
              f"finished={ac.inventory.finished_goods}")
        print(f"  Intangibles: patents={ac.intangibles.patents} customer_lists={ac.intangibles.customer_lists} "
              f"software={ac.intangibles.software}")
        print(f"  Collateral: type={ac.collateral_type}")
        if ac.collateral_description:
            print(f"    “{ac.collateral_description[:200]}”")
        print("═" * 78)

    # ---- Group 7a: Maintenance vs growth capex split ----
    print(f"\nExtracting capex split — MD&A capex section {len(footnote.mda_capex_text):,} chars …")
    cs = extract_capex_split(footnote)
    if cs is None:
        print("No capex-split extraction produced (no MD&A capex text or parse failed).")
    else:
        print("═" * 78)
        print("  EXTRACTED CAPEX SPLIT (Formula 2, Item 2b)")
        print("═" * 78)
        print(f"  split_disclosed={cs.split_disclosed}  maintenance={cs.maintenance_capex}  "
              f"growth={cs.growth_capex}  total_disclosed={cs.total_capex_disclosed}")
        if cs.notes:
            print(f"  NOTES: {cs.notes}")
        print("═" * 78)
