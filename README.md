# Credit Warning System

A Python CLI that monitors corporate bond issuers for credit stress by extracting financial metrics from SEC EDGAR filings and flagging deterioration before it becomes a problem.

Built as a 3-phase internship project. Phases 1 and 2 are complete. Phase 3 (backtest harness) is next.

---

## What It Does

Given a company's CIK number, the system:

1. Fetches XBRL-tagged financial data from SEC EDGAR
2. Computes 16 credit stress metrics across the last 8 quarters
3. Applies volatility-aware alert thresholds (🔴 Critical / 🟠 Stress / 🟡 Flag / 🔵 Watch / ✅ None)
4. Stores results in SQLite with full audit trails (which tags were used, which fallbacks fired, why)
5. Prints a terminal table for quick review

Every computed value is traceable to its source tag — no black-box numbers.

---

## Quickstart

```bash
# Install dependencies (one external library)
pip install -r requirements.txt

# Run against a single company (by CIK)
python cli.py 0000320193      # Apple — healthy control
python cli.py 0000019617      # JPMorgan — financial institution
python cli.py 0000084129      # Rite Aid — distressed anchor
```

---

## Validation Anchors

Three CIKs serve as validation anchors. Running these confirms the system is working correctly.

| Company | CIK | Expected Output |
|---|---|---|
| Apple Inc. | `0000320193` | No alerts. Leverage ~0.3–0.6x. FCF margin ~25–36%. EBITDA margin ~33–37%. Interest coverage null (Apple does not tag InterestExpense separately — correct behaviour). |
| JPMorgan Chase | `0000019617` | Financial institution suppression. SIC 6021. Leverage, coverage, current/quick ratio all null with suppression flag. FCF computed with financial institution flag. Revenue trend computed normally. |
| Rite Aid | `0000084129` | 🔴 Critical across leverage (negative EBITDA), interest coverage (−5.1x), current ratio (0.58x), maturity coverage (0.02x). D/E escalating to negative equity. EBITDA margin Critical (consecutive negative quarters). Consistent with October 2023 bankruptcy. |

---

## Project Structure

```
credit-warning-system/
├── extractor.py          # SEC EDGAR HTTP client, XBRL extraction, period engine
├── metrics.py            # 16 Formula-1 ratio computations
├── thresholds.py         # Volatility-aware alert tables, SIC classification
├── db.py                 # SQLite schema (6 tables)
├── cli.py                # Terminal table output, orchestration
├── test_manual.py        # Manual function test harness (44 checks)
├── test_period_engine.py # Unit tests for YTD subtraction and TTM logic (13 tests)
├── requirements.txt      # requests>=2.31 (only external dependency)
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

All are Formula 1 (deterministic XBRL extraction). Formula 2 and 3 (LLM footnote extraction) are Phase 3.

| Metric | `metric_name` | Alert basis | Phase 2 scope |
|---|---|---|---|
| Leverage | `leverage` | TTM Net Debt / EBITDA vs volatility tables | Full |
| Interest Coverage | `interest_coverage` | TTM EBITDA / Interest Expense | Full; net interest → null + flag |
| Free Cash Flow | `free_cash_flow` | Quarterly OCF − Capex (millions) | Full |
| FCF Margin | `fcf_margin` | FCF / Revenue % | Full |
| OCF/EBITDA Conversion | `ocf_ebitda_conversion` | OCF / EBITDA ratio | Full |
| Current Ratio | `current_ratio` | Current Assets / Current Liabilities | Full; no revolver |
| Quick Ratio | `quick_ratio` | (Current Assets − Inventory − Prepaid) / CL | Full; retail/mfg adjusted |
| Debt-to-Equity | `debt_to_equity` | Total Debt / Shareholders' Equity | Full; sector-grouped thresholds |
| EBITDA Margin | `ebitda_margin` | EBITDA / Revenue % trend | Full; no sector benchmark (Phase 3) |
| Revenue YoY Growth | `revenue_yoy_growth` | YoY quarterly revenue growth | Full; no sector context (Phase 3) |
| Asset Coverage | `asset_coverage` | Total Assets / Total Debt | F1 book value only |
| Tangible Asset Coverage | `tangible_asset_coverage` | (Assets − GW − Intangibles − DTA) / Debt | F1 only |
| Near-Term Maturity Coverage | `maturity_coverage_near_term` | (Cash + STI) / Current Debt Maturities | Current portion only; no full schedule |
| Covenant Headroom (Leverage) | `covenant_headroom_leverage` | Proxy: flag when leverage > 5.5x | Phase 3 will extract actual thresholds |
| Covenant Headroom (Coverage) | `covenant_headroom_coverage` | Proxy: flag when coverage < 2.0x | Phase 3 will extract actual thresholds |
| Loss Provisions | `loss_provisions_balance` | XBRL balance sheet tag attempt | Phase 3 for footnote extraction |

---

## Key Design Decisions

**Period handling:** SEC EDGAR XBRL reports duration items (income statement, cash flow) as either quarter-only or year-to-date. The system detects which by measuring the span between `start` and `end` dates and subtracts prior cumulative values to derive standalone quarterly figures: Q2 = H1 − Q1, Q3 = 9M − H1, Q4 = FY − 9M. Trailing twelve months (TTM) = sum of 4 most recent quarterly values. This is the most important correctness property of the extraction layer.

**Volatility-aware thresholds:** Leverage and coverage thresholds use three separate tables (Standard / Medial / Low volatility) derived from S&P's financial risk profile methodology. Volatility category is assigned at onboarding from SIC code. The Formula 1 thresholds are offset +0.5x / −0.5x from the published S&P tables to account for the absence of EBITDA addbacks in Phase 2.

**Fallback chains:** Every metric has a prioritised list of XBRL tags. When the primary tag is absent, the system tries fallbacks in order, records which tag was actually used, and attaches flags for anything that might affect interpretation (e.g. lease contamination, restricted cash bundling, gross inventory). Missing inputs never silently produce wrong ratios — they propagate as null with a flag.

**Financial institution suppression:** Issuers with SIC 6000–6499 are automatically classified as financial institutions. Leverage, coverage, current/quick ratio, EBITDA margin, and OCF/EBITDA conversion are suppressed (null + flag). FCF, revenue trend, D/E, asset coverage, maturity coverage, and loss provisions are computed with a financial institution flag appended.

**Audit trail:** Every row in `metric_values` stores `source_tags` (which XBRL tags were used), `flags` (JSON array of extraction warnings), `audit_log` (full computation inputs), and `extraction_path` (primary / fallback / derived_quarterly / ttm / none).

---

## How It Differs from the Reference Repo

The mentor's reference repo ([Khootz/Credit_Warning](https://github.com/Khootz/Credit_Warning)) is a TypeScript/Next.js + Prisma/Postgres full-stack web application. This implementation is a Python/SQLite CLI. The two systems share the same data source (SEC EDGAR companyfacts API) and general approach, but differ on:

| Area | Reference repo | This implementation |
|---|---|---|
| Language / stack | TypeScript, Next.js, Supabase | Python, SQLite, stdlib |
| Period handling | No YTD subtraction; uses fp labels | YTD → quarterly subtraction by span detection |
| TTM | Single quarter EBITDA (not TTM) | TTM = sum of 4 trailing quarters |
| Thresholds | Single universal fixed cutoffs | Volatility-aware tables (Standard/Medial/Low) per S&P methodology |
| Current/Quick ratio | Not implemented | Fully implemented with sector adjustments |
| Financial institution suppression | SVB hard-excluded | Systematic SIC 6000–6499 suppression with per-metric rules |
| Net interest detection | Not implemented | Null + flag when only net interest tag available |
| Audit trail | Limited | Full source_tags, flags, audit_log, extraction_path per row |
| Metrics | 5 partial | 16 Formula-1 metrics |

---

## Deferred to Phase 3 (LLM Layer)

The following are explicitly out of scope for Phase 2 and documented with `# PHASE 3 TODO` comments in the code:

- Full debt maturity schedule (Year 1–5 + Thereafter) from Debt Footnote — currently only current portion from balance sheet
- Revolving credit facility availability from Debt Footnote — excluded from Available Liquidity Coverage
- Actual covenant thresholds from credit agreements — currently using proxy alerts
- Covenant EBITDA addback definitions — currently using GAAP EBITDA
- Loss provisions footnote roll-forward and language classification (probable / reasonably possible / remote)
- Net interest expense reconstruction from `InterestIncomeExpenseNet` + interest income tags
- Sector benchmark comparisons for EBITDA margin and revenue trend
- Liquidation haircut-adjusted asset coverage (Formula 2)
- Implied interest rate sanity check

---

## Phase Roadmap

| Phase | Status | Deliverable |
|---|---|---|
| 1 — Understand and spec | ✅ Complete | 12 metric spec files + Section 6 implementation parameters (`spec/`) |
| 2 — MVP extraction | ✅ Complete | Python CLI, 16 metrics, SQLite, validated against 3 anchors, 57 unit tests |
| 3 — Backtest | 🔲 Next | Point-in-time backtest harness; catch rate + lead time measurement against known distressed cases |

---

## Running the Tests

```bash
# Unit tests for the period engine (13 tests — highest-risk logic)
python test_period_engine.py

# Manual function test harness (44 checks — all major functions)
python test_manual.py
```

Both should print all PASS with zero failures.

---

## Data Source

All data from [SEC EDGAR XBRL API](https://www.sec.gov/developer). No API key required. Rate limit: 10 requests/second. The system targets 6–7 requests/second with a 150ms minimum interval and exponential backoff (base 2s, max 60s, 5 retries) on 429/403/5xx responses. Responses are cached to `cache/` with 24h TTL for recent data and permanent cache for historical filings (> 90 days old).
