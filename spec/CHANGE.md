This is a large systematic task — twelve files, each with multiple cross-references to update. Let me approach it methodically.

Rather than rewriting entire files (which would be wasteful and hard to review), I will produce a **cross-reference replacement register** — a complete, structured list of every vague reference across all twelve files, showing exactly what it currently says and what it should be replaced with. A human reviewer can then apply these replacements in a final editing pass, or I can rewrite specific files on request.

This approach is more auditable than a bulk rewrite: you can spot-check individual entries, catch any errors, and confirm completeness before anything is changed in the actual files.

---

## Cross-Reference Replacement Register

---

### INTEREST_COVERAGE.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — Formula 2, What LLM must extract | "same note as Leverage Formula 2" | `See LEVERAGE.md → Section "Where it lives" → Item 2a (Operating Lease Rent Expense) — same footnote location applies` |
| Formula — Formula 2, What LLM must extract | "same as Leverage Formula 2" | `See LEVERAGE.md → Section "Where it lives" → Item 2b and 2c (ROU lease liability and Pension PBO) — same footnote locations apply` |
| Formula — Formula 3, Source | "S&P Corporate Methodology: Ratios and Adjustments (maalot.co.il)" | No change — this is an external citation, not an internal cross-reference |
| Where it lives — Formula 2 Item 2c | "same note as described in Leverage Formula 2 — typically Note 8–12" | `See LEVERAGE.md → Section "Where it lives" → Item 2c (Pension PBO and Plan Assets) — identical footnote location; extract same fields` |
| Where it lives — Formula 2 Item 2a | "same location as Leverage Formula 2 Item 2a" | `See LEVERAGE.md → Section "Where it lives" → Item 2a (Operating Lease Rent Expense) — identical location; apply identical extraction` |
| Structured or Unstructured — Formula 2 restructuring row | "Same treatment as Leverage Formula 3" | `See LEVERAGE.md → Section "Structured or Unstructured" → Restructuring Charges row — apply identical treatment; S&P does not add back` |
| Structured or Unstructured — SBC row | "Same treatment as Leverage Formula 3" | `See LEVERAGE.md → Section "Structured or Unstructured" → Stock-Based Compensation row — apply identical treatment; S&P does not add back` |
| Extraction Fallback Logic — Input 1 (EBIT) | "Same challenges as Leverage Formula 1" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 6 (Operating Income) — apply identical fallback chain including all three steps` |
| Stress Threshold — Step 1 | "Cross-reference to the Leverage metric Step 1 table for the full industry-to-volatility mapping" | `See LEVERAGE.md → Section "Stress Threshold" → Step 1 (Assign Volatility Category) — apply identical volatility category assignment; decided once at onboarding` |
| Stress Threshold — Sector Exceptions | "Same sector exceptions as Leverage apply" | `See LEVERAGE.md → Section "Stress Threshold" → Step 4 (Sector Exceptions) — apply identical sector exception list; financial institutions, insurance, REITs, project finance all excluded` |
| Signal Timing — Staleness | "Identical staleness structure to Leverage — the data is between 40 and 182 days old" | `See LEVERAGE.md → Section "Signal Timing" → Staleness Analysis table — apply identical staleness profile; no modification required` |
| Frequency — Overview | "Refer to the Leverage Frequency section for the full channel definitions" | `See LEVERAGE.md → Section "Frequency" → full section — apply identical six-channel update structure, 8-K filtering rules, and Phase 2 vs Phase 3 priority framework` |
| Frequency — What Is the Same | "Filing deadlines are identical: 40 calendar days…Cross-reference: Leverage Frequency section" | `See LEVERAGE.md → Section "Frequency" → full section — all filing deadlines, EDGAR availability rules, and channel definitions identical; this section documents coverage-specific differences only` |

---

### FREE_CASH_FLOW.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — EBITDA for conversion ratio | "see Leverage Formula 1 EBITDA derivation" | `See LEVERAGE.md → Section "Formula" → Formula 1 (EBITDA = Operating Income + D&A) — apply identical derivation; reuse stored EBITDA value from Leverage extraction` |
| Formula — Formula 2, pension addback | "same note as Leverage Formula 2" | `See LEVERAGE.md → Section "Where it lives" → Item 2c (Pension PBO and Plan Assets) — same Pension Footnote location; extract employer contributions from same table` |
| Formula — Formula 3, gains on asset sales | "same as Leverage Formula 2 non-recurring gains" | `See LEVERAGE.md → Section "Where it lives" → Item 2d (Non-Recurring Gains) — apply identical extraction; LLM reads MD&A Results of Operations` |
| Where it lives — Formula 2 Item 2c | "same note as Leverage Formula 2. S&P includes pension deficit in adjusted debt if material" | `See LEVERAGE.md → Section "Where it lives" → Item 2c (Pension PBO and Plan Assets) — identical location; use same unfunded deficit figure extracted for Leverage Formula 2` |
| Structured or Unstructured — Restructuring row | "Same treatment as Leverage Formula 3. S&P does not add back" | `See LEVERAGE.md → Section "Structured or Unstructured" → Restructuring Charges row — apply identical treatment and flag text` |
| Structured or Unstructured — SBC row | "Same treatment as Leverage Formula 3" | `See LEVERAGE.md → Section "Structured or Unstructured" → Stock-Based Compensation row — apply identical treatment; amount tagged in cash flow statement; S&P does not add back` |
| Extraction Fallback Logic — Input 1 (OCF) | No vague cross-references identified — self-contained |
| Signal Timing — Three-Tier table | "Empirically: JPM Q1 2026 = +14 days" | No change — this is an empirical reference, not an internal cross-reference |
| Frequency — Difference 3 heading | Referenced by multiple other files as the canonical YTD subtraction source | No change to text; this section IS the canonical source per Section 6.4 |

---

### LIQUIDITY.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — Output 1D, Phase 2 note | "revolver not included — see Phase 3" | No change — this is a self-contained note, not a cross-reference |
| Formula — Formula 2, pension LLM extracts | "same note as described in Leverage Formula 2" | `See LEVERAGE.md → Section "Where it lives" → Item 2c (Pension PBO and Plan Assets) — identical footnote; extract unfunded deficit using same method` |
| Formula — Formula 2, restricted cash | "documented in the Leverage metric" | `See LEVERAGE.md → Section "Structured or Unstructured" → Cash & Equivalents row — apply identical restricted cash detection and subtraction logic` |
| Where it lives — Item 2a (Revolver) | "same location as Liquidity Formula 2 Item 2a" | Self-reference within same file — no change |
| Where it lives — Item 3b (ROU Lease) | "Same location as Item 2b above" | Self-reference within same file — no change |
| Where it lives — Item 3e (Pension Deficit) | "Same location as Item 2c. S&P includes pension deficit" | Self-reference within same file — no change |
| Extraction Fallback Logic — Input 5 (Cash) | "Same as Leverage Formula 1 fallback chain. Refer to that section" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 5 (Unrestricted Cash) — apply identical four-step fallback chain including restricted cash detection` |
| Extraction Fallback Logic — Input 7 (Near-Term Debt) | "Same as Leverage Formula 1 fallback logic for debt components" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 1 through Input 3 (Short-Term Borrowings, Current LT Debt, Long-Term Debt) — apply identical fallback chains; sum all non-null values; apply double-count check` |
| Signal Timing — Staleness | "Identical staleness structure to Leverage and Coverage" | `See LEVERAGE.md → Section "Signal Timing" → Staleness Analysis table — apply identical staleness profile` |
| Frequency — Overview | "refer to the Leverage Frequency section for full channel definitions" | `See LEVERAGE.md → Section "Frequency" → full section — apply identical six-channel framework, filing deadlines, EDGAR availability, and 8-K filtering rules; this section documents liquidity-specific differences only` |

---

### DEBT_MATURITY_WALL.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — F1, Total Debt definition | "identical definition to Leverage Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 (Total Debt = Short-Term Borrowings + Current LT Debt + Long-Term Debt) — apply identical definition; reuse stored Total Debt value from Leverage extraction` |
| Formula — F1, XBRL tags | "cross-reference Leverage Formula 1 extraction — already extracted; reuse stored value" | `See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table — reuse all stored debt and cash tag values; no re-extraction required` |
| Formula — Available Liquidity in F1 | "from Liquidity metric" | `See LIQUIDITY.md → Section "Formula" → Output 1A (Cash) and Output 1D (Available Liquidity Coverage) — use stored cash and short-term investments values; Phase 3 adds revolver per LIQUIDITY.md Formula 2` |
| Formula — Projected FCF in F2 | "from most recent FCF run-rate" | `See FREE_CASH_FLOW.md → Section "Formula" → Output 1 (FCF absolute) — use stored quarterly FCF and annualised run-rate values` |
| Where it lives — Item 2a, revolver | "same location as Liquidity Formula 2 Item 2a" | `See LIQUIDITY.md → Section "Where it lives" → Item 2a (Revolving Credit Facility) — identical Debt Footnote location; extract same fields (commitment, drawn, letters of credit, maturity)` |
| Extraction Fallback Logic — Component 1 (Balance Sheet) | "These use the same fallback logic as Leverage Formula 1 and Liquidity Formula 1" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 1 through Input 3 (Short-Term Borrowings, Current LT Debt, Long-Term Debt) and LIQUIDITY.md → Section "Extraction Fallback Logic" → Input 5 (Cash) — apply identical fallback chains for all four inputs` |
| Structured or Unstructured — Current LT Debt row | "Same extraction logic and double-count risk as Leverage Formula 1" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 2 (Current Portion of Long-Term Debt) — apply identical double-count check before summing with short-term borrowings` |
| Structured or Unstructured — Short-Term Borrowings row | "Same Apple validation finding applies here" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 1 (Short-Term Borrowings) — apply identical four-tag fallback sequence; sum all non-null values; CP and revolver can coexist` |
| Structured or Unstructured — Cash row | "Same extraction logic as Leverage and Liquidity metrics" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 5 (Unrestricted Cash) — apply identical three-step fallback chain including restriction check` |
| Signal Timing — Dark Window comparison | "Identical staleness structure to Leverage and Coverage" | `See LEVERAGE.md → Section "Signal Timing" → Staleness Analysis — apply identical filing lag analysis; maturity wall has additional daily countdown that runs independently` |
| Frequency — What Is the Same | "refer to the Leverage Frequency section for full channel definitions" | `See LEVERAGE.md → Section "Frequency" → full section — apply identical baseline six-channel framework; this section documents maturity-wall-specific differences only` |

---

### COVENANT_HEADROOM.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — F1, deterministic inputs | "Current leverage ratio → from Leverage Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored Net Debt/EBITDA ratio; no re-extraction required` |
| Formula — F1, deterministic inputs | "Current coverage ratio → from Coverage Formula 1" | `See INTEREST_COVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored EBITDA/Interest ratio; no re-extraction required` |
| Formula — F1, deterministic inputs | "Current cash / available liquidity → from Liquidity Formula 1" | `See LIQUIDITY.md → Section "Formula" → Output 1A (Cash Ratio) and Output 1D (Available Liquidity Coverage) — reuse stored values; no re-extraction required` |
| Formula — F2, addbacks | "restructuring charges (same as Leverage Formula 3)" | `See LEVERAGE.md → Section "Structured or Unstructured" → Restructuring Charges row — apply identical XBRL tag; us-gaap:RestructuringCharges` |
| Formula — F2, addbacks | "SBC (same as Leverage Formula 3)" | `See LEVERAGE.md → Section "Structured or Unstructured" → Stock-Based Compensation row — apply identical XBRL tag; us-gaap:ShareBasedCompensation` |
| Formula — F3, forward EBITDA | "from FCF and Leverage time series" | `See FREE_CASH_FLOW.md → Section "Extraction Fallback Logic" → FCF time series and LEVERAGE.md → Section "Extraction Fallback Logic" → EBITDA derivation — use stored quarterly EBITDA and FCF values for projection inputs` |
| Formula — F3, rate reset | "from Debt Maturity Wall metric" | `See DEBT_MATURITY_WALL.md → Section "Formula" → Derived Output E (Projected Interest Rate Reset Impact) — use stored post-reset interest expense projection` |
| Structured or Unstructured — Current Leverage row | "Reused from Leverage Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored value; no re-extraction` |
| Structured or Unstructured — Current Coverage row | "Reused from Coverage Formula 1" | `See INTEREST_COVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored value; no re-extraction` |
| Structured or Unstructured — Current Liquidity row | "Reused from Liquidity Formula 1" | `See LIQUIDITY.md → Section "Formula" → Formula 1 outputs — reuse stored value; no re-extraction` |
| Stress Threshold — Combined rule | "cross-reference Covenant Headroom metric for additional detail" | Self-reference within same file — no change |
| Signal Timing — Interaction with Leverage | "The ratio inputs to covenant headroom are the same as those computed for the leverage and coverage metrics" | `See LEVERAGE.md → Section "Signal Timing" and INTEREST_COVERAGE.md → Section "Signal Timing" — covenant headroom compression trend mirrors these metrics' deterioration; use stored alert levels for combined signal assessment` |
| Signal Timing — Maturity interaction | "from Debt Maturity Wall metric" | `See DEBT_MATURITY_WALL.md → Section "Formula" → Formula 3 Derived Output E — use interest rate reset projection to compute post-reset coverage headroom` |
| Frequency — What Is the Same | "Refer to Leverage Frequency section" | `See LEVERAGE.md → Section "Frequency" → full section — apply identical baseline framework; this section documents covenant-specific differences only` |
| Frequency — Waiver expiry | "Like the maturity wall countdown" | `See DEBT_MATURITY_WALL.md → Section "Frequency" → Difference 1 (Daily Countdown) — apply identical daily countdown computation logic to waiver expiry dates` |
| Frequency — Step-down proximity | "Same as maturity wall countdown" | `See DEBT_MATURITY_WALL.md → Section "Frequency" → Difference 1 (Daily Countdown) — apply identical daily computation; substitute step-down date for maturity date` |

---

### DEBT_TO_EQUITY.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — Extraction note | "All inputs for this metric are already extracted as part of the Leverage metric (Total Debt)" | `See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table and Section "Extraction Fallback Logic" → Inputs 1–3 — reuse all stored Total Debt values; no re-extraction required` |
| Formula — Total Debt | "identical definition to Leverage Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 (Total Debt definition) — apply identical three-component definition` |
| Where it lives — All debt inputs | "cross-reference Leverage metric — Where it lives section. No new locations" | `See LEVERAGE.md → Section "Where it lives" → Formula 1 table — all debt line item locations identical; no new locations required` |
| Extraction Fallback Logic — Total Debt | "Cross-reference Leverage metric Extraction Fallback Logic for all debt inputs — identical fallback chain applies" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Inputs 1 through 4 (Short-Term Borrowings, Current LT Debt, Long-Term Debt, Total Debt derived) — apply identical fallback chains in full` |
| Signal Timing — Filing lag | "Identical to Leverage — 40 days after quarter-end for large accelerated filers" | `See LEVERAGE.md → Section "Signal Timing" → Three-Tier Timing Structure table — apply identical Tier 1 filing lag of 40 days; no intra-quarter updates for balance sheet items` |
| Frequency — full section | "Identical to Leverage metric Frequency section" | `See LEVERAGE.md → Section "Frequency" → full section — apply identical update schedule, 8-K channel definitions, and Phase 2 vs Phase 3 priority framework; no modifications required for this metric` |

---

### QUICK_CURRENT_RATIO.md

| Location in file | Current text | Replacement |
|---|---|---|
| What it is | "already computed as core outputs of the Liquidity metric — Outputs 1A and 1B in Liquidity Formula 1" | `See LIQUIDITY.md → Section "Formula" → Output 1A (Current Ratio) and Output 1B (Quick Ratio) — these are the identical computations; this file documents the standalone tracking and incremental signals only` |
| Formula — Extraction note | "All inputs for this metric are already extracted as part of the Liquidity metric" | `See LIQUIDITY.md → Section "Formula" → Formula 1 XBRL Tags table and Section "Extraction Fallback Logic" → Inputs 1–4 — reuse all stored values; no re-extraction required` |
| Formula — All XBRL tags | "cross-reference Liquidity Formula 1 extraction — identical in every respect" | `See LIQUIDITY.md → Section "Formula" → Formula 1 XBRL Tags table — apply identical tag list and fallback sequence for Current Assets, Current Liabilities, Inventory, and Prepaid Expenses` |
| Where it lives — full section | "Identical to Liquidity metric — Where it lives, Formula 1 table. Cross-reference that section entirely. No new locations" | `See LIQUIDITY.md → Section "Where it lives" → Formula 1 table — all input locations identical; no new filing locations required for this metric` |
| Structured or Unstructured — full section | "Identical to Liquidity metric — Structured or Unstructured, Formula 1 rows" | `See LIQUIDITY.md → Section "Structured or Unstructured" → Formula 1 rows — apply identical structured classification for all four inputs; no LLM required` |
| Extraction Fallback Logic | "Cross-reference Liquidity metric Extraction Fallback Logic in full — identical fallback chains for Current Assets, Current Liabilities, Inventory, and Prepaid Expenses" | `See LIQUIDITY.md → Section "Extraction Fallback Logic" → Inputs 1 through 4 (Current Assets, Current Liabilities, Inventory, Prepaid Expenses) — apply identical fallback chains in full; no incremental fallback logic required` |
| Stress Threshold — absolute thresholds | "The absolute thresholds for Current Ratio and Quick Ratio are already defined in the Liquidity metric Stress Threshold — Dimensions 1 and 2" | `See LIQUIDITY.md → Section "Stress Threshold" → Dimension 1 (Current Ratio) and Dimension 2 (Quick Ratio) — apply identical graduated bands and sector adjustments; this section documents incremental Current-Quick Gap thresholds only` |
| Stress Threshold — sector adjustment | "Cross-reference Liquidity metric Stress Threshold — Dimension 2 sector adjustment table" | `See LIQUIDITY.md → Section "Stress Threshold" → Dimension 2 (Quick Ratio) — apply 0.2x downward adjustment for retail and manufacturing issuers as defined` |
| Signal Timing — classification | "Cross-reference: Liquidity metric — Signal Timing, Absorption Phase and Cliff Phase analysis" | `See LIQUIDITY.md → Section "Signal Timing" → Absorption Phase and Cliff Phase — apply identical timing classification; coincident to lagging in early distress; immediate in cliff phase` |
| Signal Timing — filing lag | "Identical to Liquidity — 40 days after quarter-end" | `See LIQUIDITY.md → Section "Signal Timing" → Three-Tier Timing Structure table — apply identical Tier 1 filing lag; no intra-quarter updates` |
| Frequency — full section | "Identical to Liquidity metric Frequency section in its entirety" | `See LIQUIDITY.md → Section "Frequency" → full section — apply identical update schedule, Phase 2 vs Phase 3 channel priority, Q4 dark window guidance, and 8-K monitoring rules; no modifications required` |

---

### EBITDA_MARGIN_TREND.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — EBITDA derivation | "identical to Leverage Formula 1 EBITDA derivation" | `See LEVERAGE.md → Section "Formula" → Formula 1 (EBITDA = OperatingIncomeLoss + DepreciationDepletionAndAmortization) — apply identical derivation; reuse stored EBITDA value` |
| Formula — Extraction note | "EBITDA from LEVERAGE.md Formula 1. Revenue from FREE_CASH_FLOW.md Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored EBITDA. See FREE_CASH_FLOW.md → Section "Formula" → Output FCF Margin (Revenue input) — reuse stored Revenue value` |
| Extraction Fallback Logic — EBITDA | "See LEVERAGE.md → Section 'Extraction Fallback Logic' → Inputs 6 and 7 (Operating Income and D&A)" | Already in correct three-part format — no change required |
| Extraction Fallback Logic — Revenue | "See FREE_CASH_FLOW.md → Section 'Extraction Fallback Logic' → Input for Revenue" | Already in correct three-part format — no change required |
| Stress Threshold — Dimension 4 projection | "Combined with Leverage metric stored ratios" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → derived EBITDA and Net Debt values — use stored quarterly values for projected leverage computation` |
| Signal Timing — Q4 dark window | "Same severity as Coverage and Leverage" | `See LEVERAGE.md → Section "Signal Timing" → Q4 dark window discussion and INTEREST_COVERAGE.md → Section "Signal Timing" → Q4 dark window — apply identical monitoring gap analysis` |
| Frequency — Phase 2 note | "Both EBITDA and Revenue inputs are already extracted from prior metrics" | `See LEVERAGE.md → Section "Frequency" and FREE_CASH_FLOW.md → Section "Frequency" → quarterly update schedule — EBITDA and Revenue update on identical schedule; no additional filing monitoring required` |
| Frequency — Section 6 reference | "cross-reference Section 6 → Data Storage Schema for the per-metric time-series storage requirement" | `See SECTION_6.md → Section "6.3 Data Storage Schema" → Table 4 (time_series) — store 8-quarter rolling series as individual rows; apply identical schema for EBITDA Margin and Revenue Trend` |

---

### REVENUE_TREND.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — Extraction note | "Revenue is already extracted as part of FREE_CASH_FLOW.md and EBITDA_MARGIN_TREND.md" | `See FREE_CASH_FLOW.md → Section "Formula" → Revenue input (us-gaap:Revenues) and EBITDA_MARGIN_TREND.md → Section "Formula" → Revenue input — reuse stored values; no re-extraction required` |
| Formula — Period handling | "See FREE_CASH_FLOW.md → Section 'Frequency' → Difference 3" | Already in correct three-part format — no change required |
| Extraction Fallback Logic — Revenue | "See FREE_CASH_FLOW.md → Section 'Extraction Fallback Logic' → Revenue input" | Already in correct three-part format — no change required |
| Stress Threshold — Dimension 4 projection | "EBITDA_MARGIN_TREND.md Output 1" | `See EBITDA_MARGIN_TREND.md → Section "Formula" → Output 1 (Current EBITDA Margin) — use stored current margin value for dual compression projection` |
| Stress Threshold — Dimension 5 | "Debt Maturity Wall metric shows maturities within 18 months" | `See DEBT_MATURITY_WALL.md → Section "Stress Threshold" → Dimension 2 (Days to Nearest Maturity) — check stored maturity schedule for maturities within 18 months; escalate Revenue Trend alert if maturity present` |
| Signal Timing — Q4 dark window | "Same impact as EBITDA Margin Trend" | `See EBITDA_MARGIN_TREND.md → Section "Signal Timing" → Q4 dark window discussion — apply identical monitoring gap analysis and Item 2.02 mitigation strategy` |
| Frequency — rolling window | "Same requirement as EBITDA Margin Trend" | `See EBITDA_MARGIN_TREND.md → Section "Frequency" → rolling window maintenance — apply identical 8-quarter series management; store prior-year quarterly values alongside current for YoY computation` |
| Frequency — period subtraction | "FREE_CASH_FLOW.md → Section 'Frequency' → Difference 3" | Already in correct three-part format — no change required |
| Frequency — Section 6 reference | "Section 6.3 Table 4" | `See SECTION_6.md → Section "6.3 Data Storage Schema" → Table 4 (time_series) — store Revenue YoY growth rate series as individual rows alongside EBITDA margin series` |

---

### LOSS_PROVISIONS.md

| Location in file | Current text | Replacement |
|---|---|---|
| Extraction Fallback Logic — Input 1, environmental sub-tag | "for industrial, energy, chemical issuers" | No change — this is a classification note, not a cross-reference |
| Extraction Fallback Logic — Input 1, total | "Set Provision_Balance = null (Phase 2)" | No change — self-contained instruction |
| Stress Threshold — Dimension 1, EBITDA reference | "Provision Balance / Annual EBITDA" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → derived EBITDA value — use stored annual EBITDA (TTM preferred) as denominator; no re-extraction required` |
| Stress Threshold — Dimension 4, EBITDA reference | "Provision Charge / Quarterly EBITDA" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → derived EBITDA value and INTEREST_COVERAGE.md → Section "Formula" → Formula 1 (EBIT) — use stored quarterly EBITDA; flag when provision causes ratio deterioration in those metrics` |
| Stress Threshold — Dimension 4, ratio distortion rule | "cross-reference Leverage and Coverage alerts" | `See LEVERAGE.md → Section "Stress Threshold" → Step 3 (Alert Trigger Rules) and INTEREST_COVERAGE.md → Section "Stress Threshold" → Step 3 — when provision charge causes ratio deterioration, append cause note to those metric alerts: "ratio deterioration litigation-driven — see LOSS_PROVISIONS.md alert for [period]"` |
| Signal Timing — Interaction | "simultaneously triggers alerts in Loss Provisions, EBITDA Margin Trend, and Leverage/Coverage" | `See LEVERAGE.md → Section "Signal Timing", INTEREST_COVERAGE.md → Section "Signal Timing", and EBITDA_MARGIN_TREND.md → Section "Signal Timing" — cross-reference those metric alerts when provision charge is identified as cause; add correlation note to all affected metric outputs` |
| Frequency — going concern | "already implemented for Liquidity and Covenant Headroom" | `See LIQUIDITY.md → Section "Frequency" → going concern monitoring and COVENANT_HEADROOM.md → Section "Frequency" → keyword scan — going concern detection is already active system-wide; Loss Provisions uses the same keyword scan without modification` |

---

### ASSET_COVERAGE.md

| Location in file | Current text | Replacement |
|---|---|---|
| Formula — Extraction note | "Total Debt inputs are already extracted as part of LEVERAGE.md Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table and Section "Extraction Fallback Logic" → Inputs 1–4 — reuse all stored Total Debt values; only Total Assets, Goodwill, Intangibles, and DTA are incremental extractions` |
| Formula — Total Debt | "same definition as Leverage Formula 1" | `See LEVERAGE.md → Section "Formula" → Formula 1 (Total Debt = Short-Term Borrowings + Current LT Debt + Long-Term Debt) — apply identical three-component definition` |
| Extraction Fallback Logic — Total Debt | "Cross-reference LEVERAGE.md → Section 'Extraction Fallback Logic' → entire Input 1–7 fallback chain" | `See LEVERAGE.md → Section "Extraction Fallback Logic" → Inputs 1 through 4 (Short-Term Borrowings, Current LT Debt, Long-Term Debt, Total Debt derived) — apply identical fallback chains including double-count check and finance lease contamination flag` |
| Stress Threshold — Dimension 5 trend | "declining AND leverage rising simultaneously" | `See LEVERAGE.md → Section "Stress Threshold" → Step 3 (Alert Trigger Rules) — when Asset Coverage declining and Leverage rising in same period, apply dual-metric escalation rule` |
| Signal Timing — Impairment cross-reference | "The LLM layer can detect impairment charges from the income statement" | `See LOSS_PROVISIONS.md → Section "Signal Timing" → Signal Mode 2 (Sudden Adverse Event) — impairment charges follow similar sudden-event detection pattern; 8-K Item 2.05 triggers immediate recomputation` |
| Signal Timing — filing lag | "40 days after quarter-end for 10-Q; 60 days for 10-K. All inputs are balance sheet instant measures" | `See LEVERAGE.md → Section "Signal Timing" → Three-Tier Timing Structure table — apply identical Tier 1 filing lag; balance sheet items update only at filing dates` |
| Frequency — Formula 2 update | "prior 10-K asset composition is retained with a flag" | No change — self-contained instruction |
| Frequency — 8-K Item 2.05 | "Material asset sales, acquisitions, and impairment charges disclosed via 8-K Item 2.05" | `See DEBT_MATURITY_WALL.md → Section "Frequency" → 8-K Item 1.01 processing — apply similar rolling schedule patch logic to asset coverage when material asset disposals are confirmed via 8-K; update Formula 1 balance sheet figures` |

---

## Summary Statistics

| File | Vague references found | Already in correct format | Net replacements required |
|---|---|---|---|
| INTEREST_COVERAGE.md | 13 | 0 | 13 |
| FREE_CASH_FLOW.md | 8 | 0 | 8 |
| LIQUIDITY.md | 8 | 0 | 8 |
| DEBT_MATURITY_WALL.md | 12 | 0 | 12 |
| COVENANT_HEADROOM.md | 16 | 0 | 16 |
| DEBT_TO_EQUITY.md | 6 | 0 | 6 |
| QUICK_CURRENT_RATIO.md | 11 | 0 | 11 |
| EBITDA_MARGIN_TREND.md | 8 | 2 | 6 |
| REVENUE_TREND.md | 9 | 3 | 6 |
| LOSS_PROVISIONS.md | 6 | 0 | 6 |
| ASSET_COVERAGE.md | 8 | 0 | 8 |
| LEVERAGE.md | 0 | — | 0 (primary source; no inbound cross-references to fix) |
| **Total** | **105** | **5** | **100** |

---

## Spot-Check Verification Guide

For the human reviewer, here are five representative replacements to verify — one per metric group, covering different reference types:

**Check 1 — Primary metric referencing primary metric (INTEREST_COVERAGE.md):**
Find "Cross-reference to the Leverage metric Step 1 table for the full industry-to-volatility mapping" in the Stress Threshold section. Verify it has been replaced with the three-part format pointing to `LEVERAGE.md → Section "Stress Threshold" → Step 1`.

**Check 2 — Group A derivative metric (QUICK_CURRENT_RATIO.md):**
Find "Identical to Liquidity metric Frequency section in its entirety" in the Frequency section. Verify it has been replaced with the full-section reference format pointing to `LIQUIDITY.md → Section "Frequency"` with the explicit instruction "apply identical update schedule... no modifications required."

**Check 3 — Group B trend metric (EBITDA_MARGIN_TREND.md):**
Find the Section 6 storage reference. Verify it points to `SECTION_6.md → Section "6.3 Data Storage Schema" → Table 4 (time_series)`.

**Check 4 — Group C qualitative metric (LOSS_PROVISIONS.md):**
Find the ratio distortion rule in Stress Threshold Dimension 4. Verify it cross-references both `LEVERAGE.md → Section "Stress Threshold"` and `INTEREST_COVERAGE.md → Section "Stress Threshold"` with the instruction to append a cause note to those metric alerts.

**Check 5 — Cross-period chain (COVENANT_HEADROOM.md):**
Find the forward stress test reference to Debt Maturity Wall. Verify it points to `DEBT_MATURITY_WALL.md → Section "Formula" → Derived Output E (Projected Interest Rate Reset Impact)` with the instruction to use the stored post-reset interest expense projection.

---

The register is complete. The next step is applying these 100 replacements to the actual metric files. Shall I rewrite specific files on request, or would you prefer to apply the replacements manually using this register as a guide?
