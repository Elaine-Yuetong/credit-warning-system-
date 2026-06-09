# Credit Warning System — Data Extraction Specification

**Purpose:** Define exactly what the system extracts from SEC filings, why each metric matters, where it lives, and when it should trigger a warning.

## Section 1: Metric Definitions

For each metric, cover:

- **What it is**

- **Why it signals stress**

- **Formula**

- **Where it lives**

- **Structured** (XBRL tag) **or unstructured** (footnote → LLM)

- **Extraction fallback logic**

- **Stress threshold**

- **Signal timing**

- **Frequency**

Metrics to cover:

- **Leverage** — how much debt relative to earnings

- **Interest Coverage** — can they afford the interest payments

- **Free Cash Flow** — are they generating or burning cash

- **Liquidity** — do they have cash to cover near-term obligations

- **Debt Maturity Wall** — when does debt come due

- **Covenant Headroom** — how close are they to breaching loan conditions

- **Debt-to-Equity ratio** — overlaps heavily with leverage

- **Quick ratio / Current ratio** — overlaps with liquidity

- **EBITDA margin trend** — tells you if earnings quality is deteriorating, which feeds into leverage and coverage

- **Revenue trend** — declining revenue is an upstream signal before ratios blow up

- **Loss provisions / litigation contingencies** — the intern plan actually mentions this explicitly in Phase 1, so this one you should add

- **Asset coverage** — do assets cover debt if liquidated? More relevant for secured debt

## 1. Leverage

- **What it is** Leverage measures is how much debt a company is carrying relative to its earnings power.

> It answers: *"how many years of earnings would it take to pay off all the debt?"* A company with $600M of net debt and $100M EBITDA has 6x leverage — it would take 6 years of full earnings just to repay debt.
>
> Leverage ratios assess the ability of a company, institution, or individual to meet their financial obligations.

**Why it signals stress** High leverage means the company has little room for error. If earnings drop even modestly, debt becomes unsustainable. Lenders start getting nervous, refinancing gets harder, and the company may be forced into distressed territory. Rising leverage over time (even if not yet at a dangerous level) is often the earliest quantitative warning sign.

However

Investopia: “Uncontrolled debt levels can lead to credit downgrades or even worse consequences. However, too few debts can also raise questions. A reluctance or inability to borrow may indicate that operating margins are tight.”

**Formula**

### Leverage = Net Debt / EBITDA — Formula Specification

#### Formula 1 — Automated Baseline (XBRL / Deterministic)

**Formula:**

```text
Leverage = Net Debt / EBITDA
Net Debt = Total Debt − Unrestricted Cash
Total Debt = Short-Term Borrowings + Current Portion of Long-Term Debt + Long-Term Debt
EBITDA = Operating Income + Depreciation & Amortization
```

**XBRL tags:**

| **Input** | **Primary XBRL Tag** | **Fallback Tag** |
|----|----|----|
| Short-term borrowings | us-gaap:ShortTermBorrowings | us-gaap:NotesPayableCurrent |
| Current portion of LT debt | us-gaap:LongTermDebtCurrent | us-gaap:DebtCurrent |
| Long-term debt | us-gaap:LongTermDebtNoncurrent | us-gaap:LongTermDebt |
| Cash & equivalents | us-gaap:CashAndCashEquivalentsAtCarryingValue | us-gaap:CashCashEquivalentsAndShortTermInvestments |
| Operating income | us-gaap:OperatingIncomeLoss | us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes |
| D&A | us-gaap:DepreciationDepletionAndAmortization | us-gaap:DepreciationAndAmortization |

**What is excluded:** Operating lease liabilities, pension deficits, restructuring adjustments, any management addbacks. Purely what the structured filing reports.

**Error handling:** If any input tag is missing, mark the ratio null and log which tag failed. Never silently compute with a zero substitute.

#### Formula 2 — Moody's-Style (Adjusted, requires LLM footnote extraction)

**Formula:**

```text
Leverage = Moody's Adjusted Net Debt / Moody's Adjusted EBITDA
Moody's Adjusted Net Debt =
Total Debt (Formula 1 definition)
+ Capitalized Operating Lease Obligation*
+ Unfunded Pension Deficit (PBO minus plan assets)
− Unrestricted Cash
Moody's Adjusted EBITDA =
Operating Income
+ D&A
+ Pension service cost reclassification†
+ Operating lease depreciation component (2/3 of annual rent expense)
− Non-recurring gains (if any)
[Does NOT add back restructuring charges — treated as operating]
```

\* Moody's capitalizes operating leases by multiplying annual rent expense by a factor of 5x–10x depending on industry (or uses PV of minimum lease commitments if higher). Source: *Moody's Approach to Global Standard Adjustments*, ratings.moodys.com.

\* Moody's adjusts for the difference between pension service cost and total reported pension expense, reclassifying the excess to interest — this typically *increases* EBITDA for companies with large legacy pension obligations.

**What LLM must extract from footnotes:**

- Annual operating rent expense (pre-IFRS 16 filings) or right-of-use lease liability

- Pension projected benefit obligation (PBO) and fair value of plan assets

- Industry classification (to determine lease capitalization multiple)

**Net effect vs Formula 1:** Both adjusted debt *and* adjusted EBITDA increase. The leverage ratio can go either way — for heavily leased businesses (retail, airlines) the debt increase typically dominates and leverage rises.

#### Formula 3 — S&P-Style (Conservative, requires LLM footnote extraction)

**Formula:**

```text
Leverage = S&P Adjusted Net Debt / S&P Adjusted EBITDA
S&P Adjusted Net Debt =
Total Debt (Formula 1 definition)
+ Operating Lease Liabilities (balance sheet, post-ASC 842/IFRS 16)
+ Pension deficit (if material)
− Unrestricted Cash only (restricted cash explicitly excluded)
S&P Adjusted EBITDA =
Revenue
− Operating Expenses (as reported)
+ D&A (including noncash impairment charges)
[Restructuring charges: NOT added back — treated as recurring operating cost]
[Management fees: NOT added back — treated as cash operating cost]
[Stock-based compensation: NOT added back]
```

Source: *S&P Corporate Methodology: Ratios and Adjustments* (available via maalot.co.il); *S&P "EBITDA Addbacks Continue to Stack"*, spglobal.com, February 2022.

**What LLM must extract from footnotes:**

- Confirmation of restricted vs unrestricted cash

- Pension deficit if not on face of balance sheet

- Operating lease liabilities (for pre-2019 filings not yet under ASC 842)

**Key difference from Moody's:** S&P starts from revenue minus expenses (top-down), while Moody's starts from operating income (bottom-up). More importantly, S&P is consistently *more conservative* than Moody's and far more conservative than company-reported adjusted EBITDA, because it refuses restructuring and management fee addbacks that Moody's may permit case-by-case.

#### Implementation Guidance

**Formula 1** is the automated baseline. It uses only structured XBRL inputs, requires no human judgment, and can be computed fully deterministically in Phase 2. Every ratio it produces is traceable to a specific tag in a specific filing. It will systematically *understate* leverage for companies with large lease or pension obligations, but it is consistent, auditable, and fast.

**Formulas 2 and 3** represent the two major rating agency adjustment logics. They are more accurate representations of how professional credit analysts measure leverage, but both require footnote extraction — operating lease details, pension actuarial tables, and cash restriction disclosures are not in structured XBRL and must be read by an LLM.

These formulas are reserved for Phase 3, where the LLM extraction pipeline will be in place. Once implemented, they allow the system to be calibrated against Moody's or S&P ratings as a validation check: if the system's leverage score diverges significantly from the agency's implied leverage, that is itself a signal worth investigating.

**Where it lives**

#### Summary Table — Where Each Item Lives (details in appendix B)

| **Item** | **Formula** | **Statement / Document** | **Section** | **10-K only or both** |
|----|----|----|----|----|
| Short-term borrowings / CP | F1 | Balance Sheet | Current Liabilities | Both |
| Current portion LT debt | F1 | Balance Sheet | Current Liabilities | Both |
| LT debt non-current | F1 | Balance Sheet | Non-Current Liabilities | Both |
| Cash & equivalents | F1 | Balance Sheet | Current Assets | Both |
| Operating income | F1 | Income Statement | Operating section | Both |
| D&A | F1 | Cash Flow Statement | Operating Activities | Both |
| Operating rent expense | F2 | Lease Footnote | First table or paragraph | 10-K only |
| ROU lease liability | F2/F3 | Balance Sheet + Lease Footnote | Current + Non-current liabilities | Both |
| Pension PBO + plan assets | F2/F3 | Pension Footnote | Funded Status table | 10-K only |
| Pension service cost | F2 | Pension Footnote | Net Periodic Benefit Cost table | 10-K only |
| Non-recurring gains | F2 | Income Statement + MD&A | Other income / Results of Operations | Both |
| Restricted cash split | F3 | Cash Flow Statement + Note 1 | Reconciliation table at bottom of CFS | Both |
| Restructuring charges | F3 | Income Statement + Restructuring Footnote | Operating expenses + footnote detail | Both |
| Stock-based compensation | F3 | Cash Flow Statement + SBC Footnote | Operating Activities addback | Both |

**Structured or unstructured**

| **Input / Component** | **Formula** | **XBRL Tag** | **Structured or Unstructured** | **Notes** |
|----|----|----|----|----|
| **Short-term borrowings / Commercial paper** | F1 | Primary: us-gaap:ShortTermBorrowings Fallback 1: us-gaap:CommercialPaper Fallback 2: us-gaap:NotesPayableCurrent Fallback 3: us-gaap:LineOfCreditCurrent | Structured — but requires trying multiple tags | Do NOT rely on ShortTermBorrowings alone. Apple validation confirmed this tag is absent for CP issuers. Must try all four tags and **sum all non-null values** — a company can have both CP and a drawn revolver simultaneously. |
| **Current portion of long-term debt** | F1 | Primary: us-gaap:LongTermDebtCurrent Fallback: us-gaap:DebtCurrent | Structured — with double-count risk | DebtCurrent may aggregate short-term borrowings already captured above. If both ShortTermBorrowings and DebtCurrent are present, check for overlap before summing. Apple uses LongTermDebtCurrent cleanly. |
| **Long-term debt (non-current)** | F1 | Primary: us-gaap:LongTermDebtNoncurrent Fallback 1: us-gaap:LongTermDebt Fallback 2: us-gaap:LongTermDebtAndCapitalLeaseObligations | Structured — with ambiguity risk | LongTermDebt is ambiguous — may include current portion. If LongTermDebtCurrent is also present, subtract it. Fallback 2 bundles finance lease obligations — flag in audit log if used. |
| **Cash & cash equivalents** | F1, F2, F3 | Primary: us-gaap:CashAndCashEquivalentsAtCarryingValue Fallback 1: us-gaap:CashCashEquivalentsAndShortTermInvestments Fallback 2: us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents | Structured — with restriction risk | Fallback 1 includes short-term investments — flag. Fallback 2 includes restricted cash — must subtract us-gaap:RestrictedCashAndCashEquivalents if available, otherwise flag. F3 requires confirmed unrestricted cash only (see restricted cash row below). |
| **Operating income** | F1, F2 | Primary: us-gaap:OperatingIncomeLoss Fallback 1: us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes Fallback 2: Derived from GrossProfit − SG&A − R&D | Structured — with financing contamination risk on fallback | Fallback 1 includes interest income/expense — flag as "EBITDA includes financing items." Fallback 2 derivation may miss other operating expense lines — flag as "derived, verify completeness." |
| **Depreciation & amortization** | F1, F2 | Primary: us-gaap:DepreciationDepletionAndAmortization Fallback 1: us-gaap:DepreciationAndAmortization Fallback 2: Sum of us-gaap:Depreciation + us-gaap:AmortizationOfIntangibleAssets | Structured — most reliable from cash flow statement | Always extract from cash flow statement operating section first. Income statement version may be partial (manufacturing D&A only). Never substitute zero if missing — mark EBITDA null. |
| **EBITDA (derived)** | F1, F2 | No standard XBRL tag | Structured inputs, derived result | EBITDA = Operating Income + D&A. Must be derived — no tag exists. This is the central extraction challenge for the entire leverage metric. If either input is null, EBITDA = null. |
| **Revenue** | F3 | us-gaap:Revenues or us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | Structured | Used as S&P starting point (top-down approach). Reliable and consistently tagged. |
| **Operating expenses (as reported)** | F3 | us-gaap:OperatingExpenses or derived: CostOfRevenue + SG&A + R&D | Structured — may require summing | S&P computes EBITDA top-down as Revenue − Operating Expenses + D&A. Some companies tag OperatingExpenses as a single line; others require summing components. |
| **Operating lease rent expense (pre-ASC 842)** | F2 | No standard tag | **Unstructured — LLM required** | Only relevant for filings before fiscal year 2019. Lives in the **Lease Footnote** (typically Note 5–8, titled "Leases" or "Commitments and Contingencies"). LLM should read the **first table or paragraph** disclosing total rent/operating lease expense for the year — look for: *"Total rent expense was $X."* Moody's multiplies by 5x–10x to capitalize as debt; splits 1/3 to interest, 2/3 to depreciation for EBITDA. |
| **Operating lease ROU liability (post-ASC 842)** | F2, F3 | us-gaap:OperatingLeaseLiabilityCurrent + us-gaap:OperatingLeaseLiabilityNoncurrent | Semi-structured — balance sheet tags exist, footnote confirms | Post-2019 filings only. Current and non-current portions are on the balance sheet and tagged. Sum both. Confirm total in the **Lease Footnote maturity table**. F3 uses the liability directly; F2 uses this as the alternative to rent capitalization where available. |
| **Pension PBO and plan assets** | F2, F3 | No standard tag for PBO or fair value of plan assets | **Unstructured — LLM required** | Lives in the **Pension / Employee Benefits Footnote** (typically Note 8–12, titled "Employee Benefit Plans" or "Pension and Post-Retirement Benefits"). LLM should read the **"Funded Status" table** — it shows Projected Benefit Obligation and Fair Value of Plan Assets at year-end. Unfunded Deficit = PBO − Plan Assets. Only present in full in 10-K; 10-Q shows summary updates only. |
| **Pension service cost** | F2 | No standard tag | **Unstructured — LLM required** | Lives in the same Pension Footnote as above, in the **"Net Periodic Benefit Cost" table**. LLM should extract the "Service cost" line specifically. Moody's reclassifies excess pension expense over service cost to interest — this adjustment typically increases EBITDA for legacy pension companies. 10-K only. |
| **Restricted cash** | F3 | us-gaap:RestrictedCashAndCashEquivalents (if tagged) | Semi-structured — sometimes tagged, sometimes footnote only | Post-2018 filings should include a **reconciliation table at the bottom of the Cash Flow Statement** showing the split between restricted and unrestricted cash (required under ASU 2016-18). If absent or unclear, LLM should read **Note 1 (Summary of Significant Accounting Policies)** where the company defines what it includes in "cash and cash equivalents." S&P subtracts only unrestricted cash. |
| **Restructuring charges** | F3 | us-gaap:RestructuringCharges (sometimes tagged) | Semi-structured — tagged on income statement but detail in footnote | Income statement shows total; detail lives in the **Restructuring Footnote** (typically Note 6–10). LLM should confirm the total charge for the period and flag it. S&P does **not** add this back — it remains as an operating cost reducing EBITDA. This is the most common divergence point between company-reported Adjusted EBITDA and S&P EBITDA. |
| **Stock-based compensation** | F3 | us-gaap:ShareBasedCompensation | Structured — reliably tagged in cash flow statement | Tagged consistently in the cash flow statement operating section as a non-cash addback. Reliable XBRL source. However, S&P does **not** add this back to EBITDA — the tag is used only to *identify and exclude* it from any addback. Flag the amount in the audit log. |
| **Non-recurring gains** | F2 | Varies: us-gaap:GainLossOnDispositionOfAssets, us-gaap:GainsLossesOnExtinguishmentOfDebt, us-gaap:OtherNonoperatingIncomeExpense | Semi-structured — partially tagged, context requires LLM | Income statement may tag specific gain types. LLM should read the **MD&A — Results of Operations section** (first 2–3 paragraphs) and any **Other Income footnote** to confirm whether a gain is genuinely non-recurring. Moody's subtracts confirmed non-recurring gains from EBITDA. Do not subtract recurring items such as investment income. |

**Extraction fallback logic** EBITDA is the main problem. Since it has no standard XBRL tag:

#### Fallback Hierarchy

##### Level 1 — Preferred: Disaggregated XBRL Tags (Sum of Three Components)

**What the system attempts:** Query the XBRL instance document for each of the three debt components separately and sum all non-null values found.

**Tags to attempt, in order, for each component:**

**Component A — Short-Term Financial Debt** Try each tag below independently. Sum all non-null results (they are not mutually exclusive — a company may have both commercial paper and a drawn revolver):

1.  us-gaap:ShortTermBorrowings

2.  us-gaap:CommercialPaper

3.  us-gaap:NotesPayableCurrent

4.  us-gaap:LineOfCreditCurrent

5.  us-gaap:ShortTermBankLoansAndNotesPayable

**Component B — Current Portion of Long-Term Debt**

1.  us-gaap:LongTermDebtCurrent

2.  us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent *(flag: may include finance leases)*

3.  us-gaap:SecuredDebtCurrent

4.  us-gaap:UnsecuredDebtCurrent

**Component C — Long-Term Debt (Non-Current)**

1.  us-gaap:LongTermDebtNoncurrent

2.  us-gaap:LongTermDebtAndCapitalLeaseObligationsNoncurrent *(flag: may include finance leases)*

3.  us-gaap:SecuredLongTermDebt

4.  us-gaap:UnsecuredLongTermDebt

5.  us-gaap:SeniorLongTermNotes

6.  us-gaap:JuniorSubordinatedLongTermNotes

**When Level 1 succeeds:** At minimum, Component C must return a non-null value. If Component C is found, proceed with Level 1 result even if Components A or B are null — but log which components were missing.

**When to move to Level 2:** Component C returns null across all tags attempted.

**Audit log entry:**

```text
debt_extraction_level: 1
components_found: [A, B, C] or subset
tags_used: [list each tag that returned a value]
components_missing: [list any null components]
flag: "short-term debt components missing — Total Debt may be understated"
(only if A or B is null but C is present)
```

##### Level 2 — Fallback: Aggregated Debt Tags

**What the system attempts:** Query for tags that represent total debt as a single aggregated number, rather than broken-down components. These are less preferred because they may bundle items (finance leases, unamortized discounts) that introduce inconsistency across companies.

**Tags to try, in order:**

1.  us-gaap:DebtAndCapitalLeaseObligations *(total debt including capital/finance leases — flag if used)*

2.  us-gaap:LongTermDebtAndCapitalLeaseObligations *(non-current only — add DebtCurrent separately)*

3.  us-gaap:Liabilities — **do not use** as a proxy; too broad

**Double-count check before using Level 2:** If Level 1 returned partial results (e.g., Component C was found but A and B were null), compare:

- If DebtAndCapitalLeaseObligations \> Level 1 result → use Level 2 figure, discard Level 1 partial result, log the override

- If DebtAndCapitalLeaseObligations ≤ Level 1 result → retain Level 1 result, do not use Level 2

**When Level 2 succeeds:** Any of the above tags returns a non-null value.

**When to move to Level 3:** All Level 2 tags return null.

**Audit log entry:**

```text
debt_extraction_level: 2
tag_used: [tag name]
flag: "aggregated debt tag used — may include finance lease obligations;
Total Debt not fully disaggregated"
```

##### Level 3 — Last Structured Resort: Derive from Balance Sheet Totals

**What the system attempts:** Attempt to derive total financial debt by subtracting known non-debt liabilities from total liabilities. This is an approximation and should be flagged prominently.

**Derivation approach:**

```text
Estimated Financial Debt =
us-gaap:Liabilities (Total Liabilities)
− us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent
− us-gaap:DeferredRevenueCurrent
− us-gaap:DeferredRevenueNoncurrent
− us-gaap:OperatingLeaseLiabilityCurrent
− us-gaap:OperatingLeaseLiabilityNoncurrent
− us-gaap:DeferredTaxLiabilitiesNoncurrent
− us-gaap:OtherLiabilitiesCurrent
− us-gaap:OtherLiabilitiesNoncurrent
```

**When Level 3 succeeds:** us-gaap:Liabilities is non-null and at least three of the subtracted items are identifiable, giving a reasonable approximation.

**When to move to Level 4:** us-gaap:Liabilities itself is null, or fewer than three non-debt liability items can be identified (making the subtraction unreliable).

**Audit log entry:**

```text
debt_extraction_level: 3
flag: "APPROXIMATION — Total Debt derived by subtracting known non-debt
liabilities from total liabilities. Likely overstated.
Do not use for stress scoring without manual review."
non_debt_items_subtracted: [list tags used in subtraction]
items_not_found: [list tags that returned null and were omitted]
```

##### Level 4 — Extraction Failure

**What the system attempts:** No structured XBRL extraction was possible across Levels 1–3.

**System behavior:**

- Set Total Debt = null

- Set Net Debt = null

- Set Leverage = null

- Do **not** compute a ratio

- Do **not** substitute zero

- Escalate to manual review queue

**Audit log entry:**

```text
debt_extraction_level: 4 (FAILURE)
total_debt: null
net_debt: null
leverage: null
action_required: "Manual review — no debt data extractable from XBRL.
Check if company filed using non-standard taxonomy
or if filing is text-only (older filings pre-2009)."
```

#### Cross-Level Validation Rules

Before finalizing any Total Debt figure regardless of level, apply these sanity checks:

**Check 1 — Finance lease contamination** If the tag used includes "CapitalLeaseObligations" or "FinanceLease" in its name, flag: *"Total Debt may include finance lease obligations — overstated vs Formula 1 definition."* Formula 2/3 handle leases explicitly; including them in Formula 1 creates double-counting risk if the system is later upgraded.

**Check 2 — Unamortized discount/premium** XBRL debt tags typically report carrying value (net of unamortized discount, premium, and issuance costs), not face/principal value. This is correct for Formula 1 — do not attempt to gross up to par value.

**Check 3 — Negative Total Debt** If computed Total Debt is negative, set Total Debt = null and flag: *"Negative debt value — likely tagging error or netting artifact."* A company can be net cash (Net Debt negative) but Total Debt itself cannot be negative.

**Check 4 — Implausibly small Total Debt** If Total Debt \< 1% of us-gaap:Assets, flag for review: *"Total Debt appears unusually low relative to total assets — verify completeness of extraction."* This catches cases where only one component was found.

**Stress Threshold**

#### Volatility Category Per Issuer

Before applying any threshold, the system must classify each issuer into a volatility category. This determines which table applies. For Phase 2, assign manually when onboarding each issuer. For Phase 3, automate using SIC code mapping.

| **Volatility Category** | **Typical Industries** | **S&P Table** |
|----|----|----|
| Standard | Technology, healthcare, pharmaceuticals, business services, consumer staples | Table 4.7 |
| Medial | Retail, food & beverage, media, telecom, packaging | Table 4.8 |
| Low | Utilities, regulated infrastructure, government-related entities | Table 4.9 |
| **Not applicable** | Banks, insurance companies, oil & gas, metals & mining, REITs, project finance | **Do not apply Tables 4.7–4.9 — see Sector Exceptions below** |

If an issuer's industry is ambiguous between two categories, assign the higher-volatility category (more conservative — produces earlier warnings).

#### Threshold Table

**Standard Volatility — Table 4.7** *Apply to: Technology, healthcare, pharmaceuticals, business services, consumer staples*

| **Financial Risk Profile** | **Debt/EBITDA** | **Formula 1 Adjusted Threshold\*** |
|----|----|----|
| Minimal | \< 1.5x | \< 2.0x |
| Modest | 1.5x – 2.0x | 2.0x – 2.5x |
| Intermediate | 2.0x – 3.0x | 2.5x – 3.5x |
| Significant | 3.0x – 4.0x | 3.5x – 4.5x |
| Aggressive | 4.0x – 5.0x | 4.5x – 5.5x |
| Highly Leveraged | \> 5.0x | \> 5.5x |

**Medial Volatility — Table 4.8** *Apply to: Retail, food & beverage, media, telecom, packaging*

| **Financial Risk Profile** | **Debt/EBITDA** | **Formula 1 Adjusted Threshold\*** |
|----|----|----|
| Minimal | \< 1.75x | \< 2.25x |
| Modest | 1.75x – 2.5x | 2.25x – 3.0x |
| Intermediate | 2.5x – 3.5x | 3.0x – 4.0x |
| Significant | 3.5x – 4.5x | 4.0x – 5.0x |
| Aggressive | 4.5x – 5.5x | 5.0x – 6.0x |
| Highly Leveraged | \> 5.5x | \> 6.0x |

**Low Volatility — Table 4.9** *Apply to: Utilities, regulated infrastructure, government-related entities*

| **Financial Risk Profile** | **Debt/EBITDA** | **Formula 1 Adjusted Threshold\*** |
|----|----|----|
| Minimal | \< 2.0x | \< 2.5x |
| Modest | 2.0x – 3.0x | 2.5x – 3.5x |
| Intermediate | 3.0x – 4.0x | 3.5x – 4.5x |
| Significant | 4.0x – 5.0x | 4.5x – 5.5x |
| Aggressive | 5.0x – 6.0x | 5.5x – 6.5x |
| Highly Leveraged | \> 6.0x | \> 6.5x |

\* **Formula 1 Adjusted Threshold explanation:** The S&P tables above are calibrated to S&P-adjusted EBITDA (Formula 3), which is higher than unadjusted EBITDA because it adds back pension and lease adjustments. Formula 1 (unadjusted baseline, used in Phase 2) excludes these adjustments, producing a systematically higher leverage ratio for the same company. To avoid false positives in Phase 2, all thresholds are shifted +0.5x when Formula 1 output is used. This offset is a starting estimate and will be recalibrated against Formula 3 output once Phase 3 is complete.

#### Alert Trigger Rules

The S&P financial risk profile labels describe a state. These rules define when the system fires an alert and what action follows.

| **Alert Level** | **Trigger Condition** | **Action** |
|----|----|----|
| **Watch** | Ratio enters "Significant" band for this issuer's volatility category | Log entry; include in weekly analyst review |
| **Flag** | Ratio enters "Aggressive" band | Generate alert; move issuer to daily monitoring |
| **Stress** | Ratio enters "Highly Leveraged" band | Immediate alert; escalate to analyst same day |
| **Trend Flag** | Ratio increases by ≥ 1.0x in a single quarter, regardless of which band it is in | Alert regardless of absolute level — deterioration signal |
| **Critical** | EBITDA ≤ 0 (ratio undefined or negative) | Automatic Stress-level alert; mark as critical; flag for immediate manual review |
| **Extraction Failure** | Total Debt or EBITDA = null (extraction failed) | Do not compute ratio; log failure; add to manual review queue |

**On the Trend Flag:** A company moving from 2.5x to 3.5x in one quarter is a more urgent signal than a company that has been stable at 5.0x for eight quarters. The absolute level tells you where a company is; the trend tells you where it is going. Both must be tracked. The +1.0x threshold is a starting estimate — Phase 3 backtest should validate whether a tighter trigger (e.g., +0.75x) improves catch rate without excessive false positives.

**On persistent band occupancy:** If an issuer remains in the "Significant" or higher band for three consecutive quarters without improvement, escalate to the next alert level automatically even if the ratio has not crossed a new threshold. Stagnation at an elevated level is itself a warning sign.

#### Sector Exceptions

The following sectors fall entirely outside Tables 4.7–4.9. Applying these thresholds to them will produce systematically misleading results. Do not score these issuers on Debt/EBITDA leverage without modification.

| **Sector** | **Why Tables 4.7–4.9 Do Not Apply** | **Phase 2 Handling** |
|----|----|----|
| Banks and financial institutions | Leverage measured by regulatory capital ratios (CET1, Tier 1 capital) — Debt/EBITDA is not a relevant metric for deposit-funded institutions | Flag issuer at onboarding; exclude from leverage scoring; mark ratio as "not applicable" |
| Insurance companies | Leverage measured by financial leverage ratio and fixed-charge coverage; earnings are underwriting-based, not EBITDA-based | Flag issuer at onboarding; exclude from leverage scoring |
| Oil & gas / metals & mining | EBITDA is highly cyclical and commodity-price-dependent; S&P uses through-the-cycle EBITDA and commodity price decks that are not replicable from filed financials alone | Apply wider placeholder bands: Watch \> 3x, Flag \> 5x, Stress \> 7x; flag as "commodity-adjusted thresholds pending Phase 3" |
| Real estate / REITs | Uses Debt/EBITDA but with different thresholds; primary metrics are LTV (loan-to-value) and Debt/Assets | Apply Low Volatility table as a rough proxy; flag as "REIT — LTV not computed; leverage threshold approximate" |
| Project finance / infrastructure | Primary metric is DSCR (Debt Service Coverage Ratio), not Debt/EBITDA; cash flows are contractually structured rather than market-driven | Flag issuer; compute Debt/EBITDA for reference only; do not trigger alerts based on leverage alone |

#### Empirical Context and Backtest Anchor

The thresholds above are analytical classifications, not empirically validated default predictors for your specific portfolio. The following reference points anchor them to observed market behaviour and set expectations for Phase 3 validation.

**Historical reference — LBO market:** The average Debt/EBITDA at leveraged buyout inception has historically ranged from 5x–7x for speculative-grade issuers (S&P leveraged loan market data). Companies entering the "Highly Leveraged" band have shown materially elevated default rates within three to five years. This supports using \>5x (standard volatility) and \>6x (low volatility) as the outer stress boundary.

**Historical reference — Rite Aid:** As validated earlier in this spec, Rite Aid's leverage ratio deteriorated from 6.7x (fiscal 2021) to 5.4x (fiscal 2022, post debt reduction) before collapsing to \>10x in fiscal 2023 ahead of its October 2023 bankruptcy. Under the Standard Volatility table, the system would have flagged Rite Aid at the "Highly Leveraged" threshold (\>5x) as early as fiscal 2021 — approximately two years before the bankruptcy event. This is consistent with the catch-rate target in Phase 3.

**Phase 3 backtest validation targets:**

| **Metric** | **Target** |
|----|----|
| Catch rate (distressed names flagged before event) | ≥ 80% of known distressed cases flagged at "Aggressive" or above at least two quarters before event |
| Lead time | Median lead time of ≥ 2 quarters between first flag and credit event |
| False positive rate | ≤ 20% of healthy issuers flagged at "Aggressive" or above in any given quarter |

**Signal timing** **Medium — Signal Timing — Medium lag, with a structural blind spot in Q4.**

Leverage is a stock measure that moves slowly, confirming stress rather than predicting it. The data your system sees is between **40 days and 130 days old** at the moment of download, depending on where in the quarterly cycle the filing arrives. The typical case is **40 days of staleness** (filing day for a large accelerated filer). The worst-case structural gap is **~182 days**: Q3 data filed around November 9 is not superseded until the 10-K is filed around March 31 — a 142-day window in which Q4 deterioration is invisible to the system.

For a rising leverage trend to constitute an early warning, it must be visible across **at least 3 consecutive quarters** of filed data. Given the 40-day filing lag per quarter, the earliest a three-quarter trend can be confirmed is approximately **160 days (5.3 months)** after the first quarter in the trend series ended. This is the quantitative basis for describing leverage as a medium-lag, coincident-to-lagging indicator.

**Implication for Phase 2:** Your system should flag any Q4 data gap exceeding 90 days without a new filing as a "data staleness alert" — prompting a check for whether the company has filed an NT 10-K (extension request) or whether the 10-K is simply not yet due.

**Frequency** Updates **quarterly** via 10-Q (3x/year) and 10-K (annual). No intra-quarter updates unless the company issues an 8-K disclosing a major debt event (new borrowing, repayment, covenant amendment).

## Frequency — Updated Specification for Leverage Metric

### Overview

Leverage data arrives through six distinct channels. The table below maps all six.

| \# | Channel | Filing Type | Frequency | Legal Deadline After Event | Data Type | Leverage Impact |
|----|----|----|----|----|----|----|
| 1 | Quarterly financial statements | 10-Q | 3× per year | 40 days after quarter-end | Full financial statements — | Full leverage recompute |
| 2 | Annual financial statements | 10-K | 1× per year | 60 days after fiscal year-end | Full financial statements — structured XBRL | Full leverage recompute |
| 3 | Material debt event | 8-K Item 2.03 | Ad hoc | 4 business days after event | Debt amount and terms — unstructured text | Partial debt update — no EBITDA update |
| 4 | Debt acceleration / default trigger | 8-K Item 2.04 | Ad hoc | 4 business days after event | Triggering event description — unstructured text | Stress signal — no ratio recompute |
| 5 | New bond issuance | 424B / S-3 prospectus | Ad hoc | Day of pricing (same day or T+1) | Offering size, coupon, maturity — unstructured text | Debt increases — no EBITDA update |
| 6 | Earnings press release | 8-K Item 2.02 | 4× per year | Same day as release | Preliminary unaudited figures — unstructured text | Early leverage estimate before 10-Q |

### Phase Priority

- Phase 2: Monitor Channels 1 and 2 (10-Q and 10-K) for structured leverage recomputation. Monitor Channel 4 (Item 2.04) as an automatic escalation trigger.

- Phase 3: Add Channels 3, 5, and 6 for intra-quarter debt tracking and early warning.

### Signal Timing — Three-Tier Structure

| Tier | Source | Lag After Quarter-End | Lead Before 10-Q | Use in System |
|----|----|----|----|----|
| Tier 1 — Full recompute | 10-Q / 10-K | +40 days | n/a | Primary leverage ratio |
| Tier 2 — Early directional signal | 8-K Item 2.02 | +14 to +25 days | -15 to -25 days | Directional signal only; Phase 3 |
| Tier 3 — Real-time event trigger | 8-K Items 2.03 / 2.04 | Within 4 business days of event | Can occur any time | 2.03: partial debt update; 2.04: automatic Stress alert |

Appendix C JPM example

## Section 5: LLM vs Deterministic Split

A clear list of what gets computed by code vs what gets sent to an LLM for interpretation, and why.

#### Appendix A：

####  Comparison Table

|  | **Formula 1 — Baseline** | **Formula 2 — Moody's** | **Formula 3 — S&P** |
|----|----|----|----|
| **Starting point** | Operating Income | Pretax Income + adjustments | Revenue minus expenses |
| **Operating leases in debt** | ❌ No | ✅ Yes (capitalized multiple) | ✅ Yes (balance sheet liability) |
| **Pension deficit in debt** | ❌ No | ✅ Yes | ✅ Yes (if material) |
| **Restructuring addback** | n/a | ❌ No | ❌ No (stricter) |
| **Stock comp addback** | n/a | Sometimes | ❌ Never |
| **Management fee addback** | n/a | Sometimes | ❌ Never |
| **Restricted cash excluded** | ❌ (not distinguished) | Partially | ✅ Explicitly |
| **Requires LLM/footnotes** | ❌ No | ✅ Yes | ✅ Yes |
| **Relative EBITDA level** | Mid | Higher than F1 | Lower than F2 |
| **Relative debt level** | Lowest | Highest | High |
| **Implementation phase** | Phase 2 MVP | Phase 3 | Phase 3 |

#### Appendix B：

**Formula 1 — Automated Baseline**

All items are structured, on the face of financial statements, available in both 10-K and 10-Q.

| **Input** | **Financial Statement** | **Exact Line Item** | **Available In** |
|----|----|----|----|
| Short-term borrowings / Commercial paper | Balance Sheet — Current Liabilities | "Commercial paper" or "Short-term borrowings" or "Notes payable" | 10-K and 10-Q |
| Current portion of long-term debt | Balance Sheet — Current Liabilities | "Current portion of term debt" or "Current maturities of long-term debt" | 10-K and 10-Q |
| Long-term debt (non-current) | Balance Sheet — Non-Current Liabilities | "Term debt, non-current" or "Long-term debt, net of current portion" | 10-K and 10-Q |
| Cash & cash equivalents | Balance Sheet — Current Assets | "Cash and cash equivalents" | 10-K and 10-Q |
| Operating income | Income Statement | "Operating income" or "Income from operations" | 10-K and 10-Q |
| Depreciation & Amortization | Cash Flow Statement — Operating Activities | "Depreciation and amortization" (add-back line in indirect method) | 10-K and 10-Q |

**Note on D&A location:** The cash flow statement is the most reliable source because US GAAP requires it to be disclosed there under the indirect method. If missing from the cash flow statement, check the income statement footnotes or the PP&E footnote (typically Note 4–6 depending on the company).

**Formula 2 — Moody's-Style Adjustments**

These items are **unstructured** — they require LLM extraction from footnotes. All items below are **in addition to** the Formula 1 base inputs.

**Item 2a — Operating Lease Rent Expense (pre-ASC 842 filings, i.e., fiscal years before 2019)**

| **Field** | **Detail** |
|----|----|
| Where it lives | Lease Footnote (typically Note 5–8, titled "Leases" or "Commitments and Contingencies") |
| Available in | 10-K only (annual rent expense table rarely appears in 10-Q) |
| Exact location within footnote | First or second paragraph of the Lease Footnote, where the company discloses total operating lease/rent expense for the year. Look for a sentence like: *"Total rent expense was $X for fiscal year 20XX."* Or a small table showing "Operating lease cost" by year. |
| What LLM should extract | Single number: total annual operating rent expense in dollars. If broken into base rent and contingent rent, take base rent only. |
| Moody's use of this number | Multiply by 5x–10x (industry-dependent) to capitalize as debt. Allocate 1/3 to interest, 2/3 to depreciation for EBITDA adjustment. |

**Item 2b — Operating Lease Right-of-Use Liability (post-ASC 842 filings, i.e., fiscal years 2019 onwards)**

| **Field** | **Detail** |
|----|----|
| Where it lives | Balance Sheet (current + non-current operating lease liability lines) AND Lease Footnote |
| Available in | 10-K and 10-Q (post-ASC 842, these are on-balance-sheet) |
| Exact location | Balance sheet line items: "Operating lease liabilities, current" and "Operating lease liabilities, non-current." Confirmed and detailed in Lease Footnote maturity table. |
| What LLM should extract | Total operating lease liability = current portion + non-current portion. Also extract the implicit discount rate disclosed in the footnote (used to verify PV calculations). |

**Item 2c — Pension Projected Benefit Obligation (PBO) and Plan Assets**

| **Field** | **Detail** |
|----|----|
| Where it lives | Pension / Retirement Benefits Footnote (typically Note 8–12, titled "Employee Benefit Plans," "Pension and Other Post-Retirement Benefits," or similar) |
| Available in | 10-K only — full actuarial tables appear annually. 10-Q shows only a brief update. |
| Exact location within footnote | Look for the "Funded Status" table or "Change in Benefit Obligation" table. It will show: Projected Benefit Obligation (PBO) at year-end, Fair Value of Plan Assets at year-end. The difference (PBO minus assets) is the unfunded deficit. |
| What LLM should extract | Two numbers: (1) Projected Benefit Obligation total, (2) Fair Value of Plan Assets total. Compute: Unfunded Deficit = PBO − Plan Assets. If Plan Assets \> PBO, pension is overfunded — do not add to debt. |
| Also extract | Service cost for the year (disclosed in the "Net Periodic Benefit Cost" table in the same footnote). Used for the Moody's EBITDA pension reclassification. |

**Item 2d — Non-Recurring Gains**

| **Field** | **Detail** |
|----|----|
| Where it lives | Income Statement (gain on sale of assets, gain on debt extinguishment) and MD&A — Results of Operations section |
| Available in | 10-K and 10-Q |
| Exact location | Income statement line items such as "Gain on sale of business," "Gain on extinguishment of debt," or "Other income." MD&A typically explains material non-recurring items in the first few paragraphs of Results of Operations. |
| What LLM should extract | Any gain explicitly described as non-recurring, one-time, or related to asset sales/debt retirement. These are subtracted from EBITDA under Moody's approach. |

**Formula 3 — S&P-Style Adjustments**

These items are **in addition to** Formula 2 items where they differ. Key differences are around restricted cash and the treatment of restructuring.

**Item 3a — Restricted vs Unrestricted Cash**

| **Field** | **Detail** |
|----|----|
| Where it lives | Cash Flow Statement (reconciliation table at bottom, post-ASC 230 update) AND footnotes — typically "Summary of Significant Accounting Policies" (Note 1) or "Cash and Cash Equivalents" sub-note |
| Available in | 10-K and 10-Q |
| Exact location | Post-2018 US GAAP filings include a reconciliation table at the bottom of the cash flow statement titled "Reconciliation of cash, cash equivalents, and restricted cash." This shows the split explicitly. If absent, check Note 1 where the company defines what it includes in "cash and cash equivalents." |
| What LLM should extract | Two numbers: (1) unrestricted cash, (2) restricted cash. S&P subtracts only unrestricted cash from debt. If the company does not break this out, flag as "restricted cash status unknown — cash figure may include restricted amounts." |

**Item 3b — Operating Lease Liabilities (post-ASC 842, for S&P debt adjustment)**

Same location as Item 2b above. S&P uses the balance sheet liability directly (current + non-current) rather than Moody's rent capitalization approach. No additional extraction needed beyond Item 2b.

**Item 3c — Restructuring Charges (confirm S&P does NOT add back)**

| **Field** | **Detail** |
|----|----|
| Where it lives | Income Statement (separate line: "Restructuring charges" or included in operating expenses) AND Restructuring Footnote (typically Note 6–10, titled "Restructuring" or "Restructuring and Other Charges") |
| Available in | 10-K and 10-Q |
| Exact location | Income statement will show total restructuring charges for the period. The footnote breaks it down by type (severance, facility closure, asset write-downs). |
| What LLM should extract | Total restructuring charge for the period. Under S&P methodology, this is **not added back** — it stays as an operating expense reducing EBITDA. LLM should flag the amount and confirm it was treated as a deduction, not an addback. |
| Why this matters | Company-reported "Adjusted EBITDA" almost always adds restructuring back. S&P does not. This is often the single largest source of divergence between company EBITDA and S&P EBITDA. |

**Item 3d — Stock-Based Compensation (confirm S&P does NOT add back)**

| **Field** | **Detail** |
|----|----|
| Where it lives | Cash Flow Statement — Operating Activities (non-cash addback line: "Stock-based compensation expense") AND Stock Compensation Footnote |
| Available in | 10-K and 10-Q |
| Exact location | Cash flow statement operating section — line item "Share-based compensation" or "Stock-based compensation." Also disclosed in the Stock Compensation Footnote (typically Note 9–13). |
| What LLM should extract | Total stock-based compensation expense for the period. Under S&P methodology, this is **not added back** to EBITDA. LLM should flag the amount. Under company-reported Adjusted EBITDA, this is almost always added back — so this will be a consistent source of divergence. |

**Item 3e — Pension Deficit (for S&P debt adjustment)**

Same location as Item 2c. S&P includes pension deficit in adjusted debt if material. Use the same unfunded deficit figure (PBO minus plan assets) extracted for Formula 2.

#### Appendix C：

##### Appendix: Empirical Validation with JPMorgan Chase (CIK 0000019617)

##### Key Correction From Empirical Validation

Over 12 months, JPM filed 24 8-Ks but zero Item 2.03 filings and zero Item 2.04 filings. This is expected behavior for a large, investment-grade issuer.

Why 2.03 and 2.04 are rare for healthy investment-grade companies:

- Item 2.03 requires disclosure only when a company becomes obligated under a direct financial obligation that is material to the company. For a company like JPMorgan with hundreds of billions in outstanding debt, a single new bond issuance or credit facility amendment is rarely material at the entity level.

- Item 2.04 is triggered only by an event of default or acceleration. For healthy investment-grade companies, this item is essentially never filed.

##### The 8-K Noise Problem

JPM's 24 8-K filings over 12 months included: 10+ Item 8.01 filings, 4 Item 7.01 filings, and multiple governance filings (5.02, 5.03, 5.07). None of these are relevant to leverage monitoring in their standard form.

8-K filtering rule for credit stress purposes:

| 8-K Item | Description | Default Action |
|----|----|----|
| 2.02 | Earnings press release | Process |
| 2.03 | Material debt creation | Process immediately |
| 2.04 | Debt acceleration / default | Escalate immediately |
| 1.01, 8.01, 1.02 | Other agreements / events | Keyword filter (debt, covenant, default, credit facility, refinanc, borrow, repay) |
| 5.02, 5.03, 5.07, 7.01, 9.01 | Governance / FD / exhibits | Ignore |

##### Expected 8-K Filing Volume by Issuer Type

| Issuer Type | Typical 8-K filings per year | Items 2.03/2.04 per year | Items relevant to leverage |
|----|----|----|----|
| Large investment-grade (e.g., JPM, Apple, Microsoft) | 15–30 | 0–1 | 3–5 |
| Mid-size investment-grade (BBB-rated) | 10–20 | 0–2 | 4–8 |
| Leveraged / high-yield issuer (BB/B-rated) | 10–25 | 2–8 | 6–15 |
| Distressed issuer (CCC or below) | 15–40 | 5–15 | 10–25 |

##### Empirically Validated Example (JPM Q1 2026)

| Filing | Date | Days from Quarter-End (March 31) |
|----|----|----|
| JPM Q1 2026 quarter-end | March 31, 2026 | Day 0 |
| JPM Item 2.02 (earnings press release) | April 14, 2026 | +14 days |
| JPM 10-Q filed | May 1, 2026 | +31 days |

Lead time of Item 2.02 before 10-Q: 17 days.

##### Sources

- 10-Q deadline: SEC Final Rule 33-8644; Mayer Brown 2026 SEC Filing Deadlines

- 8-K Items 2.03 and 2.04: SEC Final Rules, March 2004; Form 8-K Instructions

- 8-K 4-business-day deadline: Mayer Brown 2026 SEC Filing Deadlines; Gibson Dunn 2026 SEC Filing Deadline Calendar

- EDGAR public availability: SEC Press Release 2002-75
