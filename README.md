# Credit Warning System

A Python CLI that monitors corporate bond issuers for credit stress by extracting financial metrics from SEC EDGAR filings — combining deterministic XBRL extraction with LLM-powered footnote reading to flag deterioration before it becomes a problem.

Built as a 3-phase internship project. All three phases complete. LLM extraction layer (Groups 1–7a) complete. Backtest validated on 30 distressed cases + 31 healthy controls + 12 stressed survivors with full statistical analysis.

---

## What It Does

Given a company's CIK number, the system:

1. Fetches XBRL-tagged financial data from SEC EDGAR
2. Computes 19 credit stress metrics across the last 8 quarters
3. Reads unstructured footnotes via LLM to extract covenant thresholds, maturity schedules, revolver availability, loss provisions, asset composition, and Moody's FCF adjustments
4. Applies volatility-aware alert thresholds (🔴 Critical / 🟠 Stress / 🟡 Flag / 🔵 Watch / ✅ None)
5. Stores results in SQLite with full audit trails (which tags were used, which fallbacks fired, why)
6. Prints a terminal table for quick review
7. Generates a static HTML dashboard for visual monitoring

Every computed value is traceable to its source — XBRL tag or LLM extraction with verbatim evidence.

---

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# XBRL extraction only (no API key required)
python cli.py 0000320193      # Apple — healthy control
python cli.py 0000019617      # JPMorgan — financial institution
python cli.py 0000084129      # Rite Aid — distressed anchor

# With LLM footnote extraction (requires Anthropic API key)
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_BASE_URL="https://api.apiyi.com"   # omit for direct Anthropic API
python llm_extractor.py 0000084129 10-Q             # extract + persist Rite Aid footnotes
python llm_extractor.py 0000320193 10-K             # extract + persist Apple footnotes
python cli.py 0000084129                            # CLI now uses real covenant thresholds
```

---

## Dashboard

Generate the static HTML dashboard from the current database and backtest results:

```bash
# Step 1 — populate the database with all backtest companies (20–30 min, runs once)
python populate_db.py

# Step 2 — generate the dashboard
python backtest.py --json backtest_results.json
python generate_dashboard.py

# Step 3 — open in browser
open dashboard.html
```

The dashboard has four sections:

| Section | Contents |
|---|---|
| **1 — Backtest Scorecard** | KPI cards (30/30 caught · 13% FP · 36mo lead · ✅ PASS) + 30-case table with first-signal alert level |
| **2 — Company Monitor** | Dropdown of 74 issuers, 19 metrics × 8 quarters with alert icons, leverage and interest coverage sparklines |
| **3 — Statistical Analysis** | Cohen's d horizontal bar chart for all 19 metrics, colour-coded by effect size |
| **4 — False Positive Analysis** | 4 remaining unannotated FPs with confirming metrics and explanations |

No backend required — single self-contained HTML file, opens in any browser.

---

## Validation Anchors

| Company | CIK | Expected Output |
|---|---|---|
| Apple Inc. | `0000320193` | No alerts on core metrics. Leverage ~0.3x. FCF margin ~25–36%. Maturity schedule: Year 1 $12,393M. Loss provisions: Tier 3 matters (patent, antitrust), regulatory investigation flagged. |
| JPMorgan Chase | `0000019617` | Financial institution suppression (SIC 6021). Leverage, coverage, current/quick ratio all null with suppression flag. |
| Rite Aid | `0000084129` | 🔴 Critical across leverage (negative EBITDA), interest coverage (−5.12x), current ratio (0.58x). Covenant coverage 🔴 Critical with real 1.0x threshold from LLM. Loss provisions 🔴 Critical ($204.54M accrued, Tier 5 matters, regulatory investigation). Chapter 11 October 2023. |

---

## Project Structure

```
credit-warning-system/
├── extractor.py          # SEC EDGAR HTTP client, XBRL extraction, YTD/TTM period engine
├── metrics.py            # 19 metric computations + LLM metric integration
├── thresholds.py         # Volatility-aware alert tables, SIC classification, tier alerts
├── db.py                 # SQLite schema (11 tables including LLM extraction tables)
├── cli.py                # Terminal table output, orchestration
├── sec_fetcher.py        # Filing HTML fetcher, footnote locators (debt, GC, contingency, PP&E, inventory, intangibles, MD&A capex)
├── llm_extractor.py      # Anthropic API calls, structured JSON extraction, persistence
├── backtest.py           # Phase 3 point-in-time backtest harness (30 distressed + 31 healthy + 12 survivors)
├── analyze_backtest.py   # Statistical analysis: Cohen's d, 95% CI, logistic regression
├── populate_db.py        # Bulk DB population for all backtest companies
├── generate_dashboard.py # Static HTML dashboard generator
├── test_manual.py        # Manual function test harness (44 checks)
├── test_period_engine.py # Unit tests for YTD subtraction and TTM logic (13 tests)
├── Makefile              # make test / make backtest / make all (CI entry points)
├── requirements.txt      # requests>=2.31, anthropic>=0.69, pydantic>=2
└── spec/                 # Phase 1 specification (12 metric files + Section 6)
```

---

## The 19 Metrics

| Metric | `metric_name` | Alert basis | LLM enhancement |
|---|---|---|---|
| Leverage | `leverage` | TTM Net Debt / EBITDA vs volatility tables | — |
| Interest Coverage | `interest_coverage` | TTM EBITDA / Interest Expense | Net interest reconstruction (Group 5) |
| Free Cash Flow | `free_cash_flow` | Quarterly OCF − Capex (millions) | — |
| FCF Margin | `fcf_margin` | FCF / Revenue % | — |
| Moody's Adjusted FCF | `moody_adjusted_fcf` | OCF + pension addback − maintenance capex − dividends | ✅ MD&A capex split (Group 7a) |
| RCF / Net Debt | `rcf_net_debt` | Retained Cash Flow / Net Debt | — |
| OCF/EBITDA Conversion | `ocf_ebitda_conversion` | OCF / EBITDA ratio | — |
| Current Ratio | `current_ratio` | Current Assets / Current Liabilities | — |
| Quick Ratio | `quick_ratio` | (Current Assets − Inventory − Prepaid) / CL | — |
| Debt-to-Equity | `debt_to_equity` | Total Debt / Shareholders' Equity | — |
| EBITDA Margin | `ebitda_margin` | EBITDA / Revenue % trend | — |
| Revenue YoY Growth | `revenue_yoy_growth` | YoY quarterly revenue growth | — |
| Asset Coverage | `asset_coverage` | Total Assets / Total Debt | — |
| Tangible Asset Coverage | `tangible_asset_coverage` | (Assets − GW − Intangibles − DTA) / Debt | — |
| Liquidation Asset Coverage | `liquidation_asset_coverage` | Haircut-adjusted asset value / Debt (Formula 2) | ✅ PP&E/inventory/intangibles composition (Group 6) |
| Near-Term Maturity Coverage | `maturity_coverage_near_term` | (Cash + STI + Revolver) / Year 1 Maturities | ✅ Full maturity schedule + revolver (Groups 2–3) |
| Covenant Headroom (Leverage) | `covenant_headroom_leverage` | Real threshold headroom; breach/Chapter 11 override | ✅ Actual covenant threshold from Debt Footnote (Group 1) |
| Covenant Headroom (Coverage) | `covenant_headroom_coverage` | Real threshold headroom; going-concern override | ✅ Actual covenant threshold from Debt Footnote (Group 1) |
| Loss Provisions | `loss_provisions_balance` | Tier-based alert (Tier 1–5 per ASC 450) | ✅ Per-matter tier classification (Group 4) |

---

## LLM Extraction Layer

### What is extracted

| Group | Source | Extracted fields |
|---|---|---|
| **1 — Covenant thresholds** | Debt Footnote + Credit Agreement | Leverage/coverage thresholds, springing mechanics, step-down schedule, breach/Chapter 11 detection |
| **2 — Maturity schedule** | Debt Footnote | Year 1–5 + Thereafter principal amounts |
| **3 — Revolving credit facility** | Debt Footnote | Commitment, drawn, letters of credit, net available, maturity date |
| **4 — Loss provisions** | Contingency Footnote + Item 3 | Per-matter ASC 450 tier (1–5), accrued amounts, regulatory investigation flag |
| **5 — Net interest reconstruction** | XBRL fallback | Gross interest from InterestIncomeExpenseNet + income tags |
| **6 — Asset composition** | PP&E / Inventory / Intangibles Footnotes | PP&E by type, inventory breakdown, intangible classification, collateral description |
| **7a — Moody's FCF adjustments** | MD&A Liquidity section | Maintenance vs growth capex split; D&A proxy when not disclosed |

### Loss provisions tier classification

| Tier | ASC 450 Language | Alert Level |
|---|---|---|
| 1 | Remote | ✅ None |
| 2 | Reasonably possible, quantified range | 🔵 Watch |
| 3 | Reasonably possible, no range, potentially material | 🟡 Flag |
| 4 | Probable, not yet estimable | 🟠 Stress |
| 5 | Probable, estimable — provision recorded | 🔴 Critical |
| — | Regulatory investigation disclosed | 🟠 Stress (minimum) |

---

## Phase 3 — Backtest Results

The distress signal is **≥2 non-suppressed metrics at Stress+** (excluding `current_ratio`, `debt_to_equity`, and `rcf_net_debt` from the confirmation count — statistically justified, see below).

```
SCORECARD: 30/30 distressed caught ≥2 quarters early
           catch rate 100% · FP rate 13% (4 unannotated / 31 controls; 2 annotated excluded)
           stress detection 12/12 survivors · median lead 36mo
TARGETS:   catch ≥80% ✅ · FP ≤20% ✅ · median lead ≥2Q ✅
RESULT:    ✅ PASS
```

**Distressed (30):** Retail (Rite Aid, Bed Bath & Beyond, JCPenney, Sears, Party City, Pier 1, Tailored Brands, Tupperware), Energy E&P (Chesapeake, Whiting, Denbury, Lilis, Extraction Oil, Sanchez, Briggs & Stratton), Media (iHeartMedia, Cumulus, Revlon), Transport (Hertz, Yellow Corp), Telecom (Frontier, Windstream, Intelsat), Healthcare/Pharma (Mallinckrodt, Lannett, Akorn), Services (WeWork, Garrett Motion, Conduent, Coty)

**Healthy controls (31):** Apple, Microsoft, J&J, Waste Management, P&G, Costco, Emerson, ITW, ADP, Colgate, Becton, Air Products, Ecolab, Cintas, Fastenal, Visa, Amgen, Eli Lilly, Caterpillar, Lockheed, RTX, Motorola, General Mills, Kimberly-Clark, Walmart, Home Depot, UPS, Paychex, Accenture, Exxon, Aflac

**Stressed survivors (12):** Macy's, Ford, Occidental, Delta, Carnival, GE, Kraft Heinz, Teva, Kohl's, Bausch, Pfizer, Texas Instruments

---

## Statistical Validation

All findings exploratory — n=30 distressed cases. See `analyze_backtest.py` for full output.

### Key findings (Cohen's d, alert-level ordinal [0,4])

| Metric | d | 95% CI | Result |
|---|---|---|---|
| `leverage` | +1.54 | [+0.85, +2.24] | **Large effect — conclusion** |
| `interest_coverage` | +1.52 | [+0.83, +2.22] | **Large effect — conclusion** |
| `rcf_net_debt` | +1.35 | [+0.67, +2.03] | Medium-large — likely meaningful |
| `current_ratio` | −0.03 | [−0.65, +0.59] | **Statistically inert** |

Only `leverage` and `interest_coverage` reach Altman (1968) benchmark separation (d > 1.2) with CI lower bound above 0.8. Reference: Altman, E.I. (1968). "Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy." *Journal of Finance*, 23(4), 589–609.

### Metrics excluded from confirmation count

| Metric | Statistical justification |
|---|---|
| `current_ratio` | d = −0.03, p = 0.92 — statistically inert; fires equally on healthy and distressed |
| `debt_to_equity` | 66 Critical-quarters on 31 healthy controls vs 18 on 30 distressed — capital structure artifact from buybacks |
| `rcf_net_debt` | Stress+ in only 50% of distressed at first signal; 14% of healthy IG quarters also Stress+ from dividend seasonality |

All three retained as displayed metrics — excluded from confirmation count only.

---

## Key Design Decisions

**Period handling:** YTD → quarterly subtraction by span detection. TTM = sum of 4 trailing quarters.

**Volatility-aware thresholds:** Standard / Medial / Low volatility tables assigned from SIC code, derived from S&P financial risk profile methodology.

**Fallback chains:** Missing inputs propagate as null with a flag — never silently produce wrong ratios.

**Financial institution suppression:** SIC 6000–6499 suppresses leverage, coverage, current/quick ratio, EBITDA margin, OCF/EBITDA conversion.

**LLM anti-hallucination:** Verbatim quote required for every extracted value. Null when absent.

**Maintenance capex proxy:** D&A used as proxy per Moody's convention when MD&A split not disclosed.

---

## Known Limitations

- LLM extractions point-in-time for most recent filing only — applied uniformly across displayed quarters
- PP&E footnotes structured by geography cannot be decomposed — blanket haircut applied
- Combined PP&E + finance lease ROU tag not used — conservative zero treatment when only combined tag available
- Maintenance vs growth capex split proxied by D&A for most companies
- Covenant EBITDA addbacks not extracted — GAAP EBITDA used as conservative proxy
- Statistical findings in d = 0.5–1.0 range have wide CIs at n=30 — hypothesis-generating only
- Backtest weighted toward retail (27%) and energy (23%) — technology and healthcare underrepresented
- Groups 7b (buyback classification) and 8 (revenue segments) deferred

---

## Phase Roadmap

| Phase | Status | Deliverable |
|---|---|---|
| 1 — Spec | ✅ Complete | 12 metric spec files + Section 6 |
| 2 — MVP | ✅ Complete | 19 metrics, SQLite, CLI, 57 unit tests |
| 3 — Backtest | ✅ Complete | 30/30 caught · 13% FP · 36mo lead · ✅ PASS |
| LLM Groups 1–7a | ✅ Complete | Covenant, maturity, revolver, loss provisions, asset coverage, net interest, Moody's FCF |
| Statistical validation | ✅ Complete | Cohen's d CI, logistic regression, recalibration on 30+31+12 case library |
| Dashboard | ✅ Complete | Static HTML, 74 issuers, Chart.js, no backend |
| Groups 7b + 8 | 🔲 Future | Buyback classification, revenue segments |
| Phase 4 | 🔲 Future | Logistic regression model (n ≥ 100), sector thresholds, automated refresh |

---

## Running the Tests

```bash
make test        # 13 unit tests + 44 manual checks
make backtest    # point-in-time backtest — exits 0 on PASS
make all         # test + backtest
```

---

## Data Sources

Structured data: [SEC EDGAR XBRL API](https://www.sec.gov/developer). No API key required. Rate limit: 10 req/s, targeted at 6–7 req/s with 150ms minimum interval and exponential backoff. 24h TTL cache for recent data, permanent cache for historical filings.

LLM extraction: [Anthropic Messages API](https://docs.anthropic.com/en/api/messages). Requires `ANTHROPIC_API_KEY`. Compatible with relay services via `ANTHROPIC_BASE_URL`.
