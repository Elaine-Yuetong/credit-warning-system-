# Debt-to-Equity Ratio

---

### What it is

The Debt-to-Equity ratio measures how much of a company's financing comes from debt versus equity. It answers: *"for every dollar of equity shareholders have invested, how many dollars has the company borrowed?"* A company with $800M of total debt and $400M of shareholders' equity has a D/E ratio of 2.0x — it has borrowed twice as much as its equity base.

Where leverage (Net Debt / EBITDA) measures debt relative to earnings capacity, D/E measures debt relative to the book value of ownership. It is a balance sheet solvency measure rather than an earnings-based serviceability measure. The two metrics are complementary — a company can have moderate leverage but high D/E if its equity base has been eroded by accumulated losses, or high leverage but low D/E if it has a large equity cushion from retained earnings.

---

### Why it signals stress

D/E signals stress through two mechanisms distinct from the leverage metric.

**Equity erosion signal:** When a company generates persistent net losses, retained earnings decline and the equity base shrinks — increasing D/E even if the debt level is unchanged. A rising D/E driven by equity erosion rather than new debt issuance is a structural deterioration signal that leverage alone may not capture if EBITDA has not yet declined materially.

**Refinancing access signal:** Lenders and equity investors use D/E as a quick screen for balance sheet solvency. A very high D/E ratio signals that equity holders have little remaining stake in the company — in a liquidation scenario, almost all asset value would go to creditors before any residual reached equity. This perception reduces willingness to provide new equity capital and increases the cost of refinancing, reinforcing the stress feedback loop documented in the Leverage metric.

**Negative equity — the most severe signal:** When accumulated losses exceed paid-in capital, shareholders' equity turns negative. A negative D/E ratio is essentially meaningless as a ratio but the condition — negative equity — is an automatic stress flag. It means the company is technically insolvent on a book value basis.

---

### Formula

**Extraction note:** See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table and Section "Extraction Fallback Logic" → Inputs 1–3 — reuse all stored Total Debt values; no re-extraction required. and are available from the balance sheet (Shareholders' Equity). No additional XBRL queries are required beyond what Leverage extraction already captures. This section documents only what is incremental.

```
Debt-to-Equity Ratio = Total Debt / Shareholders' Equity

Total Debt = Short-Term Borrowings
           + Current Portion of Long-Term Debt
           + Long-Term Debt (Non-Current)
           (See LEVERAGE.md → Section "Formula" → Formula 1 (Total Debt definition) — apply identical three-component definition)

Shareholders' Equity = us-gaap:StockholdersEquity
                    OR us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest
```

**Two variants:**

```
Variant 1 — Debt-to-Equity (financial debt only):
D/E = Total Financial Debt / Shareholders' Equity
(preferred for credit analysis — consistent with
Leverage metric debt definition)

Variant 2 — Total Liabilities-to-Equity:
TL/E = Total Liabilities / Shareholders' Equity
(broader — includes operating liabilities;
less useful for credit stress but sometimes
disclosed by companies)

System computes Variant 1 as primary.
Variant 2 stored as supplementary.
```

**XBRL tags (incremental only):**

| Input | Primary Tag | Fallback Tag |
|---|---|---|
| Shareholders' Equity | `us-gaap:StockholdersEquity` | `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| Total Liabilities (supplementary) | `us-gaap:Liabilities` | Derived from Assets − Equity |

Total Debt tags: Total Debt tags: See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table — reuse all stored debt tag values; no re-extraction required.

**Error handling:**
```
If Shareholders' Equity = 0: ratio undefined
   Flag: "zero equity — D/E undefined"
If Shareholders' Equity < 0: ratio negative
   Flag: "NEGATIVE EQUITY — book value insolvent;
   D/E ratio not meaningful; condition itself
   is the stress signal"
   Do NOT suppress — store the negative equity
   value and generate alert
If Total Debt null: See LEVERAGE.md → Section "Extraction Fallback Logic" → Inputs 1–4 — apply identical null propagation logic
```

---

### Where it lives

All debt inputs: See LEVERAGE.md → Section "Where it lives" → Formula 1 table — all debt line item locations identical; no new locations required.

**Incremental input only — Shareholders' Equity:**

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Shareholders' Equity | Balance Sheet — Equity section | "Total stockholders' equity" or "Total shareholders' equity" or "Total equity" | 10-K and 10-Q |

**Note on noncontrolling interests:** Some companies report equity as "Total equity attributable to [Company] shareholders" plus "Noncontrolling interests." For credit analysis use the total equity including noncontrolling interests — the fallback tag above captures this. Flag if noncontrolling interests are material (>10% of total equity) as the D/E ratio may be distorted.

---

### Structured or Unstructured

All structured. Shareholders' equity is one of the most reliably tagged items in XBRL. Total debt already extracted for Leverage. No LLM required for any formula version of this metric.

| Input | XBRL Tag | Structured or Unstructured |
|---|---|---|
| Total Debt | See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored value; no re-extraction | Structured — already extracted |
| Shareholders' Equity | `us-gaap:StockholdersEquity` | Structured — reliable |
| Total Liabilities (supplementary) | `us-gaap:Liabilities` | Structured — required GAAP subtotal |

---

### Extraction Fallback Logic

See LEVERAGE.md → Section "Extraction Fallback Logic" → Inputs 1 through 4 (Short-Term Borrowings, Current LT Debt, Long-Term Debt, Total Debt derived) — apply identical fallback chains in full.

**Incremental fallback for Shareholders' Equity only:**

```
Step 1 — Try: us-gaap:StockholdersEquity
Step 2 — Try: us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest
Step 3 — Derive: us-gaap:Assets − us-gaap:Liabilities
          Flag: "equity derived from assets minus
          liabilities — verify balance sheet balances"
Step 4 — If all null: Equity = null → D/E = null
          Flag: "shareholders' equity not extractable"

Negative equity handling:
   If extracted value < 0: do NOT set to null
   Store the negative value
   Generate automatic stress flag
   D/E computation proceeds but result is
   flagged as "negative equity — ratio sign
   inverted; condition more important than ratio"
```

---

### Stress Threshold — Debt-to-Equity Ratio (Fully Revised)

---

**Source basis:** S&P Global Market Intelligence data confirming investment-grade company median D/E of approximately 0.87x and non-investment-grade median of approximately 1.22x. FullRatio industry data (March 2025) covering average D/E across 130+ US industries. Sector-specific healthy range benchmarks from practitioner analysis.

---

**Step 1 — Sector grouping (revised and empirically anchored)**

| Sector Group | Representative Industries | Empirical Average D/E Range | Basis |
|---|---|---|---|
| **Asset-light** | Technology, pharma/biotech, healthcare services, software | 0.15x – 0.60x | Semiconductors 0.32x; Software-Application 0.32x; Biotechnology 0.16x |
| **Standard** | Industrials, consumer staples, consumer discretionary, retail, telecom | 0.40x – 1.40x | Grocery 1.14x; Telecom 1.05x; Packaging 1.76x (high end) |
| **Capital-intensive** | Utilities, energy midstream, airlines, railroads | 0.90x – 1.55x | Regulated Electric 1.55x; Regulated Gas 1.48x; Airlines 1.32x |
| **Real estate / REITs** | All REIT sub-types, real estate services | 0.87x – 2.64x | REIT-Mortgage 2.64x; REIT-Diversified 0.97x |
| **Not applicable** | Banks, insurance companies, financial institutions | N/A — D/E not meaningful | Deposits inflate liabilities; regulatory capital ratios used instead |

---

**Step 2 — Absolute threshold table (revised)**

**Asset-light (Technology, Pharma, Biotech, Software)**
*Empirical healthy range: 0.15x – 0.60x*

| D/E | Interpretation | Alert Level |
|---|---|---|
| < 0.5x | Normal for sector | No alert |
| 0.5x – 1.0x | Slightly elevated — monitor | Watch |
| 1.0x – 1.5x | High for asset-light company | Flag |
| 1.5x – 2.5x | Very high — equity cushion thinning | Stress |
| > 2.5x | Extreme for sector | Critical |

**Standard (Industrials, Consumer, Retail, Telecom)**
*Empirical healthy range: 0.40x – 1.40x*

| D/E | Interpretation | Alert Level |
|---|---|---|
| < 1.0x | Normal | No alert |
| 1.0x – 1.5x | Moderate — within sector norms | Watch |
| 1.5x – 2.5x | Elevated — above median | Flag |
| 2.5x – 3.5x | High — well above sector norm | Stress |
| > 3.5x | Extreme for sector | Critical |

**Capital-intensive (Utilities, Midstream Energy, Airlines, Railroads)**
*Empirical healthy range: 0.90x – 1.55x*

| D/E | Interpretation | Alert Level |
|---|---|---|
| < 1.5x | Normal for sector | No alert |
| 1.5x – 2.0x | Slightly elevated | Watch |
| 2.0x – 2.75x | Elevated — above sector average | Flag |
| 2.75x – 3.5x | High — equity cushion thinning | Stress |
| > 3.5x | Extreme for capital-intensive sector | Critical |

**Real estate / REITs**
*Empirical healthy range: 0.87x – 2.64x depending on sub-type*

| D/E | Interpretation | Alert Level |
|---|---|---|
| < 1.5x | Conservative for sector | No alert |
| 1.5x – 2.0x | Normal — within REIT norms | Watch |
| 2.0x – 3.0x | Elevated — above sector median | Flag |
| 3.0x – 4.0x | High — approaching stress territory | Stress |
| > 4.0x | Extreme even for REITs | Critical |

> **Note on prior thresholds corrected:** The original draft set Critical at >5.0x (generic) and >9.0x (REITs). Both are revised downward substantially. The empirical data shows no major non-financial sector averaging above 2.64x — a 5.0x+ universal threshold would miss genuinely stressed companies for most sectors.

---

**Step 3 — Negative equity — automatic Critical (all sectors)**

```
If Shareholders' Equity < 0:
   D/E ratio = negative or undefined
   Do NOT attempt to interpret the ratio sign
   Generate automatic Critical alert:
   "NEGATIVE EQUITY — book value insolvent;
   shareholders' equity has been fully consumed
   by accumulated losses, impairments, or
   leveraged recapitalisations; ratio not
   meaningful; condition itself is the signal"

Important distinction:
   Negative equity from accumulated losses:
   → Acute stress signal; deteriorating business
   Negative equity from leveraged recapitalisation
   (large buybacks exceeding retained earnings):
   → Common in strong cash-flow companies
     (e.g. mature consumer brands, some tech)
   → LLM should read MD&A equity section to
     determine cause; flag accordingly
   → If buyback-driven: downgrade from Critical
     to Stress; flag: "negative equity from
     capital return programme — verify FCF
     remains sufficient to service debt"
```

---

**Step 4 — Relative threshold (Tier 2 — more sensitive)**

Absolute thresholds detect extreme outliers. The relative threshold detects deterioration relative to a company's own history and sector peers — catching stress earlier.

```
Relative trigger: Flag when company D/E exceeds
2× its own three-year average D/E for two
consecutive quarters.

This catches rapid leverage-up events (LBOs,
large debt-funded acquisitions) regardless of
whether the absolute threshold is breached.

Example:
   Company A: three-year average D/E = 0.6x
   Current D/E = 1.3x (>2× average)
   → Relative Flag triggered even though 1.3x
     is below the absolute Flag threshold for
     standard sectors

Sector median relative trigger (Phase 3):
   Flag when company D/E exceeds 2× the
   sector median computed from the portfolio
   at onboarding.
   Requires maintaining sector median reference
   per the 30-name portfolio — one-time setup.
```

---

**Step 5 — Trend rule**

| D/E Trend | Alert Level |
|---|---|
| D/E stable or declining | No trend alert |
| D/E increasing for 2 consecutive quarters | Watch — equity erosion or debt accumulation beginning |
| D/E increasing for 3 consecutive quarters | Flag — sustained deterioration regardless of absolute level |
| D/E increasing for 4+ consecutive quarters | Stress — persistent structural change |
| D/E increasing AND absolute level in Flag band | Escalate one level beyond trend-only alert |

---

**Step 6 — Combined alert trigger rules**

| Alert Level | Condition | Action |
|---|---|---|
| **Watch** | D/E in Watch band for sector; OR D/E increasing 2 consecutive quarters | Log; weekly review |
| **Flag** | D/E in Flag band; OR D/E increasing 3 consecutive quarters; OR D/E exceeds 2× own three-year average | Generate alert; daily monitoring |
| **Stress** | D/E in Stress band; OR D/E increasing 4+ consecutive quarters; OR negative equity from losses | Immediate alert; escalate same day |
| **Critical** | D/E in Critical band; OR negative equity (any cause pending LLM review) | Immediate escalation; cross-reference leverage and coverage |
| **Trend Flag** | Any 3 consecutive quarters of increase | Alert regardless of band |

---

**Step 7 — Relationship to Leverage metric**

D/E and Net Debt / EBITDA are complementary not redundant. When both are in stress bands simultaneously, the combination is more informative than either alone:

S&P Global Market Intelligence data confirms that interest coverage weakened alongside higher D/E ratios for both investment-grade and non-investment-grade companies in 2025 — validating that D/E deterioration and coverage deterioration move together in stress environments, and that monitoring both provides confirmation rather than redundancy.

```
Combined D/E + Leverage signal rule:
If D/E in Flag or above AND Leverage in
Aggressive or Highly Leveraged band simultaneously:
   Escalate both to next alert level
   Flag: "dual balance sheet stress —
   D/E and Net Debt/EBITDA both elevated;
   equity cushion thin and earnings
   insufficient relative to debt load"
```



---

### Signal Timing

**Lagging — slower than leverage, faster than balance sheet insolvency.**

D/E moves slowly because both debt and equity are stock measures that change gradually. It is a confirming signal rather than a leading one — by the time D/E reaches stress thresholds, leverage and coverage have almost always already flagged the deterioration.

The one scenario where D/E leads the other metrics is **equity erosion without new debt.** A company generating large net losses will see its equity base shrink quarter over quarter even if it takes on no new debt — D/E rises while leverage (Net Debt / EBITDA) may appear stable if EBITDA has not yet collapsed. This makes D/E a useful cross-check on the leverage metric for companies with large goodwill impairments, restructuring charges, or pension losses flowing through other comprehensive income.

**Filing lag:** See LEVERAGE.md → Section "Signal Timing" → Three-Tier Timing Structure table — apply identical Tier 1 filing lag of 40 days; no intra-quarter updates for balance sheet items.

---

### Frequency

See LEVERAGE.md → Section "Frequency" → full section — apply identical update schedule, 8-K channel definitions, and Phase 2 vs Phase 3 priority framework; no modifications required. Going concern keyword monitoring: See LIQUIDITY.md → Section "Frequency" → going concern monitoring — apply identical keyword scan.

See LEVERAGE.md → Section "Frequency" → full section — apply identical update schedule, 8-K channel definitions, and Phase 2 vs Phase 3 priority framework; no modifications required. Going concern keyword monitoring: See LIQUIDITY.md → Section "Frequency" → going concern monitoring — apply identical keyword scan.




## Appendix: Debt-to-Equity Ratio — Empirical Calibration Notes

The following section documents the empirical data and reasoning that informed the revised Stress Thresholds. This appendix is provided for reference and auditability; the normative thresholds are defined in the Stress Threshold section above.

---

### Three Corrections to the Original Threshold Logic

**Correction 1 — Sector groupings were mis-calibrated**

The original draft assumed utilities operate with D/E of 2x–3x+. Actual data shows:

| Utility Sub-sector | Average D/E |
|---|---|
| Regulated Electric | 1.55x |
| Regulated Gas | 1.48x |
| Diversified Utilities | 1.21x |

These are moderate, not extreme. The original Flag threshold of >3.5x for utilities was far too forgiving.

**Correction 2 — REITs are the highest legitimate D/E sector, not utilities**

| REIT Sub-sector | Average D/E |
|---|---|
| REIT — Mortgage | 2.64x |
| REIT — Specialty | 1.60x |
| REIT — Office | 1.37x |

Even the highest REIT sub-sector averages only 2.64x. The original Critical threshold of 9.0x for REITs was absurdly forgiving.

**Correction 3 — Investment-grade vs non-investment-grade split is more useful than sector alone**

| Issuer Type | Median D/E |
|---|---|
| Investment-grade (non-financial) | ~0.85x – 0.87x |
| Non-investment-grade (non-financial) | ~1.18x – 1.22x |

> **Key empirical anchor:** Investment-grade median is below 1.0x across all non-financial sectors. A company at 3.0x+ is already well above the non-investment-grade median.

---

### Healthy Sector Benchmarks (Empirical)

| Sector | Healthy D/E Range |
|---|---|
| Technology | 0.2x – 0.6x |
| Utilities | 0.5x – 2.0x |
| Consumer Discretionary / Retail | 0.5x – 1.5x |
| Industrial / Manufacturing | 0.4x – 1.0x |

---

### Original 5.0x Critical Threshold — Why It Was Revised

Even the most leveraged non-financial sectors have average D/E well below 5.0x:

| Sector | Average D/E |
|---|---|
| REIT — Mortgage | 2.64x |
| Resorts & Casinos | 2.44x |

A truly alarming D/E for most sectors is **above 3.0x–4.0x**, not 5.0x. The original 5.0x universal Critical threshold was therefore too high and has been replaced with sector-specific thresholds in the Stress Threshold section.

---

### Data Sources

- S&P Global Market Intelligence. (2023). *US companies reduce debt loads as interest burden grows.* spglobal.com
- S&P Global Market Intelligence. (2025). *Debt burden grows for rated US corporations in Q1.* spglobal.com
- FullRatio. (2025). *Debt to equity ratio by industry — US, March 2025.* fullratio.com
- Vested Finance. (2026). *Debt-to-equity ratio: formula, industry benchmarks and risk factors.* vestedfinance.com
