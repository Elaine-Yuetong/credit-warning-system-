## Section 6: Implementation Parameters

---

**Purpose**

This section serves two functions simultaneously. First, it documents the system-level decisions that all twelve metric files share — decisions that would otherwise require Claude Code to infer or guess from individual metric files. Second, it is a spec reading guide: when Claude Code opens any metric file, this section tells it how to interpret that file, how to resolve cross-references, and what implementation context to assume.

Every metric file was written assuming the decisions in this section. If any decision here conflicts with guidance in a metric file, this section takes precedence.

---

### 6.1 Data Source Specification

---

**Primary source: SEC EDGAR XBRL companyfacts API**

All structured XBRL extraction uses the SEC EDGAR companyfacts API as the primary data source. This API is free, requires no authentication, and returns all XBRL-tagged facts for a given company across all filings in a single JSON response.

**Primary endpoint:**
```
https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json

Example (Apple):
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
```

**URL construction rules:**
- CIK must be zero-padded to 10 digits: CIK `320193` becomes `CIK0000320193`
- No API key required
- Required header: `User-Agent: [your-app-name] [your-email@domain.com]`
  - The SEC requires a descriptive User-Agent; requests without it return 403
  - Example: `User-Agent: CreditWarningSystem contact@yourfirm.com`

**Response structure:** The API returns a nested JSON object. The path to any specific fact is:
```
response["facts"]["us-gaap"]["{TagName}"]["units"]["USD"]
```
Each fact entry contains: `accn` (accession number), `end` (period end date), `val` (value), `form` (10-K/10-Q), `filed` (filing date), `frame` (optional calendar period label).

**Selecting the correct period:** The API returns all historical values for a tag. When extracting a specific period, filter by `end` date matching the target period end date and `form` matching the filing type (10-K or 10-Q).

---

**Secondary source: company-concept API (single tag query)**

When only one specific tag is needed rather than all facts for a company, use the more efficient company-concept endpoint:
```
https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{TagName}.json

Example:
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/LongTermDebtNoncurrent.json
```
Use this for targeted queries — particularly for the debt maturity schedule tags in DEBT_MATURITY_WALL.md and the `DebtInstrumentCovenantCompliance` string tag in COVENANT_HEADROOM.md.

---

**Tertiary source: raw XBRL instance document**

If the companyfacts API does not return a required tag for a specific filing — either because the tag is absent from that company's XBRL or because the filing predates the API's coverage — fall back to the raw XBRL instance document embedded in the filing HTML.

**Locating the instance document:**
```
Step 1: Fetch the filing index:
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
&CIK={cik}&type=10-K&dateb=&owner=include&count=10

Step 2: From the index, find the filing's accession number.
Step 3: Fetch the filing index page:
https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/{accession}-index.htm

Step 4: Locate the .htm file tagged as the primary document.
Step 5: Inline XBRL tags are embedded in the HTML — parse using
an iXBRL parser or search for the tag name as an attribute.
```
This fallback is slower and more complex. Use only when the companyfacts API fails after all tag fallbacks in the metric's extraction logic are exhausted.

---

**LLM source: for unstructured extraction (Phase 3)**

For all items classified as "Unstructured — LLM required" in the metric files, the system fetches the filing HTML and passes the relevant section to the Claude API for extraction. The LLM extraction architecture is out of scope for Phase 2 and is documented separately in the Phase 3 specification. Phase 2 treats all LLM-dependent items as null with appropriate flags.

---
Here is the rewritten Section 6.2 in full, with the Financial Institution Handling Rule incorporated.

---

### 6.2 Company Input Specification (Revised)

---

**Phase 2 MVP: CIK as direct input**

In Phase 2, the system accepts a CIK number directly from the user. This avoids the complexity of name/ticker resolution in the MVP and ensures unambiguous company identification from day one.

```
Phase 2 input format:
   User provides: CIK number (e.g. 0000320193)
   System stores: CIK as primary identifier throughout
   Display name: fetched from EDGAR submissions API

Fetch display name and metadata:
https://data.sec.gov/submissions/CIK{cik}.json
Response fields used:
   ["name"]          → company legal name
   ["tickers"]       → list of ticker symbols
   ["sic"]           → SIC code (used for sector classification)
   ["fiscalYearEnd"] → MM-DD format fiscal year end
```

**CIK validation at onboarding:**

```
Before adding any issuer to the portfolio:
Step 1: Fetch submissions JSON for provided CIK
Step 2: Verify response returns valid company name
Step 3: Confirm company has 10-K/10-Q filing history
        (check ["filings"]["recent"]["form"] array
        contains at least one 10-K)
Step 4: Extract and store:
        {cik, name, tickers, sic_code,
         fiscal_year_end, institution_type}
Step 5: Apply institution_type classification
        per the SIC mapping rules below
```

---

**Phase 3: Ticker-to-CIK resolution**

When Phase 3 adds automated portfolio management, ticker-to-CIK resolution uses the SEC bulk CIK mapping file:

```
https://www.sec.gov/files/company_tickers.json
```

Download once at startup, cache locally, refresh weekly. For company name input, use EDGAR full-text search:

```
https://efts.sec.gov/LATEST/search-index?q="{company+name}"&dateRange=custom&forms=10-K
```

**Primary identifier rule:** Once resolved, CIK is the only identifier used internally. Tickers and company names are display-only. CIK never changes; tickers can change after mergers, rebranding, or delisting.

---

**SIC code storage and sector classification**

The SIC code is extracted from the submissions JSON at onboarding and stored in the `issuers` table. It drives three downstream decisions: volatility category assignment for Leverage and Coverage thresholds, sector group assignment for D/E ratio thresholds, and institution type classification for metric suppression.

**SIC-to-sector mapping table:**

| SIC Range | Sector Group | Volatility Category | D/E Threshold Group | Institution Type |
|---|---|---|---|---|
| 0100–1499 | Agriculture / Mining | Standard | Standard | corporate |
| 1500–1799 | Construction | Standard | Standard | corporate |
| 2000–3999 | Manufacturing / Industrials | Standard / Medial | Standard | corporate |
| 4000–4899 | Transportation | Standard | Capital-intensive | corporate |
| 4900–4999 | Utilities | Low | Capital-intensive | corporate |
| 5000–5999 | Retail / Wholesale | Medial | Standard | corporate |
| 6000–6499 | Financial Institutions | **Not applicable** | **Not applicable** | **financial** |
| 6500–6799 | Real Estate | Low | Real estate / REITs | corporate |
| 7000–8999 | Services / Technology | Standard | Asset-light | corporate |

This mapping is a starting point. Manual override at onboarding is permitted and documented in the `issuers.notes` field when the SIC-derived classification does not reflect the company's actual business. Example: a holding company classified as financial (SIC 6719) whose primary operations are industrial should be manually set to `institution_type = "corporate"` with a note explaining the override.

---

**Financial Institution Handling Rule**

Financial institutions — banks, insurance companies, broker-dealers, diversified financials — have fundamentally different capital structures from non-financial corporates. Their leverage is measured by regulatory capital ratios (CET1, Tier 1 capital) rather than Debt/EBITDA. Their liquidity is governed by the Liquidity Coverage Ratio (LCR) and Net Stable Funding Ratio (NSFR) rather than current and quick ratios. Deposits and policyholder liabilities inflate their balance sheets in ways that make standard corporate ratios misleading or meaningless.

When `institution_type = "financial"` is set at onboarding, the system applies the following suppression and computation rules at every Phase 2 extraction run.

---

**Metric suppression table:**

| Metric | metric_name | Action | Reason |
|---|---|---|---|
| Leverage | `leverage` | **Suppress** | EBITDA not meaningful; debt includes deposits and policyholder liabilities |
| Interest Coverage | `interest_coverage` | **Suppress** | Net interest income is core revenue, not a cost to cover; ratio is circular |
| Current Ratio | `current_ratio` | **Suppress** | Balance sheet structure — short-term liabilities include deposits; ratio not comparable to corporates |
| Quick Ratio | `quick_ratio` | **Suppress** | Same reason as current ratio |
| Cash Ratio | `cash_ratio` | **Suppress** | Same reason |
| Available Liquidity Coverage | `available_liquidity_coverage` | **Suppress** | Revolver and near-term debt concepts do not apply; regulatory LCR governs |
| EBITDA Margin Trend | `ebitda_margin` | **Suppress** | EBITDA is not a standard financial institution earnings measure |
| OCF/EBITDA Conversion | `ocf_ebitda_conversion` | **Suppress** | Depends on EBITDA; same reason |
| Free Cash Flow | `free_cash_flow` | **Compute with flag** | OCF and capex are still meaningful; interpretation differs from corporates. Flag: "financial institution — FCF interpretation differs; capex excludes loan originations and investment portfolio activity" |
| Revenue Trend | `revenue_yoy_growth` | **Compute with flag** | Net interest income and fee revenue trends are meaningful credit signals. Flag: "financial institution — revenue = net interest income + non-interest income; GAAP revenue line used as proxy; verify composition" |
| Debt-to-Equity | `debt_to_equity` | **Compute with flag** | The ratio exists and is computable; thresholds are completely different from corporates (banks operate at 8x–12x D/E by design). Flag: "financial institution — D/E thresholds not applicable; regulatory capital ratios (CET1, Tier 1) govern; use for trend monitoring only" |
| Asset Coverage | `asset_coverage` | **Compute F1 only with flag** | Total and tangible asset coverage are computable from balance sheet and directionally meaningful. Liquidation haircuts (Formula 2) require bank-specific assumptions not defined in this spec. Flag: "financial institution — Formula 1 book value coverage only; liquidation haircuts not applicable without bank-specific asset quality data" |
| Near-Term Maturity Coverage | `maturity_coverage_near_term` | **Compute normally** | Debt maturities are real obligations regardless of sector; no flag needed |
| Debt Maturity Schedule | (maturity_schedule table) | **Compute normally** | Full maturity schedule extraction applies; lender confidence and refinancing risk signals are fully applicable |
| Loss Provisions Balance | `loss_provisions_balance` | **Compute normally — higher priority** | Loan loss provisions (allowance for credit losses) are a primary credit signal for banks; this metric is MORE analytically relevant for financial institutions than for most corporates. The provision balance, provision charge, and coverage ratio (provisions / total loans) are standard bank credit metrics. No flag needed; no suppression. |
| Covenant Headroom | `covenant_headroom_*` | **Phase 3 only — same as all issuers** | Credit agreements contain covenants regardless of sector; Phase 3 LLM extraction applies without modification |

---

**Suppression implementation:**

```
At extraction time, for each metric:

If issuer.institution_type = "financial":

   Check metric_name against suppression table:

   If action = "Suppress":
      Set value = null
      Set alert_level = null
      Set flags = ["financial institution —
                   standard ratio not applicable;
                   regulatory capital framework governs;
                   manual assessment required"]
      Write to metric_values table as normal
      Do NOT trigger any alerts for this metric
      Do NOT include in portfolio alert summary

   If action = "Compute with flag":
      Compute normally using standard extraction logic
      Append flag: [sector-specific flag text from table]
      Compute alert level using standard thresholds
      BUT add qualifier to all alerts:
      "[Alert level] — note: financial institution;
      threshold calibration may differ"

   If action = "Compute normally" or
              "Compute normally — higher priority":
      Execute with no modification
      No additional flag needed
```

---

**Display rule for financial institutions:**

Financial institution issuers are displayed separately from corporate issuers in all output formats to prevent misleading comparisons.

**Terminal output:**

```
PORTFOLIO SUMMARY — [date]

CORPORATE ISSUERS (26 names)
══════════════════════════════════════════════════════
COMPANY              LEVERAGE   COVERAGE   FCF    TOP ALERT
────────────────────────────────────────────────────────────
[Company A]            🔴10.2x    🔴-0.7x   🟠    🔴 CRITICAL
[Company B]            🟠 5.8x    🟡 2.1x   🟡    🟠 STRESS
...
══════════════════════════════════════════════════════

FINANCIAL INSTITUTION ISSUERS (4 names)
Limited metric coverage — regulatory framework applies
══════════════════════════════════════════════════════
COMPANY              REV TREND   MATURITY   PROVISIONS   MONITORING
────────────────────────────────────────────────────────────────────
[Bank A]              🟡 -2.1%   ✅ 2.3x    🟡 rising    8-K active
[Insurer B]           ✅ +3.4%   ✅ 4.1x    ✅ stable    8-K active
...
══════════════════════════════════════════════════════
Note: Standard credit ratios suppressed for financial
issuers. Columns show metrics applicable to this sector.
Manual review recommended for detailed credit assessment.
══════════════════════════════════════════════════════
```

**JSON output:** Financial institution issuers are stored in a separate top-level key `"financial_institution_issuers"` alongside the standard `"corporate_issuers"` key. Suppressed metrics appear in the JSON with `"value": null` and the suppression flag — they are not omitted entirely, so downstream consumers can distinguish suppressed from failed extractions.

---

**8-K monitoring for financial institutions:**

All six 8-K monitoring channels defined in the Leverage Frequency section remain fully active for financial institution issuers regardless of metric suppression. Financial institutions frequently disclose material events relevant to bondholders — regulatory enforcement actions, consent orders, large litigation settlements, capital ratio breaches — via 8-K. The keyword filters defined in LIQUIDITY.md and LOSS_PROVISIONS.md apply without modification. Going concern keyword monitoring is active.

Additionally, for financial institution issuers, activate two additional 8-K keywords not relevant for corporates:

```
Additional financial institution 8-K keywords:
   "regulatory capital"
   "capital requirement"
   "consent order"
   "cease and desist"
   "enforcement action"
   "Federal Reserve"
   "OCC" (Office of the Comptroller of the Currency)
   "FDIC"
   "PRA" (Prudential Regulation Authority — UK)
   "stress test"
   "DFAST"
   "living will"
```

Any 8-K containing these keywords generates a Flag alert regardless of which other metrics are active for the issuer.

---

**Pre-screening recommendation:**

Phase 2 delivers its maximum analytical value for non-financial corporate bond issuers. Before onboarding the 30-name portfolio, apply the following screen:

```
Pre-screening check at portfolio construction:
   Count issuers with SIC 6000–6499
   If count = 0–2:
      Standard onboarding with suppression rules above
      Financial institution issuers monitored via
      computable metrics and 8-K monitoring only
   If count = 3–6:
      Consider whether financial institution bonds
      are a deliberate allocation or incidental.
      If deliberate: discuss with Steven whether a
      separate financial institution monitoring module
      should be scoped before Phase 3.
      If incidental: use suppression rules and note
      the limited analytical coverage in system documentation.
   If count > 6:
      Standard corporate credit monitoring spec
      is not the right tool for this portfolio.
      A significant financial institution allocation
      requires a separate analytical framework based on
      regulatory capital ratios, NIM trends, deposit
      stability, and asset quality metrics.
      Phase 2 MVP should be scoped for the corporate
      portion of the portfolio first.
```

This recommendation is not a hard constraint — the system will function with financial institution issuers present using the suppression rules above. It is a flag that the analytical coverage is materially reduced for those issuers and the team should set expectations accordingly.

---


### 6.3 Data Storage Schema

---

**Database: SQLite for Phase 2**

Phase 2 uses a single SQLite database file (`credit_warning.db`) stored in the project directory. SQLite requires no server, no configuration, and no dependencies beyond the Python standard library. All tables below are created at first run if they do not exist.

---

**Table 1: issuers**

Stores one record per tracked company. Created at onboarding.

```sql
CREATE TABLE issuers (
    cik             TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    tickers         TEXT,          -- JSON array of ticker strings
    sic_code        TEXT,
    sector_group    TEXT,
    volatility_cat  TEXT,          -- Standard / Medial / Low / NA
    fiscal_year_end TEXT,          -- MM-DD format e.g. "12-31"
    onboarded_date  TEXT,          -- ISO date
    notes           TEXT           -- manual override notes
);
```

---

**Table 2: filings**

Stores one record per filing processed. Enables the system to know which filings have been ingested and avoid re-fetching.

```sql
CREATE TABLE filings (
    accession_number    TEXT PRIMARY KEY,
    cik                 TEXT NOT NULL,
    form_type           TEXT,      -- 10-K / 10-Q / 8-K
    period_end_date     TEXT,      -- ISO date
    filing_date         TEXT,      -- ISO date
    processed           INTEGER,   -- 0 = fetched, 1 = extracted
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);
```

---

**Table 3: metric_values**

Stores one record per metric per period per issuer. The core output table.

```sql
CREATE TABLE metric_values (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    filing_date     TEXT NOT NULL,
    form_type       TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    formula_version TEXT,          -- F1 / F2 / F3
    value           REAL,          -- null if extraction failed
    value_unit      TEXT,          -- ratio / percent / millions_usd / days
    alert_level     TEXT,          -- None / Watch / Flag / Stress / Critical
    flags           TEXT,          -- JSON array of flag strings
    source_tags     TEXT,          -- JSON object of {input: tag_used}
    audit_log       TEXT,          -- JSON object (full audit record)
    extraction_path TEXT,          -- primary / fallback_1 / fallback_2 / llm / derived
    created_at      TEXT,          -- ISO datetime
    FOREIGN KEY (cik) REFERENCES issuers(cik),
    UNIQUE (cik, period_end_date, metric_name, formula_version)
);
```

**metric_name values** — use these exact strings throughout the system:

| Metric | metric_name string |
|---|---|
| Leverage | `leverage` |
| Interest Coverage | `interest_coverage` |
| Free Cash Flow | `free_cash_flow` |
| FCF Margin | `fcf_margin` |
| OCF/EBITDA Conversion | `ocf_ebitda_conversion` |
| Liquidity — Current Ratio | `current_ratio` |
| Liquidity — Quick Ratio | `quick_ratio` |
| Liquidity — Cash Ratio | `cash_ratio` |
| Liquidity — Available Coverage | `available_liquidity_coverage` |
| Debt Maturity — Near-Term Coverage | `maturity_coverage_near_term` |
| Covenant Headroom — Leverage | `covenant_headroom_leverage` |
| Covenant Headroom — Coverage | `covenant_headroom_coverage` |
| Debt-to-Equity | `debt_to_equity` |
| Tangible Asset Coverage | `tangible_asset_coverage` |
| EBITDA Margin | `ebitda_margin` |
| Revenue YoY Growth | `revenue_yoy_growth` |
| Loss Provisions Balance | `loss_provisions_balance` |
| Asset Coverage | `asset_coverage` |

---

**Table 4: time_series**

For trend metrics that require 8-quarter history (EBITDA Margin, Revenue Trend), the rolling series is stored as a separate table rather than as a JSON array in metric_values — this enables SQL queries over time without JSON parsing.

```sql
CREATE TABLE time_series (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    value           REAL,
    yoy_change      REAL,          -- year-over-year change
    qoq_change      REAL,          -- quarter-over-quarter change
    trend_class     TEXT,          -- Growing/Stable/Declining/Accelerating
    FOREIGN KEY (cik) REFERENCES issuers(cik),
    UNIQUE (cik, metric_name, period_end_date)
);
```

---

**Table 5: maturity_schedule**

For Debt Maturity Wall — stores the rolling year-by-year maturity schedule as individual rows rather than a JSON array.

```sql
CREATE TABLE maturity_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    as_of_date      TEXT NOT NULL,  -- filing date of source
    fiscal_year_end TEXT NOT NULL,  -- year-end date of the maturity year
    maturity_year   INTEGER,        -- 1–5 or 99 for thereafter
    amount_millions REAL,
    source          TEXT,           -- xbrl / llm / patch
    patch_source    TEXT,           -- accession number if patched
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);
```

---

**Table 6: alerts**

Stores alert history — every time an alert level changes, a record is written here. Enables trend analysis of alert escalations and de-escalations.

```sql
CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    alert_level     TEXT NOT NULL,
    prior_level     TEXT,
    trigger_reason  TEXT,          -- description of what crossed the threshold
    created_at      TEXT,
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);
```

---

### 6.4 Period Handling Specification

---

**Two XBRL period types**

Every XBRL fact has one of two period contexts:

| Type | Definition | Examples |
|---|---|---|
| Instant | Value at a single point in time | Balance sheet items: Assets, Debt, Cash, Equity |
| Duration | Value covering a time range | Income statement and cash flow items: Revenue, EBITDA, Interest Expense, OCF, Capex |

Instant items cause no period alignment issues — they represent the balance sheet at the period end date. Duration items require careful handling in quarterly filings.

---

**Duration item handling — the YTD vs quarterly problem**

In 10-Q filings, companies report duration items in two possible formats:

- **Quarter-only:** The value covers only the three months of that quarter (e.g. April–June for Q2)
- **Year-to-date (YTD):** The value covers from fiscal year start through quarter end (e.g. January–June for Q2)

The XBRL period context identifies which format is used. Check the `startDate` and `endDate` in the period context:

```
If (endDate - startDate) ≈ 3 months: quarter-only → use directly
If (endDate - startDate) ≈ 6 months: YTD Q2 → subtract Q1 value
If (endDate - startDate) ≈ 9 months: YTD Q3 → subtract H1 value
If (endDate - startDate) ≈ 12 months: annual → use directly (10-K)
```

**Subtraction logic for quarterly derivation:**

```
Quarterly_Value(Q2) = YTD_Value(Q2) − Quarterly_Value(Q1)
Quarterly_Value(Q3) = YTD_Value(Q3) − YTD_Value(Q2)
Quarterly_Value(Q4) = Annual_Value − YTD_Value(Q3)
```

This logic applies to all duration items: Revenue, Operating Income, D&A, Interest Expense, Operating Cash Flow, Capital Expenditures, and any other income statement or cash flow item.

See FREE_CASH_FLOW.md → Section "Frequency" → Difference 3 for the original derivation of this logic. This section is the canonical reference — FREE_CASH_FLOW.md cross-references back here for all other metrics.

---

**Storage requirement for subtraction**

The subtraction logic requires storing cumulative period values, not just the most recent value. The system must retain:
- Q1 YTD value (to compute Q2 quarterly)
- Q2 YTD value (to compute Q3 quarterly)
- Prior year quarterly values (for YoY comparisons in trend metrics)

These are stored in `metric_values` with their original period context intact. The derived quarterly value is stored as a separate row with `extraction_path = "derived_quarterly"` and a flag indicating which prior period was subtracted.

---

**Period alignment for combined ratios**

Some metrics combine instant and duration items (e.g. Leverage = Net Debt (instant) / EBITDA (duration)). The alignment rule is:

- Use the instant value as of the period end date
- Use the duration value for the period ending on that same date
- For annual ratios using quarterly EBITDA: use trailing twelve months (TTM) = sum of four most recent quarterly EBITDA values

**TTM computation:**
```
TTM_EBITDA = Q(current) + Q(current-1) + Q(current-2) + Q(current-3)
```
Store TTM alongside the point-in-time quarterly value. Use TTM for leverage and coverage alert computation; use quarterly for trend analysis.

---

### 6.5 Output Specification — Phase 2 MVP

---

**Primary persistent store: SQLite**

All computed values are written to the SQLite database defined in Section 6.3 as the primary output. JSON and terminal outputs are derived views — they read from the database and do not store anything independently.

---

**Terminal output: formatted table**

When the user runs the system for a specific company, display a formatted table in the terminal:

```
Credit Warning System — [Company Name] ([Ticker]) — CIK [CIK]
Last updated: [datetime]
═══════════════════════════════════════════════════════════════════

METRIC               Q4 2022    Q1 2023    Q2 2023    Q3 2023    ALERT
─────────────────────────────────────────────────────────────────────
Leverage (F1)          5.1x       5.4x       6.8x      10.2x    🔴 CRITICAL
Interest Coverage      2.1x       1.8x       1.2x      -0.7x    🔴 CRITICAL
FCF Margin            -0.2%      -0.4%      -0.3%      -0.3%    🟠 STRESS
Current Ratio          1.22x      1.18x      1.15x      1.13x    🟡 WATCH
Quick Ratio            0.51x      0.47x      0.44x      0.42x    🔴 CRITICAL
EBITDA Margin          3.2%       2.8%       2.1%       1.8%     🟠 STRESS
Revenue YoY           -1.2%      -2.1%      -3.4%      -4.1%    🟠 STRESS
D/E Ratio              2.8x       3.1x       3.6x       4.1x    🟠 STRESS
─────────────────────────────────────────────────────────────────────
FLAGS:
  ⚠ Leverage: EBITDA negative in Q3 2023 — ratio not meaningful
  ⚠ Quick Ratio: retail/pharmacy sector adjustment applied
  ⚠ Interest Coverage: EBIT negative — acute stress signal
═══════════════════════════════════════════════════════════════════
```

Alert icons: 🔴 Critical, 🟠 Stress, 🟡 Flag, 🔵 Watch, ✅ No alert

---

**JSON export format**

Export on demand via a command flag. One JSON file per company per run, stored in `output/{CIK}_{date}.json`.

```json
{
  "cik": "0000084129",
  "name": "Rite Aid Corporation",
  "tickers": ["RAD"],
  "export_date": "2024-01-15",
  "periods": ["2022-Q4", "2023-Q1", "2023-Q2", "2023-Q3"],
  "metrics": {
    "leverage": {
      "formula": "F1",
      "values": {
        "2022-Q4": {
          "value": 5.1,
          "alert": "Flag",
          "flags": [],
          "source_tags": {
            "net_debt": "us-gaap:LongTermDebtNoncurrent + ...",
            "ebitda": "derived: OperatingIncomeLoss + DepreciationDepletionAndAmortization"
          }
        }
      }
    }
  },
  "active_alerts": [
    {
      "metric": "leverage",
      "level": "Critical",
      "triggered": "2023-Q2",
      "reason": "Leverage entered Highly Leveraged band (>5.5x adjusted threshold)"
    }
  ]
}
```

---

**Portfolio summary view**

When run across the full 30-name portfolio, output a summary table sorted by highest alert severity:

```
PORTFOLIO SUMMARY — [date]
══════════════════════════════════════════════════════
COMPANY              LEVERAGE   COVERAGE   FCF    TOP ALERT
────────────────────────────────────────────────────────────
Rite Aid (RAD)         🔴10.2x    🔴-0.7x   🟠    🔴 CRITICAL
[Company B]            🟠 5.8x    🟡 2.1x   🟡    🟠 STRESS
[Company C]            🟡 4.2x    ✅ 3.8x   ✅    🟡 FLAG
...
══════════════════════════════════════════════════════
```

---

### 6.6 Rate Limiting and Caching (Revised)

---

**SEC EDGAR rate limit**

The SEC enforces a maximum of 10 requests per second per IP address. Exceeding this returns HTTP 403 (blocked) or HTTP 429 (too many requests). The block duration is approximately 10 minutes for the first offense; repeated violations may result in longer blocks. These limits apply across all EDGAR domains: `data.sec.gov`, `efts.sec.gov`, and `www.sec.gov`.

**Proactive rate limiting — prevent 429s before they occur:**

```
Target request rate: 6–7 requests per second
(below the 10/sec hard limit; leaves margin for
network variance and burst requests)

Minimum interval between requests: 150ms
(~6.5 requests/second)

Implementation: sliding window rate limiter
Track timestamps of last N requests.
If N requests have been made in the last 1 second,
sleep until the oldest timestamp is more than
1 second old before making the next request.

Required header on every request:
User-Agent: CreditWarningSystem contact@yourfirm.com
(replace with actual app name and email address)
Missing User-Agent returns HTTP 403 immediately —
this is the most common cause of blocks for new
implementations.
```

**Reactive handling — exponential backoff with jitter:**

Exponential backoff with jitter is required because the API does not specify how long to wait before retrying. Without randomness, multiple clients retry at the same time, causing synchronized bursts that generate more 429s.

```
On HTTP 429 or HTTP 403 response:

   base_delay = 2 seconds
   max_delay = 60 seconds
   max_retries = 5

   For each retry attempt (0-indexed):
      jitter = random float between 0 and 1
      wait = min(base_delay × 2^attempt + jitter, max_delay)

   Wait sequence (approximate, before jitter):
      Attempt 0: ~2 seconds
      Attempt 1: ~4 seconds
      Attempt 2: ~8 seconds
      Attempt 3: ~16 seconds
      Attempt 4: ~32 seconds

   After 5 failed retries:
      Log error with URL, status code, and attempt count
      Mark filing as failed in the filings table
         (processed = -1, meaning extraction failed)
      Continue to next filing — do not crash the run

On HTTP 5xx (server error):
   Apply same exponential backoff as 429
   5xx errors are transient — EDGAR occasionally
   has brief outages; backoff handles these cleanly

On HTTP 404 (not found):
   Do not retry — the resource does not exist
   Log and mark as failed immediately

On network timeout (no response within 30 seconds):
   Apply same exponential backoff as 429
   Timeout indicates server overload, not a rate
   limit issue, but backoff is still appropriate
```

**Why not a fixed wait:** A fixed 60-second wait is slower than necessary when the server recovers quickly (common for brief rate limit triggers) and no safer than exponential backoff for extended blocks. Exponential backoff converges on the same total wait time in worst-case scenarios while recovering faster in typical scenarios.

---

**Caching strategy**

```
Cache location: ./cache/ directory
Cache filename: {CIK}_{endpoint_hash}_{period}.json

Example filenames:
   0000084129_companyfacts_20240115.json
   0000084129_LongTermDebtNoncurrent_2023Q3.json
   0000320193_submissions_20240115.json

Cache TTL rules:

   companyfacts bulk response (CIK companyfacts JSON):
      Cache TTL: 24 hours from fetch time
      This single file covers all XBRL tags for the
      company — always prefer this over individual
      tag queries; one fetch serves all metrics.
      At each run: check cache age; refetch if > 24 hours.

   Historical filing data
   (period_end_date more than 90 days before today):
      Cache TTL: permanent — never refetch
      SEC filings do not change after acceptance.
      A 10-Q filed in 2022 will never be amended
      to change its XBRL data.

   Recent filing data
   (period_end_date within last 90 days):
      Cache TTL: 24 hours
      A new filing may have arrived since last fetch.
      Refetch once per day maximum.

   EDGAR submissions index (filing list for CIK):
      Cache TTL: 24 hours
      New filings appear within minutes of EDGAR
      acceptance; daily refresh is sufficient for
      a credit monitoring system.

Cache hit behaviour:
   Before any API request: check cache directory
   for matching filename.
   If hit AND within TTL: use cached response;
   make no API call.
   If miss OR expired: fetch from API;
   write response to cache file; use response.

Cache invalidation:
   Manual: delete cache/{CIK}_*.json to force
   full refetch for a specific issuer.
   Automated: none beyond TTL rules above.
   Do not implement automated cache purging —
   historical data is valuable and cheap to retain.

Cache storage estimate for 30-name portfolio:
   ~30 companyfacts files × ~2MB each = ~60MB
   ~300 filing index files × ~50KB each = ~15MB
   Total cache size: approximately 75–100MB
   This is negligible on any modern system.
```

---

**Expected run times for 30-name portfolio:**

| Run Type | API Calls | Estimated Time |
|---|---|---|
| Initial run (cold cache) | ~30 companyfacts + ~60 filing index fetches | 3–5 minutes |
| Daily run (warm cache, new quarter just filed) | ~30 companyfacts TTL checks + ~30 new filings | 45–90 seconds |
| Daily run (warm cache, no new filings) | ~30 companyfacts TTL checks only | 10–20 seconds |
| Single issuer update | ~1 companyfacts + ~3 new filings | 5–10 seconds |

These estimates assume 150ms between requests and no 429 errors. A single 429 triggering backoff adds 2–30 seconds depending on retry count. In practice, with the proactive 150ms rate limiter active, 429 errors should be rare — the backoff logic is a safety net, not a regular occurrence.

### 6.7 File Map

---

**Canonical metric file list**

All twelve metric files are stored in the same directory. The filenames below are the canonical references used in all cross-references throughout the spec.

| Metric | Filename | Group | Phase 2 Formula |
|---|---|---|---|
| Leverage | `LEVERAGE.md` | Primary | F1 (XBRL deterministic) |
| Interest Coverage | `INTEREST_COVERAGE.md` | Primary | F1 (XBRL deterministic) |
| Free Cash Flow | `FREE_CASH_FLOW.md` | Primary | F1 (XBRL deterministic) |
| Liquidity | `LIQUIDITY.md` | Primary | F1 partial (no revolver) |
| Debt Maturity Wall | `DEBT_MATURITY_WALL.md` | Primary | F1 + XBRL maturity tags |
| Covenant Headroom | `COVENANT_HEADROOM.md` | Primary | Proxy only in Phase 2 |
| Debt-to-Equity Ratio | `DEBT_TO_EQUITY.md` | Group A | F1 (XBRL deterministic) |
| Quick / Current Ratio | `QUICK_CURRENT_RATIO.md` | Group A | F1 (XBRL deterministic) |
| EBITDA Margin Trend | `EBITDA_MARGIN_TREND.md` | Group B | F1 (derived from prior metrics) |
| Revenue Trend | `REVENUE_TREND.md` | Group B | F1 (derived from prior metrics) |
| Loss Provisions | `LOSS_PROVISIONS.md` | Group C | Partial XBRL only |
| Asset Coverage | `ASSET_COVERAGE.md` | Group C | F1 (XBRL deterministic) |

---

**Canonical section names**

Every metric file uses these exact section names. Cross-references use these names verbatim.

| Section | Heading as written in file |
|---|---|
| 1 | `What it is` |
| 2 | `Why it signals stress` |
| 3 | `Formula` |
| 4 | `Where it lives` |
| 5 | `Structured or Unstructured` |
| 6 | `Extraction Fallback Logic` |
| 7 | `Stress Threshold` |
| 8 | `Signal Timing` |
| 9 | `Frequency` |

---

**Key sub-section anchors**

For sections with named sub-items referenced across metric files:

| File | Section | Sub-item anchor | Used by |
|---|---|---|---|
| `LEVERAGE.md` | Formula | `Formula 1 XBRL Tags table` | DEBT_TO_EQUITY.md, COVENANT_HEADROOM.md |
| `LEVERAGE.md` | Extraction Fallback Logic | `Input 1 (Short-Term Borrowings)` | LIQUIDITY.md, DEBT_MATURITY_WALL.md |
| `LEVERAGE.md` | Extraction Fallback Logic | `Input 5 (Unrestricted Cash)` | LIQUIDITY.md, QUICK_CURRENT_RATIO.md |
| `LEVERAGE.md` | Stress Threshold | `Step 1 (volatility category table)` | INTEREST_COVERAGE.md, COVENANT_HEADROOM.md |
| `LIQUIDITY.md` | Formula | `Output 1A (Current Ratio)` | QUICK_CURRENT_RATIO.md |
| `LIQUIDITY.md` | Formula | `Output 1B (Quick Ratio)` | QUICK_CURRENT_RATIO.md |
| `LIQUIDITY.md` | Extraction Fallback Logic | `Input 2 (Current Liabilities)` | QUICK_CURRENT_RATIO.md |
| `LIQUIDITY.md` | Stress Threshold | `Dimension 2 (Quick Ratio thresholds)` | QUICK_CURRENT_RATIO.md |
| `LIQUIDITY.md` | Frequency | full section | QUICK_CURRENT_RATIO.md |
| `FREE_CASH_FLOW.md` | Frequency | `Difference 3 (YTD subtraction logic)` | REVENUE_TREND.md, EBITDA_MARGIN_TREND.md, Section 6.4 |
| `DEBT_MATURITY_WALL.md` | Frequency | full section | COVENANT_HEADROOM.md |

---

### 6.8 Cross-Reference Format Specification

---

**Purpose**

Every cross-reference in the twelve metric files follows a three-part format. This section defines that format so Claude Code can parse and resolve cross-references deterministically.

---

**The three-part format**

```
See [FILENAME.md] → Section "[Exact Section Name]" → [Instruction]
```

The three parts are:

| Part | Purpose | Example |
|---|---|---|
| `[FILENAME.md]` | Which file to open — always a canonical filename from the File Map in Section 6.7 | `LEVERAGE.md` |
| `Section "[Name]"` | Where in that file to look — always a canonical section name from Section 6.7 | `Section "Extraction Fallback Logic"` |
| `[Instruction]` | What to do with what is found — explicit; never inferred | `Input 1 (Short-Term Borrowings) — apply identical fallback chain` |

---

**The three instruction types**

| Instruction Type | Meaning | Example |
|---|---|---|
| `apply identical` | Use the referenced logic exactly as written; no modification | `apply identical fallback chain` |
| `apply with the following modification: [X]` | Use the referenced logic but change the specified element | `apply with the following modification: omit revolver component; set to null with flag` |
| `use as context only` | Read for background understanding; do not execute as logic | `use as context only — sector classification informs threshold selection` |

---

**Extended format for sub-item references**

When a cross-reference points to a specific sub-item within a section, add a fourth element:

```
See [FILENAME.md] → Section "[Section Name]" → [Sub-item] → [Instruction]
```

---

**Worked examples**

```
1. Identical application:
See LEVERAGE.md → Section "Extraction Fallback Logic"
→ Input 1 (Short-Term Borrowings)
→ apply identical fallback chain including CommercialPaper
   and LineOfCreditCurrent fallback tags; sum all non-null values

2. Modified application:
See LIQUIDITY.md → Section "Extraction Fallback Logic"
→ Input 2 (Current Liabilities)
→ apply with the following modification: if Current Liabilities = 0,
   mark Quick Ratio as undefined rather than null; flag separately

3. Context only:
See LEVERAGE.md → Section "Stress Threshold" → Step 1
→ use as context only — volatility category assigned at onboarding
   determines which threshold table applies to this issuer;
   do not re-execute assignment logic here

4. Full section reference:
See LIQUIDITY.md → Section "Frequency"
→ apply identical update schedule, Phase 2/Phase 3 channel
   priority table, and Q4 dark window guidance;
   no modifications required for Quick/Current Ratio metric

5. Derivation reference:
See FREE_CASH_FLOW.md → Section "Frequency" → Difference 3
→ apply identical YTD subtraction logic to Revenue duration items;
   store prior period cumulative values per Section 6.3 Table 4
```

---

**Resolving a cross-reference: step-by-step**

When Claude Code encounters a cross-reference during implementation:

```
Step 1: Identify the filename from Part 1.
        Open that file from the project directory.
Step 2: Navigate to the section named in Part 2.
        Use exact string match on section heading.
Step 3: If a sub-item is specified, locate it within
        the section by heading or label.
Step 4: Read the instruction in Part 3 (and Part 4
        if present) to determine what to do:
        — "apply identical": copy the logic
        — "apply with modification": copy and change
        — "use as context only": read, do not execute
Step 5: If the referenced section or sub-item does
        not exist in the file, raise an error:
        "Cross-reference resolution failed:
        [FILENAME.md] → Section '[Name]' not found"
        Do NOT silently infer an alternative.
```

---

**What cross-references are not**

Cross-references are not suggestions to read background material. They are executable instructions — when a metric file says "apply identical fallback chain from LEVERAGE.md", Claude Code should implement that fallback chain in the current metric's extraction code, not merely understand that the chain exists.

Cross-references are also not authorisations to copy-paste code verbatim. They instruct on logic, not implementation. The same fallback logic may be implemented differently depending on the programming language, framework, or data structure in use.

---



## Appendix 6.A — Phase 3 Enhancement: edgartools Library

The following appendix documents a Phase 3 enhancement option identified during the Section 6 review. It is provided for future reference and does not modify the Phase 2 specification above.

---

### Context

Section 6.6 defines rate limiting and caching using direct SEC EDGAR API calls with a custom rate limiter. This is the Phase 2 implementation.

For Phase 3, where LLM extraction of footnotes requires fetching full filing HTML documents alongside XBRL data, the edgartools library provides an alternative HTTP and extraction layer that may reduce custom code.

---

### Important Clarification

`EDGAR_ACCESS_MODE` is a parameter of the **edgartools third-party Python library**, not a native SEC EDGAR API parameter. This enhancement is optional and applies only if Phase 3 adopts edgartools as the HTTP and XBRL extraction layer.

---

### Recommended Configuration (if edgartools is adopted)

```bash
export EDGAR_IDENTITY="CreditWarningSystem contact@yourfirm.com"
export EDGAR_ACCESS_MODE="CAUTION"
export EDGAR_USE_LOCAL_DATA="True"
export EDGAR_LOCAL_DATA_DIR="./cache/edgar"
export EDGAR_RATE_LIMIT_PER_SEC="7"
```

| Parameter | Recommended Value | Rationale |
|---|---|---|
| `EDGAR_IDENTITY` | App name + contact email | Equivalent to User-Agent header |
| `EDGAR_ACCESS_MODE` | `CAUTION` | Production environment; more conservative than NORMAL |
| `EDGAR_USE_LOCAL_DATA` | `True` | Enable local caching |
| `EDGAR_LOCAL_DATA_DIR` | `"./cache/edgar"` | Cache directory path |
| `EDGAR_RATE_LIMIT_PER_SEC` | `7` | Below edgartools default (9) and SEC limit (10) |

---

### Access Mode Options

| Mode | Use Case | Recommended For |
|---|---|---|
| `NORMAL` | High-performance research, development | Testing Phase 3 with edgartools |
| `CAUTION` | Conservative production access | Phase 3 production deployment |
| `CRAWL` | Large-scale bulk processing | Not needed for 30-name portfolio (relevant >200 names) |

---

### Important Warning

Edgartools' HTTP 429 handling does **not** automatically retry. Regardless of which access mode is selected, the exponential backoff logic defined in Section 6.6 must be layered on top of edgartools' HTTP client. The access mode controls request concurrency and delays; it does not replace the retry logic.

---

### Decision Point for Phase 3

The choice between custom HTTP implementation (Phase 2 approach) and edgartools should be made at Phase 3 scoping. Key considerations:

- **Custom implementation (Phase 2):** Minimal dependencies, full control, SQLite cache already implemented
- **Edgartools (Phase 3):** Handles iXBRL parsing, XBRL fact extraction, and filing HTML retrieval through a single interface; adds a library dependency and its own caching layer

If edgartools is adopted, note that the rate limiting and caching strategy in Section 6.6 remains the authoritative specification — edgartools configuration must align with it, not replace it.

---

This appendix is informational only. No changes to the Phase 2 specification are required.

