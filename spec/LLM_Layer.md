Let me search the spec thoroughly for all LLM-required extractions.Now I have the complete picture. Here is the **full and accurate LLM layer list** from the entire spec:

---

## Complete LLM Layer — All Extractions Required

**Your 5 priorities are correct but incomplete. There are 13 distinct LLM extraction areas.**

---

### Group 1 — Covenant Headroom (your Priority 1, expanded)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 1a | Covenant thresholds (leverage, coverage, liquidity, capex) | Debt Footnote + Credit Agreement Exhibit 10.x | COVENANT_HEADROOM.md |
| 1b | Covenant breach / waiver / amendment language | Debt Footnote + 8-K Item 1.01 | COVENANT_HEADROOM.md |
| 1c | Covenant step-down schedule | Debt Footnote + Credit Agreement | COVENANT_HEADROOM.md |
| 1d | Compliance affirmation statement | Debt Footnote | COVENANT_HEADROOM.md |
| 1e | Covenant EBITDA definition + addback list | Credit Agreement Exhibit 10.x | COVENANT_HEADROOM.md |
| 1f | Voluntary headroom disclosure by management | MD&A — Liquidity and Capital Resources | COVENANT_HEADROOM.md |

---

### Group 2 — Debt Maturity Wall (your Priority 2, expanded)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 2a | Full maturity schedule Year 1–5 + Thereafter | Debt Footnote table | DEBT_MATURITY_WALL.md |
| 2b | Revolving credit facility maturity date | Debt Footnote | DEBT_MATURITY_WALL.md |
| 2c | Covenant acceleration provisions (cross-default, change of control) | Debt Footnote + Exhibit 10.x | DEBT_MATURITY_WALL.md |
| 2d | Individual tranche descriptions (principal, maturity, coupon, type) | Debt Footnote | DEBT_MATURITY_WALL.md F3 |
| 2e | Floating rate reference + spread per tranche | Debt Footnote + Note 1 | DEBT_MATURITY_WALL.md F3 |
| 2f | Call and put features per tranche | Debt Footnote | DEBT_MATURITY_WALL.md F3 |
| 2g | New issuance tenor from 424B and 8-K Item 2.03 | 424B prospectus + 8-K | DEBT_MATURITY_WALL.md F3 |

---

### Group 3 — Revolving Credit Facility / Liquidity (your Priority 3)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 3a | Revolver commitment (total facility size) | Debt Footnote | LIQUIDITY.md |
| 3b | Revolver drawn amount | Debt Footnote (XBRL semi-structured fallback) | LIQUIDITY.md |
| 3c | Letters of credit outstanding | Debt Footnote | LIQUIDITY.md |
| 3d | Revolver maturity date | Debt Footnote | LIQUIDITY.md |
| 3e | Forward FCF projection from management guidance | MD&A — Liquidity and Capital Resources | LIQUIDITY.md |

---

### Group 4 — Loss Provisions (your Priority 4, expanded)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 4a | Provision roll-forward (beginning, additions, payments, reversals, ending) | Loss Contingency Footnote | LOSS_PROVISIONS.md |
| 4b | Individual matter descriptions + language tier classification (Tier 1–5) | Loss Contingency Footnote + Item 3 | LOSS_PROVISIONS.md |
| 4c | Unrecorded contingency maximum exposure | Loss Contingency Footnote prose | LOSS_PROVISIONS.md |
| 4d | New matter detection vs prior filing | Cross-period comparison of LLM extractions | LOSS_PROVISIONS.md |
| 4e | Settlement agreements | 8-K Item 1.01 + subsequent events footnote | LOSS_PROVISIONS.md |
| 4f | Insurance coverage offset | MD&A + contingency footnote | LOSS_PROVISIONS.md |
| 4g | Regulatory investigation disclosures | 8-K Item 8.01 + Item 3 | LOSS_PROVISIONS.md |

---

### Group 5 — Net Interest Reconstruction (your Priority 5)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 5a | Gross interest reconstruction from InterestIncomeExpenseNet + interest income tags | Interest Footnote / Note 1 | INTEREST_COVERAGE.md |

---

### Group 6 — Asset Coverage Formula 2 (not in your list)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 6a | PP&E composition by type (real estate, equipment, leasehold) for haircut application | PP&E Footnote Note 4–7 | ASSET_COVERAGE.md |
| 6b | Inventory type breakdown (raw materials, WIP, finished goods) | Inventory Footnote or Note 1 | ASSET_COVERAGE.md |
| 6c | Intangible asset composition by type (patents, customer lists, software) | Intangibles Footnote | ASSET_COVERAGE.md |
| 6d | Secured debt collateral description (which assets pledged, lien priority) | Debt Footnote prose | ASSET_COVERAGE.md |

---

### Group 7 — Free Cash Flow Moody's / S&P Adjustments (not in your list)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 7a | Maintenance vs growth capex split | MD&A capital expenditures discussion | FREE_CASH_FLOW.md F2/F3 |
| 7b | Share buyback classification (recurring programme vs opportunistic) | MD&A capital allocation discussion | FREE_CASH_FLOW.md F3 |

---

### Group 8 — Revenue Trend Segment Level (not in your list)

| # | What to extract | Document | Spec location |
|---|---|---|---|
| 8a | Segment revenue by reportable segment | Segment Footnote Note 14–18 | REVENUE_TREND.md |

---

## Prioritised Build Order for Your Remaining Days

| Priority | Group | Reason | Days |
|---|---|---|---|
| **Must build** | 1a–1d (Covenant breach + thresholds) | Supervisor explicitly required; immediate Critical alert value | Day 4–5 |
| **Must build** | 2a–2b (Maturity schedule + revolver maturity) | Core footnote extraction; directly improves existing metrics | Day 5 |
| **Must build** | 3a–3d (Revolver availability) | Completes Available Liquidity Coverage metric | Day 5 |
| **Must build** | 4a–4b (Provisions roll-forward + language tier) | Supervisor mentioned explicitly in Phase 1 | Day 6 |
| **Should build** | 5a (Net interest reconstruction) | Already flagged in code; straightforward | Day 6 |
| **Should build** | 6a–6d (Asset coverage haircuts) | Completes Formula 2 | Day 6–7 |
| **Nice to have** | 1e–1f, 2c–2g (Covenant EBITDA, tranche detail) | Analytically valuable but complex | Day 7 if time |
| **Defer** | 7a–7b, 8a (FCF adjustments, segments) | Lowest priority; not core to credit stress signal | After internship |

The Groups 1a–4b are what your supervisor was referring to when he said the program needs to read footnotes. Those are the non-negotiable LLM extractions. Everything else is enhancement.
