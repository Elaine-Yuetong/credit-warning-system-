# Credit Warning System

A Python CLI that monitors corporate bond issuers for credit stress by extracting financial metrics from SEC EDGAR filings — combining deterministic XBRL extraction with LLM-powered footnote reading to flag deterioration before it becomes a problem.

Built as a 3-phase internship project. All three phases complete. LLM extraction layer (Groups 1–4) also complete.

---

## What It Does

Given a company's CIK number, the system:

1. Fetches XBRL-tagged financial data from SEC EDGAR
2. Computes 16 credit stress metrics across the last 8 quarters
3. Reads unstructured footnotes via LLM to extract covenant thresholds, maturity schedules, revolver availability, and loss provisions
4. Applies volatility-aware alert thresholds (🔴 Critical / 🟠 Stress / 🟡 Flag / 🔵 Watch / ✅ None)
5. Stores results in SQLite with full audit trails (which tags were used, which fallbacks fired, why)
6. Prints a terminal table for quick review

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
├── metrics.py            # 16 Formula-1 ratio computations + LLM metric integration
├── thresholds.py         # Volatility-aware alert tables, SIC classification, tier alerts
├── db.py                 # SQLite schema (8 tables including LLM extraction tables)
├── cli.py                # Terminal table output, orchestration
├── sec_fetcher.py        # Filing HTML fetcher, footnote locator (Debt, GC, contingency)
├── llm_extractor.py      # Anthropic API calls, structured JSON extraction, persistence
├── backtest.py           # Phase 3 point-in-time backtest harness
├── test_manual.py        # Manual function test harness (44 checks)
├── test_period_engine.py # Unit tests for YTD subtraction and TTM logic (13 tests)
├── Makefile              # make test / make backtest / make all (CI entry points)
├── requirements.txt      # requests>=2.31, anthropic>=0.69, pydantic>=2
├── spec/                 # Phase 1 specification (12 metric files + Section 6)
│   ├── LEVERAGE.md
│   ├── INTEREST_COVERAGE.md
│   ├── FREE_CASH_FLOW.md
│   ├── LIQUIDITY.md
│   ├── DEBT_MATURITY_WALL.md
│   ├── COVENANT_HEADROOM.md
│   ├── DEBT_TO_EQUITY.md
│   ├── QUICK_CURRENT_RATIO.md
│   ├── EBITDA_MARGIN_TREND.md
│   ├── REVENUE_TREND.md
│   ├── LOSS_PROVISIONS.md
│   ├── ASSET_COVERAGE.md
│   └── SECTION_6.md
└── cache/                # EDGAR API response cache (gitignored)
```

---

## The 16 Metrics

| Metric | `metric_name` | Alert basis | LLM enhancement |
|---|---|---|---|
| Leverage | `leverage` | TTM Net Debt / EBITDA vs volatility tables | — |
| Interest Coverage | `interest_coverage` | TTM EBITDA / Interest Expense | Net interest → null + flag |
| Free Cash Flow | `free_cash_flow` | Quarterly OCF − Capex (millions) | — |
| FCF Margin | `fcf_margin` | FCF / Revenue % | — |
| OCF/EBITDA Conversion | `ocf_ebitda_conversion` | OCF / EBITDA ratio | — |
| Current Ratio | `current_ratio` | Current Assets / Current Liabilities | — |
| Quick Ratio | `quick_ratio` | (Current Assets − Inventory − Prepaid) / CL | — |
| Debt-to-Equity | `debt_to_equity` | Total Debt / Shareholders' Equity | — |
| EBITDA Margin | `ebitda_margin` | EBITDA / Revenue % trend | — |
| Revenue YoY Growth | `revenue_yoy_growth` | YoY quarterly revenue growth | — |
| Asset Coverage | `asset_coverage` | Total Assets / Total Debt | — |
| Tangible Asset Coverage | `tangible_asset_coverage` | (Assets − GW − Intangibles − DTA) / Debt | — |
| Near-Term Maturity Coverage | `maturity_coverage_near_term` | (Cash + STI + Revolver) / Year 1 Maturities | ✅ Full maturity schedule + revolver from Debt Footnote |
| Covenant Headroom (Leverage) | `covenant_headroom_leverage` | Real threshold headroom; breach/Chapter 11 override | ✅ Actual covenant threshold from Debt Footnote |
| Covenant Headroom (Coverage) | `covenant_headroom_coverage` | Real threshold headroom; going-concern override | ✅ Actual covenant threshold from Debt Footnote |
| Loss Provisions | `loss_provisions_balance` | Tier-based alert (Tier 1–5 per ASC 450) | ✅ Per-matter tier classification from Contingency Footnote |

---

## LLM Extraction Layer

The LLM layer reads unstructured footnote text from SEC filings that cannot be sourced from XBRL. It uses `sec_fetcher.py` to locate and extract the relevant footnote sections, then calls the Anthropic API via `llm_extractor.py` to produce structured JSON output.

### What is extracted

| Group | Source | Extracted fields |
|---|---|---|
| **1 — Covenant thresholds** | Debt Footnote + Credit Agreement | Leverage/coverage thresholds, springing mechanics, step-down schedule, maintenance vs incurrence |
| **2 — Maturity schedule** | Debt Footnote | Year 1–5 + Thereafter principal amounts; instrument-level dates aggregated by fiscal year |
| **3 — Revolving credit facility** | Debt Footnote | Commitment, drawn, letters of credit, net available, maturity date, springing maturity flag |
| **4 — Loss provisions** | Contingency Footnote + Item 3 | Per-matter ASC 450 tier (1–5), accrued amounts, maximum exposure, roll-forward, regulatory investigation flag |

### Compliance and breach detection

The LLM reads the Going-Concern note and Subsequent Events footnote alongside the Debt Footnote. This captures:
- Covenant breach disclosures → automatic 🔴 Critical on covenant headroom
- Chapter 11 / default events → automatic 🔴 Critical on covenant headroom
- Going-concern doubt → automatic 🟠 Stress on covenant headroom

### Loss provisions tier classification

Per LOSS_PROVISIONS.md (severity rises with tier number):

| Tier | ASC 450 Language | Alert Level |
|---|---|---|
| 1 | Remote — no financial impact expected | ✅ None |
| 2 | Reasonably possible, quantified range disclosed | 🔵 Watch |
| 3 | Reasonably possible, no range given but potentially material | 🟡 Flag |
| 4 | Probable, amount not yet estimable | 🟠 Stress |
| 5 | Probable, amount estimable — provision recorded | 🔴 Critical |
| — | Regulatory investigation disclosed | 🟠 Stress (minimum) |

### Relay compatibility

The LLM layer works with APIYI and other Claude API relay services. Set `ANTHROPIC_BASE_URL` to route through a relay. The `thinking` parameter is intentionally omitted for relay compatibility.

---

## Phase 3 — Backtest Results

The backtest rewinds each issuer to historical quarterly dates and scores using **only data filed on or before that date** — no look-ahead from later restatements. The distress signal is **≥2 non-suppressed metrics at Stress+ on the same date**.

```
SCORECARD: 6/6 distressed caught ≥2 quarters early · catch rate 100% · FP rate 17% · median lead 36mo
TARGETS:   catch ≥80% ✅ · FP ≤20% ✅ · median lead ≥2Q ✅
RESULT: ✅ PASS
```

**Distressed cases (6/6 caught):** Rite Aid, Bed Bath & Beyond, WeWork, Revlon, Party City, Yellow Corp — all flagged 27–36 months before bankruptcy, peak alert Critical.

**Healthy controls (6):** Apple, Microsoft, J&J, P&G, Costco stay clean. Waste Management flagged ⚠️ ANNOTATED — D/E spike from Stericycle acquisition (one-off leveraging event, not credit deterioration).

---

## Key Design Decisions

**Period handling:** XBRL duration items are reported as either quarter-only or year-to-date. The system detects which by measuring the span between `start` and `end` dates and subtracts prior cumulative values: Q2 = H1 − Q1, Q3 = 9M − H1, Q4 = FY − 9M. TTM = sum of 4 trailing quarterly values.

**Volatility-aware thresholds:** Leverage and coverage use three separate tables (Standard / Medial / Low volatility) derived from S&P's financial risk profile methodology, assigned at onboarding from SIC code. Formula 1 thresholds are offset ±0.5x to account for the absence of EBITDA addbacks.

**Fallback chains:** Every metric has a prioritised XBRL tag list. Missing inputs never silently produce wrong ratios — they propagate as null with a flag. Every row stores `source_tags`, `flags`, `audit_log`, and `extraction_path`.

**Financial institution suppression:** SIC 6000–6499 suppresses leverage, coverage, current/quick ratio, EBITDA margin, and OCF/EBITDA conversion with flags. FCF and revenue trend computed with a financial institution flag.

**LLM anti-hallucination:** Every LLM extraction requires a verbatim quote from the filing for each extracted value. Null when absent — the model is instructed never to infer or estimate values not explicitly stated.

---

## How It Differs from the Reference Repo

The mentor's reference repo ([Khootz/Credit_Warning](https://github.com/Khootz/Credit_Warning)) is a TypeScript/Next.js + Prisma/Postgres full-stack web application. This implementation is a Python/SQLite CLI with an LLM extraction layer.

| Area | Reference repo | This implementation |
|---|---|---|
| Language / stack | TypeScript, Next.js, Supabase | Python, SQLite, Anthropic SDK |
| Period handling | No YTD subtraction | YTD → quarterly subtraction by span detection |
| TTM | Single quarter EBITDA | TTM = sum of 4 trailing quarters |
| Thresholds | Single universal cutoffs | Volatility-aware tables (Standard/Medial/Low) |
| Current/Quick ratio | Not implemented | Fully implemented with sector adjustments |
| LLM extraction | Full-stack with LLM pipeline | Footnote-level: covenant, maturity, revolver, loss provisions |
| Loss provisions | Not implemented | ASC 450 tier classification (Tier 1–5) with per-matter detail |
| Covenant thresholds | Not implemented | Real thresholds from Debt Footnote; breach/going-concern overrides |
| Audit trail | Limited | Full source_tags, flags, audit_log, extraction_path per row |

---

## Known Limitations

- **LLM extractions are point-in-time for the most recent filing only** and are applied uniformly across all displayed quarters. Historical per-quarter LLM extraction is a future enhancement.
- **Net interest reconstruction** (when only `InterestIncomeExpenseNet` is available) is not implemented — flagged as null + "LLM required per spec."
- **Asset Coverage Formula 2** (liquidation haircut-adjusted) requires PP&E and inventory composition from footnotes — not yet implemented.
- **Covenant EBITDA addbacks** (management-defined adjustments from credit agreements) are not extracted — GAAP EBITDA is used as a conservative proxy.
- **Sector benchmarks** for EBITDA margin and revenue trend require external data — not yet wired.
- **Backtest case library** contains 6 distressed and 6 healthy issuers — sufficient for baseline calibration but not for statistically robust threshold validation. Expanding to 20+ cases is planned after the full LLM layer is implemented.
- **Footnote locator** uses keyword-density scoring and covers standard SEC filing heading variants. Non-standard or minimally-labelled footnotes may return found=False and receive no LLM extraction. A structural fallback (numbered note boundary detection) is planned for Phase 4.

---

## Phase Roadmap

| Phase | Status | Deliverable |
|---|---|---|
| 1 — Understand and spec | ✅ Complete | 12 metric spec files + Section 6 (`spec/`) |
| 2 — MVP extraction | ✅ Complete | 16 metrics, SQLite, CLI, 57 unit tests, 3 validated anchors |
| 3 — Backtest | ✅ Complete | Point-in-time harness — 6/6 caught, 17% FP, 36mo lead, ✅ PASS |
| LLM layer (Groups 1–4) | ✅ Complete | Covenant thresholds, maturity schedule, revolver, loss provisions |
| LLM layer (Groups 5–8) | 🔲 Future | Net interest reconstruction, asset coverage haircuts, FCF adjustments, segment revenue |

---

## Running the Tests

```bash
make test        # unit tests (period engine 13) + manual harness (44 checks)
make backtest    # point-in-time backtest — exits 0 on PASS
make all         # test + backtest (CI entry point)
```

---

## Data Source

All structured data from [SEC EDGAR XBRL API](https://www.sec.gov/developer). No API key required. Rate limit: 10 req/s — system targets 6–7 req/s with 150ms minimum interval and exponential backoff. Responses cached with 24h TTL for recent data, permanent cache for historical filings.

LLM extraction uses the [Anthropic Messages API](https://docs.anthropic.com/en/api/messages). Requires `ANTHROPIC_API_KEY`. Compatible with relay services via `ANTHROPIC_BASE_URL`.
