# Debt Maturity Wall

## What it is

### Core Definition

The Debt Maturity Wall measures the schedule of when a company's debt obligations come due — mapping every tranche of debt to the year or quarter in which principal repayment is required. It answers: *"how much debt does this company need to repay or refinance, and when?"*

### Not a Ratio — A Schedule

Unlike every other metric in this spec, the Debt Maturity Wall is **not a ratio**. It does not produce a single number that can be compared to a threshold. It produces a **schedule** — a time series of future cash obligations — that must be interpreted in the context of the company's current liquidity, projected FCF, and capital market access.

| Scenario | Position |
|----------|----------|
| $5B debt maturing in year 5 | Time to improve position |
| $5B debt maturing in year 1 | Immediate existential test |

Same total debt. Same leverage ratio. Completely different risk profile.

### The "Wall" Metaphor

When debt maturities are plotted as a bar chart by year, companies with concentrated maturities in a single year show a tall isolated bar — a **wall** — that represents a moment when the company must either:

- Generate enough cash internally, OR
- Successfully refinance a large amount of debt in the capital markets simultaneously

If that moment arrives during a period of market stress, elevated credit spreads, or company-specific deterioration, **the wall becomes a cliff**.

### Two Risk Dimensions

The maturity wall captures two distinct risk dimensions that no other metric in this spec addresses directly.

| Risk Dimension | Description |
|----------------|-------------|
| **Refinancing risk** | The risk that when debt matures, the company cannot refinance it on acceptable terms or at all. Low when maturities are spread across many years, markets are open, and credit quality is strong. High when maturities are concentrated, markets are tight, or credit quality has deteriorated. |
| **Interest rate reset risk** | The risk that when fixed-rate debt is refinanced, it must be replaced at a higher coupon rate — mechanically increasing interest expense and compressing coverage even if the business itself has not deteriorated. In a rising rate environment, refinancing becomes more expensive, reducing future coverage ratios. |

**Cross-metric signal:** The interaction between the maturity wall and the interest coverage metric is one of the most important cross-metric signals in the system.

### Data Source

The maturity wall is extracted primarily from the **debt footnote** in 10-K and 10-Q filings, where companies are required to disclose the schedule of future principal payments under long-term debt arrangements.

| Disclosure Format | Description |
|-------------------|-------------|
| Table structure | Amounts due in each of the next **five fiscal years** and the aggregate amount due thereafter |

**XBRL limitation:** The total debt is tagged, but the **year-by-year breakdown is not**. This makes the maturity wall one of the primary use cases for the LLM extraction layer in Phase 3.

### Phase 2 vs Phase 3

| Phase | What the System Captures | Limitation |
|-------|--------------------------|-------------|
| **Phase 2** | Only the current portion of long-term debt — the amount maturing within 12 months that has been reclassified to current liabilities on the balance sheet | Tells you what is due immediately, but **nothing about the shape of the wall in years 2 through 5** |
| **Phase 3** | Full maturity schedule extracted by LLM from the debt footnote | Analytically complete picture |


## Why it signals stress

The debt maturity wall signals stress through four mechanisms, each operating on a different timeline and with a different interaction with the other metrics in this spec.

---

### Mechanism 1 — The refinancing imperative (timeline-dependent)

Every debt maturity creates a refinancing imperative — the company must either repay the maturing debt from internal cash generation or replace it with new debt.

**Normal conditions:** Routine treasury management. Capital markets are open, credit quality is acceptable, new debt replaces maturing debt at similar terms.

**Stress conditions — three conditions converge simultaneously:**

| Condition | Description |
|-----------|-------------|
| 1. Maturity is large relative to available liquidity and projected FCF | Internal repayment not feasible; company entirely dependent on market access |
| 2. Credit quality has deteriorated | Lenders demand higher spreads, tighter covenants, or refuse to lend |
| 3. Capital markets are tight | Even creditworthy borrowers face elevated costs and reduced access |

> None of these three conditions alone creates a crisis. **All three together, arriving at the moment a large maturity comes due** — distressed refinancing, covenant-driven default, or bankruptcy.

**The maturity wall metric identifies condition 1.** Leverage and coverage identify condition 2. Market conditions are external to filing data.

**The timeline-dependent signal:**

| Time to Maturity | Alert Level |
|------------------|-------------|
| 36 months | Monitoring item |
| 18 months | Flag |
| 12 months | Stress |
| 6 months | Critical |

> Time is the primary variable that converts a future risk into an immediate one.

---

### Mechanism 2 — The concentration effect (structural risk)

The shape of the maturity wall matters as much as its total size.

| Scenario | Risk Level |
|----------|-----------|
| $3B debt spread evenly across 6 years ($500M/year) | Manageable annual refinancing |
| $3B debt all maturing in a single year | May exceed market absorption or lender capacity |

**Why concentration creates structural risk:**

| Maturity Profile | Flexibility |
|------------------|-------------|
| Staggered maturities | Can refinance early in favourable years, wait out difficult periods — has time and flexibility |
| Concentrated wall | Must refinance on whatever terms the market offers at the moment debt matures — **no flexibility** |

**Interaction with Leverage:**
- Highly leveraged company (Aggressive or Highly Leveraged band) + concentrated maturity wall = compounding risk
- Credit quality makes refinancing expensive; lack of flexibility means cannot wait for better conditions
- This combination is most commonly associated with **distressed exchanges and pre-packaged bankruptcies**

**The concentration signal:**

| Single-Year Maturities % of Total Debt | Signal |
|----------------------------------------|--------|
| > 30% | Worth flagging — refinancing burden disproportionate to annual management capacity |
| > 50% | Severe concentration |

---

### Mechanism 3 — The interest rate reset amplifier (medium term)

When fixed-rate debt matures and is refinanced at higher market rates, interest expense increases mechanically — not because the business deteriorated, but because the cost of debt rose.

**This effect directly compresses interest coverage ratio** even if EBITDA is unchanged.

**Three variables determine amplification:**

| Variable | Description |
|----------|-------------|
| Size of maturing tranche | Larger tranche = larger impact |
| Coupon vs current market rate gap | Larger gap = larger impact |
| Proportion of total interest expense | Higher proportion = larger impact |

**Example:**
- Company refinances $500M of 3% bonds at 7%
- Adds $20M of annual interest expense
- With $200M EBITDA, coverage drops from 4.0x to approximately 3.0x
- **No operational deterioration required**

**System capability (Phase 3):** Combine maturity wall schedule (tranche-level coupon rate and maturity date) with current market spreads. Projected post-refinancing coverage ratio — one of the most valuable forward-looking signals.

**The amplifier signal:**
Any tranche maturing within 18 months with a coupon rate **more than 200 basis points below** the issuer's current market spread. Identifies bonds where refinancing will materially increase interest expense and compress coverage.

---

### Mechanism 4 — The lender confidence signal (early warning)

How a company manages its maturity wall **in advance** reveals lender confidence information not available from any balance sheet metric.

| Behavior | Signal |
|----------|--------|
| Refinances 12–18 months ahead of maturity | Capital markets are open; lenders willing to commit at acceptable terms |
| Cannot refinance until forced at maturity | Lender confidence is limited |
| Accepts onerous terms (high spreads, tight covenants, shorter maturities) | Reveals limited lender confidence |

**Visible in your system through:** 424B prospectus filings (new bond issuances) and 8-K Item 2.03 filings (new credit facilities).

**The most alarming version — short-dated refinancing:**

| Before | After | Signal |
|--------|-------|--------|
| 7-year bond | 2-year term loan | Nominal maturity extended but wall merely pushed forward; market willing to lend but only short-term, reflecting uncertainty about medium-term credit trajectory |

**The lender confidence signal:**
**Average debt maturity declining across consecutive annual 10-K filings.**

Example: 6 years (2021) → 4.5 years (2022) → 3 years (2023)

> The company is not resolving its maturity wall — it is **compressing it**. Each refinancing pushes the wall closer rather than further away.

---

### Interaction with Other Metrics

The debt maturity wall does not generate isolated stress signals — it **amplifies and contextualises** signals from every other metric in this spec.

| Metric | Interaction |
|--------|-------------|
| **Leverage** | High leverage + near-term maturity wall = refinance large debt load when credit quality already impaired — worst possible combination for refinancing terms |
| **Coverage** | Near-term maturity wall + deteriorating coverage = even if refinancing achieved, new debt carries higher coupon, further compressing coverage in self-reinforcing loop |
| **FCF** | Negative FCF + near-term maturity wall = eliminates internal repayment option; entirely dependent on capital market access exactly when cash generation is insufficient |
| **Liquidity** | Available liquidity below size of near-term maturity = most direct and quantifiable definition of near-term default risk — company literally does not have cash to repay what is due |
| **Covenant Headroom** | Covenant breach that accelerates debt = extreme version of maturity wall event where entire debt stack becomes current simultaneously |

---

### Institutional Validation

| Source | Content |
|--------|---------|
| **Moody's** | Debt maturity analysis is core to liquidity assessment; near-term maturities relative to available liquidity are primary determinant of SGL rating |
| **S&P** | Liquidity descriptor framework explicitly requires assessment of debt maturities in Year 1 and Year 2 as inputs to sources-and-uses calculation |
| **Empirical evidence** | Companies with >40% of debt maturing within two years default at materially higher rates than those with staggered profiles — holding leverage and coverage constant |

> The maturity wall provides information about default risk that is **not captured by the other metrics**.

---

### Summary of Debt Maturity Wall Alert Signals

| Mechanism | Signal | Timeline | Alert Level |
|-----------|--------|----------|-------------|
| M1 — Refinancing imperative | Large maturity approaching with limited resources | 18 mo → Flag; 12 mo → Stress; 6 mo → Critical | Timeline-dependent |
| M2 — Concentration | >30% of debt maturing in single year | Any | Flag |
| M2 — Concentration | >50% of debt maturing in single year | Any | Severe concentration |
| M3 — Interest rate reset | Tranche maturing within 18 months with coupon >200bps below market | 18 months | Forward-looking signal (Phase 3) |
| M4 — Lender confidence | Average debt maturity declining across consecutive years | Annual | Stress indicator |

## Formula

---

**The Debt Maturity Wall is not a single ratio — it is a structured schedule combined with four derived analytical outputs.**

Unlike all prior metrics which produce one or more ratios from financial statement inputs, the maturity wall's primary output is a time series — a year-by-year table of principal repayments. The four derived outputs are computed from this schedule in combination with inputs already extracted for other metrics. This makes the maturity wall the most structurally different metric in the spec and the one with the sharpest Phase 2 vs Phase 3 capability gap.

---

**Formula 1 — Automated Baseline (XBRL / Deterministic)**

Phase 2 can extract only one component of the maturity wall from structured XBRL — the amount maturing within the next 12 months that has been reclassified to current liabilities.

```
Phase 2 Maturity Capture:

Near-Term Maturity (12 months) =
    us-gaap:LongTermDebtCurrent
  + us-gaap:ShortTermBorrowings
  + us-gaap:CommercialPaper

Maturity Coverage Ratio =
    Available Liquidity (See LIQUIDITY.md → Section "Formula" → Output 1A (Cash) and Output 1D (Available Liquidity Coverage) — use stored cash and short-term investments values; Phase 3 adds revolver per LIQUIDITY.md Formula 2)
    / Near-Term Maturity

Where Available Liquidity =
    Cash & Equivalents
  + Short-Term Investments
  (Phase 2 — revolver excluded)
  (Phase 3 — revolver included)
```

**What Phase 2 cannot capture:** The maturity schedule beyond 12 months. Years 2 through 5 and the thereafter bucket are disclosed in the debt footnote as a table but are not tagged in XBRL at the individual year level. Phase 2 therefore sees only the immediate maturity obligation — the first bar of the wall — without the full wall shape.

**XBRL tags for Formula 1:**

| Input | Primary XBRL Tag | Fallback Tag |
|---|---|---|
| Current portion of LT debt | `us-gaap:LongTermDebtCurrent` | `us-gaap:DebtCurrent` |
| Short-term borrowings | `us-gaap:ShortTermBorrowings` | `us-gaap:CommercialPaper` |
| Commercial paper | `us-gaap:CommercialPaper` | `us-gaap:NotesPayableCurrent` |
| Cash (for coverage ratio) | `us-gaap:CashAndCashEquivalentsAtCarryingValue` | `us-gaap:CashCashEquivalentsAndShortTermInvestments` |
| Short-term investments | `us-gaap:ShortTermInvestments` | `us-gaap:MarketableSecuritiesCurrent` |

**Error handling:** If LongTermDebtCurrent is null, Near-Term Maturity = sum of short-term components only — flag: "current portion of LT debt not found — near-term maturity figure captures short-term borrowings only; may be materially understated." If all components null → Near-Term Maturity = null → Maturity Coverage Ratio = null.

---

**Formula 2 — Full Maturity Schedule (LLM extraction, Phase 3)**

The complete maturity wall requires LLM extraction of the debt footnote maturity table. This is the analytically complete version of the metric.

```
Full Maturity Schedule:

Raw extraction from Debt Footnote maturity table:
Year 1:  $X million  (next fiscal year)
Year 2:  $X million
Year 3:  $X million
Year 4:  $X million
Year 5:  $X million
After:   $X million  (aggregate beyond year 5)
Total:   $X million  (sum — verify equals total debt)

Derived Output A — Maturity Concentration Ratio:
Concentration(year n) =
    Maturities in year n / Total Debt Outstanding
Flag if any single year > 30% of total debt

Derived Output B — Near-Term Maturity Ratio:
Near-Term Ratio =
    (Year 1 + Year 2 Maturities) / Total Debt
Flag if > 40% — severe near-term concentration

Derived Output C — Weighted Average Debt Maturity (WADM):
WADM =
    Σ (Year n Maturity × Years to Maturity n)
    / Total Debt

Where Years to Maturity:
Year 1 = 1.0
Year 2 = 2.0
Year 3 = 3.0
Year 4 = 4.0
Year 5 = 5.0
After  = 7.0 (convention — midpoint of years 6–8)

Flag if WADM < 3.0 years — short average maturity
Flag if WADM declining across consecutive annual filings
— maturity wall compressing over time

Derived Output D — Liquidity-to-Maturity Coverage:
Full Coverage =
    Available Liquidity (cash + revolver, Phase 3)
    / Year 1 Maturities

Extended Coverage =
    Available Liquidity + Projected Annual FCF
    / (Year 1 + Year 2 Maturities)

Flag if Full Coverage < 1.0x — cannot cover
Year 1 maturities from available liquidity alone
Flag if Extended Coverage < 1.0x — cannot cover
two-year maturities from liquidity plus FCF
```

---

**Formula 3 — Tranche-Level Analysis (LLM extraction, Phase 3)**

The most granular level of maturity wall analysis requires tranche-by-tranche extraction — identifying each individual debt instrument, its maturity date, principal amount, coupon rate, and instrument type. This enables the interest rate reset analysis described in Why it signals stress Mechanism 3.

```
Tranche-Level Data Structure:

For each debt tranche identified in Debt Footnote:
{
  instrument_type:    "Senior Notes" / "Term Loan" /
                      "Revolving Credit" / "Convertible Notes" /
                      "Subordinated Notes" / other
  principal_amount:   $X million (face value)
  maturity_date:      YYYY-MM-DD
  coupon_rate:        X.XX% (fixed) or
                      "SOFR + X.XX%" (floating)
  coupon_type:        "fixed" / "floating"
  currency:           USD / EUR / other
  secured:            true / false
  callable:           true / false
  call_date:          YYYY-MM-DD (if callable)
}

Derived Output E — Projected Interest Rate Reset Impact:
For each tranche maturing within 18 months:

Current annual interest = Principal × Coupon Rate
Estimated new coupon = Current market spread
                       for this issuer's credit quality
                       (requires external market data
                       — not from filing)
Estimated new annual interest = Principal × New Coupon
Interest rate reset impact = New − Current (annual)

Cumulative reset impact across all tranches
maturing within 18 months:
Total annual interest increase = Σ reset impacts

Projected coverage post-reset =
    Current EBITDA /
    (Current Interest Expense + Total annual increase)

Flag if projected coverage post-reset crosses
a threshold band relative to current coverage:
Coverage compression ≥ 0.5x → Watch
Coverage compression ≥ 1.0x → Flag
Coverage compression ≥ 1.5x → Stress

Derived Output F — Refinancing Tenor Analysis:
Track average tenor of new debt issued vs
average tenor of debt retired over trailing
four quarters:
New issuance tenor = weighted average maturity
                     of 424B and 8-K Item 2.03
                     filings in trailing 4 quarters
Retired debt tenor = weighted average remaining
                     maturity of debt repaid

If new issuance tenor < retired debt tenor
for two consecutive annual periods:
Flag: "average debt maturity shortening —
possible lender confidence deterioration;
maturity wall compressing"
```

---

**Companion Metric — Days to Nearest Maturity**

```
Days to Nearest Maturity =
    Calendar days from filing date to
    earliest debt maturity date

(Requires tranche-level maturity dates from
Formula 3 extraction — Phase 3 only)

Phase 2 approximation:
If LongTermDebtCurrent > 0:
   Nearest maturity is within 365 days
   Exact date unknown — flag as "within 12 months"
If LongTermDebtCurrent = 0:
   No maturity within 12 months from balance sheet
   Exact next maturity date unknown in Phase 2

Phase 3:
   Exact days computed from tranche-level dates
   Alert thresholds:
   > 365 days:  No immediate alert
   180–365 days: Watch — maturity approaching
   90–180 days:  Flag — refinancing window narrowing
   30–90 days:   Stress — imminent maturity
   < 30 days:    Critical — maturity imminent;
                 refinancing or repayment must
                 be confirmed or underway
```

---

**Comparison Table**

| | Formula 1 — Phase 2 Baseline | Formula 2 — Full Schedule | Formula 3 — Tranche Level |
|---|---|---|---|
| **Primary output** | Near-term maturity (12M) + coverage ratio | Year-by-year schedule + 4 derived outputs | Per-tranche data + interest rate reset + tenor analysis |
| **Maturity horizon** | 12 months only | Years 1–5 + thereafter | Exact dates per tranche |
| **Concentration analysis** | ❌ No | ✅ Yes | ✅ Yes (by instrument type) |
| **WADM computation** | ❌ No | ✅ Yes (approximate) | ✅ Yes (exact) |
| **Interest rate reset** | ❌ No | ❌ No | ✅ Yes (requires market data) |
| **Tenor trend analysis** | ❌ No | ❌ No (annual only) | ✅ Yes (quarterly) |
| **Requires LLM** | ❌ No | ✅ Yes | ✅ Yes (extensive) |
| **Requires market data** | ❌ No | ❌ No | ✅ Yes (current spreads) |
| **Implementation phase** | Phase 2 | Phase 3 | Phase 3 |

---

**Implementation Guidance**

Formula 1 is the Phase 2 baseline. It captures the most urgent component of the maturity wall — what is due within 12 months — and combines it with the liquidity metric's cash figure to produce a Maturity Coverage Ratio. This is a narrow but actionable signal: a Maturity Coverage Ratio below 1.0x means the company cannot cover its near-term debt maturities from cash alone, which is a direct and unambiguous liquidity stress signal that requires no further analytical judgement.

Formula 2 is the Phase 3 primary target. The full maturity schedule — available in every 10-K debt footnote — is the most valuable piece of credit information the LLM layer will extract. The four derived outputs (Concentration Ratio, Near-Term Ratio, WADM, Liquidity-to-Maturity Coverage) together give a complete picture of refinancing risk that is unavailable from any other source. The WADM trend across consecutive annual filings is particularly valuable — it is a slow-moving signal that requires no threshold calibration and is unambiguous in its interpretation: a declining WADM means the debt structure is becoming more fragile.

Formula 3 is a Phase 3 enhancement that unlocks the most forward-looking analytical capability in this spec — projecting future coverage compression from interest rate resets before they occur. It requires both LLM extraction and external market data (current spread levels for the issuer), making it the most complex computation in the entire system. It should be implemented after Formula 2 is validated and stable.

The maturity wall's primary Section 6 deviation — noted in the earlier discussion of implementation parameters — is that its output is a schedule and a set of derived metrics rather than a single ratio. The data storage schema must accommodate a variable-length array of maturity data points per issuer per filing rather than a fixed set of ratio fields. This is the most significant schema difference between the maturity wall and all other metrics in this spec.


## Where it lives — Debt Maturity Wall

---

**Formula 1 — Automated Baseline**

All items are structured, on the face of financial statements, available in both 10-K and 10-Q.

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Current portion of LT debt | Balance Sheet — Current Liabilities section | "Current portion of long-term debt" or "Current maturities of long-term debt" or "Current portion of term debt" | 10-K and 10-Q |
| Short-term borrowings | Balance Sheet — Current Liabilities section | "Short-term borrowings" or "Short-term debt" | 10-K and 10-Q |
| Commercial paper | Balance Sheet — Current Liabilities section | "Commercial paper" | 10-K and 10-Q |
| Cash & equivalents | Balance Sheet — Current Assets section | "Cash and cash equivalents" | 10-K and 10-Q |
| Short-term investments | Balance Sheet — Current Assets section | "Short-term investments" or "Marketable securities, current" | 10-K and 10-Q |

**Note on current portion reclassification timing:** The reclassification of long-term debt to current happens at the balance sheet date when the maturity falls within 12 months of that date. For a December 31 fiscal year company, debt maturing before December 31 of the following year appears as a current liability. This means the current portion figure changes every quarter as new maturities enter the 12-month window and prior maturities are repaid or refinanced. Tracking the quarter-over-quarter change in current portion is itself a useful signal — a sudden increase indicates a large maturity has entered the 12-month window.

---

**Formula 2 — Full Maturity Schedule**

**Correction from original draft:** The original draft classified the full maturity schedule as entirely unstructured (LLM only). This was incorrect. The US GAAP taxonomy contains standard XBRL tags for individual year maturities that are queryable via the EDGAR companyconcept API. However, filer adoption is inconsistent — many companies populate these tags, many do not. The correct classification is **semi-structured**: attempt XBRL extraction first, fall back to LLM extraction for missing years or reconciliation failures.

---

**Item 2a — Debt Maturity Schedule Table**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote (typically Note 5–9, titled "Debt," "Long-Term Debt," "Borrowings," or "Credit Facilities") AND EDGAR XBRL companyconcept API |
| Available in | 10-K — full five-year schedule required under US GAAP; 10-Q — XBRL tags may be present if company updates them quarterly; LLM footnote schedule usually absent from 10-Q |
| Exact location — structured | EDGAR companyconcept API: `data.sec.gov/api/xbrl/companyconcept/CIK{number}/us-gaap/{tag}.json` for each of the six maturity tags listed below |
| Exact location — unstructured | Debt Footnote table titled "Maturities of Long-Term Debt," "Scheduled Debt Maturities," "Future Principal Payments," or "Aggregate Annual Maturities." The table shows amounts due in each of the next five fiscal years and the aggregate amount due thereafter. Almost always present in the 10-K. |
| What to extract | Six numbers: Year 1 through Year 5 maturities and the Thereafter bucket. Also extract the total — verify it equals total debt disclosed on the balance sheet. |
| Fiscal year vs calendar year note | Year labels in the maturity table are fiscal years not calendar years. A company with a March 31 fiscal year-end will show Year 1 as the 12 months ending March 31 of the following year. Store all maturity amounts with explicit fiscal year-end dates not generic year labels. |
| 10-Q availability | Most companies do not update the full LLM-readable maturity schedule in 10-Q filings. XBRL tags may update quarterly for companies that populate them. If XBRL tags are absent and no updated footnote table is present in the 10-Q, use the most recent 10-K schedule adjusted for any debt events since that filing. Flag: "maturity schedule from [10-K date] — updated for [debt events if any]; full update pending next 10-K." |

**XBRL tags for maturity schedule (attempt before LLM):**

| Year | XBRL Tag |
|---|---|
| Year 1 (next 12 months) | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths` |
| Year 2 | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo` |
| Year 3 | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree` |
| Year 4 | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour` |
| Year 5 | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive` |
| Thereafter | `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive` |

**Reconciliation check — mandatory before using XBRL maturity data:**

```
Sum of all six XBRL maturity tags must reconcile to total debt:

Sum = Year1 + Year2 + Year3 + Year4 + Year5 + Thereafter

Compare to: us-gaap:LongTermDebt
         OR us-gaap:DebtAndCapitalLeaseObligations

Case 1 — Sum reconciles within 5% of total debt:
   Use XBRL maturity tags as primary source
   Flag: "maturity schedule from XBRL tags —
   reconciled to total debt (within 5% tolerance)"

Case 2 — Difference between 5% and 10%:
   Use XBRL maturity tags but flag:
   "maturity schedule reconciliation discrepancy exceeds 5% 
    but is less than 10% — investigate source
    (unamortized discount, issuance costs, leases)
    before relying on XBRL data"
   Store XBRL data as provisional; mark for manual review

Case 3 — Difference exceeds 10%:
   Discard XBRL maturity tags entirely
   Escalate to full LLM extraction from Debt Footnote
   Flag: "XBRL maturity tags discarded (reconciliation
   failure >10%) — full LLM extraction required"

Case 4 — Any individual year tag is null while total debt non-zero:
   Flag which specific years are missing:
   "Year [N] maturity tag absent — LLM extraction
   required for missing year(s)"
   Use XBRL for populated years
   Use LLM for missing years
   Re-verify reconciliation after combining both

Case 5 — All six tags are null:
   Full LLM extraction required
   Flag: "no XBRL maturity tags found —
   full LLM extraction from Debt Footnote"
   This is expected for a significant proportion of filers
```

**Why the reconciliation check is mandatory:** Even when all six tags are populated, they may not sum correctly if the company has also tagged finance lease obligations within the debt tags, uses a non-standard fiscal year convention, or has partially updated tags mid-year. A reconciliation failure with populated tags is more dangerous than absent tags because it creates a silently incorrect maturity schedule.

**Fallback for missing XBRL tags — Phase 2 only:**

If XBRL maturity tags for Year 1 are absent or zero (and not recoverable via LLM in Phase 2):
   Use `us-gaap:LongTermDebtCurrent` as an estimate for Year 1 maturities
   Flag: "Year 1 maturity not tagged in XBRL — estimated using
          LongTermDebtCurrent figure from balance sheet;
          actual Year 1 maturity may be understated if
          short-term borrowings also due within 12 months
          or overstated if LongTermDebtCurrent includes
          finance lease obligations"
   Do NOT attempt to estimate Year 2-5 maturities from any source
   in Phase 2 — mark Year 2-5 as null and flag "Phase 2 limitation"

---

**Item 2b — Revolving Credit Facility Maturity**

Unchanged from original draft.

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — revolving credit facility description paragraph (See LIQUIDITY.md → Section "Where it lives" → Item 2a (Revolving Credit Facility) — identical Debt Footnote location; extract same fields (commitment, drawn, letters of credit, maturity) |
| Available in | 10-K and 10-Q |
| Exact location | Revolving credit facility description paragraph. The maturity date is typically stated explicitly: "the revolving credit facility matures on [date]." |
| What LLM should extract | Maturity date of the revolving credit facility. This does not appear in the maturity schedule table because revolvers are not term debt — they are committed facilities with no scheduled principal amortisation. Store separately from the term debt maturity schedule. Flag if maturity within 18 months: "revolving credit facility maturing [date] — primary liquidity backstop at risk; renewal required." |

---

**Item 2c — Debt Covenant Acceleration Provisions**

Unchanged from original draft.

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — covenant description section AND credit agreement (Exhibit 10.x filed with the 10-K or 8-K) |
| Available in | 10-K primarily; updated in 10-Q if material changes |
| Exact location | Covenant section of the Debt Footnote. Look for language describing cross-default provisions, change of control provisions, and financial maintenance covenants whose breach triggers acceleration. |
| What LLM should extract | Three items: (1) whether cross-default provisions exist and which instruments they link, (2) whether change of control provisions exist and their terms, (3) whether any covenant breach has occurred or is disclosed. |
| Why this matters | Cross-default provisions convert a scheduled future maturity into a potentially immediate event — a covenant breach can accelerate debt due in years 3–5 into a year-1 equivalent obligation. |

---

**Formula 3 — Tranche-Level Analysis (LLM extraction)**

All four items unchanged from original draft.

**Item 3a — Individual Debt Tranche Descriptions**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — long-term debt summary table AND individual instrument descriptions |
| Available in | 10-K primarily; 10-Q includes current balances but less descriptive detail |
| Exact location | The Debt Footnote contains: (1) a summary table listing all outstanding instruments with carrying value, interest rate, and maturity; (2) descriptive paragraphs for each major instrument type. |
| What LLM should extract | For each instrument: principal amount, exact maturity date, coupon rate and type, instrument type, secured or unsecured status, callable status and call date if applicable. |

**Item 3b — Floating Rate Debt Reference Rate and Spread**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — individual instrument descriptions OR Note 1 (interest rate risk section) |
| Available in | 10-K and 10-Q |
| Exact location | Debt description specifies reference rate and spread: "SOFR plus 2.50%." Market risk footnote summarises total floating rate exposure. |
| What LLM should extract | For each floating rate tranche: reference rate, spread in basis points, any rate floor, current effective rate if disclosed. |

**Item 3c — Callable and Puttable Debt Features**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — individual instrument descriptions |
| Available in | 10-K primarily |
| Exact location | Call features: "the notes are callable at [price] on or after [date]." Put features: "holders may require the company to repurchase the notes at par upon [event]." |
| What LLM should extract | For callable instruments: first call date and call price. For puttable instruments: put date and put price. For convertible notes: conversion price, conversion date, and current stock price relative to conversion price. |

**Item 3d — New Debt Issuance Tenor (from 424B and 8-K Item 2.03)**

| Field | Detail |
|---|---|
| Where it lives | 424B prospectus filings AND 8-K Item 2.03 |
| Available in | Filed on pricing date (424B) or within 4 business days (Item 2.03) |
| Exact location | 424B cover page: principal amount, interest rate, maturity date in offering summary table. 8-K Item 2.03: maturity date in agreement description. |
| What LLM should extract | For each new issuance: principal amount, maturity date, coupon rate, instrument type. Used to compute new issuance tenor for refinancing tenor analysis. |

---

**Summary Table — Where Each Item Lives**

| Item | Formula | Statement / Document | Section | Structured or Unstructured | 10-K Only or Both |
|---|---|---|---|---|---|
| Current portion of LT debt | F1 | Balance Sheet | Current Liabilities | Structured — XBRL | Both |
| Short-term borrowings / CP | F1 | Balance Sheet | Current Liabilities | Structured — XBRL | Both |
| Cash & equivalents | F1 | Balance Sheet | Current Assets | Structured — XBRL | Both |
| Short-term investments | F1 | Balance Sheet | Current Assets | Structured — XBRL | Both |
| Debt maturity schedule Year 1–5 + thereafter | F2 | XBRL API + Debt Footnote | Maturity tags + maturity table | **Semi-structured — XBRL first, LLM fallback** | 10-K primarily; XBRL may update quarterly |
| Revolving credit facility maturity date | F2 | Debt Footnote | Facility description paragraph | Unstructured — LLM | Both |
| Covenant acceleration provisions | F2 | Debt Footnote + Exhibit 10.x | Covenant section + credit agreement | Unstructured — LLM | 10-K primarily |
| Individual tranche descriptions | F3 | Debt Footnote | Summary table + instrument paragraphs | Unstructured — LLM | 10-K primarily |
| Floating rate reference rate and spread | F3 | Debt Footnote + Note 1 | Instrument descriptions + market risk section | Unstructured — LLM | Both |
| Call and put features | F3 | Debt Footnote | Instrument description paragraphs | Unstructured — LLM | 10-K primarily |
| New issuance tenor | F3 | 424B + 8-K Item 2.03 | Cover page + filing text | Unstructured — LLM | Both (event-driven) |
| Cross-default provisions | F2 | Debt Footnote | Covenant section | Unstructured — LLM | 10-K primarily |

---

**Critical Note on 10-Q Maturity Schedule Availability**

The maturity schedule is the most analytically important item in this metric and the one with the most variable availability across filing types. The table below now reflects the corrected two-path extraction approach:

| Filing Type | XBRL Tag Availability | LLM Footnote Table Availability | System Action |
|---|---|---|---|
| 10-K | Tags present if company populates them — attempt first | Full five-year schedule always present | Attempt XBRL → reconcile → LLM for failures or gaps; store as annual baseline |
| 10-Q (Q1) | Tags may update quarterly for some filers — attempt | Usually absent | Attempt XBRL → if reconciled use; if not: use 10-K baseline adjusted for Q1 debt events |
| 10-Q (Q2) | Same as Q1 | Usually absent; more likely present if significant debt changes | Same as Q1 |
| 10-Q (Q3) | Same as Q1 | Usually absent | Same as Q1 |
| 8-K Item 2.03 | Not available | Not available — describes new debt event only | Extract new tranche details; patch into rolling maturity schedule |
| 424B | Not available | Not available — describes new issuance only | Extract new tranche; patch into rolling maturity schedule |

**Implication:** Between annual 10-K filings, the maturity schedule stored by your system is a living document that must be updated for debt events rather than replaced wholesale. The system maintains a rolling maturity schedule anchored to the most recent 10-K and patched with intra-year debt events. XBRL tags provide quarterly updates where companies populate them — use these as a lightweight refresh mechanism rather than waiting for the next 10-K. This is the most complex data maintenance requirement of any metric in the spec and represents the primary implementation challenge for the Debt Maturity Wall in Phase 3.

**Key change from original draft summarised:** Item 2a classification changed from "unstructured — LLM only" to "semi-structured — XBRL first with mandatory reconciliation check, LLM fallback." All other items unchanged. The Summary Table and the 10-Q Availability Table have been updated to reflect this reclassification.


## Structured or Unstructured — Debt Maturity Wall Metric (All Three Formulas)

| Input / Component | Formula | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|---|
| **Current Portion of LT Debt** | F1 | Primary: `us-gaap:LongTermDebtCurrent` Fallback: `us-gaap:DebtCurrent` | Structured — with double-count risk | See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 2 (Current Portion of Long-Term Debt) — apply identical double-count check before summing with short-term borrowings. `DebtCurrent` may aggregate short-term borrowings already captured separately — check for overlap before summing. Represents only the Year 1 component of the maturity wall visible from balance sheet XBRL. |
| **Short-Term Borrowings** | F1 | Primary: `us-gaap:ShortTermBorrowings` Fallback 1: `us-gaap:CommercialPaper` Fallback 2: `us-gaap:NotesPayableCurrent` Fallback 3: `us-gaap:LineOfCreditCurrent` | Structured — must sum all non-null values | Same Apple validation finding applies — sum all non-null tags; not mutually exclusive. Commercial paper and drawn revolver can coexist. |
| **Cash & Equivalents** | F1 | Primary: `us-gaap:CashAndCashEquivalentsAtCarryingValue` Fallback 1: `us-gaap:CashCashEquivalentsAndShortTermInvestments` Fallback 2: `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | Structured — with restriction risk | See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 5 (Unrestricted Cash) — apply identical three-step fallback chain including restriction check. Fallback 2 includes restricted cash — subtract `us-gaap:RestrictedCashAndCashEquivalents` if available; flag if not. |
| **Short-Term Investments** | F1 | Primary: `us-gaap:ShortTermInvestments` Fallback: `us-gaap:MarketableSecuritiesCurrent` | Structured — with bundling risk | Check for overlap with cash tag. If `CashCashEquivalentsAndShortTermInvestments` was used for cash, do not add short-term investments separately. |
| **Near-Term Maturity Total** (derived F1) | F1 | No standard tag | Structured inputs, derived result | = LongTermDebtCurrent + ShortTermBorrowings + CommercialPaper (sum all non-null). Represents Year 1 maturity wall only. If all components null → Near-Term Maturity = null → Maturity Coverage Ratio = null. |
| **Maturity Coverage Ratio** (derived F1) | F1 | No standard tag | Structured inputs, derived result | = (Cash + ShortTermInvestments) / Near-Term Maturity. Phase 2 cash only — revolver excluded; flag. Phase 3 adds revolver from LLM. If Near-Term Maturity = 0: ratio = undefined — flag as "no near-term debt maturities; maturity coverage adequate by definition." If Near-Term Maturity null → ratio null. |
| **Year 1 Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths` | **Semi-structured — XBRL first, LLM fallback** | Attempt XBRL tag first. If null or fails reconciliation: escalate to LLM extraction from Debt Footnote maturity table. Note: this tag covers term debt maturities only — it may differ from `LongTermDebtCurrent` on the balance sheet because the balance sheet current portion includes all short-term debt reclassifications while this tag covers only scheduled principal repayments. Cross-check both and flag discrepancies. |
| **Year 2 Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo` | **Semi-structured — XBRL first, LLM fallback** | Same extraction approach as Year 1. Not available from balance sheet — only from XBRL maturity tag or Debt Footnote. If null after XBRL attempt: LLM extraction required. |
| **Year 3 Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree` | **Semi-structured — XBRL first, LLM fallback** | Same as Year 2. |
| **Year 4 Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour` | **Semi-structured — XBRL first, LLM fallback** | Same as Year 2. |
| **Year 5 Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive` | **Semi-structured — XBRL first, LLM fallback** | Same as Year 2. |
| **Thereafter Maturity** | F2 | Primary: `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive` | **Semi-structured — XBRL first, LLM fallback** | Same as Year 2. Represents aggregate of all maturities beyond year 5 — not individually year-by-year. |
| **Maturity Schedule Reconciliation** (derived F2) | F2 | No standard tag | Structured inputs, derived verification | Sum of six maturity tags must reconcile to total debt within 5% tolerance. If reconciliation fails: escalate all years to LLM. If reconciliation passes: use XBRL tags as authoritative; store LLM extraction as verification only. This check is mandatory before any maturity schedule is used for alert computation. |
| **Maturity Concentration Ratio** (derived F2) | F2 | No standard tag | Structured inputs, derived result | = Maturities in year n / Total Debt. Computed for each year once schedule is established. Flag if any single year > 30% of total debt. Flag if > 50% as severe concentration. |
| **Near-Term Ratio** (derived F2) | F2 | No standard tag | Structured inputs, derived result | = (Year 1 + Year 2) / Total Debt. Flag if > 40%. |
| **Weighted Average Debt Maturity** (derived F2) | F2 | No standard tag | Structured inputs, derived result | = Σ (Year n Maturity × Years to Maturity n) / Total Debt. Uses convention: Year 1=1.0, Year 2=2.0, Year 3=3.0, Year 4=4.0, Year 5=5.0, Thereafter=7.0. Flag if WADM < 3.0 years. Flag if WADM declining across consecutive annual filings. |
| **Liquidity-to-Maturity Coverage** (derived F2) | F2 | No standard tag | Semi-structured inputs, derived result | Full Coverage = Available Liquidity (cash + revolver) / Year 1 Maturities. Extended Coverage = (Available Liquidity + Projected Annual FCF) / (Year 1 + Year 2 Maturities). Revolver component requires LLM extraction (Phase 3). See FREE_CASH_FLOW.md → Section "Formula" → Output 1 (FCF absolute) — use stored quarterly FCF and annualised run-rate values. Flag if Full Coverage < 1.0x. |
| **Revolving Credit Facility Maturity Date** | F2 | No standard tag | **Unstructured — LLM required** | Lives in Debt Footnote revolving credit facility description paragraph. LLM extracts maturity date — store as date field not dollar amount. Critical: revolver maturing within 18 months triggers flag regardless of other metrics. Revolvers do not appear in the standard maturity schedule table — must be tracked separately. |
| **Covenant Acceleration Provisions** | F2 | No standard tag | **Unstructured — LLM required** | Lives in Debt Footnote covenant section and Exhibit 10.x credit agreement. LLM extracts: (1) cross-default provisions, (2) change of control provisions, (3) any disclosed covenant breach. Output is structured flags (true/false + description), not dollar amounts. A disclosed covenant breach is an automatic escalation trigger regardless of maturity schedule. |
| **Individual Tranche Descriptions** | F3 | No standard tag at tranche level | **Unstructured — LLM required** | Lives in Debt Footnote summary table and instrument description paragraphs. LLM extracts per-tranche: principal, exact maturity date, coupon rate, coupon type, instrument type, secured status, callable status. Most analytically granular extraction in this metric. |
| **Floating Rate Reference Rate and Spread** | F3 | No standard tag | **Unstructured — LLM required** | Lives in Debt Footnote instrument descriptions and Note 1 market risk section. LLM extracts: reference rate (SOFR, EURIBOR), spread in basis points, rate floor if any, current effective rate. Used for interest rate sensitivity analysis alongside maturity timing. |
| **Call and Put Features** | F3 | No standard tag | **Unstructured — LLM required** | Lives in Debt Footnote instrument description paragraphs. LLM extracts: first call date and price, put date and price, convertible note conversion price and date. Put dates are economic maturities not shown in standard maturity table — must be tracked as contingent maturity obligations. |
| **Projected Interest Rate Reset Impact** (derived F3) | F3 | No standard tag | Unstructured inputs + external market data, derived result | Requires: tranche-level coupon data (LLM), current market spreads (external data not from filing), current EBITDA and interest expense (from Leverage and Coverage metrics). Computes projected coverage compression from refinancing at current market rates. Phase 3 enhancement requiring external data integration. |
| **New Issuance Tenor** | F3 | No standard tag | **Unstructured — LLM required** | Lives in 424B cover page and 8-K Item 2.03 filing text. LLM extracts: principal, maturity date, coupon rate, instrument type for each new issuance. Stored in separate new issuance log; reconciled to maturity schedule at each 10-K. |
| **Refinancing Tenor Trend** (derived F3) | F3 | No standard tag | Unstructured inputs, derived result | = Weighted average tenor of new issuances vs weighted average remaining maturity of retired debt over trailing four quarters. Declining trend signals lender confidence deterioration. Requires new issuance log (from 424B + Item 2.03) and retirement log (from principal repayments in cash flow statement). |

---

**Quick Reference — Structured vs Unstructured by Formula**

| | F1 — Baseline | F2 — Full Schedule | F3 — Tranche Level |
|---|---|---|---|
| **Fully structured (XBRL)** | Current LT debt, short-term borrowings, CP, cash, short-term investments | Inherits F1 structured items | Inherits F1 and F2 structured items |
| **Semi-structured (XBRL first, LLM fallback)** | None | Year 1–5 maturity tags + Thereafter tag (with mandatory reconciliation check) | Inherits F2 semi-structured items |
| **Fully unstructured (LLM required)** | None | Revolver maturity date, covenant acceleration provisions | Tranche descriptions, coupon details, call/put features, new issuance tenor |
| **Derived — structured inputs** | Near-term maturity total, maturity coverage ratio (Phase 2 partial) | Concentration ratio, near-term ratio, WADM, liquidity-to-maturity coverage | Refinancing tenor trend |
| **Derived — requires external data** | None | None | Interest rate reset impact (requires current market spreads) |
| **LLM needed?** | ❌ No (Phase 2 revolver excluded) | ✅ Yes (revolver, covenants, fallback for XBRL gaps) | ✅ Yes (extensive) |
| **Phase** | Phase 2 | Phase 3 | Phase 3 |

---

**Key Difference From Prior Metrics**

All prior metrics in this spec are fully structured at Formula 1 level and introduce LLM requirements only at Formula 2 and Formula 3. The Debt Maturity Wall introduces semi-structured extraction at Formula 2 — XBRL tags exist for individual year maturities but adoption is inconsistent, making the mandatory reconciliation check a prerequisite for any maturity schedule computation. This is unique to this metric and must be reflected in the Phase 3 implementation architecture: the system needs both an XBRL extraction path and an LLM extraction path running in parallel, with the reconciliation check determining which result is used.

## Extraction Fallback Logic — Debt Maturity Wall Metric

---

### Design Principles

Same four rules as prior metrics apply, plus four additional rules specific to the Debt Maturity Wall:

**Rule 1 — Never substitute zero for a missing input.** A missing Year 3 maturity tag does not mean no debt matures in Year 3. Mark null and escalate to LLM.

**Rule 2 — Try every fallback before giving up.** Attempt XBRL extraction before LLM. Attempt LLM before declaring failure.

**Rule 3 — Log what you used.** Every maturity figure records whether it came from XBRL, LLM, or derivation — and which specific tag or footnote location was the source.

**Rule 4 — Never compute ratios from a non-reconciled schedule.** If the maturity schedule does not reconcile to total debt within 5%, do not use it for alert computation until the discrepancy is resolved. A silently wrong maturity schedule is more dangerous than a null one.

**Rule 5 — The maturity schedule is a living document, not a snapshot.** Between 10-K filings, the system patches the stored schedule with debt events. Each patch must be logged with its source filing date and accession number. The schedule's provenance — which 10-K it was anchored to, which events have patched it since — must be stored alongside the schedule itself.

**Rule 6 — XBRL and LLM paths run in parallel for Formula 2.** Unlike prior metrics where XBRL is primary and LLM is a fallback triggered only by XBRL failure, the Debt Maturity Wall requires both paths to be attempted and their results compared. Reconciliation determines which is used — not which path succeeded first.

**Rule 7 — Year-specific null is different from full schedule null.** A single missing year (e.g. Year 3 tag absent) is less severe than a fully absent schedule. The system must handle partial schedule extraction — using XBRL for populated years and LLM for missing years — and re-verify reconciliation after combining.

**Rule 8 — Covenant breach disclosure overrides all maturity schedule computations.** If a covenant breach is disclosed in the filing, the effective maturity wall may be zero quarters away regardless of what the schedule shows. Covenant breach detection runs independently of and takes priority over maturity schedule extraction.

---

### Component 1 — Formula 1 Inputs (Balance Sheet)

See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 1 through Input 3 (Short-Term Borrowings, Current LT Debt, Long-Term Debt) and LIQUIDITY.md → Section "Extraction Fallback Logic" → Input 5 (Cash) — apply identical fallback chains for all four inputs. Summarised here for completeness with cross-references.

**Current Portion of LT Debt:**
```
Step 1: us-gaap:LongTermDebtCurrent
Step 2: us-gaap:DebtCurrent
        (double-count check — may include short-term
        borrowings; verify before summing)
Step 3: us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent
        (flag: may include finance leases)
Step 4: null → flag → escalate to manual review
```

**Short-Term Borrowings / Commercial Paper:**
```
Step 1: us-gaap:ShortTermBorrowings
Step 2: us-gaap:CommercialPaper
Step 3: us-gaap:NotesPayableCurrent
Step 4: us-gaap:LineOfCreditCurrent
Sum all non-null — not mutually exclusive
If all null: ShortTermDebt = null; flag
```

**Cash and Short-Term Investments:**
Same as Leverage Formula 1 fallback chain. Refer to that section. Restriction check applies.

**Near-Term Maturity Total:**
```
= LongTermDebtCurrent + ShortTermBorrowings + CP
If LongTermDebtCurrent null:
   Near-Term Maturity = short-term components only
   Flag: "current LT debt absent — near-term
   maturity may be understated; Year 1 XBRL
   tag or LLM extraction recommended"
If all null: Near-Term Maturity = null
```

---

### Component 2 — Formula 2 Maturity Schedule (Semi-Structured)

This is the most complex fallback chain in the entire spec. It runs two paths simultaneously and uses reconciliation to determine the final result.

---

#### Path A — XBRL Extraction

```
Step A1 — Query all six maturity tags via EDGAR
           companyconcept API:

           Year1 = LongTermDebtMaturities
                   RepaymentsOfPrincipalInNextTwelveMonths
           Year2 = LongTermDebtMaturities
                   RepaymentsOfPrincipalInYearTwo
           Year3 = LongTermDebtMaturities
                   RepaymentsOfPrincipalInYearThree
           Year4 = LongTermDebtMaturities
                   RepaymentsOfPrincipalInYearFour
           Year5 = LongTermDebtMaturities
                   RepaymentsOfPrincipalInYearFive
           After = LongTermDebtMaturities
                   RepaymentsOfPrincipalAfterYearFive

           Use period context matching filing date to
           ensure correct reporting period is extracted.
           EDGAR companyconcept API returns multiple
           periods — select the one matching the
           current filing's period end date.

Step A2 — Record which tags returned values
           and which returned null:
           XBRL_populated = [list of years with values]
           XBRL_null = [list of years with null]

Step A3 — If XBRL_null is empty (all six populated):
           Proceed to reconciliation check (Step A4)
           If XBRL_null is not empty (partial):
           Flag: "XBRL maturity tags partially
           populated — Years [X] absent;
           proceeding to LLM for missing years"
           Proceed to Path B for missing years only
           Combine XBRL and LLM results before
           reconciliation

Step A4 — Reconciliation check (mandatory):
           XBRL_Sum = Year1+Year2+Year3+Year4+Year5+After
           Total_Debt = us-gaap:LongTermDebt
                     OR us-gaap:DebtAndCapitalLeaseObligations

           Tolerance = 5% of Total_Debt

           If abs(XBRL_Sum - Total_Debt) <= Tolerance:
              RECONCILED = true
              Flag: "maturity schedule reconciled via
              XBRL — sum within 5% of total debt"
              Use XBRL as primary schedule

           If abs(XBRL_Sum - Total_Debt) > Tolerance:
              RECONCILED = false
              Flag: "XBRL maturity tags do not reconcile
              to total debt — discrepancy of $X million
              ([Y]% of total debt); escalating to LLM
              for full schedule extraction"
              Proceed to Path B for full extraction
              Do NOT use XBRL schedule for alerts
              until reconciliation is resolved
```

---

#### Path B — LLM Extraction

```
Step B1 — LLM reads Debt Footnote maturity table.
           Target table titles:
           "Maturities of Long-Term Debt"
           "Scheduled Debt Maturities"
           "Future Principal Payments"
           "Aggregate Annual Maturities"
           "Long-Term Debt Maturities"

Step B2 — LLM extracts six figures:
           Year 1 through Year 5 and Thereafter
           Also extracts the total row if present.
           Returns structured JSON:
           {
             "year1": X,
             "year2": X,
             "year3": X,
             "year4": X,
             "year5": X,
             "thereafter": X,
             "total_per_table": X,
             "source_quote": "[verbatim table header
                              and first row from filing]",
             "fiscal_year_end_date": "YYYY-MM-DD",
             "confidence": "high/medium/low"
           }

Step B3 — LLM reconciliation check:
           If table includes a total row:
              Verify: Year1+Year2+Year3+Year4+Year5
                      +After ≈ total_per_table
              If mismatch: flag "table internal
              inconsistency — verify LLM extraction"
           Compare LLM_Sum to Total_Debt (same
           tolerance as Path A — 5%)
           If reconciled: flag "maturity schedule
           reconciled via LLM extraction"
           If not reconciled: flag discrepancy and
           reason if identifiable (e.g. "finance
           leases may be included in debt total
           but excluded from maturity table")

Step B4 — LLM confidence handling:
           If confidence = "low":
              Flag: "LLM extraction low confidence —
              table format may be non-standard;
              manual verification recommended"
              Store result but do not trigger alerts
              based on this schedule alone

Step B5 — If LLM cannot find maturity table:
           Set LLM_Schedule = null
           Flag: "maturity table not found in
           Debt Footnote — verify filing structure;
           check if company uses alternative
           disclosure format"
           Attempt: search other footnotes
           (Note 1 accounting policies,
           Commitments and Contingencies note)
           for maturity information
```

---

#### Path C — Combined Result

```
Step C1 — Determine which path(s) succeeded:

Case 1: XBRL reconciled AND LLM reconciled:
   Primary: XBRL schedule
   Verification: LLM schedule
   If XBRL and LLM agree within 5% per year:
      Use XBRL as final schedule
      Flag: "dual-path verification passed —
      XBRL and LLM schedules consistent"
   If XBRL and LLM disagree by >5% for any year:
      Flag: "XBRL and LLM schedules diverge for
      Year [N] — XBRL: $X, LLM: $Y; manual
      review required; using LLM as conservative
      estimate pending resolution"
      Use higher of the two for alert computation
      (conservative approach)

Case 2: XBRL not reconciled, LLM reconciled:
   Use LLM schedule as primary
   Flag: "XBRL maturity tags failed reconciliation;
   LLM schedule used as primary"

Case 3: XBRL reconciled, LLM not run or failed:
   Use XBRL schedule as primary
   Flag: "maturity schedule from XBRL only —
   LLM verification not available"

Case 4: XBRL partial (some years populated),
        LLM fills missing years:
   Combine: XBRL years where populated,
            LLM years where XBRL was null
   Re-run reconciliation on combined schedule
   If combined schedule reconciles: use it
   Flag: "hybrid schedule — XBRL Years [X],
   LLM Years [Y]"
   If combined schedule still does not reconcile:
   Proceed to Case 5

Case 5: Neither path reconciles:
   Use best available schedule with heavy flagging
   Flag: "maturity schedule unreconciled —
   total discrepancy $X million; schedule
   used for directional analysis only;
   do NOT trigger automated alerts based
   on this schedule; manual review required"
   Escalate to analyst immediately

Case 6: Both paths completely failed:
   Schedule = null
   Flag: "maturity schedule extraction complete
   failure — neither XBRL nor LLM produced
   usable data; manual review required"
   Formula 2 derived outputs = null
   Revert to Formula 1 (balance sheet current
   portion only) for all alert computation
```

---

### Component 3 — Revolving Credit Facility Maturity (LLM)

```
Step 1 — LLM reads Debt Footnote revolving credit
          facility description paragraph.
          Extract maturity date as YYYY-MM-DD.

Step 2 — Verify against MD&A Liquidity section:
          MD&A often restates revolver maturity.
          If dates conflict: use earlier date
          (conservative) and flag discrepancy.

Step 3 — Compute days to revolver maturity:
          Days = target_date - filing_date

Step 4 — Alert thresholds:
          > 548 days (18 months): no alert
          365–548 days (12–18 months): Watch
          < 365 days (12 months): Flag —
          "revolving credit facility matures
          within 12 months — primary liquidity
          backstop at risk; renewal required"

Step 5 — If LLM cannot find revolver maturity:
          Set Revolver_Maturity = null
          Flag: "revolving credit facility maturity
          not found — verify whether company has
          a committed revolving facility"
          Check balance sheet for drawn revolver
          (LineOfCreditCurrent or ShortTermBorrowings)
          If drawn amount present but maturity absent:
          Flag: "revolver drawn but maturity date
          not extracted — escalate to manual review"
```

---

### Component 4 — Covenant Acceleration Provisions (LLM)

```
Step 1 — LLM reads Debt Footnote covenant section.
          Target language:
          "cross-default"
          "event of default"
          "acceleration"
          "change of control"
          "covenant breach"
          "waiver"
          "amendment"

Step 2 — LLM extracts three binary flags
          plus description:
          {
            "cross_default_exists": true/false,
            "cross_default_description": "text",
            "change_of_control_exists": true/false,
            "change_of_control_description": "text",
            "covenant_breach_disclosed": true/false,
            "covenant_breach_description": "text",
            "waiver_obtained": true/false,
            "waiver_description": "text"
          }

Step 3 — Covenant breach handling:
          If covenant_breach_disclosed = true:
             IMMEDIATE CRITICAL ALERT
             Flag: "covenant breach disclosed in
             filing — debt may be subject to
             acceleration; effective maturity
             wall may be immediate regardless
             of scheduled maturities"
             Override maturity schedule alerts
             with Critical classification
             Cross-reference Covenant Headroom
             metric for additional detail

Step 4 — If LLM cannot find covenant section:
          Set all flags = null
          Flag: "covenant section not extracted —
          acceleration risk unknown; manual
          review recommended for leveraged issuers"
          This is not a benign null — for high-yield
          and leveraged issuers, covenant absence
          from extraction is an escalation trigger
```

---

### Component 5 — Rolling Maturity Schedule Maintenance

This component has no equivalent in any prior metric. It governs how the stored maturity schedule is updated between annual 10-K filings.

```
Trigger: New debt event detected (8-K Item 2.03,
         424B, 8-K Item 1.01 credit facility
         amendment, cash flow statement repayment)

Step 1 — Identify event type:
          New issuance: adds to future maturity year
          Repayment: subtracts from maturity year
          Amendment: may change maturity date of
                     existing tranche
          Refinancing: removes old maturity,
                       adds new maturity

Step 2 — LLM extracts from triggering filing:
          New issuance (424B / Item 2.03):
             Principal amount
             Maturity date → map to fiscal year
             Coupon rate and type
          Repayment (cash flow or Item 8.01):
             Amount repaid
             Instrument repaid (if identifiable)
          Amendment (Item 1.01):
             Original maturity date
             New maturity date
             Principal amount affected

Step 3 — Update rolling schedule:
          Patched_Schedule[affected_year] =
             Prior_Schedule[affected_year]
             + New_Issuance (if applicable)
             - Repayment (if applicable)
          Store patch with metadata:
          {
            "patch_date": "YYYY-MM-DD",
            "patch_source": "8-K accession number
                            or 424B accession number",
            "event_type": "issuance/repayment/
                           amendment/refinancing",
            "year_affected": N,
            "amount_change": +/- $X million
          }

Step 4 — Re-run reconciliation after each patch:
          Patched_Sum vs Total_Debt
          (Total_Debt also updated from Item 2.03
          or balance sheet if new filing available)
          If reconciliation fails after patch:
          Flag: "rolling schedule reconciliation
          failure after [event type] on [date] —
          manual review required"

Step 5 — At next 10-K filing:
          Replace rolling schedule with fresh
          10-K extraction (XBRL + LLM)
          Reconcile fresh schedule against
          accumulated patches — discrepancy
          indicates a debt event was missed
          Flag if fresh 10-K schedule differs
          from patched schedule by >5%:
          "maturity schedule gap detected —
          10-K schedule differs from rolling
          patched schedule by $X million;
          review missed debt events between
          [prior 10-K date] and [current 10-K date]"
```

---

### Cross-Level Validation Rules

**Check 1 — Year 1 XBRL tag vs balance sheet current portion**
```
Year1_XBRL = LongTermDebtMaturitiesRepaymentsOf
             PrincipalInNextTwelveMonths
Balance_Sheet_Current = LongTermDebtCurrent

These two figures may legitimately differ because:
— Balance sheet current portion includes ALL current
  financial debt (short-term borrowings, CP)
— Year 1 XBRL tag covers only scheduled LT debt
  principal repayments

Expected: Year1_XBRL ≤ Balance_Sheet_Current
If Year1_XBRL > Balance_Sheet_Current:
   Flag: "Year 1 maturity tag exceeds balance
   sheet current portion — possible tagging
   inconsistency; verify which figure is correct"
   This is a genuine red flag — it should not occur
   in a well-tagged filing
```

**Check 2 — WADM trend check**
```
Compute WADM for current period and prior two
annual periods (from stored 10-K schedule history)

If WADM declines for two consecutive annual periods:
   Watch alert — maturity wall compressing
If WADM declines for three consecutive annual periods:
   Flag alert — sustained compression trend
If WADM < 2.0 years:
   Stress alert — very near-term maturity concentration
   regardless of trend
```

**Check 3 — Near-term concentration sudden change**
```
Compare Year 1 maturity to prior quarter Year 1
maturity (after adjusting for repayments):

If Year 1 increases by > 20% quarter-over-quarter
(not explained by a known new maturity entering
the 12-month window):
   Flag: "Year 1 maturity increased significantly —
   verify whether new debt has been reclassified
   to current or whether a debt event was missed"
```

**Check 4 — Thereafter bucket concentration**
```
If Thereafter / Total Debt > 60%:
   No alert — well-laddered structure
If Thereafter / Total Debt < 20% AND
   WADM < 3.0 years:
   Flag: "very little debt beyond year 5 —
   entire debt stack concentrated in near-term;
   refinancing risk elevated"
```

**Check 5 — Revolver maturity vs term debt maturity alignment**
```
If any term debt maturity occurs AFTER revolver
maturity date:
   Flag: "term debt matures after revolving credit
   facility expiry — revolver renewal is a
   prerequisite for refinancing term maturities;
   elevated refinancing risk if revolver not renewed"
```

---

### Audit Log Output Format (per company, per period)

```
{
  "ticker": "RAD",
  "period": "2023-03-04",
  "filing": "10-K",
  "schedule_anchor": "10-K 2023-03-04",
  "patches_applied": [],

  "formula_1": {
    "current_lt_debt": {
      "value": 166.5,
      "tag": "us-gaap:LongTermDebtCurrent",
      "path": "primary"
    },
    "short_term_borrowings": {
      "value": 0,
      "tag": "us-gaap:ShortTermBorrowings",
      "path": "primary"
    },
    "near_term_maturity_total": 166.5,
    "cash": 188.4,
    "maturity_coverage_ratio_partial": 1.13,
    "flags": ["revolver excluded — Phase 2"]
  },

  "formula_2": {
    "xbrl_extraction": {
      "year1": 166.5,
      "year2": 500.0,
      "year3": 800.0,
      "year4": 0,
      "year5": 1200.0,
      "thereafter": 800.0,
      "xbrl_sum": 3466.5,
      "total_debt": 3450.0,
      "reconciled": true,
      "discrepancy_pct": 0.48
    },
    "llm_extraction": {
      "year1": 166.5,
      "year2": 500.0,
      "year3": 800.0,
      "year4": 0,
      "year5": 1200.0,
      "thereafter": 800.0,
      "llm_sum": 3466.5,
      "reconciled": true,
      "confidence": "high",
      "source": "Note 7 — Long-Term Debt,
                 Maturities table"
    },
    "dual_path_agreement": true,
    "final_schedule": {
      "year1": 166.5,
      "year2": 500.0,
      "year3": 800.0,
      "year4": 0,
      "year5": 1200.0,
      "thereafter": 800.0,
      "source": "XBRL (verified by LLM)"
    },
    "derived": {
      "wadm": 3.8,
      "near_term_ratio": 0.193,
      "concentration_max_year": "year5 — 34.7%",
      "liquidity_to_maturity_coverage": 1.13
    },
    "revolver_maturity": {
      "date": "2025-01-31",
      "days_to_maturity": 333,
      "flag": "revolving credit facility matures
               within 12 months — Watch alert"
    },
    "covenant_flags": {
      "cross_default_exists": true,
      "covenant_breach_disclosed": false,
      "waiver_obtained": false
    }
  },

  "alerts": [
    "WATCH — revolver matures within 12 months",
    "WATCH — WADM 3.8 years; monitor for decline",
    "FLAG — Year 5 concentration 34.7% exceeds 30% threshold"
  ],

  "warnings": [
    "Year 4 maturity = 0 — verify no debt due in
     fiscal year 4; confirm with LLM extraction"
  ],

  "nulls": []
}
```

## Stress Threshold — Debt Maturity Wall

---

### Structural Difference From Prior Metrics

All prior metrics produce ratios that can be compared to published threshold tables or market convention bands. The Debt Maturity Wall is fundamentally different in three ways that require a different threshold framework.

**First difference — no single universal threshold table exists.** S&P and Moody's assess maturity profiles as part of their liquidity descriptor and SGL rating frameworks rather than as standalone ratio thresholds. There is no equivalent of Tables 4.7–4.9 for maturity concentration. The thresholds below are derived from rating agency methodology commentary, leveraged finance market convention, and empirical default research rather than a single published table.

**Second difference — the metric has multiple outputs requiring separate thresholds.** Unlike leverage which produces one ratio, the maturity wall produces a schedule, four derived ratios, and several binary flags. Each requires its own threshold logic. The combined alert level is determined by the most severe signal across all outputs.

**Third difference — time is the primary variable.** The same maturity amount is more or less alarming depending on how far away it is. Threshold logic must incorporate the time dimension — not just the size of the maturity but the number of days until it arrives.

---

### Threshold Dimension 1 — Near-Term Maturity Coverage Ratio (Formula 1)

This is the only maturity wall output computable in Phase 2. It measures whether available cash covers debt due within 12 months.

Source: Moody's SGL framework and S&P liquidity descriptor methodology — both treat near-term maturity coverage as a primary quantitative input to liquidity assessment.

| Near-Term Maturity Coverage (cash only — Phase 2) | Interpretation | Alert Level |
|---|---|---|
| ≥ 3.0x | Cash covers near-term maturities three times over | No alert |
| 2.0x – 3.0x | Comfortable cash coverage | No alert — monitor trend |
| 1.5x – 2.0x | Adequate — limited buffer | Watch |
| 1.0x – 1.5x | Thin — cash barely covers near-term debt | Flag |
| 0.5x – 1.0x | Insufficient — cash cannot cover near-term debt | Stress |
| < 0.5x | Severely insufficient | Critical |

| Near-Term Maturity Coverage (cash + revolver — Phase 3) | Interpretation | Alert Level |
|---|---|---|
| ≥ 2.0x | Strong liquidity relative to near-term obligations | No alert |
| 1.5x – 2.0x | Adequate | Watch |
| 1.2x – 1.5x | Below adequate | Flag |
| 1.0x – 1.2x | Thin — total liquidity barely covers maturities | Stress |
| < 1.0x | Total liquidity insufficient to cover near-term debt | Critical |

**Phase 2 flag on all outputs:** All near-term maturity coverage alerts generated in Phase 2 must note: "alert based on cash only — revolver excluded; actual coverage may be higher; verify revolver availability before escalating." Do not suppress the alert but note the limitation on every output.

---

### Threshold Dimension 2 — Days to Nearest Maturity (Formula 3, Phase 3)

Source: Leveraged finance market convention. The number of days before a maturity is not actionable alone — it must be combined with the company's refinancing capacity. The thresholds below reflect the typical window within which companies must complete a refinancing to avoid a distressed situation.

| Days to Nearest Material Maturity | Interpretation | Alert Level |
|---|---|---|
| > 730 days (> 2 years) | Ample time for proactive refinancing | No alert |
| 548 – 730 days (18–24 months) | Refinancing planning should begin | Watch |
| 365 – 548 days (12–18 months) | Refinancing window narrowing — execution required | Flag |
| 180 – 365 days (6–12 months) | Refinancing must be underway or completed | Stress |
| 90 – 180 days (3–6 months) | Imminent — refinancing or repayment must be confirmed | Critical |
| < 90 days | Near-default unless refinancing or cash repayment confirmed | Critical — highest urgency |

**Materiality threshold:** Apply these thresholds only when the maturing tranche exceeds the lower of: (a) $50M, or (b) 5% of total debt. Small maturities below this threshold do not trigger the days-to-maturity alert regardless of proximity.

**Combination rule:** Days to nearest maturity alerts are escalated one level when combined with a Stress or Critical alert on leverage or coverage. A company with a 270-day maturity (Stress level) that is also in the Highly Leveraged band on leverage should be treated as Critical — its ability to refinance is compromised by its credit quality.

---

### Threshold Dimension 3 — Maturity Concentration Ratio (Formula 2)

Source: Empirical default research. Studies of leveraged loan and high-yield bond defaults consistently identify concentration of maturities as an independent predictor of refinancing failure. Moody's guidance notes that a maturity wall concentrated in a single year is a negative factor in liquidity assessment regardless of the absolute amount.

| Single-Year Concentration (any year in Years 1–5) | Interpretation | Alert Level |
|---|---|---|
| < 20% of total debt | Well-distributed — no concentration concern | No alert |
| 20% – 30% | Moderate concentration — monitor | Watch |
| 30% – 40% | Elevated concentration | Flag |
| 40% – 50% | High concentration — refinancing event risk | Stress |
| > 50% | Severe concentration — single-year refinancing risk | Critical |

**Year proximity adjustment:** Apply the following multiplier to concentration thresholds based on which year the concentration falls in. The same concentration is more alarming in Year 1 than in Year 5.

| Year of Concentration | Threshold Adjustment | Effect |
|---|---|---|
| Year 1 | Reduce all thresholds by 10 percentage points | 20% → Flag; 30% → Stress; 40% → Critical |
| Year 2 | Reduce all thresholds by 5 percentage points | 25% → Flag; 35% → Stress; 45% → Critical |
| Year 3 | Standard thresholds apply | As per table above |
| Year 4 | Increase all thresholds by 5 percentage points | 35% → Flag; 45% → Stress; 55% → Critical |
| Year 5 | Increase all thresholds by 10 percentage points | 40% → Flag; 50% → Stress; 60% → Critical |

**Rationale:** A 35% concentration in Year 1 is a near-term crisis. The same concentration in Year 5 is a future planning item. Adjusting thresholds by proximity reflects this reality without requiring separate tables for each year.

---

### Threshold Dimension 4 — Near-Term Ratio (Formula 2)

Source: S&P liquidity descriptor methodology — the Year 1 plus Year 2 maturity relative to total debt is a direct input to the sources-and-uses assessment.

| Near-Term Ratio (Year 1 + Year 2 / Total Debt) | Interpretation | Alert Level |
|---|---|---|
| < 15% | Low near-term refinancing burden | No alert |
| 15% – 25% | Moderate — manageable with normal market access | Watch |
| 25% – 40% | Elevated — meaningful refinancing requirement | Flag |
| 40% – 55% | High — significant near-term wall | Stress |
| > 55% | Severe — majority of debt stack matures within 2 years | Critical |

---

### Threshold Dimension 5 — Weighted Average Debt Maturity (Formula 2)

Source: Moody's and S&P both reference average debt maturity in liquidity commentary. No single published table — the ranges below reflect investment-grade and high-yield market norms.

| WADM | Interpretation | Alert Level |
|---|---|---|
| ≥ 7 years | Long-dated — minimal refinancing pressure | No alert |
| 5 – 7 years | Adequate — normal investment-grade range | No alert |
| 4 – 5 years | Below average — moderate refinancing pressure | Watch |
| 3 – 4 years | Short — elevated refinancing pressure | Flag |
| 2 – 3 years | Very short — significant near-term wall building | Stress |
| < 2 years | Critically short | Critical |

**WADM trend rule — more important than absolute level:**

| WADM Trend | Alert Level |
|---|---|
| WADM stable or increasing | No trend alert |
| WADM declining for 1 year | No alert — single data point |
| WADM declining for 2 consecutive annual periods | Watch — compression trend beginning |
| WADM declining for 3 consecutive annual periods | Flag — sustained compression |
| WADM declining for 4+ consecutive annual periods | Stress — persistent structural deterioration |
| WADM declining AND absolute WADM < 3 years | Escalate one level beyond trend-only alert |

---

### Threshold Dimension 6 — Revolving Credit Facility Maturity

Source: S&P liquidity descriptor framework — revolver maturity within 12 months is an explicit negative qualitative factor that reduces the liquidity descriptor regardless of other metrics.

| Days to Revolver Maturity | Interpretation | Alert Level |
|---|---|---|
| > 548 days (18+ months) | No near-term concern | No alert |
| 365 – 548 days (12–18 months) | Renewal planning required | Watch |
| 180 – 365 days (6–12 months) | Renewal must be in progress | Flag |
| < 180 days (< 6 months) | Renewal urgently required — liquidity at risk | Stress |
| < 90 days (< 3 months) without confirmed renewal | Primary liquidity backstop effectively gone | Critical |

**Interaction with coverage ratio:** If the revolver is maturing within 12 months AND it currently has drawn amounts outstanding: escalate the revolver maturity alert one level. A maturing revolver with outstanding borrowings requires both renewal of the facility AND refinancing of the drawn amount — a compounded liquidity requirement.

---

### Threshold Dimension 7 — Covenant Acceleration Flags (Binary)

These are binary triggers — either the condition is present or it is not. No graduated threshold applies.

| Condition | Alert Level | Action |
|---|---|---|
| Covenant breach disclosed | CRITICAL — immediate | Override all maturity schedule alerts; escalate regardless of schedule; cross-reference Covenant Headroom metric |
| Waiver obtained for disclosed breach | Stress — sustained | Breach occurred; waiver is temporary; underlying deterioration persists; monitor for breach recurrence |
| Cross-default provisions present AND leverage in Aggressive or Highly Leveraged band | Flag — elevated risk | Cross-default provisions make a potential covenant breach more systemic; flag the combination |
| Change of control provision present AND M&A activity rumoured or announced | Flag | Change of control event would make debt immediately due; monitor alongside news and 8-K filings |

---

### Threshold Dimension 8 — Interest Rate Reset Impact (Formula 3, Phase 3)

Source: Coverage metric thresholds — the interest rate reset is measured by its impact on the coverage ratio.

| Projected Coverage Compression from Reset | Interpretation | Alert Level |
|---|---|---|
| < 0.25x compression | Minimal reset impact | No alert |
| 0.25x – 0.5x compression | Moderate — coverage will tighten | Watch |
| 0.5x – 1.0x compression | Material — coverage meaningfully reduced | Flag |
| > 1.0x compression | Severe — reset materially impairs coverage | Stress |
| Reset causes coverage to cross a threshold band | Automatic escalation | Escalate to level implied by post-reset coverage band |

---

### Combined Alert Trigger Rules

The most severe alert across all eight dimensions governs the overall maturity wall alert level, subject to the combination rules below.

| Alert Level | Any of These Conditions | Action |
|---|---|---|
| **Watch** | Near-term coverage 1.5x–2.0x (Phase 2); OR concentration 20%–30% in Year 3–5; OR near-term ratio 15%–25%; OR WADM 4–5 years or declining 2 consecutive years; OR revolver maturity 365–548 days | Log; weekly review |
| **Flag** | Near-term coverage 1.0x–1.5x (Phase 2); OR concentration 30%–40% (adjusted by year proximity); OR near-term ratio 25%–40%; OR WADM 3–4 years or declining 3 consecutive years; OR revolver maturity 180–365 days; OR cross-default present + leverage stressed | Generate alert; daily monitoring |
| **Stress** | Near-term coverage 0.5x–1.0x (Phase 2); OR concentration 40%–50% (adjusted); OR near-term ratio 40%–55%; OR WADM 2–3 years or declining 4+ years; OR revolver maturity < 180 days; OR waiver obtained for disclosed breach; OR coverage compression > 1.0x from rate reset | Immediate alert; escalate same day |
| **Critical** | Near-term coverage < 0.5x; OR concentration > 50% (adjusted); OR near-term ratio > 55%; OR WADM < 2 years; OR revolver maturity < 90 days without renewal; OR covenant breach disclosed; OR days to nearest material maturity < 90 | Immediate escalation; cross-reference all metrics |
| **Trend Flag** | WADM declining consecutively regardless of absolute level; OR near-term ratio increasing for 3 consecutive quarters | Alert regardless of band |
| **Extraction Failure** | Schedule null after all fallbacks | Revert to Formula 1 only; escalate to manual review |

---

### Sector Exceptions and Adjustments

**Financial institutions:** Not applicable — same exception as all prior metrics. Banks and insurance companies manage maturity profiles under regulatory frameworks that render these thresholds meaningless.

**Utilities and regulated infrastructure:** These sectors routinely carry higher maturity concentration because their stable, regulated cash flows and strong credit quality enable reliable access to capital markets at any point in the cycle. Apply a 10 percentage point upward adjustment to all concentration thresholds for confirmed utility issuers.

**Investment-grade issuers with strong capital markets access:** For issuers rated BBB− or above with confirmed strong capital markets access (from S&P Strong or Exceptional liquidity descriptor), the near-term ratio and concentration thresholds can be relaxed by one alert level — an investment-grade issuer with 45% of debt maturing in Year 2 has materially lower effective refinancing risk than a high-yield issuer with the same profile. This adjustment requires Phase 3 LLM extraction of the S&P liquidity descriptor or rating confirmation — it is not applicable in Phase 2.

**Companies in active liability management:** Some companies deliberately run down their maturity wall through tender offers, open market repurchases, and exchange offers. A declining WADM accompanied by active liability management (visible in 424B and 8-K Item 2.03 filings showing new long-dated issuances and tender offer filings) should be assessed differently from a passive decline. Flag the trend but note the context: "WADM declining — consistent with active liability management programme; verify new issuance tenor is extending rather than compressing the wall."

---

### Empirical Context and Backtest Anchor

**Historical reference — Rite Aid:**
From the audit log validated earlier: Rite Aid's revolver matured January 31, 2025 — at the time of the fiscal 2023 10-K filing (filed May 1, 2023), the revolver maturity was 639 days away — Watch level on Dimension 6. However the revolver was already under stress because FCF was negative and leverage was above 10x, making renewal uncertain. This combination — revolver maturity in the Watch band combined with Stress or Critical signals on leverage, coverage, and FCF — illustrates why the combination rules escalating maturity alerts by one level when leverage is stressed are operationally important.

**Historical reference — iHeartMedia:**
iHeartMedia's maturity wall was a defining feature of its distress trajectory. As validated in the Leverage section, the company accumulated over $20B of debt through its leveraged buyout. The maturity concentration in 2019 (multiple large tranches maturing simultaneously) combined with leverage above 10x and negative FCF made refinancing impossible on acceptable terms. A system monitoring WADM and near-term concentration would have flagged the 2016–2017 filings as Stress on multiple dimensions — approximately 18–24 months before the March 2018 bankruptcy filing.

**Phase 3 backtest validation targets:**

| Metric | Target |
|---|---|
| Catch rate (any dimension at Flag or above) | ≥ 80% of known distressed cases flagged at Flag or above at least two quarters before credit event |
| Days-to-maturity precision | ≥ 85% of Critical days-to-maturity alerts (< 90 days) followed by a refinancing event, repayment, or credit event within the flagged period |
| WADM trend catch rate | ≥ 70% of distressed cases show declining WADM for ≥ 2 consecutive years before credit event |
| False positive rate | ≤ 25% of investment-grade issuers falsely flagged at Stress or above — reflecting the sector adjustment for strong capital markets access |
| Covenant breach precision | 100% of covenant breach disclosures should trigger Critical alert — zero tolerance for missed covenant breach signals |


## Signal Timing — Debt Maturity Wall

---

### Classification

**Structurally unique — the only metric in this spec that combines a leading indicator function with a fixed-date cliff event.**

Every other metric in this spec signals stress through deteriorating ratios — the signal is about direction and trend. The debt maturity wall is fundamentally different because it contains a calendar-driven component that is completely independent of business performance. A debt maturity date does not move based on how well or poorly the company is doing. It is fixed at issuance and approaches at one day per day regardless of EBITDA, FCF, or covenant compliance. This creates a timing dynamic unlike any other metric: the signal can be known years in advance with complete certainty, but its severity increases non-linearly as the date approaches.

This dual nature — early visibility combined with accelerating urgency — means the maturity wall serves two distinct functions in your system simultaneously. At long horizons (Years 3–5) it is a planning and monitoring signal that complements FCF and leverage trend analysis. At short horizons (within 12 months) it becomes the most time-critical signal in the entire spec — more urgent than any ratio-based metric because the clock is fixed and cannot be slowed by operational improvement.

---

### The Three Temporal Zones

The maturity wall signal operates across three distinct temporal zones, each requiring a different system response:

**Zone 1 — Strategic horizon (18 months to 5 years)**

In this zone the maturity is a known future event but its refinancing risk is highly uncertain. Capital market conditions 3 years from now are unknowable. The company's credit quality at that time depends on its operational trajectory between now and then. The maturity wall signal in Zone 1 is primarily structural — it identifies concentration risk and WADM compression as design flaws in the company's debt structure that create future vulnerability. The appropriate system response is monitoring and trend tracking, not escalation.

The most important Zone 1 signal is WADM compression across consecutive annual filings. A company whose WADM was 5.2 years in 2021, 4.4 years in 2022, and 3.6 years in 2023 is not refinancing at longer tenors than it is retiring — its debt structure is becoming more fragile each year. This is visible 3–5 years before the wall arrives and is detectable only through the annual 10-K maturity schedule extractions.

**Zone 2 — Tactical horizon (6 to 18 months)**

In this zone the maturity is approaching and refinancing activity must be observable. Capital markets access is now testable — the company either can or cannot execute a refinancing at acceptable terms. Absence of refinancing activity in this zone is itself a signal: a company that has not begun addressing a maturity 12 months away is either relying on available cash (check liquidity metric), relying on future FCF (check FCF metric), or struggling to find willing lenders (the most alarming interpretation).

Your system detects Zone 2 refinancing activity through 424B filings (new public bond issuances) and 8-K Item 2.03 filings (new credit facilities). A new long-dated bond issuance accompanied by a tender offer for the maturing bonds is the clearest positive resolution signal. Absence of these filings as a maturity enters Zone 2 is a Watch-to-Flag escalation trigger.

**Zone 3 — Crisis horizon (0 to 6 months)**

In this zone the maturity is imminent and every day without a confirmed refinancing or repayment plan increases default probability. The company's options are narrowing — each passing week reduces the time available to complete a transaction, negotiate terms, and close a new facility. In Zone 3 the maturity wall signal dominates all other metrics in urgency. A company that is modestly stressed on leverage and coverage but has a $1B maturity due in 45 days with no announced refinancing is facing a potential default regardless of its operating performance.

Your system's primary Zone 3 monitoring tool is daily 8-K surveillance for issuers in this zone — specifically looking for 424B bond pricing announcements, 8-K Item 1.01 credit facility signings, and 8-K Item 8.01 announcements confirming refinancing completion. These filings provide resolution confirmation within hours of execution.

---

### Three-Tier Timing Structure

| Tier | Source | Data Quality | Lag After Quarter-End | Lead Before 10-Q | Use in System |
|---|---|---|---|---|---|
| **Tier 1 — Annual schedule update** | 10-K | Audited; XBRL + LLM extraction; Formula 2 full schedule | **+60 days** after fiscal year-end (large accelerated filer) | n/a | Full maturity schedule refresh; WADM computed; all eight threshold dimensions updated |
| **Tier 1b — Quarterly balance sheet update** | 10-Q | Reviewed; structured XBRL only; Formula 1 near-term maturity | **+40 days** after quarter-end | n/a | Near-term maturity coverage ratio updated quarterly; full schedule not refreshed unless XBRL maturity tags updated |
| **Tier 2 — Intra-year debt event** | 8-K Item 2.03 / 424B / Item 1.01 | Event disclosure; LLM extraction; patches rolling schedule | **Within 4 business days** (Item 2.03) or same day (424B) | Any time intra-year | Rolling schedule patch; new maturities added; refinancing completions noted |
| **Tier 3 — Earnings press release** | 8-K Item 2.02 | Preliminary; company may disclose refinancing status | **+14 to +25 days** after quarter-end | **−15 to −25 days before 10-Q** | Refinancing status commentary; Phase 3 only |

**Critical difference from prior metrics:** The maturity wall has a Tier 1b (quarterly balance sheet update) that is separate from the Tier 1 annual schedule update. The full maturity schedule refreshes only annually from the 10-K. The near-term maturity coverage ratio (Formula 1) updates quarterly from the balance sheet current portion. This asymmetry means the system has two update frequencies running simultaneously for the same metric — quarterly for the near-term signal and annually for the full wall picture.

---

### The Lead Time Advantage — Longest of All Metrics

The debt maturity wall is the only metric in this spec where the system knows about a stress event years before it occurs. A bond issued in 2020 with a 2026 maturity date creates a maturity wall entry in 2020 that is visible in every filing from issuance to maturity. Compare this to leverage, which can only signal deterioration after it has already occurred in the filed numbers.

**Quantitative lead time comparison:**

| Metric | Typical Lead Time Before Credit Event | Basis |
|---|---|---|
| Free Cash Flow (compression trend) | 4–6 quarters | Empirical — cash deterioration precedes earnings deterioration |
| Interest Coverage (declining trend) | 2–4 quarters | Empirical — earnings deterioration precedes balance sheet stress |
| Leverage (rising trend) | 2–4 quarters | Empirical — debt accumulation visible in filed ratios |
| Liquidity (ratio deterioration) | 1–2 quarters | Coincident to lagging — absorbs stress until cliff |
| **Debt Maturity Wall (Zone 1 detection)** | **8–20 quarters (2–5 years)** | **Structural — maturity date is known from issuance** |
| Debt Maturity Wall (Zone 3 crisis) | 0–2 quarters | Coincident — the event itself is the signal |

This lead time advantage is theoretical — a Zone 1 maturity wall signal does not mean a credit event is imminent. It means the structural vulnerability is visible and should be monitored in combination with the other metrics. The lead time becomes actionable when Zone 1 visibility is combined with deteriorating FCF, coverage, or leverage trends — the maturity wall defines the destination, the other metrics define how quickly the company is approaching it.

---

### The Dark Window Problem Is Smallest for This Metric

The Q4 dark window — which is most severe for FCF and significant for coverage and leverage — is smallest for the maturity wall. This is because:

The scheduled maturity dates are fixed and known from prior 10-K filings. The system does not need a new filing to know that a bond matures on March 15 next year — this was disclosed in the prior 10-K and is stored in the rolling schedule. The days-to-maturity countdown runs continuously regardless of the filing calendar.

The only maturity wall information that goes dark during Q4 is intra-quarter debt events — new issuances or repayments that change the schedule. These are partially illuminated by 424B filings (same day) and 8-K Item 2.03 filings (within 4 business days), making the maturity wall the best-illuminated metric during the Q4 dark window.

```
Q4 dark window impact by metric (ranked most to least affected):

1. FCF — worst affected: no OCF or capex data available
2. Coverage — severely affected: no EBITDA update
3. Leverage — moderately affected: no EBITDA update;
              debt events partially visible via 8-K
4. Liquidity — moderately affected: no balance sheet update;
               revolver status partially visible via Item 1.01
5. Debt Maturity Wall — least affected: schedule known from
                        prior 10-K; debt events visible via
                        424B and Item 2.03; days countdown
                        continues regardless
```

---

### Refinancing Activity Monitoring — The Unique Intra-Zone Signal

The maturity wall is the only metric that generates a meaningful signal from the absence of activity as well as from the presence of activity. For every other metric, the absence of a filing means no update — neutral. For the maturity wall, the absence of a refinancing filing as a Zone 2 maturity approaches is itself a signal.

```
Refinancing Activity Monitor — Phase 3:

For each issuer with a maturity in Zone 2
(6–18 months away), activate refinancing tracking:

Monitor for:
   424B filings (new public bond issuances)
   8-K Item 2.03 (new credit facilities, term loans)
   8-K Item 1.01 (material agreement — revolving
                  credit facility renewal or amendment)
   8-K Item 8.01 (voluntary disclosure of refinancing
                  completion — keyword: "refinanc",
                  "tender offer", "redemption",
                  "repurchase", "matured")

Positive resolution signals:
   New issuance with maturity > maturing instrument:
      Flag: "refinancing activity detected —
      [maturity] being addressed by [new instrument];
      maturity alert downgrade pending confirmation"
   Tender offer announcement for maturing bonds:
      Flag: "tender offer for maturing bonds —
      active liability management; monitor for
      completion"
   Revolver renewal confirmed (Item 1.01):
      Flag: "revolving credit facility renewed —
      liquidity backstop secured"

Absence signal (no refinancing activity detected):
   Zone 2 entry (180 days) → no activity for 30 days:
      Flag: "no refinancing activity detected for
      issuer with maturity in 150 days — monitor
      for execution; lender access uncertain"
   Zone 2 entry (180 days) → no activity for 60 days:
      Escalate to Stress: "180-day maturity approaching
      with no refinancing activity observed — elevated
      execution risk"
   Zone 3 entry (90 days) → no activity confirmed:
      Escalate to Critical: "90-day maturity with no
      confirmed refinancing or repayment plan —
      near-term default risk elevated"
```

---

### Interaction With Filing Calendar

Unlike prior metrics which update on the filing calendar (40 days after quarter-end, 60 days after year-end), the maturity wall's most important signal — days to nearest maturity — updates every single day. The system does not need to wait for a filing to know that a maturity is 89 days away rather than 90. The days countdown should run continuously in the background as a standing daily computation, not a filing-triggered computation.

```
Daily computation (no filing required):
For each issuer in portfolio:
   For each maturity in rolling schedule:
      Days_Remaining = maturity_date - today
      If Days_Remaining crosses a threshold boundary:
         Generate alert at new threshold level
         Log: "days threshold crossed — maturity
         [date] now [N] days away; alert escalated
         from [prior level] to [new level]"

This daily computation is the only place in the
entire system where alerts are generated without
a new filing triggering them. It is the maturity
wall's unique contribution to real-time monitoring.
```

---

### Comparison: Maturity Wall vs Other Metrics Signal Characteristics

| Characteristic | Debt Maturity Wall | FCF | Coverage | Leverage | Liquidity |
|---|---|---|---|---|---|
| **Signal type** | Calendar-driven + structural | Flow deterioration | Flow deterioration | Stock accumulation | Stock depletion |
| **Lead time** | 2–5 years (Zone 1) to 0 (Zone 3) | 4–6 quarters | 2–4 quarters | 2–4 quarters | 1–2 quarters |
| **Updates from filings** | Annually (full schedule) + quarterly (near-term) + event-driven (patches) | Quarterly | Quarterly | Quarterly | Quarterly |
| **Updates without filings** | ✅ Yes — daily countdown | ❌ No | ❌ No | ❌ No | ❌ No |
| **Absence-of-activity signal** | ✅ Yes — no refinancing in Zone 2 | ❌ No | ❌ No | ❌ No | ❌ No |
| **Q4 dark window severity** | Minimal | Severe | Significant | Moderate | Moderate |
| **Predictable future event** | ✅ Yes — maturity date known | ❌ No | ❌ No | ❌ No | ❌ No |
| **Primary Phase 2 signal** | Near-term maturity coverage + daily countdown | FCF margin + conversion ratio | EBITDA coverage | Net Debt/EBITDA | Current + quick ratio |

---

### Updated Signal Timing Summary

> **Signal Timing — Structurally unique: the only metric combining multi-year advance visibility with a fixed-date cliff event.**
>
> The debt maturity wall is detectable years before it becomes critical — WADM compression and concentration are visible in Zone 1 (18 months to 5 years) as structural vulnerabilities. In Zone 2 (6–18 months), the refinancing execution window is open and absence of activity is itself a stress signal. In Zone 3 (under 6 months), the wall is imminent and dominates all other metrics in urgency.
>
> Unlike every other metric in this spec, maturity wall alerts update daily through a continuous countdown computation — not just when filings arrive. A maturity crossing from 91 days to 89 days triggers a threshold escalation regardless of the filing calendar.
>
> The Q4 dark window is smallest for this metric — scheduled maturity dates are known from prior filings and the countdown continues uninterrupted. Intra-quarter debt events are partially illuminated by 424B and 8-K filings, making the maturity wall the best-monitored metric during the dark window period.
>
> The maturity wall's lead time advantage is the longest of any metric — 2–5 years of structural visibility in Zone 1. This advantage is realised only when combined with other metrics: FCF compression and leverage deterioration determine how quickly a company is approaching its wall, while the wall itself defines the deadline by which financial improvement must occur or refinancing must be executed. All five primary metrics — FCF, coverage, leverage, liquidity, and maturity wall — must be evaluated simultaneously to assess whether a company will reach its maturity wall in a position to successfully refinance.

## Frequency — Debt Maturity Wall

---

### Overview

The debt maturity wall has the most complex update structure of any metric in this spec. It differs from all prior metrics in three fundamental ways that make a simple reference to the Leverage Frequency section insufficient (See LEVERAGE.md → Section "Frequency" → full section — apply identical baseline six-channel framework; this section documents maturity-wall-specific differences only).

First, it has two distinct structured update frequencies running simultaneously — annual for the full schedule and quarterly for the near-term balance sheet component. Second, it generates daily alerts from a countdown computation that requires no filing trigger. Third, it has more relevant intra-quarter event-driven update channels than any other metric because debt issuances, repayments, and amendments are directly and immediately visible through prospectus and 8-K filings.

---

### What Is the Same as Prior Metrics

| Channel | Filing Type | Phase 2 | Phase 3 |
|---|---|---|---|
| Quarterly balance sheet | 10-Q | ✅ Near-term maturity coverage ratio (Formula 1 only) | ✅ Same + XBRL maturity tag check |
| Annual full schedule | 10-K | ✅ XBRL attempt + LLM extraction (Formula 2) | ✅ Full Formula 2 + Formula 3 tranche analysis |
| Earnings press release | 8-K Item 2.02 | ❌ Ignore | ✅ Add (refinancing status commentary) |
| Debt acceleration / default | 8-K Item 2.04 | ✅ Monitor — immediate Critical alert | ✅ Monitor |

---

### Maturity Wall-Specific Differences

**Difference 1 — Daily countdown computation (no filing required)**

This is the only metric in the system that generates alerts without a new filing. The days-to-maturity countdown runs every day as a background computation against the stored rolling schedule.

```
Daily Countdown Process:

Input: Rolling maturity schedule (stored per issuer)
       containing maturity dates and principal amounts

For each maturity entry in schedule:
   Days_Remaining = maturity_date - current_date
   Prior_Alert_Level = stored alert level for this entry

   Compute new alert level per Dimension 2 thresholds:
   > 730 days → No alert
   548–730 days → Watch
   365–548 days → Flag
   180–365 days → Stress
   90–180 days → Critical
   < 90 days → Critical (highest urgency)

   If new alert level > Prior_Alert_Level:
      Generate escalation alert:
      "Maturity threshold crossed — [issuer] [instrument]
       principal $X million now [N] days away;
       alert escalated from [prior] to [new level]"
      Update stored alert level
      Log: escalation_date, days_remaining,
           prior_level, new_level, maturity_date,
           principal_amount

   If new alert level = Prior_Alert_Level:
      No new alert — existing alert confirmed active
      Update stored days_remaining value

   If new alert level < Prior_Alert_Level:
      This occurs only if a refinancing has been
      detected and the maturity entry has been
      resolved — should not occur from countdown
      alone; log as anomaly if it does

Run frequency: daily on all business days
               (Monday through Friday)
               Skip weekends and public holidays —
               maturity dates falling on non-business
               days are legally due on the next
               business day; adjust accordingly
```

**Implementation note for Phase 2:** The daily countdown is the lowest-cost, highest-value addition to Phase 2. It requires no new data extraction — only the stored maturity schedule from the most recent 10-K and the current date. It can be implemented as a simple loop over the stored schedule. The alert generation logic is identical to the threshold computation already defined. This should be implemented from day one of Phase 2 for the near-term maturity (12-month current portion) even before Phase 3 LLM extraction of the full schedule is available.

---

**Difference 2 — 424B prospectus filings are a primary channel**

For all prior metrics, the 424B filing is a Phase 3 channel that provides partial updates (new debt affects leverage and FCF projections). For the maturity wall, 424B filings are a primary real-time data source that directly patches the rolling schedule.

```
424B Processing — Phase 3:

Trigger: Any 424B, 424B2, 424B3, 424B5 filing
         by a monitored issuer on EDGAR

LLM extraction targets (from cover page and
pricing supplement):
   (1) Principal amount of new issuance
   (2) Maturity date (exact date)
   (3) Coupon rate and type (fixed/floating)
   (4) Instrument type (senior notes, subordinated,
       convertible, etc.)
   (5) Use of proceeds — specifically whether
       proceeds will be used to repay maturing debt
       ("intended to be used to redeem/repay/refinance
       [instrument]")

System action:
   Add new maturity to rolling schedule:
   Schedule[maturity_year] += principal_amount
   Log patch with 424B accession number

   If use of proceeds confirms repayment of
   existing instrument:
      Identify instrument being repaid
      Mark that maturity as "refinancing confirmed"
      Reduce Schedule[maturing_year] by repaid amount
      Flag: "refinancing confirmed — [original
      instrument] being repaid with proceeds
      from [new instrument] maturing [new date]"
      Downgrade alert level for original maturity
      if repayment confirmed

   Re-run reconciliation check after patch
```

---

**Difference 3 — 8-K Item 1.01 is a primary channel for maturity changes**

For liquidity, Item 1.01 is an important channel for revolver amendments. For the maturity wall, Item 1.01 covers a broader set of maturity-relevant events including term loan amendments, maturity extensions, and covenant modifications.

```
8-K Item 1.01 Maturity Wall Triggers:

Primary triggers (always process):
   "maturity" + "extend" OR "amendment"
   "term loan" + "amendment"
   "credit agreement" + "amendment"
   "refinanc"
   "tender offer"
   "redemption"
   "repurchase"

LLM extraction when triggered:
   (1) Which instrument is being amended
   (2) Original maturity date
   (3) New maturity date (if extended)
   (4) Principal amount affected
   (5) Whether amendment involves covenant
       changes that affect acceleration provisions

System action:
   Maturity extension:
      Update rolling schedule:
      Remove principal from original_year
      Add principal to new_maturity_year
      Flag: "maturity extended — [instrument]
      maturity moved from [original] to [new];
      rolling schedule updated"
      Recompute WADM and concentration ratios

   Maturity extension at shorter tenor than hoped:
      Flag: "maturity extended but tenor shorter
      than original instrument — possible lender
      confidence signal; monitor"

   Covenant modification reducing headroom:
      Cross-reference Covenant Headroom metric
      Flag for joint review
```

---

**Difference 4 — Cash flow statement repayment monitoring**

Principal repayments on the cash flow statement — visible in financing activities — confirm that maturities have been paid. This is the structured confirmation that a maturity has been retired.

```
Cash flow statement repayment detection:

Tags to monitor in financing activities section:
   us-gaap:RepaymentsOfLongTermDebt
   us-gaap:RepaymentsOfDebt
   us-gaap:RepaymentsOfSeniorDebt
   us-gaap:RepaymentsOfNotesPayable

If repayment amount detected in current period
that matches a scheduled maturity within ±10%:
   Mark that maturity as "repaid"
   Remove from rolling schedule
   Flag: "maturity confirmed repaid —
   $X million repayment in financing activities
   matches scheduled maturity for [year]"

If repayment amount detected that does NOT match
any scheduled maturity:
   Flag: "unscheduled repayment detected —
   $X million; may represent early repayment,
   revolver pay-down, or untracked instrument;
   verify against Debt Footnote at next 10-K"
   Store as unmatched repayment in audit log

This structured detection runs quarterly from
the 10-Q cash flow statement — no LLM required.
```

---

**Difference 5 — 8-K Item 8.01 keyword filter is narrower than for Liquidity**

For liquidity, the Item 8.01 filter uses a broad set of keywords because companies voluntarily disclose liquidity reassurances. For the maturity wall, the filter is focused specifically on refinancing activity and maturity resolution events.

```
Maturity Wall-specific 8.01 keyword filter:

Always process:
   "refinanc"
   "tender offer"
   "redemption notice"
   "repurchase" + "notes" OR "bonds"
   "called for redemption"
   "matured"
   "repaid in full"

Process if issuer in Zone 2 or Zone 3:
   "debt" + "transaction"
   "capital markets"
   "offering"

Do NOT process unless above keywords present:
   General operational updates
   Earnings guidance
   Personnel changes
   All other topics
```

---

**Difference 6 — Tender offer filings (SC TO-I) are relevant**

When a company launches a tender offer to repurchase its own maturing bonds, it files a Schedule TO-I with the SEC. This is outside the standard 8-K / 10-Q / 10-K universe but is directly relevant to maturity wall resolution.

```
Schedule TO-I monitoring — Phase 3:

Trigger: SC TO-I or SC TO-T filing by monitored issuer

LLM extraction:
   (1) Which bonds are being tendered
   (2) Tender price and expiration date
   (3) Whether tender is conditional on
       new financing being completed

System action:
   Flag: "tender offer launched for [instrument]
   maturing [date] — active liability management;
   maturity resolution in progress"
   If tender is successful (confirmed by SC TO-I/A
   amendment showing results): mark maturity
   as resolved; update rolling schedule
   Downgrade maturity alert level to No Alert
   for tendered portion
```

---

### Full Update Schedule — Calendar Year Large Accelerated Filer

| Timing | Event | Channel | Maturity Wall Update Type |
|---|---|---|---|
| Every business day | Days countdown | Internal computation | Days-to-maturity updated; threshold crossing alerts generated if applicable |
| ~Mar 31 | 10-K filed | 10-K | Full schedule refresh: XBRL extraction + LLM extraction + reconciliation + Formula 3 tranche analysis; new annual baseline stored |
| ~May 10 | Q1 10-Q filed | 10-Q | Formula 1 near-term maturity coverage ratio updated from balance sheet; XBRL maturity tags checked for quarterly update; cash flow statement repayments checked |
| ~Aug 9 | Q2 10-Q filed | 10-Q | Same as Q1 10-Q |
| ~Nov 9 | Q3 10-Q filed | 10-Q | Same as Q1 10-Q |
| ~Jan 30 – Feb 15 | Q4 earnings press release | 8-K Item 2.02 | Refinancing status commentary if disclosed; Phase 3 only |
| Any business day | New bond issuance | 424B filing | Immediate rolling schedule patch; new maturity added; use of proceeds checked for refinancing confirmation; Phase 3 |
| Any business day | New credit facility or maturity extension | 8-K Item 1.01 | Rolling schedule update; maturity date changes logged; WADM recomputed; Phase 3 for full LLM; Phase 2 keyword monitoring for flagged issuers |
| Any business day | Debt acceleration / default | 8-K Item 2.04 | IMMEDIATE CRITICAL ALERT — effective maturity wall collapsed to zero |
| Any business day | Tender offer launch | SC TO-I | Active liability management flag; Phase 3 |
| Any business day | Tender offer completion | SC TO-I/A | Maturity resolved for tendered portion; rolling schedule updated; Phase 3 |
| Any business day | Voluntary refinancing announcement | 8-K Item 8.01 (keyword filtered) | Refinancing activity signal; Phase 3 |
| Any business day | Principal repayment detected | 10-Q cash flow statement | Structured confirmation of maturity retirement; quarterly update |

---

### Phase Summary

**Phase 2:**

Monitor 10-Q and 10-K for Formula 1 near-term maturity coverage ratio. Attempt XBRL maturity tag extraction at each 10-K filing with mandatory reconciliation check — fall back to LLM if reconciliation fails. Run daily countdown computation against stored rolling schedule anchored to most recent 10-K. Monitor 8-K Item 2.04 as automatic Critical escalation. Monitor 8-K Item 1.01 and 8-K Item 8.01 with keyword filters for flagged issuers in Zone 2 or Zone 3. Monitor cash flow statement financing activities quarterly for principal repayments to confirm maturity retirements. Implement going concern keyword search across all filing types — same as Liquidity metric.

**Phase 3:**

Add full Formula 2 LLM maturity schedule extraction at each 10-K with dual-path XBRL and LLM verification. Add 424B processing for same-day rolling schedule patching. Add 8-K Item 1.01 full LLM extraction for maturity extensions and amendments across all issuers. Add SC TO-I tender offer monitoring. Add Formula 3 tranche-level analysis including floating rate spread extraction and callable/puttable feature tracking. Add interest rate reset impact computation requiring external spread data. Add refinancing absence signal for Zone 2 issuers — flag when no refinancing activity is detected within 30 and 60 days of Zone 2 entry. Add 8-K Item 2.02 LLM processing for refinancing status commentary.

