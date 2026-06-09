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



## 2. Interest Coverage

**What it is**

Interest Coverage measures whether a company generates enough operating earnings to pay the interest on its debt. 

> It answers: "for every $1 of interest the company owes, how many dollars of earnings does it have to cover it?" A company with $100M of EBITDA and $25M of interest expense has a coverage ratio of 4.0x — it earns four times what it needs just to service interest.

Unlike leverage, which measures the stock of debt relative to earnings, interest coverage measures the flow 
> it is a direct test of whether this year's earnings are sufficient to meet this year's interest bill. A company can have high leverage and still be comfortable if interest rates are low and maturities are far away. Conversely, a company with moderate leverage can face acute stress if its debt carries high coupons or if EBITDA has fallen sharply, compressing coverage toward 1.0x.

The ratio sits at the intersection of two independent risk factors: 
**earnings quality** and **debt cost**. 

Either can move it — a revenue shock compresses the numerator; a refinancing at higher rates expands the denominator. When both move against the company simultaneously, coverage can deteriorate very rapidly.

Coverage is also the metric most directly connected to cash reality. 
> A company cannot defer interest payments the way it can defer capex or hiring. Interest is contractual and due on a fixed schedule. A coverage ratio below 1.0x means the company cannot pay its interest bill from operations — it must draw on cash reserves, sell assets, or borrow more just to stay current. That is the definition of a company in acute financial distress.


## Why it signals stress
> Appendix A

Interest coverage signals stress through three distinct mechanisms, each operating on a different timeline.

### Mechanism 1 — The contractual floor problem (immediate)

- Interest payments are not discretionary. A company that misses an interest payment is in technical default within the grace period specified in its indenture — typically 30 days for public bonds.
- Unlike dividends, which can be cut, or capex, which can be deferred, interest cannot be negotiated away unilaterally after the debt is issued.
- As coverage falls toward 1.0x, the company has essentially no margin for error.
- A single bad quarter — an unexpected cost, a revenue shortfall, a working capital swing — can push it from barely covering interest to not covering it at all.
- The ratio does not need to reach zero to trigger a crisis. It only needs to reach a point where the next quarterly variance could push it below 1.0x.
  **conclusion: no need to be close to 0, it has been dangerous in 1.0x**

### Mechanism 2 — The refinancing feedback loop (medium term)

- Lenders and rating agencies monitor interest coverage as a primary indicator of debt serviceability.
- When coverage deteriorates, the credit consequences arrive before the company actually misses a payment. Rating agencies downgrade. Bond prices fall.
- New borrowing becomes more expensive — which directly increases future interest expense, which further compresses coverage.
- This feedback loop is self-reinforcing: a falling coverage ratio raises the cost of the debt that is causing the coverage to fall.
- Companies that enter this loop at coverage of 2.0x–3.0x can find themselves at 1.5x within two quarters simply because the cost of refinancing maturing debt has risen, even if EBITDA has not changed.
   **conclusion: The refinancing feedback loop is self-reinforcing**

### Mechanism 3 — The earnings quality signal (early warning)

- A coverage ratio that is falling over time — even from a comfortable level — tells you that either earnings are deteriorating, interest costs are rising, or both. Both are upstream signals of broader credit stress.
- A company declining from 8.0x to 5.0x to 3.0x over six quarters is sending a consistent directional message even if the absolute level has not yet crossed into danger territory.
- The trend is the warning.
- Coverage can function as an early warning indicator — a company does not need to reach a distressed absolute level for the trend to be actionable.
  **conclusion: Coverage functions as a leading indicator**



**Formula**
> Appendix B
---

**Interest Coverage = EBIT / Interest Expense**

This is the base definition used across most rating agency methodologies and academic literature. It uses EBIT rather than EBITDA because interest is a financing cost that sits below operating income — EBIT represents what the company earned from operations before paying lenders, which is the most direct measure of ability to service debt.

However, in practice three formula versions are used depending on the analytical purpose, exactly as with leverage.

---

**Formula 1 — Automated Baseline (XBRL / Deterministic)**

```
Interest Coverage = EBIT / Interest Expense

EBIT = Operating Income
     = us-gaap:OperatingIncomeLoss

Interest Expense = us-gaap:InterestExpense
                 OR us-gaap:InterestAndDebtExpense (fallback)
```

**XBRL tags:**

| Input | Primary XBRL Tag | Fallback Tag |
|---|---|---|
| EBIT (Operating Income) | `us-gaap:OperatingIncomeLoss` | `us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes` |
| Interest Expense | `us-gaap:InterestExpense` | `us-gaap:InterestAndDebtExpense` |

**What is excluded:** D&A addback, interest income netting, capitalized interest adjustment, lease interest component. Purely what the structured filing reports.

**Error handling:** If either input tag is missing, mark the ratio null and log which tag failed. Never silently compute with a zero substitute. If Interest Expense = 0 and the company carries visible debt, flag as "interest expense tag missing or zero — verify company has no debt before accepting."

**Rule:** If Interest Expense = 0 but Total Debt (from Leverage Formula 1 extraction) > 0, then:
1. Mark Interest Coverage = null (do not compute 0 or infinite)
2. Log: "Interest expense reported as zero but debt exists — possible netting or tag error"
3. Escalate to manual review queue

**Important note on EBIT vs EBITDA for coverage:**
Some practitioners use EBITDA/Interest Expense rather than EBIT/Interest Expense, arguing that D&A is non-cash and therefore available to service interest. Both versions are valid — they answer slightly different questions. EBIT/Interest asks "do operating earnings cover interest?" EBITDA/Interest asks "does operating cash generation cover interest?" For Formula 1, EBIT is preferred because it is directly tagged and requires no derivation. EBITDA coverage is computed separately as a supplementary figure.



**Note on EBIT definition:** For Formula 1, EBIT is defined as `us-gaap:OperatingIncomeLoss`. The system does not attempt to add back non-operating income or expense. This is the cleanest XBRL-based definition and matches the most common rating agency starting point.

---

**Formula 2 — Moody's-Style (Adjusted, requires LLM footnote extraction)**

```
Interest Coverage = Moody's Adjusted EBIT / Moody's Adjusted Interest Expense

Moody's Adjusted EBIT =
    Operating Income
  + Pension service cost reclassification
  + Operating lease depreciation component (2/3 of annual rent expense)
  − Non-recurring gains (if any)
  [Does NOT add back restructuring charges]

Moody's Adjusted Interest Expense =
    Reported Interest Expense
  + Pension interest cost reclassification
    (excess pension expense over service cost, reclassified from operating to interest)
  + Operating lease interest component (1/3 of annual rent expense)
  − Capitalized interest (if any — not yet cash paid)
```

**What LLM must extract from footnotes:**
- Annual operating rent expense (pre-ASC 842) or ROU lease liability (post-ASC 842) — same as Leverage Formula 2
- Pension service cost and total pension expense — same as Leverage Formula 2
  > See LEVERAGE.md → Section "Where it lives" → Item 2a (Operating Lease Rent Expense) — same footnote location applies
  > See LEVERAGE.md → Section "Where it lives" → Item 2b and 2c (ROU lease liability and Pension PBO) — same footnote locations apply
  
- Capitalized interest amount (disclosed in PP&E footnote or interest expense footnote)



**Net effect vs Formula 1:** Moody's adjusted interest expense is typically higher than reported interest expense because it adds the lease interest component and pension interest reclassification. Adjusted EBIT is also typically higher. The net direction of the coverage ratio depends on which adjustment dominates — for heavily leased businesses, the interest expense increase typically outweighs the EBIT increase, compressing coverage.

---

**Formula 3 — S&P-Style (Conservative, requires LLM footnote extraction)**

S&P uses a fixed charge coverage ratio rather than pure interest coverage, which is more conservative because it includes lease payments as a fixed charge alongside interest.

```
Fixed Charge Coverage = S&P Adjusted EBITDA / Fixed Charges

S&P Adjusted EBITDA =
    Revenue
  − Operating Expenses (as reported)
  + D&A
  [Restructuring charges: NOT added back]
  [Stock-based compensation: NOT added back]
  [Management fees: NOT added back]

Fixed Charges =
    Interest Expense (gross, not netted against interest income)
  + Operating Lease Payments (current year)
  + Preferred Dividends (if any)
  [Capitalized interest: included — S&P treats it as a real cost]
```

Source: S&P Corporate Methodology: Ratios and Adjustments (maalot.co.il); S&P defines fixed charge coverage as a key ratio alongside Debt/EBITDA in the financial risk profile assessment. (No change — this is an external citation, not an internal cross-reference)

**Key difference from Moody's:** S&P includes the full operating lease payment in fixed charges (not just the interest component) and does not add lease depreciation back to EBIT. This makes S&P's fixed charge coverage consistently lower than Moody's interest coverage for leased businesses — S&P is more conservative on this metric as it is on leverage.

**What LLM must extract from footnotes:**
- Current year operating lease payments (from Lease footnote maturity table — the amount due within 12 months)
- Preferred dividend amount (from equity section or dividend footnote — if applicable)
- Capitalized interest (from PP&E footnote or interest expense footnote)



**Implementation guidance**

Formula 1 is the automated baseline for Phase 2. Both EBIT and Interest Expense are among the most reliably tagged items in XBRL — this ratio has fewer extraction challenges than leverage. The main failure mode is companies that net interest income against interest expense and report only a net figure, which understates gross interest expense and overstates coverage. Flag any case where `us-gaap:InterestExpense` appears lower than expected relative to the company's total debt load.

Formulas 2 and 3 are reserved for Phase 3. Once implemented, the divergence between Formula 1 coverage and Formula 3 fixed charge coverage for the same company is itself an analytical signal — a large gap indicates the company has significant lease obligations that are not reflected in the headline interest coverage number.

---

## Where it lives

> Appendix C
---

**Formula 1 — Automated Baseline**

All items are structured, on the face of financial statements, available in both 10-K and 10-Q.

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| EBIT (Operating Income) | Income Statement | "Operating income" or "Income from operations" | 10-K and 10-Q |
| Interest Expense | Income Statement — below operating income, in the "Other income / expense" section | "Interest expense" or "Interest and debt expense" | 10-K and 10-Q |

**Note on Interest Expense location:** Unlike operating income which sits in the operating section, interest expense lives below the operating income line in the non-operating / other income and expense section. In the XBRL document it is tagged separately from operating items. Some companies present a subtotal called "Total other expense, net" that bundles interest expense with other non-operating items — if this is the only tag available, LLM extraction from the income statement footnote is required to isolate interest expense alone.

**Note on interest income netting:** Some companies — particularly those with large cash balances like Apple or Microsoft — report only net interest (interest expense minus interest income) as a single line item rather than gross interest expense. This overstates coverage because it reduces the denominator. Your system must detect this and flag it. The signal is: `us-gaap:InterestExpense` is absent but `us-gaap:InterestIncomeExpenseNet` is present. When this occurs, gross interest expense must be reconstructed from the interest footnote via LLM.

> **Phase 2 rule for bundled interest expense:**
> If `us-gaap:InterestExpense` is absent and only `us-gaap:InterestIncomeExpenseNet` or a bundled "Other expense, net" line exists:
> - Mark Interest Coverage = null
> - Log: "interest expense cannot be isolated from net interest or other non-operating items — LLM required for Phase 3"
> - Do not compute a ratio using the net figure (it would overstate coverage)

> **Phase 3 rule:**
Use LLM to extract gross interest expense from the interest footnote or income statement footnote, then recompute coverage.

---

**Formula 2 — Moody's-Style Adjustments**

All adjustment items are unstructured — they require LLM extraction from footnotes. All items below are in addition to the Formula 1 base inputs.

**Item 2a — Capitalized Interest**

| Field | Detail |
|---|---|
| Where it lives | PP&E Footnote (typically Note 4–7, titled "Property, Plant and Equipment") or the Interest Expense footnote if one exists separately |
| Available in | 10-K only in most cases; occasionally in 10-Q for capital-intensive companies mid-construction |
| Exact location within footnote | Look for a sentence or table disclosing "capitalized interest" or "interest capitalized during the period." It typically appears as a reconciliation: gross interest incurred minus capitalized interest equals interest expense charged to income. |
| What LLM should extract | Single number: total interest capitalized during the period. Moody's subtracts this from reported interest expense because capitalized interest has not yet been charged to the income statement — it is not a current cash obligation against earnings. |

> See LEVERAGE.md → Section "Where it lives" → Item 2a (Operating Lease Rent Expense) — identical location; apply identical extraction


**Item 2b — Pension Interest Cost Reclassification**

| Field | Detail |
|---|---|
| Where it lives | Pension / Employee Benefits Footnote — See LEVERAGE.md → Section "Where it lives" → Item 2c (Pension PBO and Plan Assets) — identical footnote location (typically Note 8–12); extract pension interest cost from "Net Periodic Benefit Cost" table, same table used for Leverage Formula 2 |
| Available in | 10-K only |
| Exact location within footnote | The "Net Periodic Benefit Cost" table. Look for the line items "Interest cost" and "Service cost" within that table. Moody's reclassifies the excess of total pension expense over service cost — including the interest cost component — from operating expense to interest expense. |
| What LLM should extract | Two numbers from the Net Periodic Benefit Cost table: (1) Service cost, (2) Interest cost. The interest cost component is added to the interest expense denominator under Moody's adjusted methodology. |

**Item 2c — Operating Lease Interest Component**

| Field | Detail |
|---|---|
| Where it lives | Lease Footnote — See LEVERAGE.md → Section "Where it lives" → Item 2b (ROU Lease Liability and Operating Lease Expense) — identical location (typically Note 5–8); extract total annual operating lease expense from "Lease Cost" table, same figure used in Leverage Formula 2 |
| Available in | 10-K and 10-Q (post-ASC 842) |
| Exact location within footnote | The "Lease Cost" table in the Lease Footnote, which breaks down total lease cost into: operating lease cost, finance lease interest cost, and finance lease amortization. For operating leases, the interest component is not separately stated — Moody's estimates it as 1/3 of total annual operating lease expense. |
| What LLM should extract | Total annual operating lease expense (same figure used in Leverage Formula 2). The system then applies the 1/3 rule to derive the interest component for the denominator adjustment. |

---

**Formula 3 — S&P-Style Adjustments**

**Item 3a — Current Year Operating Lease Payments (for Fixed Charges denominator)**

| Field | Detail |
|---|---|
| Where it lives | Lease Footnote — maturity schedule table |
| Available in | 10-K and 10-Q |
| Exact location within footnote | The operating lease maturity table shows future minimum lease payments by year. The first row — "Less than 1 year" or "2025" (the next fiscal year) — is the current year payment used in S&P's fixed charges denominator. This is the full lease payment, not just the interest component, which is what distinguishes S&P from Moody's on this item. |
| What LLM should extract | Single number: operating lease payments due within the next 12 months from the maturity schedule. |

**Item 3b — Preferred Dividends (for Fixed Charges denominator)**

| Field | Detail |
|---|---|
| Where it lives | Equity section of the Balance Sheet AND Dividends footnote or Equity footnote (typically Note 10–15, titled "Stockholders' Equity" or "Capital Stock") |
| Available in | 10-K and 10-Q |
| Exact location | Income statement may show "Preferred stock dividends" as a deduction from net income attributable to common shareholders. Alternatively, the equity footnote discloses dividend rate and shares outstanding, from which the annual preferred dividend can be computed. |
| What LLM should extract | Total preferred dividends paid or declared during the period. For most corporate bond issuers this will be zero — flag if non-zero as it meaningfully reduces S&P fixed charge coverage. |
| XBRL tag if available | `us-gaap:PreferredStockDividendsAndOtherAdjustments` — semi-structured; verify against footnote |

**Item 3c — Gross vs Net Interest Expense Confirmation**

| Field | Detail |
|---|---|
| Where it lives | Interest Expense footnote or Note 1 (Summary of Significant Accounting Policies) |
| Available in | 10-K and 10-Q |
| Exact location | Note 1 or a standalone interest footnote will describe the company's policy on presenting interest income and expense — whether gross or net. S&P uses gross interest expense. If the company reports only net interest, LLM must extract gross interest expense from the footnote breakdown. |
| What LLM should extract | Confirmation of gross vs net presentation. If net: extract (1) gross interest expense and (2) interest income separately so the system can use gross interest in the denominator. |

---


## Structured or Unstructured — Interest Coverage Metric (All Three Formulas)

> Appendix D

| Input / Component | Formula | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|---|
| **Operating Income (EBIT)** | F1, F2 | Primary: `us-gaap:OperatingIncomeLoss` Fallback 1: `us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes` Fallback 2: Derived from `us-gaap:GrossProfit` − `us-gaap:SellingGeneralAndAdministrativeExpense` − `us-gaap:ResearchAndDevelopmentExpense` | Structured — with financing contamination risk on fallback | Fallback 1 includes interest income and expense below the operating line — flags as "EBIT includes non-operating items; coverage ratio may be understated." Fallback 2 derivation may miss other operating expense lines — flag as "derived, verify completeness." |
| **Interest Expense (gross)** | F1, F2, F3 | Primary: `us-gaap:InterestExpense` Fallback 1: `us-gaap:InterestAndDebtExpense` Fallback 2: `us-gaap:InterestIncomeExpenseNet` (net figure — flag) | Structured — with netting risk | Critical: some companies tag only net interest. If `us-gaap:InterestExpense` is absent but `us-gaap:InterestIncomeExpenseNet` is present, flag: "gross interest expense not separately tagged — coverage ratio may be overstated; gross figure requires LLM extraction from interest footnote." Never use net interest as a silent substitute for gross. |
| **Interest Income** | F1 supplementary | `us-gaap:InterestIncomeOperating` or `us-gaap:InvestmentIncomeInterest` | Structured — supplementary only | Used only to detect netting. If Interest Expense tag is missing and net interest tag is present, subtract interest income from net to reconstruct gross. Flag in audit log. |
| **EBITDA** (supplementary coverage) | F1 supplementary | No standard tag — derived: `us-gaap:OperatingIncomeLoss` + `us-gaap:DepreciationDepletionAndAmortization` | Structured inputs, derived result | Computed as supplementary figure alongside EBIT-based coverage. Labeled "EBITDA Coverage" in output — not the primary ratio. Same derivation as Leverage Formula 1. |
| **Revenue** | F3 | `us-gaap:Revenues` or `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | Structured | Used as S&P starting point for Adjusted EBITDA numerator. Reliable and consistently tagged. |
| **Operating Expenses** | F3 | `us-gaap:OperatingExpenses` or derived: `us-gaap:CostOfRevenue` + `us-gaap:SellingGeneralAndAdministrativeExpense` + `us-gaap:ResearchAndDevelopmentExpense` | Structured — may require summing | S&P computes Adjusted EBITDA top-down as Revenue − Operating Expenses + D&A. Some companies tag `OperatingExpenses` as a single line; others require summing components. |
| **D&A** | F3 | Primary: `us-gaap:DepreciationDepletionAndAmortization` Fallback: `us-gaap:DepreciationAndAmortization` | Structured | Same extraction as Leverage Formula 1. Cash flow statement operating section is the most reliable source. |
| **Capitalized Interest** | F2 | No standard tag | **Unstructured — LLM required** | Lives in PP&E Footnote (typically Note 4–7). LLM should read the interest reconciliation paragraph: "gross interest incurred minus capitalized interest equals interest expense charged to income." Extract single number: total interest capitalized during the period. Moody's subtracts this from reported interest expense. Available in 10-K; occasionally in 10-Q for capital-intensive companies. |
| **Pension Interest Cost** | F2 | No standard tag at required granularity | **Unstructured — LLM required** | Lives in Pension Footnote (typically Note 8–12). LLM should read the "Net Periodic Benefit Cost" table and extract the "Interest cost" line specifically. Distinguished from "Service cost" — both must be extracted. Moody's adds the interest cost component to the interest expense denominator. 10-K only. |
| **Operating Lease Interest Component** | F2 | No standard tag for interest component alone | **Semi-structured — partial tag, rule applied** | Post-ASC 842: total operating lease cost is tagged as `us-gaap:OperatingLeaseCost`. Moody's estimates interest component as 1/3 of total annual operating lease expense — this 1/3 split is a Moody's rule, not a disclosed figure. System applies the rule to the tagged or LLM-extracted lease cost figure. Flag: "lease interest component estimated at 1/3 of annual lease expense per Moody's methodology." |
| **Current Year Operating Lease Payments** | F3 | No standard tag for Year 1 of maturity schedule | **Unstructured — LLM required** | Lives in Lease Footnote maturity schedule table. LLM should read the first row of the operating lease maturity table — labeled "Less than 1 year," "Within 1 year," or the next fiscal year (e.g., "2026"). This is the full lease payment used in S&P's fixed charges denominator — not just the interest component. Available in both 10-K and 10-Q. |
| **Preferred Dividends** | F3 | `us-gaap:PreferredStockDividendsAndOtherAdjustments` (if tagged) | Semi-structured — sometimes tagged, sometimes footnote only | Appears as a deduction below net income on the income statement. If not tagged, LLM should read the Equity Footnote (typically Note 10–15) to extract dividend rate and compute total. For most investment-grade corporate bond issuers this will be zero — flag if non-zero as it materially reduces fixed charge coverage. |
| **Gross vs Net Interest Confirmation** | F3 | No tag — policy disclosure | **Unstructured — LLM required** | LLM should read Note 1 (Summary of Significant Accounting Policies) or a standalone interest footnote to confirm whether the company presents interest gross or net. If net presentation confirmed: LLM must also extract gross interest expense and interest income separately so the system can use gross in the denominator. Flag: "interest presented net — gross figure reconstructed from footnote." |
| **Restructuring Charges** | F3 | `us-gaap:RestructuringCharges` (sometimes tagged) | Semi-structured — tagged on income statement, detail in footnote | See LEVERAGE.md → Section "Structured or Unstructured" → Restructuring Charges row — apply identical treatment; S&P does not add back restructuring — it remains as an operating cost reducing Adjusted EBITDA. |
| **Stock-Based Compensation** | F3 | `us-gaap:ShareBasedCompensation` | Structured — reliably tagged in cash flow statement | See LEVERAGE.md → Section "Structured or Unstructured" → Stock-Based Compensation row — apply identical treatment; S&P does not add back SBC to EBITDA. Tag used only to identify and confirm the amount is not added back. Flag in audit log. |


## Phase 2 Handling for Semi-Structured Items

For Phase 2 (no LLM):
- Items marked "semi-structured" that require a rule (e.g., lease interest component = 1/3 of lease cost) **are computed** using the XBRL tag + the rule, without LLM
- Items marked "semi-structured" that require footnote verification (e.g., preferred dividends, restructuring) are **marked as null** with a log message: "requires LLM for Phase 3"

For Phase 3:
- All semi-structured items are recomputed with LLM confirmation


## Extraction Fallback Logic — Interest Coverage Metric

---

### Design Principles

Same three rules as Leverage apply here, plus one additional rule specific to Interest Coverage:

**Rule 1 — Never substitute zero for a missing input.** A missing Interest Expense tag does not mean the company has no interest expense. A company carrying visible debt that reports zero interest expense has an extraction failure, not a genuinely zero cost. Mark null and log.

**Rule 2 — Try every fallback before giving up.** Exhaust all tag options before escalating to LLM or declaring failure.

**Rule 3 — Log what you used.** Every computed ratio records which tag path was used for each input.

**Rule 4 — Never divide by zero or a negative interest expense.** If Interest Expense resolves to zero or negative after all fallbacks, do not compute coverage. Flag as "interest expense zero or negative — ratio not meaningful; verify company carries no debt." A negative interest expense figure almost always indicates a tagging error or that the company has netted interest income exceeding interest expense — both require investigation.

---

### Input 1 — Operating Income (EBIT)

**What we are trying to capture:** Earnings from core operations before interest and tax — the numerator of the coverage ratio.

**The messiness:** Same challenges as Leverage Formula 1. The primary tag is reliable for most companies, but fallbacks introduce non-operating items that distort the ratio.

```
Step 1 — Try: us-gaap:OperatingIncomeLoss
           (primary — use whenever available)

Step 2 — Try: us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes
           WARNING: includes interest income and interest expense below
           the operating line. Using this as EBIT means the numerator
           already reflects interest costs, making coverage circular.
           Flag: "EBIT proxied by pretax income — coverage ratio
           includes financing items in numerator; ratio may be
           understated or distorted."

Step 3 — Derive from components:
           us-gaap:GrossProfit
           − us-gaap:SellingGeneralAndAdministrativeExpense
           − us-gaap:ResearchAndDevelopmentExpense
           − us-gaap:OtherOperatingIncomeExpenseNet
           Flag: "EBIT derived from components — verify no operating
           expense lines omitted."

Step 4 — If all steps return null → log "EBIT: no tag found"
           Set EBIT = null → Coverage = null
```

**Additional check:** If the extracted EBIT is negative, do not mark the ratio null — a negative EBIT is meaningful and should produce a negative or undefined coverage ratio. Flag as "EBIT negative — company not covering interest from operations; acute stress signal." Do not suppress this result.

---

### Input 2 — Interest Expense (Gross)

**What we are trying to capture:** The total interest cost the company incurs on its debt obligations during the period, before netting against any interest income.

**The netting problem — the most important extraction challenge for this metric:**

Some companies — particularly those with large cash balances or financial subsidiaries — report only net interest on the face of the income statement. Using net interest as the denominator overstates coverage because it reduces the denominator by interest income. Your system must detect this pattern and handle it explicitly.

```
Step 1 — Try: us-gaap:InterestExpense
           This should be gross interest expense.
           Sanity check: compare to total debt × average interest rate.
           If InterestExpense appears implausibly low relative to
           total debt, flag for review even if tag is present.

Step 2 — Try: us-gaap:InterestAndDebtExpense
           Broader tag that includes debt issuance cost amortization
           and other debt-related charges alongside interest.
           Flag: "Interest expense includes debt issuance cost
           amortization — denominator may be slightly overstated."

Step 3 — Netting detection:
           If Steps 1 and 2 both return null, check for:
           us-gaap:InterestIncomeExpenseNet
           If this tag is present and negative → net interest expense
           exists but is presented as a net figure.
           Attempt reconstruction:
               Gross Interest Expense =
               abs(InterestIncomeExpenseNet)
               + us-gaap:InterestIncomeOperating
               + us-gaap:InvestmentIncomeInterest
           Flag: "gross interest expense not separately tagged —
           reconstructed from net interest plus interest income tags;
           verify against interest footnote."

Step 4 — If netting reconstruction fails (interest income tags also
           absent):
           Set Interest Expense = null
           Escalate to LLM: read interest expense footnote or Note 1
           (accounting policies) to extract gross interest expense
           and interest income separately.
           Flag: "interest expense extracted via LLM from footnote —
           unstructured source; verify manually."

Step 5 — If all steps including LLM return null → log "interest
           expense: no tag found and LLM extraction failed"
           Set Interest Expense = null → Coverage = null
```

**Capitalized interest adjustment (Formula 2 only):**

```
After gross interest expense is established via Steps 1–4:

Step 2a — Check for capitalized interest:
           Try: us-gaap:InterestCostsCapitalized
           If found: Adjusted Interest Expense =
           Gross Interest Expense − Capitalized Interest
           Flag: "capitalized interest subtracted per Moody's
           methodology — adjusted interest expense used."

Step 2b — If us-gaap:InterestCostsCapitalized not tagged:
           Escalate to LLM: read PP&E footnote for sentence
           disclosing "interest capitalized during the period."
           If LLM finds it: apply same adjustment as Step 2a.
           If LLM does not find it: assume zero capitalized interest;
           flag: "capitalized interest not found — Moody's adjustment
           not applied; interest expense may be slightly overstated
           as denominator."
```

---

### Input 3 — Coverage Ratio (Derived)

**This input is not directly tagged — it is computed from Inputs 1 and 2.**

```
Interest Coverage = EBIT / Interest Expense

Null propagation rules:
  — If EBIT is null → Coverage = null
  — If Interest Expense is null → Coverage = null
  — If Interest Expense = 0 → Coverage = undefined
    Flag: "interest expense zero — ratio undefined; verify company
    carries no interest-bearing debt before accepting"
  — If Interest Expense < 0 → Coverage = undefined
    Flag: "negative interest expense — likely tagging error or
    interest income exceeds interest expense; investigate"
  — If EBIT < 0 and Interest Expense > 0 → Coverage = negative
    Flag: "negative coverage — EBIT insufficient to cover any
    interest; acute stress signal — do not suppress"
  — If EBIT > 0 and Interest Expense > 0 → compute normally

Supplementary EBITDA coverage:
  EBITDA Coverage = (EBIT + D&A) / Interest Expense
  Compute alongside primary ratio using D&A from cash flow statement.
  Tag as "supplementary — EBITDA-based" in output.
  Subject to same null propagation rules.
  If D&A is null: compute EBIT coverage only; flag EBITDA
  coverage as null separately — do not suppress EBIT coverage.
```

---

### Cross-Level Validation Rules

Before finalising any Interest Coverage figure, apply these sanity checks:

**Check 1 — Implied interest rate sanity check**
Compute: Implied Rate = Interest Expense / Total Debt (from Leverage extraction). If implied rate is below 1% or above 20% for a non-distressed issuer, flag: "implied interest rate of X% appears anomalous — verify interest expense extraction is gross and covers all debt obligations." This catches silent netting errors and missing debt components simultaneously.

**Check 2 — Coverage vs leverage consistency**
A company with very high leverage (>6x) and very high coverage (>8x) simultaneously is unusual — it implies very low interest rates on a large debt load. Flag for review: "high leverage combined with high coverage — verify interest expense captures all debt tranches including floating rate instruments."

**Check 3 — Period alignment**
Interest Expense is a duration item (covers the full reporting period). EBIT is also a duration item. Both must cover the same period. For 10-Q filings, verify both tags reference the same period context (e.g. both are year-to-date or both are quarter-only). Mixing a year-to-date EBIT with a quarter-only interest expense produces a ratio that is approximately 3x overstated for Q3 filings.

**Check 4 — Negative EBIT handling**
Do not mark negative coverage as an error. A coverage ratio of −0.5x is a valid and important data point. It means the company is losing money from operations before interest — a severe stress signal. Store it, flag it, and trigger an alert per the threshold rules.

---

### Audit Log Output Format (per company, per period)

```
{
  "ticker": "RAD",
  "period": "2023-03-04",
  "filing": "10-K",

  "inputs": {
    "ebit": {
      "value": -306.4,
      "tag_used": "us-gaap:OperatingIncomeLoss",
      "path": "primary",
      "unit": "millions USD"
    },
    "interest_expense": {
      "value": 441.2,
      "tag_used": "us-gaap:InterestAndDebtExpense",
      "path": "fallback_1",
      "unit": "millions USD",
      "flag": "InterestExpense tag absent — InterestAndDebtExpense
               used; may include debt issuance cost amortization"
    },
    "da": {
      "value": 289.1,
      "tag_used": "us-gaap:DepreciationDepletionAndAmortization",
      "path": "primary",
      "unit": "millions USD"
    }
  },

  "derived": {
    "ebit_coverage": -0.69,
    "ebitda_coverage": -0.04,
    "implied_interest_rate": "9.8%"
  },

  "flags": [
    "EBIT negative — company not covering interest from operations",
    "EBITDA coverage also negative — D&A insufficient to bridge gap",
    "InterestAndDebtExpense used as fallback — verify gross interest"
  ],

  "alerts": [
    "STRESS — coverage below 1.0x",
    "CRITICAL — EBIT negative; coverage ratio negative"
  ],

  "warnings": [],
  "nulls": []
}
```

This example uses Rite Aid fiscal 2023 figures, consistent with the empirical validation in the Leverage section, and confirms that the coverage ratio was signalling acute stress in the same filing period where leverage was also deteriorating.

## Phase 2 vs Phase 3 — LLM Boundary Rules for Interest Coverage

The fallback logic above references LLM escalation in several places. The following rules clarify what Phase 2 does versus Phase 3.

### Rule 1 — LLM escalation in Phase 2

In Phase 2, LLM is not available. When extraction reaches a step that would require LLM:

- Set the output value to `null`
- Log: "requires LLM extraction — not available in Phase 2; manual review required"
- Do **not** substitute a fallback value (e.g., do not use net interest as a proxy for gross interest)

### Rule 2 — Capitalized interest adjustment in Phase 2

- If `us-gaap:InterestCostsCapitalized` exists → use it, compute the adjustment
- If the tag does **not** exist → skip the adjustment, log "capitalized interest not tagged — Moody's adjustment not applied in Phase 2"

### Summary

| Step | Phase 2 | Phase 3 |
|------|---------|---------|
| Interest Expense — LLM escalation | Set null, log | LLM extract from footnote |
| Capitalized interest — tag missing | Skip adjustment, log | LLM extract from PP&E footnote |
| F3 items (lease payments, preferred dividends) | Not computed | LLM extract |


## Stress Threshold — Interest Coverage

---

### Step 1 — Assign Volatility Category Per Issuer

Same volatility category assignment as Leverage. Decided once at issuer onboarding and applied consistently across all ratio thresholds. Refer to the Leverage metric Step 1 table for the full industry-to-volatility mapping.

The volatility category affects coverage thresholds in the same direction as leverage — low volatility industries (utilities) tolerate lower coverage because their cash flows are more predictable and contractually protected. Standard volatility industries (technology, healthcare) require higher coverage to achieve the same financial risk profile rating.

---

### Step 2 — Apply the Correct Threshold Table

Source: S&P Global Corporate Methodology (2013), Tables 4.7, 4.8, 4.9 — Cash Flow/Leverage Analysis Ratios. S&P publishes EBITDA interest coverage thresholds alongside Debt/EBITDA thresholds within the same financial risk profile framework. Both metrics must be evaluated together — a company can be in the "Significant" band on leverage but "Intermediate" on coverage, or vice versa. The more conservative classification governs the overall financial risk profile assignment.

---

**Standard Volatility — Table 4.7**
*Apply to: Technology, healthcare, pharmaceuticals, business services, consumer staples*

| Financial Risk Profile | EBITDA Interest Coverage | Formula 1 Adjusted Threshold* |
|---|---|---|
| Minimal | > 13.0x | > 12.5x |
| Modest | 9.0x – 13.0x | 8.5x – 12.5x |
| Intermediate | 6.0x – 9.0x | 5.5x – 8.5x |
| Significant | 4.0x – 6.0x | 3.5x – 5.5x |
| Aggressive | 2.5x – 4.0x | 2.0x – 3.5x |
| Highly Leveraged | < 2.5x | < 2.0x |

---

**Medial Volatility — Table 4.8**
*Apply to: Retail, food & beverage, media, telecom, packaging*

| Financial Risk Profile | EBITDA Interest Coverage | Formula 1 Adjusted Threshold* |
|---|---|---|
| Minimal | > 10.0x | > 9.5x |
| Modest | 7.0x – 10.0x | 6.5x – 9.5x |
| Intermediate | 4.5x – 7.0x | 4.0x – 6.5x |
| Significant | 3.0x – 4.5x | 2.5x – 4.0x |
| Aggressive | 1.75x – 3.0x | 1.25x – 2.5x |
| Highly Leveraged | < 1.75x | < 1.25x |

---

**Low Volatility — Table 4.9**
*Apply to: Utilities, regulated infrastructure, government-related entities*

| Financial Risk Profile | EBITDA Interest Coverage | Formula 1 Adjusted Threshold* |
|---|---|---|
| Minimal | > 5.0x | > 4.5x |
| Modest | 4.0x – 5.0x | 3.5x – 4.5x |
| Intermediate | 3.0x – 4.0x | 2.5x – 3.5x |
| Significant | 2.0x – 3.0x | 1.5x – 2.5x |
| Aggressive | 1.5x – 2.0x | 1.0x – 1.5x |
| Highly Leveraged | < 1.5x | < 1.0x |

---

> \* **Formula 1 Adjusted Threshold explanation:** S&P thresholds are calibrated to EBITDA interest coverage using S&P-adjusted EBITDA and gross interest expense. Formula 1 uses unadjusted EBITDA (Operating Income + D&A) and reported gross interest expense — which typically produces a lower EBITDA figure than S&P-adjusted, meaning Formula 1 coverage will appear slightly lower than S&P-adjusted coverage for the same company. The −0.5x adjustment applied to all thresholds corrects for this systematic bias in Phase 2. Recalibrate against Formula 3 output once Phase 3 is implemented.

**Important note on EBIT vs EBITDA thresholds:** The S&P tables above use EBITDA interest coverage. Formula 1 computes both EBIT coverage and EBITDA coverage as described in the formula section. Apply the S&P thresholds to the EBITDA coverage figure. Use the EBIT coverage figure as a supplementary signal — if EBIT coverage falls below 1.0x it is an automatic stress escalation regardless of which financial risk profile band the EBITDA coverage sits in.

---

### Step 3 — Alert Trigger Rules

| Alert Level | Trigger Condition | Action |
|---|---|---|
| **Watch** | EBITDA coverage enters "Significant" band for this issuer's volatility category | Log; include in weekly analyst review |
| **Flag** | EBITDA coverage enters "Aggressive" band | Generate alert; move to daily monitoring |
| **Stress** | EBITDA coverage enters "Highly Leveraged" band | Immediate alert; escalate to analyst same day |
| **Trend Flag** | EBITDA coverage declines by ≥ 1.0x in a single quarter regardless of absolute level | Alert regardless of band — deterioration signal |
| **Critical — EBIT below 1.0x** | EBIT coverage falls below 1.0x | Immediate escalation regardless of EBITDA coverage band — company cannot cover interest from operating earnings alone |
| **Critical — Negative coverage** | EBIT coverage is negative (EBIT < 0) | Automatic Stress alert; flag as critical; company losing money from operations before interest |
| **Critical — Undefined coverage** | Interest Expense = 0 or null after all fallbacks | Do not compute ratio; escalate to manual review; flag as extraction failure or verify company carries no debt |
| **Extraction Failure** | Either EBIT or Interest Expense = null after all fallbacks | Do not compute ratio; log failure; add to manual review queue |

**On the 1.0x floor:** The 1.0x EBIT coverage threshold is independent of volatility category and independent of which S&P band the company sits in. It is an absolute floor. Below 1.0x EBIT coverage, the company cannot service interest from operating earnings — it must draw on cash, sell assets, or borrow to pay interest. This condition, sustained across two or more consecutive quarters, is one of the strongest precursors to a credit event in the empirical literature.

**On combined leverage and coverage alerts:** When both leverage and coverage trigger alerts simultaneously — leverage in the "Aggressive" band and coverage in the "Aggressive" band in the same quarter — escalate the combined signal to the next alert level. Two metrics confirming stress simultaneously is more significant than either alone. Flag as "dual metric stress — leverage and coverage both flagging."

**EBIT vs EBITDA coverage in Phase 2:**
> After **Critical — EBIT below 1.0x**
- Primary ratio for threshold tables: EBITDA coverage (matches S&P methodology)
- EBIT coverage is computed and stored, but not compared to the tables
- The only rule applied to EBIT coverage is the 1.0x floor: if EBIT coverage < 1.0x → Critical alert (regardless of EBITDA coverage band)

**Dual metric stress trigger:**
> between **Trend Flag** and **Critical — EBIT below 1.0x**
Trigger when both metrics are in the **"Aggressive" band or worse** for the issuer's volatility category.
Example (standard volatility):
- Leverage > 4.0x (Aggressive or Highly Leveraged)
- AND EBITDA coverage < 4.0x (Aggressive or Highly Leveraged)
→ Escalate one level
---

### Step 4 — Sector Exceptions

See LEVERAGE.md → Section "Stress Threshold" → Step 4 (Sector Exceptions) — apply identical sector exception list; financial institutions, insurance, REITs, project finance all excluded. Financial institutions, insurance companies, REITs, and project finance entities are outside the scope of Tables 4.7–4.9 for coverage as well as leverage.

Two additional sector-specific notes for coverage:

**Capital-intensive industries (oil & gas, mining, utilities under construction):** These sectors frequently capitalise significant interest during asset construction phases. Capitalised interest reduces reported interest expense on the income statement, making coverage appear higher than economic reality during construction periods. When capitalised interest is material (>10% of gross interest incurred), flag: "coverage may be overstated due to significant interest capitalisation — Moody's adjusted figure recommended."

**Financial holding companies with treasury operations:** Companies like JPMorgan that earn substantial interest income may report net interest rather than gross interest expense. As documented in the extraction fallback logic, using net interest overstates coverage. For financial holding companies, coverage ratio is not a meaningful metric at all — flag for manual review and do not apply these thresholds.

---

### Step 5 — Empirical Context and Backtest Anchor

**Historical reference — Rite Aid:**
As validated in the Leverage section, Rite Aid's EBITDA fell from $505.9M in fiscal 2022 to $429.2M in fiscal 2023 while interest expense remained approximately $441M. This produces an EBITDA coverage ratio of approximately 0.97x in fiscal 2023 — below 1.0x and below the "Highly Leveraged" threshold for any volatility category. Under the Standard Volatility table, Rite Aid would have been flagged as "Highly Leveraged" on coverage at least one fiscal year before its October 2023 bankruptcy. The EBIT coverage was negative in the same period, triggering the Critical alert rule independently of the band classification.

**Historical reference — general empirical evidence:**
Academic research consistently identifies interest coverage below 1.5x as a strong predictor of financial distress. Altman's Z-score model (1968) embeds an earnings-to-assets ratio that captures the same dynamic. More recent empirical work on leveraged loan defaults confirms that issuers with EBITDA/Interest coverage below 2.0x at the time of origination default at materially higher rates than those above 3.0x, holding leverage constant.

**Phase 3 backtest validation targets:**

| Metric | Target |
|---|---|
| Catch rate | ≥ 80% of known distressed cases flagged at "Aggressive" or above at least two quarters before credit event |
| Lead time | Median lead time of ≥ 2 quarters between first coverage flag and credit event |
| False positive rate | ≤ 20% of healthy issuers flagged at "Aggressive" or above in any given quarter |
| EBIT < 1.0x precision | ≥ 90% of issuers triggering the EBIT floor rule should show a credit event within 4 quarters — if not, the rule is generating false positives and the threshold should be reviewed |

---

## Signal Timing — Interest Coverage

---

### Classification

**Early to coincident — faster moving than leverage, with one critical lead advantage.**

Interest coverage is a flow measure, not a stock measure. This is the fundamental difference from leverage. Leverage reflects accumulated debt — it changes slowly because debt levels change slowly. Coverage reflects the current period's earnings relative to the current period's interest bill — it can deteriorate sharply in a single quarter if EBITDA falls or interest costs rise, even if the debt stock has not changed at all.

This makes coverage a faster signal than leverage in most stress scenarios, and in some scenarios — particularly earnings shocks — it provides earlier warning than leverage does.

---

### The Three Deterioration Paths and Their Timing

Coverage can deteriorate through three distinct paths, each with a different signal speed:

**Path 1 — Earnings collapse (fastest, 1–2 quarters)**

A sudden revenue shock, margin compression, or large one-time charge collapses EBITDA in a single quarter. Interest expense does not change because the debt stock has not changed. Coverage falls immediately and sharply. The signal appears in the first 10-Q after the event — typically within 40 days of quarter-end for a large accelerated filer. If the earnings press release (8-K Item 2.02) is filed 14–25 days before the 10-Q, your system gets a directional signal approximately 15–25 days earlier than the structured XBRL data.

This is the fastest-moving credit stress scenario your system will encounter. A company with 5.0x coverage in Q1 can be at 2.5x coverage by Q2 if EBITDA is cut in half. Leverage would barely move in the same period because total debt has not changed.

**Path 2 — Interest cost increase (medium, 2–4 quarters)**

Maturing fixed-rate debt is refinanced at higher rates, or floating-rate debt reprices upward as market rates rise. Interest expense increases gradually across multiple quarters as tranches mature and are refinanced. EBITDA may be stable. Coverage drifts downward over 2–4 quarters. This path is slower than Path 1 but more predictable — the maturity schedule (Debt Maturity Wall metric) gives advance warning of when refinancing will occur, allowing your system to project coverage deterioration before it appears in reported figures.

**Path 3 — Simultaneous compression (most dangerous, confirms distress)**

Both EBITDA falls and interest costs rise at the same time. This is the classic leveraged credit stress scenario — a deteriorating business environment reduces earnings while rising credit spreads increase refinancing costs. Coverage deteriorates faster than either path alone. When your system detects simultaneous movement in both the numerator and denominator, escalate immediately regardless of the absolute level.

---

### Three-Tier Timing Structure

Identical framework to Leverage, with one important difference: the Item 2.02 lead advantage is more valuable for coverage than for leverage because earnings are the primary driver of coverage deterioration, and earnings are what the press release discloses first.

| Tier | Source | Data Quality | Lag After Quarter-End | Lead Before 10-Q | Use in System |
|---|---|---|---|---|---|
| **Tier 1 — Full recompute** | 10-Q / 10-K | Reviewed (10-Q) or audited (10-K); structured XBRL; Formula 1 computable | **+40 days** (large accelerated filer) | n/a | Primary coverage ratio; triggers all alerts |
| **Tier 2 — Early directional signal** | 8-K Item 2.02 earnings press release | Preliminary; unaudited; company-defined EBITDA; unstructured text | **+14 to +25 days** (empirically: JPM Q1 2026 = +14 days) | **−15 to −25 days before 10-Q** | Directional signal only; does not replace Tier 1; Phase 3 only |
| **Tier 3 — Real-time event trigger** | 8-K Item 2.03 / 2.04 | Event disclosure only; no income statement data | **Within 4 business days of event** | Can occur any time intra-quarter | 2.04: automatic Stress alert; 2.03: debt increase noted but coverage cannot be updated without new EBITDA |

**Critical asymmetry vs Leverage:** For leverage, an intra-quarter 8-K Item 2.03 (new debt) allows a partial ratio update because debt changed but EBITDA did not. For coverage, an intra-quarter debt event changes interest expense — but the new interest expense will only be fully reflected in the next quarterly filing. A company that draws $500M on its revolver in month 2 of the quarter will show higher interest expense in the next 10-Q, but the current quarter's interest expense figure is already partially committed. Your system should note the debt event and flag that forward coverage will likely be lower, but cannot recompute the ratio intra-quarter with precision.

---

### Staleness Analysis

See LEVERAGE.md → Section "Signal Timing" → Staleness Analysis table — apply identical staleness profile; no modification required, depending on where in the quarterly cycle the filing arrives. The full staleness table from the Leverage Signal Timing section applies here without modification.

One coverage-specific addition: interest expense is a duration item that accrues daily. A company that issues $1B of new 8% bonds on the first day of Q3 will show the full quarter's interest on those bonds in the Q3 10-Q. A company that issues the same bonds on the last day of Q3 will show almost no interest in Q3 — it appears fully only in Q4. This means the timing of debt issuance within a quarter affects how quickly the interest expense impact shows up in reported figures, creating up to one full quarter of additional lag between a debt event and its full coverage impact appearing in filed financials.

---

### Comparison: Coverage vs Leverage Signal Speed

| Scenario | Coverage Signal Speed | Leverage Signal Speed | Which Leads |
|---|---|---|---|
| EBITDA falls sharply (revenue shock) | **Fast — 1 quarter** | Slow — leverage barely moves | **Coverage leads** |
| New debt issued | Slow — interest expense rises gradually as debt is drawn and accrues | **Fast — debt increases immediately** | **Leverage leads** |
| Interest rates rise on refinancing | Medium — 2–4 quarters as tranches mature | Slow — principal unchanged | **Coverage leads** |
| Both EBITDA falls and debt rises | **Fastest — same quarter** | Fast — same quarter | Simultaneous — dual alert |
| Gradual margin erosion over years | Medium — visible after 3–4 quarters of trend | Medium — similar speed | Neither leads clearly |

**System implication:** Coverage and leverage are complementary, not redundant. Coverage leads in earnings-driven stress. Leverage leads in debt-accumulation stress. Running both simultaneously and flagging when either or both deteriorate gives the system broader detection capability than either metric alone.


> **Phase 2 note:** In Phase 2, Tier 2 and Tier 3 are not yet implemented. Only Tier 1 (10-Q/10-K) is used.

### Updated Signal Timing Summary

> **Signal Timing — Early to coincident, faster than leverage for earnings-driven stress.**
>
> Interest coverage is a flow measure that responds within a single quarter to earnings shocks — the fastest of the primary credit metrics. Tier 1 structured data arrives 40 days after quarter-end. Tier 2 directional signal (Item 2.02 press release) arrives 14–25 days after quarter-end — approximately 15–25 days before the 10-Q — and is particularly valuable for coverage because earnings are what the press release discloses first.
>
> A falling coverage trend across 2–3 consecutive quarters is a strong early warning signal even if the absolute level has not crossed a stress threshold. A single-quarter drop of ≥ 1.0x should trigger an immediate trend flag regardless of absolute level. A coverage ratio below 1.0x on an EBIT basis is an automatic critical escalation regardless of band classification.
>
> Coverage leads leverage in earnings-driven stress scenarios. Leverage leads coverage in debt-accumulation scenarios. The two metrics should always be evaluated together — simultaneous deterioration in both is the strongest quantitative stress signal the system can produce from structured data alone.

## Frequency — Interest Coverage
---

### Overview

Interest coverage shares the same six-channel update structure as leverage. The update schedule, filing deadlines, and EDGAR availability rules are identical — See LEVERAGE.md → Section "Frequency" → full section — apply identical six-channel update structure, 8-K filtering rules, and Phase 2 vs Phase 3 priority framework, 8-K filtering rules, and expected filing volumes by issuer type.

This section documents only the differences and coverage-specific considerations that do not appear in the Leverage Frequency section.

---


### Shared Structure with LEVERAGE.md

Interest coverage shares the same six-channel update structure, filing deadlines, and Phase 2/Phase 3 priorities as leverage. Refer to the **Leverage Frequency** section for:

- The full six-channel table (10-Q, 10-K, Item 2.02, Item 2.03, Item 2.04, 424B)
- Filing deadlines (40 days / 60 days / 4 business days)
- Phase 2: monitor 10-Q/10-K + Item 2.04 automatic escalation
- Phase 3: add Item 2.02, Item 2.03, 424B
- 8-K filtering rules and expected filing volumes

The following subsections document only the **coverage-specific differences** that do not appear in the Leverage section.

All six channels apply without modification:

| Channel | Filing Type | Phase 2 | Phase 3 |
|---|---|---|---|
| Quarterly financials | 10-Q | ✅ Primary source | ✅ Primary source |
| Annual financials | 10-K | ✅ Primary source | ✅ Primary source |
| Earnings press release | 8-K Item 2.02 | ❌ Ignore | ✅ Add |
| Material debt creation | 8-K Item 2.03 | ❌ Ignore | ✅ Add (with caveat — see below) |
| Debt acceleration / default | 8-K Item 2.04 | ✅ Monitor (alert only) | ✅ Monitor |
| New bond issuance | 424B prospectus | ❌ Ignore | ✅ Add (with caveat — see below) |

Filing deadlines are identical: 40 calendar days after quarter-end for large accelerated filers (10-Q), 60 days after fiscal year-end (10-K), 4 business days after triggering event (8-K Items 2.03 and 2.04). EDGAR availability within minutes of acceptance. All sourced and validated in the Leverage Frequency section, detailedly see this path: 
 > See LEVERAGE.md → Section "Frequency" → full section — all filing deadlines, EDGAR availability rules, and channel definitions identical; this section documents coverage-specific differences only

---

### Coverage-Specific Differences

**Difference 1 — Item 2.03 and 424B update logic is asymmetric for coverage**

For leverage, an intra-quarter debt event (Item 2.03 or 424B) allows a partial ratio update: new debt increases the numerator of Net Debt immediately, and the system can recompute a partial leverage estimate using the prior period's EBITDA.

For coverage, the same event changes future interest expense — but the current quarter's interest expense accrual is already partially committed and cannot be precisely recomputed from the 8-K disclosure alone. The system cannot produce a meaningful partial coverage estimate from a debt event filing.

**Correct system behavior when Item 2.03 or 424B is detected:**

```
Do NOT attempt to recompute coverage ratio intra-quarter.

Instead:
Step 1 — Log the debt event: issuer, date, amount, coupon rate
         (coupon extracted from 8-K Item 2.03 text or 424B
         pricing table via LLM)
Step 2 — Compute forward interest expense impact:
         Estimated additional annual interest =
         New Debt Amount × Coupon Rate
         Estimated additional quarterly interest =
         Annual interest / 4
Step 3 — Compute projected coverage:
         Projected Coverage =
         Prior EBITDA / (Prior Interest Expense
         + Estimated additional quarterly interest)
Step 4 — Flag prominently:
         "Projected coverage estimate — based on new debt event
         filed [date]; actual interest expense impact will appear
         in [next quarter] 10-Q; treat as directional signal only"
Step 5 — Store projected figure separately from Tier 1 ratio.
         Do not overwrite prior Tier 1 coverage figure.
```

This projected coverage estimate is more useful for coverage than the partial leverage update is for leverage, because interest expense is contractually fixed at the coupon rate — the estimate is mechanical, not speculative. Flag it as a projection but treat it as a reasonably reliable directional signal for Phase 3.

**Difference 2 — Item 2.02 is more valuable for coverage than for leverage**

As noted in Signal Timing, earnings are the primary driver of coverage deterioration in the most common stress scenarios. The earnings press release (Item 2.02) discloses revenue, EBITDA, and sometimes net income 14–25 days before the 10-Q. For coverage, this means the most important input — EBITDA — becomes visible earlier than it does for leverage (where the debt stock, which changes slowly, is the more important input).

In Phase 3, when Item 2.02 monitoring is active, treat the coverage directional signal from the press release as higher priority than the leverage directional signal from the same filing. If the press release implies EBITDA has fallen sharply, the coverage alert is more likely to be confirmed by the subsequent 10-Q than the leverage alert.

**Difference 3 — The Q4 dark window affects coverage and leverage differently**

For leverage, the Q4 dark window (Q3 10-Q filed ~November 9, 10-K filed ~March 31, gap of ~142 days) primarily matters if the company takes on significant new debt in Q4. This is visible via 8-K Item 2.03 or 424B filings, partially mitigating the dark window for leverage.

For coverage, the Q4 dark window matters if Q4 EBITDA deteriorates — and Q4 EBITDA is not disclosed anywhere until the earnings press release (Item 2.02, typically filed in late January or early February for calendar-year companies) or the 10-K itself. There is no intra-quarter EBITDA signal equivalent to the debt event filings that partially illuminate the leverage dark window.

**This means the Q4 dark window is structurally worse for coverage than for leverage.** A company whose EBITDA collapses in Q4 will not trigger a coverage alert until the Item 2.02 press release approximately 45–50 days after December 31, or the 10-K approximately 60 days after December 31. Your system should treat Q4 as a monitoring gap for coverage and flag any issuer already in the "Significant" or "Aggressive" band at Q3 as requiring heightened attention during the November–February window.

---

### Full Update Schedule — Calendar Year Large Accelerated Filer

| Month | Event | Channel | Coverage Update Type |
|---|---|---|---|
| ~Jan 30 – Feb 15 | Q4 / full year earnings press release | 8-K Item 2.02 | Preliminary EBITDA estimate — directional signal; Phase 3 only |
| ~Mar 31 | 10-K filed | 10-K | Full structured recompute (Formula 1); full LLM extraction possible (Formula 2/3) |
| ~Apr 14–25 | Q1 earnings press release | 8-K Item 2.02 | Preliminary EBITDA estimate — directional signal; Phase 3 only |
| ~May 10 | Q1 10-Q filed | 10-Q | Full structured recompute |
| ~Jul 15–25 | Q2 earnings press release | 8-K Item 2.02 | Preliminary EBITDA estimate — directional signal; Phase 3 only |
| ~Aug 9 | Q2 10-Q filed | 10-Q | Full structured recompute |
| ~Oct 14–25 | Q3 earnings press release | 8-K Item 2.02 | Preliminary EBITDA estimate — directional signal; Phase 3 only |
| ~Nov 9 | Q3 10-Q filed | 10-Q | Full structured recompute |
| Nov 9 – Mar 31 | **Q4 dark window** | None for EBITDA | **No coverage update possible — heightened monitoring period for issuers already flagged** |
| Any business day | New bond / loan issuance | 8-K Item 2.03 or 424B | Projected forward coverage estimate — Phase 3 only; see Difference 1 above |
| Any business day | Debt acceleration / default | 8-K Item 2.04 | Automatic Stress alert — no ratio recompute |

---

### Phase Summary

**Phase 2:** Monitor 10-Q and 10-K only. Full structured recompute 4× per year (3 × 10-Q + 1 × 10-K). Monitor 8-K Item 2.04 as automatic escalation trigger (type-level filter, no text processing). Flag Q4 dark window for issuers already in Significant or Aggressive band at Q3.

**Phase 3:** Add 8-K Item 2.02 for early EBITDA directional signal (14–25 days before 10-Q). Add 8-K Item 2.03 and 424B for projected forward coverage estimate using coupon rate and new debt amount. Maintain Item 2.04 automatic escalation. Apply keyword filter to 8-K Items 1.01, 8.01, and 7.01 for debt-related disclosures that may affect interest expense.




## Appendix A
### Academic and institutional validation

- Moody's explicitly states that interest coverage — measured as EBIT/Interest Expense — is one of its primary financial metrics across virtually all non-financial corporate rating methodologies, alongside leverage.
- S&P's Corporate Methodology treats fixed charge coverage as a direct input into the financial risk profile assessment, alongside Debt/EBITDA, and assigns lower financial risk profile scores as coverage declines toward and below 2.0x.
- Altman's original Z-score model (1968) included EBIT/Total Assets as one of its five discriminating variables, capturing the same earnings-relative-to-obligations logic that coverage embeds.

### The Rite Aid confirmation

- As validated in the Leverage section, Rite Aid's EBITDA fell from $505.9M in fiscal 2022 to $429.2M in fiscal 2023 — a $76.7M decline.
- Over the same period, its interest expense remained elevated because its debt load had not meaningfully decreased.
- The result was a coverage ratio compressing toward and eventually below 1.0x in the quarters leading up to its October 2023 bankruptcy.
- The coverage signal was visible in the same quarterly filings that showed leverage deteriorating — confirming that the two metrics move together in distress but that coverage often deteriorates faster because interest expense is sticky while EBITDA can fall quickly.



## Appendix B


```
Supplementary: EBITDA Coverage = (Operating Income + D&A) / Interest Expense
```

---

**Comparison Table**

| | Formula 1 — Baseline | Formula 2 — Moody's | Formula 3 — S&P |
|---|---|---|---|
| **Numerator** | EBIT (Operating Income) | Adjusted EBIT | Adjusted EBITDA |
| **Denominator** | Interest Expense | Adjusted Interest Expense | Fixed Charges (interest + lease payments + preferred dividends) |
| **D&A in numerator** | ❌ No | ❌ No | ✅ Yes (EBITDA base) |
| **Lease payments in denominator** | ❌ No | Partial (1/3 of rent as interest) | ✅ Full lease payment |
| **Restructuring addback** | n/a | ❌ No | ❌ No |
| **Capitalized interest excluded** | ❌ Not adjusted | ✅ Subtracted from interest | ✅ Included as fixed charge |
| **Requires LLM** | ❌ No | ✅ Yes | ✅ Yes |
| **Relative coverage level** | Mid | Higher than F1 for most companies | Lower than F2 |
| **Implementation phase** | Phase 2 | Phase 3 | Phase 3 |

---


## Appendix C

**Summary Table — Where Each Item Lives**

| Item | Formula | Statement / Document | Section | 10-K Only or Both |
|---|---|---|---|---|
| Operating Income (EBIT) | F1 | Income Statement | Operating section | Both |
| Interest Expense | F1 | Income Statement | Non-operating / Other expense section | Both |
| Capitalized interest | F2 | PP&E Footnote | Capitalized interest disclosure | 10-K only (usually) |
| Pension interest cost | F2 | Pension Footnote | Net Periodic Benefit Cost table | 10-K only |
| Operating lease interest component | F2 | Lease Footnote | Lease Cost table | Both |
| Current year lease payments | F3 | Lease Footnote | Maturity schedule — Year 1 row | Both |
| Preferred dividends | F3 | Income Statement + Equity Footnote | Below net income / Equity note | Both |
| Gross interest confirmation | F3 | Note 1 or Interest Footnote | Accounting policies or interest breakdown | Both |


## Appendix D

---

**Quick Reference — Structured vs Unstructured by Formula**

| | F1 — Baseline | F2 — Moody's | F3 — S&P |
|---|---|---|---|
| **Fully structured (XBRL)** | Operating Income, Interest Expense | Inherits F1 + Operating Lease Cost (partial) | Revenue, OpEx, D&A, SBC |
| **Semi-structured (tag exists but needs verification)** | Interest netting detection | Lease interest component (tag + rule) | Preferred dividends, restructuring |
| **Fully unstructured (LLM required)** | None | Capitalized interest, Pension interest cost | Gross interest confirmation, Current year lease payments |
| **LLM needed?** | ❌ No | ✅ Yes | ✅ Yes |
| **Phase** | Phase 2 | Phase 3 | Phase 3 |

---

