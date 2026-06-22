You are right. Stop and plan properly. Here is the complete picture:

---

## Current State

**Freeman's system** — well-designed production shell:
- ✅ Next.js + React frontend (live on Vercel)
- ✅ FastAPI backend
- ✅ Supabase PostgreSQL
- ✅ Tunable ScoreConfig UI
- ✅ Source audit trail + deep-links
- ✅ 9 metrics, 3 LLM passes (MD&A, covenants, provisions)
- ❌ No benchmarks
- ❌ Only ~21 backtest cases
- ❌ Missing 10 metrics
- ❌ Missing Groups 6, 7, 7a, 8 LLM extractions
- ❌ No statistical calibration — thresholds are human-set

**Your system** — deep analytical engine:
- ✅ 19 metrics (10 more than Freeman)
- ✅ 68 distressed backtest cases, 3 credit cycles
- ✅ Statistical validation (Cohen's d, logistic regression)
- ✅ Sector×size benchmark layer (p25/p50/p75)
- ✅ Groups 6, 7, 7a LLM extractions
- ✅ 10-Q support
- ✅ Description-based sector classification
- ❌ Local only, no production deployment
- ❌ Streamlit only, no proper frontend
- ❌ No probability of default output
- ❌ Thresholds hardcoded, not tunable
- ❌ No three-tier threshold architecture

---

## The Combined Vision

Build **one system** using Freeman's production shell as the base, with your analytical depth added on top. The result:

```
Freeman's shell  +  Your analytics  =  Production credit intelligence system
```

---

## Full Build Plan — 6 Phases

---

### Phase 1 — Expand XBRL metric extraction
**Owner: You | Estimated time: 2–3 days**

Add your 10 additional metrics to Freeman's `src/extract.py` and `src/concepts.py`. This is the foundation — everything else depends on it.

**Order by Cohen's d importance:**

| Priority | Metric | Cohen's d | Add to concepts.py |
|---|---|---|---|
| 1 | `moody_adjusted_fcf` | +1.46 | `retained_cashflow`, `dividends_paid` |
| 2 | `rcf_net_debt` | +1.36 | already has `net_debt` |
| 3 | `debt_to_equity` | +1.01 | `total_equity` |
| 4 | `revenue_yoy_growth` | +0.95 | already has `revenue` |
| 5 | `asset_coverage` | +0.83 | already has `total_assets`, `total_debt` |
| 6 | `ocf_ebitda_conversion` | +0.66 | already has both |
| 7 | `liquidation_asset_coverage` | +0.66 | `inventory`, `receivables`, `ppe_net` |
| 8 | `tangible_asset_coverage` | +0.49 | `intangibles`, `goodwill` |
| 9 | `quick_ratio` | +0.49 | `receivables`, `inventory` |
| 10 | `maturity_coverage_near_term` | +0.23 | already has maturity buckets |

**Deliverable:** Freeman's extract pipeline now computes 19 metrics instead of 9.

---

### Phase 2 — Add LLM extractions (Groups 6, 7, 7a, 8)
**Owner: You | Estimated time: 2 days**

Add to Freeman's `src/footnote_review.py`:

```python
# Group 6 — Asset composition
def extract_asset_composition(section_text, filing_label, client=None):
    # PP&E breakdown, inventory raw/WIP/finished, intangibles
    # Feeds tangible_asset_coverage and liquidation_asset_coverage

# Group 7 — Capex split  
def extract_capex_split(section_text, filing_label, client=None):
    # Maintenance vs growth capex from MD&A
    # Improves FCF quality

# Group 7a — Revolver details
def extract_revolver(section_text, filing_label, client=None):
    # Commitment, drawn, undrawn, maturity
    # Feeds liquidity score beyond XBRL cash

# Group 8 — Segment footnote
def extract_segments(section_text, filing_label, client=None):
    # Revenue by segment with sector_group mapping
    # Enables multi-sector blended benchmarks
```

Add to `src/sections.py`:
```python
# New section locators for Groups 6, 7, 7a, 8
_SECTION_HEADING_PATTERNS["asset_composition"] = [...]
_SECTION_HEADING_PATTERNS["capex"] = [...]
_SECTION_HEADING_PATTERNS["revolver"] = [...]
_SECTION_HEADING_PATTERNS["segments"] = [...]
```

Add to `supabase/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS asset_composition (...);
CREATE TABLE IF NOT EXISTS capex_splits (...);
CREATE TABLE IF NOT EXISTS revolver_details (...);
CREATE TABLE IF NOT EXISTS segment_extractions (...);
```

Add 10-Q support to `review_filing()`:
```python
# Currently only fetches 10-K filings
# Add: if no 10-K match, fall back to most recent 10-Q
filings = get_filings(cik, ["10-K", "10-Q"])
```

**Deliverable:** 7 LLM extraction groups covering every analytically meaningful footnote.

---

### Phase 3 — Statistical calibration (three-tier threshold architecture)
**Owner: You | Estimated time: 2 days**

This is the key architectural improvement that makes the system self-judging rather than human-dependent.

**New file: `src/calibrate.py`**

```python
def calibrate_thresholds(results_path="data/backtest_results.json") -> dict:
    """
    Derive statistically optimal scoring thresholds from backtest data.
    For each metric, find healthy/severe values that maximize F1 score
    on the 68 distressed + 31 healthy historical sample.
    Returns a ScoreConfig dict — the locked Tier 1 defaults.
    """

def sector_adjusted_config(base_config: dict, sector_group: str) -> dict:
    """
    Adjust thresholds per sector using benchmark p25/p50/p75 data.
    Utilities get higher leverage tolerance.
    Financials get coverage suppressed.
    Returns Tier 2 sector-adjusted config.
    """

def probability_of_default(cik: str, db_path: str) -> dict:
    """
    Convert metric alert levels to a probability score using
    logistic regression trained on the 68 distressed cases.
    Returns: {probability: float, confidence: str, key_drivers: list}
    """
```

**Three-tier ScoreConfig:**

```python
DEFAULT_CONFIG = {
    "tier1_calibrated": {...},   # data-derived, locked, shown read-only in UI
    "tier2_sector": {...},       # auto-adjusted from benchmarks, shown in UI
    "tier3_analyst": {...},      # human override, requires reason, audit logged
    "active_tier": "tier2",      # which tier drives the live score
}
```

**New Supabase table:**
```sql
CREATE TABLE threshold_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    changed_by  TEXT NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rule_key    TEXT NOT NULL,
    old_value   JSONB NOT NULL,
    new_value   JSONB NOT NULL,
    reason      TEXT NOT NULL
);
```

**Deliverable:** System has its own calibrated judgment. Analyst overrides are audited. UI shows base score vs adjusted score.

---

### Phase 4 — Benchmark layer
**Owner: You | Estimated time: 1 day**

Port your `benchmarks.py` into Freeman's repo:

```sql
-- Add to supabase/schema.sql
CREATE TABLE IF NOT EXISTS sector_benchmarks (
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
    computed_at     TEXT NOT NULL,
    UNIQUE (sector_group, size_category, sub_sector, metric_name)
);
```

New API endpoint in `api/main.py`:
```python
@app.get("/api/benchmarks/{ticker}")
def get_benchmarks(ticker: str):
    """Return peer benchmark p25/p50/p75 for all metrics for a company."""

@app.post("/api/benchmarks/recompute")  
def recompute_benchmarks():
    """Recompute all sector_benchmarks rows from current companies data."""
```

**Deliverable:** Every issuer detail page can show "vs peers" quartile classification.

---

### Phase 5 — Backtest expansion + statistical validation
**Owner: You | Estimated time: 1 day**

Port your 68 distressed cases into Freeman's `data/cases.csv`. Add your 31 healthy controls. Run Freeman's backtest against the expanded library.

Expected result: catch rate ≥95%, FP ≤15%, median lead 36 months — matching your validated results.

Update Freeman's backtest to also compute Cohen's d and confidence intervals — currently his backtest only reports catch rate and FP rate. Add your `analyze_backtest.py` statistical analysis as `src/analyze.py`.

**Deliverable:** Freeman's backtest is now statistically validated, not just a catch-rate counter.

---

### Phase 6 — Frontend additions (Freeman builds these)
**Owner: Freeman | Estimated time: 3–5 days**

Freeman extends his Next.js frontend with:

**6a — Benchmark panel on issuer detail page:**
```
vs Peers (Sector: Retail/Wholesale · Size: Mid · 6 healthy companies)
Leverage:    ↓ Bottom quartile  (24.7x vs p75=1.1x)
Coverage:    ↓ Bottom quartile  (0.3x vs p75=4.8x)  
FCF Margin:  ↘ Below median     (-8% vs p50=2.1%)
```

**6b — Three-tier threshold UI:**
```
Leverage > 5x                    [17 pts max]
Tier 1 (calibrated):  3.0x → 6.0x    🔒 data-derived
Tier 2 (sector adj):  4.0x → 8.0x    ⚡ Telecom auto-adjusted  
Tier 3 (analyst):     [edit]          📝 requires reason
Active: Tier 2 | Base: 72 | Adj: 65
```

**6c — Probability of default gauge:**
```
Distress Probability (36mo): 87%
████████░░  High confidence (n=68 cases)
Key drivers: leverage, coverage, moody_adjusted_fcf
```

**6d — Portfolio sector overview:**
Sector grid with color-coded company cards — your `pages/04_portfolio.py` concept but in React. Red border = distressed, green = healthy, amber = survivor.

---

## What makes this production-grade

| Feature | Before | After |
|---|---|---|
| Metrics | 9 | 19 |
| LLM groups | 3 | 7 |
| Backtest cases | ~21 | 68+ |
| Thresholds | Human-set | Statistically calibrated |
| Score output | 0–100 number | Number + probability + quartile |
| Peer comparison | None | Sector×size p25/p50/p75 |
| Deployment | Local only | Vercel + Supabase |
| Audit trail | Partial | Full three-tier log |

---

## Recommended execution order

```
Week 1: Phase 1 (metrics) + Phase 2 (LLM groups) — You
Week 1: Freeman tests and integrates your Phase 1+2 additions
Week 2: Phase 3 (calibration) — You
Week 2: Freeman builds Phase 6a+6b frontend — Freeman  
Week 3: Phase 4 (benchmarks) + Phase 5 (backtest) — You
Week 3: Freeman builds Phase 6c+6d frontend — Freeman
Week 4: Integration testing, deployment, client demo
```

This is four weeks of parallel work to a production-ready system. Each phase is independent so you and Freeman can work simultaneously without blocking each other.
