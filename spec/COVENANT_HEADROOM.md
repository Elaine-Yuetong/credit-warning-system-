# Covenant Headroom 

## What it is

### Core Definition

Covenant Headroom measures how close a company is to breaching the financial maintenance conditions embedded in its debt agreements. It answers: *"given the financial ratios the company has promised its lenders it will maintain, how much deterioration can the company absorb before it violates those promises?"*

### What Is a Financial Covenant?

When a company borrows money — whether through a bank loan, a revolving credit facility, or a term loan — lenders make a multi-year commitment based on their assessment of the company's financial health at the time of the loan.

**Lender's concern:** The company's financial condition may deteriorate between the loan date and maturity.

**Lender's solution:** A mechanism that gives them the right to act — demand repayment, restrict further borrowing, or renegotiate terms — if deterioration crosses an unacceptable threshold.

**That mechanism is the financial maintenance covenant.**

### Financial Maintenance Covenant Definition

A financial maintenance covenant is a contractual promise, written into the credit agreement, that the company will maintain certain financial ratios above or below specified thresholds throughout the life of the loan.

**Most common types:**

| Covenant Type | Example Threshold |
|---|---|
| Maximum leverage ratio | Net Debt / EBITDA ≤ 5.5x |
| Minimum interest coverage ratio | EBITDA / Interest Expense ≥ 2.0x |
| Minimum liquidity threshold | Maintain ≥ $X million of unrestricted cash or available revolver capacity at all times |

Less common: minimum net worth covenant, maximum capital expenditure covenant.

### Covenant Headroom Defined

Covenant headroom is the distance between where the company's ratio currently sits and where the covenant threshold is.

| Scenario | Current Leverage | Covenant Cap | Headroom | Implication |
|---|---|---|---|---|
| Company A | 4.2x | 5.5x | **1.3x** | EBITDA would need to fall ~24% or debt would need to increase materially |
| Company B | 5.1x | 5.5x | **0.4x** | Small buffer — a single bad quarter could eliminate it |

> The word "headroom" is important. It is **not the ratio itself** — it is the gap between the ratio and the line that cannot be crossed.

**Key insight:** Two companies can have identical leverage ratios but completely different covenant headroom if their respective covenants were set at different levels. A company with 4.0x leverage and a 4.5x covenant is more stressed from a covenant perspective than a company with 5.0x leverage and an 8.0x covenant, even though the first company's absolute leverage is lower.

### The Central Extraction Challenge

Covenant headroom is qualitatively different from every other metric in this spec in one important way:

> It is defined by a **private contractual agreement**, not by a public accounting standard.

| Challenge | Description |
|---|---|
| Threshold values | Negotiated between the company and its lenders — not set by GAAP |
| Standardisation | Not standardised across companies |
| Disclosure | Not always fully disclosed in public filings; may be described imprecisely, qualified by numerous exceptions, or not disclosed at all |

> This is why covenant headroom is one of the primary use cases for the LLM extraction layer — not because the computation is complex but because the inputs are locked inside unstructured legal prose.

### Maintenance vs Incurrence Covenants

An important distinction your system must understand:

| | Maintenance Covenants | Incurrence Covenants |
|---|---|---|
| **Testing frequency** | Tested continuously at every reporting period | Tested only when the company attempts a specific action (issuing more debt, paying a dividend, making an acquisition) |
| **Breach consequence** | Lenders have the right to demand immediate repayment regardless of when the debt actually matures | Do not give lenders the right to accelerate existing debt — simply prohibit the triggering action |
| **Where typically found** | Leveraged loans and high-yield bank facilities | Investment-grade bonds |

> Maintenance covenants are the stress signals. Incurrence covenants are constraints on future actions but are not themselves default triggers.

### Relationship with Other Metrics

Covenant headroom directly quantifies the legal boundaries that the other metrics measure from a financial analysis perspective.

| Covenant Type | What It Tells You | Related Metric |
|---|---|---|
| Leverage covenant headroom | How much EBITDA can fall before a breach | FCF, Coverage |
| Coverage covenant headroom | How much interest expense can rise before a breach | Debt Maturity Wall (interest rate reset analysis) |
| Liquidity covenant headroom | How much cash can be consumed before a breach | Liquidity (cash runway calculation) |

> Covenant headroom is the legal formalisation of the stress thresholds that the other metrics approach from the direction of financial analysis.



## Why it signals stress

Covenant headroom signals stress through five mechanisms, each operating on a different timeline and with a different relationship to the other metrics in this spec.

---

### Mechanism 1 — The acceleration trigger (most immediate)

**Core logic:**
- A covenant breach gives lenders the contractual right to declare an event of default and accelerate the debt — making the entire principal balance immediately due regardless of the scheduled maturity date
- This is the most direct and legally consequential stress signal in the entire system
- Every other metric in this spec signals that stress is developing or approaching. A covenant breach means it has arrived in a legally actionable form

**How acceleration changes the dynamic:**
- A company whose leverage ratio drifts from 4.5x → 5.3x → 5.6x over three quarters shows slow deterioration
- If the covenant limit is 5.5x, the moment the ratio crosses 5.5x:
  - Lenders have the right — not the obligation — to call the entire loan balance
  - Whether they exercise that right depends on relationship, market conditions, and their own considerations
  - But the right exists, and its existence fundamentally changes the company's position
  - The company must now negotiate from weakness rather than strength — seeking a waiver or amendment while lenders hold the acceleration card

**The immediate signal:**
- Any disclosed covenant breach, regardless of whether a waiver has been obtained → **automatic Critical alert**
- The breach has already occurred. The waiver is a temporary accommodation that may not be renewed
- The underlying financial deterioration that caused the breach is real and persists

---

### Mechanism 2 — The headroom compression warning (early warning)

**Core logic:**
- Covenant breaches do not arrive without warning in well-monitored systems
- Headroom compression — the gradual narrowing of the gap between the current ratio and the covenant threshold — is visible in every quarterly filing for companies that disclose their covenant terms
- A company moving from 35% headroom → 25% → 15% over three quarters tells you the breach is approaching before it occurs

**Why this signal is particularly valuable:**
- Provides earlier warning than the ratio-level alerts from leverage and coverage metrics alone
- Leverage metric tells you the ratio is deteriorating
- Covenant headroom metric tells you how close the deterioration is to triggering a legal event
- Both pieces of information are necessary for a complete picture

| Scenario | Leverage Ratio | Covenant Cap | Interpretation |
|---|---|---|---|
| Company A | 3.5x → 4.5x | 8.0x | Alarming but benign |
| Company B | 3.5x → 4.5x | 5.0x | Critical |

**Covenant step-down risk:**
- Unlike other metrics where thresholds are stable market conventions, covenant thresholds are fixed by contract
- Headroom can compress even if the ratio is not moving — a company that negotiated a covenant step-down (a contractually scheduled tightening of the covenant over time) will see its headroom narrow automatically even if financial performance is unchanged

**The early warning signal:**
- Headroom declining for **two consecutive quarters**, regardless of absolute level
- Headroom **below 20%** on any maintenance covenant
- Covenant step-down approaching that will reduce headroom materially

---

### Mechanism 3 — The covenant-liquidity feedback loop (self-reinforcing)

**Core logic:**
When a maintenance covenant is breached and lenders accelerate the debt, the immediate effects cascade:

| Effect | Description |
|--------|-------------|
| **Current ratio collapse** | All accelerated debt reclassifies from long-term to current liabilities on the balance sheet — a company that appeared liquid suddenly has enormous current liabilities |
| **Cross-default triggers** | If the leveraged loan is accelerated due to a covenant breach, indentures on senior notes typically contain cross-default language making those bonds also immediately due |
| **Revolver unavailable** | Most revolvers contain the same financial maintenance covenants as term loans; a breach that accelerates the term loan simultaneously makes the revolver unavailable for further draws |

**The feedback loop:**

Covenant breach
↓
Debt acceleration
↓
Current ratio collapse
↓
Cross-default acceleration of remaining debt
↓
Revolver unavailability
↓
Acute liquidity crisis
↓
Forced asset sales or bankruptcy


> This sequence can complete **within weeks** of a covenant breach if lenders choose to exercise their rights aggressively. The covenant headroom metric is the only place in your system where this feedback loop is visible **before it begins** — once it starts, the other metrics are confirming a crisis that is already in motion.

**The self-reinforcing signal:**
- Covenant headroom **below 10%** combined with **any cross-default provision** in the debt structure
- The combination means a single covenant breach could simultaneously accelerate most or all of the company's debt

---

### Mechanism 4 — The negotiating position indicator (medium term)

**Core logic:**
Even when a breach has not yet occurred, thin covenant headroom fundamentally changes the company's negotiating position with lenders, suppliers, customers, and employees.

**Operational constraints with thin headroom:**

| Constraint | Implication |
|------------|-------------|
| Cannot take on additional debt to fund growth | Expansion limited |
| Cannot absorb operational setback without lender consent | Every deviation requires negotiation |
| Cannot make acquisitions or pay dividends | Strategic options eliminated |
| Effectively operating under lender supervision | Even without formal breach |

**Why this is a stress signal:**
- Limits the company's ability to respond to deteriorating conditions
- A company with ample headroom can issue new debt to fund working capital if FCF turns negative
- A company at 5% headroom cannot — any new debt issuance would likely breach the leverage covenant
- It is trapped in a deteriorating position with fewer tools to improve it

**Lender and rating agency perspective:**
- S&P and Moody's both treat thin covenant headroom as a negative factor in their liquidity and financial flexibility assessments, independent of whether a breach has occurred
- A company that must seek a covenant waiver or amendment is confirming to the market that its financial trajectory has been worse than lenders expected when the loan was originally negotiated — which is itself a credit signal

**The medium-term signal:**
- Headroom **below 15% for two consecutive quarters** signals operational constraint even without a breach
- The company's financial flexibility is effectively exhausted

---

### Mechanism 5 — The hidden stress revealer (analytical)

**Core logic:**
Covenant headroom occasionally reveals stress that the standard metrics do not capture because **covenant definitions differ from GAAP definitions**. This is the subtlest but analytically most interesting mechanism.

**How covenant definitions differ:**

| Metric | GAAP Definition (Formula 1) | Covenant Definition |
|--------|----------------------------|---------------------|
| EBITDA | Operating Income + D&A | "Consolidated EBITDA" — includes addbacks for non-recurring charges, restructuring costs, pro forma synergies from acquisitions, management fees |
| Interest Expense | GAAP interest expense | May exclude certain non-cash interest charges |

**Two possible divergence directions:**

| Direction | GAAP Ratio | Covenant Ratio | Interpretation |
|-----------|------------|----------------|----------------|
| **Stress may be less severe** | Stress (e.g., 6.5x) | Compliance with headroom | Addbacks inflate Covenant EBITDA — lenders are using looser definition |
| **Hidden stress revealed** | Comfortable (e.g., 4.5x) | Near threshold | Lenders are applying a **stricter** definition than public accounting standards — company is closer to lenders' stress threshold than headline ratios suggest |

**The hidden stress signal:**
- Covenant EBITDA materially higher than GAAP EBITDA (large addbacks) combined with thin headroom on the covenant definition
- This means the company's headline ratios are flattered by addbacks — remove the addbacks and the covenant headroom disappears
- **Flag when company-disclosed covenant EBITDA exceeds your Formula 1 EBITDA by more than 20%**

---

### Institutional validation

| Source | Content |
|--------|---------|
| **Moody's** | Covenant packages and headroom are considered as part of financial policy and liquidity assessment in cross-sector methodology |
| **S&P** | Covenant headroom below 15% is a negative factor in liquidity descriptor, potentially reducing the descriptor by one level (as documented in Liquidity metric threshold section) |
| **Both agencies** | Covenant amendment or waiver is a rating-negative event — confirms financial trajectory has been worse than originally expected |

**Empirical evidence:**
- Covenant breaches are leading indicators of eventual default — not because the breach itself causes default, but because companies that breach covenants have already demonstrated financial deterioration that lenders were unwilling to accept
- Research by Moody's on leveraged loan defaults finds that companies that obtain covenant waivers default at **materially higher rates within 12 months** than companies that maintain covenant compliance
- Waivers are confirmed stress signals rather than resolutions of the underlying problem

---

### Summary of Covenant Headroom Alert Signals

| Mechanism | Signal | Timeline | Alert Level |
|-----------|--------|----------|-------------|
| M1 — Acceleration trigger | Any disclosed covenant breach (regardless of waiver) | Immediate | **Critical** |
| M2 — Headroom compression | Headroom declining for 2 consecutive quarters | Early warning | Watch/Flag |
| M2 — Headroom compression | Headroom below 20% | Early warning | Flag |
| M2 — Headroom compression | Covenant step-down approaching | Early warning | Flag |
| M3 — Covenant-liquidity feedback | Headroom below 10% + cross-default provisions | Weeks | **Stress/Critical** |
| M4 — Negotiating position | Headroom below 15% for 2 consecutive quarters | Medium term | Flag |
| M5 — Hidden stress revealer | Covenant EBITDA > GAAP EBITDA by 20% + thin headroom | Analytical | Flag/Stress |


## Formula

---

**Covenant Headroom is a hybrid metric — deterministic computation applied to LLM-extracted inputs.**

Unlike all prior metrics where Formula 1 is fully deterministic from XBRL and Formulas 2 and 3 introduce LLM requirements, Covenant Headroom has no fully structured formula. Even the simplest headroom computation requires at least one LLM-extracted input — the covenant threshold — because covenant thresholds are not tagged in XBRL and are not disclosed on the face of financial statements. They live in the prose of the debt footnote and the credit agreement.

The formula structure therefore differs from prior metrics. Rather than Formula 1 / Formula 2 / Formula 3 representing increasing analytical sophistication with increasing LLM dependency, the three formulas here represent three levels of covenant completeness — from the minimum extractable information to a full covenant compliance model.

---

**Formula 1 — Basic Headroom (LLM threshold + deterministic ratio)**

The simplest useful computation. Requires one LLM extraction (the covenant threshold) combined with the deterministic ratio already computed by the Leverage, Coverage, or Liquidity metrics.

```
For each financial maintenance covenant identified:

Headroom (absolute) =
    Covenant Threshold − Current Ratio
    (for maximum covenants — leverage, capex)
    OR
    Current Ratio − Covenant Threshold
    (for minimum covenants — coverage, liquidity)

Headroom (percentage) =
    Headroom (absolute) / Covenant Threshold × 100

Headroom (EBITDA cushion) =
    For leverage covenant only:
    EBITDA_required_for_breach =
        Net Debt / Covenant_Max_Leverage
    EBITDA_cushion =
        Current EBITDA − EBITDA_required_for_breach
    EBITDA_cushion_pct =
        EBITDA_cushion / Current EBITDA × 100
```

**Example — leverage covenant:**
```
Current Net Debt / EBITDA = 4.2x (from Leverage F1)
Covenant Maximum Leverage = 5.5x (from LLM)

Headroom (absolute) = 5.5 − 4.2 = 1.3x
Headroom (percentage) = 1.3 / 5.5 × 100 = 23.6%

EBITDA required for breach =
    Net Debt / 5.5
    = $2,100M / 5.5 = $381.8M
Current EBITDA = $500M
EBITDA cushion = $500M − $381.8M = $118.2M
EBITDA cushion % = $118.2M / $500M = 23.6%

Interpretation: EBITDA can fall 23.6% before
the leverage covenant is breached.
```

**Example — coverage covenant:**
```
Current EBITDA / Interest = 3.8x (from Coverage F1)
Covenant Minimum Coverage = 2.0x (from LLM)

Headroom (absolute) = 3.8 − 2.0 = 1.8x
Headroom (percentage) = 1.8 / 2.0 × 100 = 90.0%

Interest required for breach =
    Current EBITDA / 2.0
    = $500M / 2.0 = $250M
Current Interest Expense = $131.6M
Interest cushion = $250M − $131.6M = $118.4M
Interest can increase $118.4M before breach.
```

**LLM inputs required for Formula 1:**
- Covenant type (maximum leverage, minimum coverage, minimum liquidity, other)
- Covenant threshold value (the specific ratio or dollar amount)
- Whether the covenant uses GAAP or credit-agreement-defined ratios
- Testing frequency (quarterly, semi-annual, annual)

**Deterministic inputs (from prior metrics):**
- See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored Net Debt/EBITDA ratio; no re-extraction required
- See INTEREST_COVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored EBITDA/Interest ratio; no re-extraction required
- See LIQUIDITY.md → Section "Formula" → Output 1A (Cash Ratio) and Output 1D (Available Liquidity Coverage) — reuse stored values; no re-extraction required
- Net Debt, EBITDA, Interest Expense → already extracted

**Error handling:** If LLM cannot extract the covenant threshold, headroom = null. Do not attempt to compute headroom against an assumed threshold. Do not default to industry-average covenant levels. Null headroom for a leveraged issuer should trigger escalation to manual review — covenant terms exist but were not successfully extracted.

---

**Formula 2 — Covenant-Adjusted Headroom (uses credit agreement definitions)**

Most credit agreements define financial ratios differently from GAAP. Formula 2 attempts to replicate the covenant definition rather than using GAAP ratios — producing the headroom as lenders actually measure it rather than as GAAP accounting would suggest.

```
Covenant-Adjusted Leverage Headroom:

Step 1 — Compute Covenant EBITDA:
Covenant EBITDA =
    GAAP EBITDA (Formula 1 of Leverage metric)
  + Restructuring charges addback
    (if permitted by credit agreement)
  + Non-recurring charges addback
    (if permitted — "non-recurring, extraordinary,
    or unusual items" as defined in agreement)
  + Pro forma synergies from acquisitions
    (if within 12 months — "run-rate" basis)
  + Stock-based compensation
    (if credit agreement excludes from EBITDA)
  + Other permitted addbacks
    (extracted by LLM from credit agreement
    definition of Consolidated EBITDA)
  − Cash taxes (if credit agreement uses
    cash-tax-adjusted EBITDA)

Step 2 — Compute Covenant Net Debt:
Covenant Net Debt =
    Total Debt (Formula 1 of Leverage metric)
  − Cash (unrestricted — per credit agreement
    definition, which may differ from GAAP)
  ± Other adjustments per credit agreement
    (e.g. certain guarantee obligations may
    be included or excluded)

Step 3 — Compute Covenant Leverage:
Covenant Leverage =
    Covenant Net Debt / Covenant EBITDA

Step 4 — Compute Adjusted Headroom:
Adjusted Headroom (absolute) =
    Covenant Threshold − Covenant Leverage
Adjusted Headroom (percentage) =
    Adjusted Headroom / Covenant Threshold × 100

Step 5 — Compute GAAP vs Covenant divergence:
Divergence =
    Covenant EBITDA − GAAP EBITDA
Divergence % =
    Divergence / GAAP EBITDA × 100
Flag if Divergence % > 20%:
    "Covenant EBITDA materially exceeds GAAP
    EBITDA — addbacks are significant; headline
    leverage flatters true financial position;
    covenant headroom may be misleadingly wide"
```

**What LLM must extract from credit agreement / Debt Footnote:**
- Full definition of "Consolidated EBITDA" or equivalent as used in the credit agreement — including the complete list of permitted addbacks
- Full definition of "Consolidated Net Debt" or "Consolidated Total Debt" as used in the credit agreement
- Any caps on addbacks (e.g. "non-recurring addbacks capped at 25% of Consolidated EBITDA")
- Pro forma treatment rules for acquisitions and dispositions
- Any step-downs in the covenant threshold over time (scheduled tightening)

**Note on addback caps:** Post-2018 leveraged loan market practice introduced caps on the total amount of addbacks permitted in the EBITDA definition — typically 25% to 35% of unadjusted EBITDA. LLM must extract whether such caps apply and compute whether current addbacks are within or approaching the cap. If addbacks are at or near the cap, the company cannot add back further items and the covenant EBITDA is effectively fixed — a deterioration in GAAP EBITDA will flow through fully to covenant leverage without any addback buffer.

---

**Formula 3 — Forward-Looking Covenant Stress Test**

Extends Formula 2 by projecting future covenant compliance under stress scenarios. This is the most analytically complete version and requires both the LLM-extracted covenant definition and the forward-looking FCF and EBITDA projections from other metrics.

```
Covenant Stress Test:

Scenario 1 — Base case (management guidance):
   Forward EBITDA = most recent LTM EBITDA
                    ± management guidance if disclosed
   Forward Net Debt = current Net Debt
                    − projected FCF (next 4 quarters)
                    + scheduled debt maturities
                      (See DEBT_MATURITY_WALL.md → Section "Formula" → Derived Output E (Projected Interest Rate Reset Impact) — use stored post-reset interest expense projection)
   Forward Leverage = Forward Net Debt / Forward EBITDA
   Forward Headroom = Covenant Threshold − Forward Leverage

Scenario 2 — Stress case (10% EBITDA decline):
   Stress EBITDA = Current EBITDA × 0.90
   Stress Net Debt = Current Net Debt
                   (assuming no FCF available for
                   debt reduction under stress)
   Stress Leverage = Stress Net Debt / Stress EBITDA
   Stress Headroom = Covenant Threshold − Stress Leverage
   Flag if Stress Headroom < 0:
       "10% EBITDA decline would breach leverage
        covenant — covenant stress test failed"

Scenario 3 — Severe stress case (20% EBITDA decline):
   Severe EBITDA = Current EBITDA × 0.80
   Same Net Debt assumption as Scenario 2
   Severe Headroom = Covenant Threshold − Severe Stress Leverage
   Flag if Severe Headroom < 0:
       "20% EBITDA decline would breach covenant"

Scenario 4 — Interest rate reset stress:
   (Requires Debt Maturity Wall Formula 3 data)
   Post-reset Interest Expense =
       Current Interest Expense
     + Projected rate reset impact
       (See DEBT_MATURITY_WALL.md → Section "Formula" → Derived Output E (Projected Interest Rate Reset Impact) — use stored post-reset interest expense projection)
   Post-reset Coverage =
       Current EBITDA / Post-reset Interest Expense
   Post-reset Coverage Headroom =
       Post-reset Coverage − Coverage Covenant Minimum
   Flag if Post-reset Coverage Headroom < 0:
       "Projected interest rate reset would breach
        coverage covenant — combined maturity wall
        and covenant stress"

Covenant Step-Down Projection:
   If covenant threshold tightens over time
   (step-down schedule extracted by LLM):
   For each step-down date:
       Projected_Threshold(date) =
           covenant threshold after step-down
       Projected_Headroom(date) =
           Projected_Threshold(date)
           − Forward_Leverage(date)
       Flag if Projected_Headroom < 0 at any date:
           "Covenant step-down on [date] projected
            to breach covenant under base case —
            step-down stress identified"
```

**What LLM must extract for Formula 3 (in addition to Formula 2 inputs):**
- Covenant step-down schedule — the specific dates and new threshold values at each step
- Management guidance on EBITDA and FCF (from MD&A Liquidity and Capital Resources section)
- Any equity cure rights — provisions allowing the company to inject equity to cure a covenant breach rather than requiring a waiver (reduces breach severity; LLM should flag if equity cure exists)
- Any EBITDA cure baskets — provisions allowing the company to add back certain items to cure a breach (less common but important to identify)

---

**Comparison Table**

| | Formula 1 — Basic Headroom | Formula 2 — Covenant-Adjusted | Formula 3 — Forward Stress Test |
|---|---|---|---|
| **Headroom definition** | GAAP ratio vs covenant threshold | Covenant-defined ratio vs threshold | Projected ratio vs current and stepped-down threshold |
| **EBITDA used** | GAAP EBITDA (Formula 1 of Leverage) | Covenant EBITDA (addbacks included) | Projected EBITDA under scenarios |
| **Net Debt used** | GAAP Net Debt | Covenant Net Debt (may differ) | Projected Net Debt (FCF-adjusted) |
| **Addbacks modelled** | ❌ No | ✅ Yes — full addback list | ✅ Yes — with addback cap check |
| **Step-down schedule** | ❌ No | ❌ No (current threshold only) | ✅ Yes — future thresholds modelled |
| **Stress scenarios** | ❌ No | ❌ No | ✅ Yes — 10% and 20% EBITDA decline |
| **Rate reset interaction** | ❌ No | ❌ No | ✅ Yes — requires Maturity Wall F3 |
| **Equity cure rights** | ❌ Not modelled | ❌ Not modelled | ✅ Identified and flagged |
| **LLM required** | ✅ Yes (threshold only) | ✅ Yes (full covenant definition) | ✅ Yes (step-downs, guidance, cure rights) |
| **Deterministic inputs** | Current ratios from prior metrics | Current ratios from prior metrics | Projected ratios from prior metrics |
| **Implementation phase** | Phase 3 | Phase 3 | Phase 3 |

---

**Implementation Guidance**

All three formulas require LLM extraction — there is no Phase 2 structured equivalent for Covenant Headroom. This is the only metric in the spec with no XBRL-extractable primary computation. The Phase 2 contribution to this metric is limited to: going concern keyword detection (already implemented for Liquidity), covenant breach disclosure keyword detection in all filing types, and flagging when the Leverage or Coverage ratios cross levels that are commonly associated with covenant thresholds in the leveraged finance market (leverage above 5.5x, coverage below 2.0x) as proxy stress signals pending Phase 3 LLM extraction.

Formula 1 is the Phase 3 starting point — extract the covenant threshold from the Debt Footnote and compute basic headroom against the GAAP ratios already available. This alone is a major analytical step forward from the Phase 2 proxy approach.

Formula 2 is the analytically correct version for leveraged issuers — it replicates what lenders actually measure. For investment-grade issuers whose covenants are typically less restrictive and whose GAAP EBITDA is closer to covenant EBITDA (fewer addbacks), Formula 1 and Formula 2 will produce similar results and the added complexity of Formula 2 may not be warranted. Apply Formula 2 selectively to issuers rated BB or below or to any issuer where the LLM identifies material addbacks in the covenant EBITDA definition.

Formula 3 is the most forward-looking capability in the entire spec. The covenant step-down projection combined with the interest rate reset stress from the Debt Maturity Wall metric produces a quantitative estimate of when a company will breach its covenants under specified assumptions — the single most valuable output the system can produce for near-term default prediction. It should be implemented once Formulas 1 and 2 are validated and stable.

The cross-metric dependency of this formula is the highest in the spec. Formula 3 Covenant Headroom requires validated outputs from: Leverage (Net Debt, EBITDA), Coverage (Interest Expense), FCF (projected FCF), Liquidity (cash), and Debt Maturity Wall (interest rate reset impact, maturity schedule). It is the culmination of the analytical framework and should be treated as the integration layer that combines all prior metric outputs into a single forward-looking stress assessment.



## Where it lives — Covenant Headroom

---

### Structural Note

Every prior metric's "Where it lives" section begins with a Formula 1 structured table of balance sheet and income statement locations. Covenant Headroom has no Formula 1 structured location because no covenant data is tagged in XBRL. This section is organised differently — by covenant type and document source rather than by formula number — because the location of covenant information depends on the type of covenant and the type of debt instrument, not on which formula version is being computed.

All covenant inputs are unstructured or semi-structured. The deterministic inputs (current ratios) are already extracted by prior metrics and reused here. The only new extraction task for this metric is finding the covenant terms themselves.

---

### Document Hierarchy for Covenant Information

Covenant terms appear in up to four locations in decreasing order of completeness and increasing order of accessibility:

| Document | Completeness | Accessibility | Contains |
|---|---|---|---|
| Credit Agreement (Exhibit 10.x) | Highest — full legal definition | Lowest — dense legal prose, hundreds of pages | Complete covenant definitions, all addbacks, step-down schedules, cure rights, cross-default provisions, full event of default list |
| Debt Footnote (in 10-K / 10-Q) | Medium — summary disclosure | Highest — standardised footnote format, 1–3 paragraphs | Key covenant thresholds, current compliance status, whether any breach has occurred, sometimes headroom disclosure |
| MD&A — Liquidity and Capital Resources | Low-medium — management summary | High — plain English narrative | Management's description of key covenants, sometimes explicit headroom disclosure, covenant compliance statement |
| 8-K Item 1.01 (when credit agreement is entered or amended) | High — full agreement filed as exhibit | Medium — filed on event date, not embedded in periodic report | Full credit agreement as exhibit; most complete source for new facilities |

**Extraction priority:** Debt Footnote first (most accessible, sufficient for Formula 1). Credit Agreement exhibit second (required for Formula 2 full addback list). MD&A third (useful for headroom disclosure and management characterisation). 8-K Item 1.01 for new or amended facilities (most current version of the agreement).

---

### Location by Covenant Type

---

**Type 1 — Maximum Leverage Covenant**

| Field | Detail |
|---|---|
| Where it lives — primary | Debt Footnote (typically Note 5–9 titled "Debt," "Long-Term Debt," or "Credit Facilities") — covenant compliance section within the note |
| Where it lives — secondary | Credit Agreement filed as Exhibit 10.x with the 10-K or the 8-K at facility origination |
| Where it lives — tertiary | MD&A — Liquidity and Capital Resources subsection |
| Available in | 10-K and 10-Q — Debt Footnote updated each period; Credit Agreement only refiled if amended |
| Exact location in Debt Footnote | Look for a paragraph or table within the Debt Footnote titled "Covenants" or "Financial Covenants" or embedded within the revolving credit or term loan description. Typical language: "The credit agreement requires us to maintain a Consolidated Net Leverage Ratio not to exceed [X.Xx] to 1.00 as of the last day of each fiscal quarter." Some companies include a compliance table showing actual vs required ratio. |
| What LLM should extract | (1) Covenant threshold value (e.g. 5.5x), (2) definition of the ratio as stated (e.g. "Consolidated Net Leverage Ratio" — note exact name used), (3) testing frequency (quarterly is most common), (4) whether any step-down schedule is disclosed (e.g. "reducing to 5.0x after [date]"), (5) whether the company is currently in compliance, (6) any disclosed headroom amount if management provides it |
| Exact location in Credit Agreement | Section titled "Financial Covenants" or "Section 7.11" or similar — varies by agreement. The definition of "Consolidated EBITDA" or "Consolidated Adjusted EBITDA" will be in the definitions section (Section 1.01 in most agreements) and may span multiple pages with extensive addback lists. |
| What LLM should extract from Credit Agreement | Complete definition of Consolidated EBITDA including: (1) starting point (GAAP net income or GAAP EBITDA), (2) each individual addback item, (3) any caps on addbacks (e.g. "not to exceed 25% of Consolidated EBITDA"), (4) pro forma treatment rules, (5) look-back period (typically trailing twelve months) |

---

**Type 2 — Minimum Interest Coverage Covenant**

| Field | Detail |
|---|---|
| Where it lives — primary | Debt Footnote — same covenant section as leverage covenant, often in the same paragraph or adjacent table |
| Where it lives — secondary | Credit Agreement — Financial Covenants section, same location as leverage covenant |
| Available in | 10-K and 10-Q |
| Exact location in Debt Footnote | Typical language: "The credit agreement requires us to maintain a Consolidated Interest Coverage Ratio of not less than [X.Xx] to 1.00." Or combined with leverage in a single covenant compliance table. |
| What LLM should extract | (1) Coverage covenant threshold (e.g. 2.0x minimum), (2) definition of the ratio — specifically whether numerator is EBITDA or EBIT, and whether denominator is gross or net interest expense, (3) testing frequency, (4) step-down schedule if any (coverage covenants may step up over time — requiring higher coverage — rather than stepping down), (5) current compliance status |
| Note on coverage covenant prevalence | Coverage maintenance covenants are more common in leveraged bank loans than in high-yield bonds. Many high-yield bond indentures contain only incurrence-based coverage tests — not maintenance tests. LLM must distinguish between the two and flag: "coverage covenant is incurrence-based not maintenance-based — does not trigger acceleration if breached; only limits ability to incur additional debt." |

---

**Type 3 — Minimum Liquidity Covenant**

| Field | Detail |
|---|---|
| Where it lives — primary | Debt Footnote — covenant section, sometimes in a separate liquidity or availability covenant paragraph |
| Where it lives — secondary | Credit Agreement — Financial Covenants section |
| Available in | 10-K and 10-Q |
| Exact location in Debt Footnote | Two common forms: (a) Minimum cash: "The credit agreement requires us to maintain unrestricted cash and cash equivalents of not less than $[X] million at all times." (b) Minimum availability: "The credit agreement requires that we maintain minimum availability under the revolving credit facility of not less than $[X] million (the 'Availability Block')." The availability block form is particularly common in asset-based lending (ABL) facilities. |
| What LLM should extract | (1) Minimum threshold amount in dollars, (2) whether it is a minimum cash covenant or a minimum availability covenant or both, (3) whether it is tested continuously or at period-end, (4) definition of "unrestricted cash" or "availability" per the credit agreement — these may differ from the GAAP definitions used in the Liquidity metric, (5) whether a springing covenant exists: "this covenant is only tested when availability falls below $[X] million" — springing covenants are inactive until triggered by low revolver availability |
| Springing covenant note | Springing covenants are common in ABL facilities and some revolving credit facilities. They are invisible when availability is ample but activate automatically when availability tightens — at exactly the moment the company is most stressed. LLM must flag the existence of any springing covenant and the trigger level even if the covenant is currently inactive. |

---

**Type 4 — Maximum Capital Expenditure Covenant**

| Field | Detail |
|---|---|
| Where it lives — primary | Debt Footnote — covenant section |
| Where it lives — secondary | Credit Agreement — Financial Covenants section |
| Available in | 10-K and 10-Q |
| Exact location | Less common than leverage and coverage covenants. When present: "The credit agreement restricts annual capital expenditures to not more than $[X] million per fiscal year." Some agreements include rollover provisions: "unused capex allowance from one year may be carried forward to the next year up to $[X] million." |
| What LLM should extract | (1) Annual capex limit, (2) rollover provisions, (3) current period capex vs limit — headroom in dollar terms, (4) whether growth capex and maintenance capex are treated differently |
| Prevalence note | Capex covenants are more common in smaller leveraged transactions and less common in large investment-grade facilities. For your 30-issuer portfolio of corporate bond names, capex covenants are unlikely to be material for most issuers but should be checked for any high-yield or leveraged names. |

---

**Type 5 — Incurrence Covenants (High-Yield Bond Indentures)**

| Field | Detail |
|---|---|
| Where it lives | Bond Indenture filed as Exhibit 4.x with the 10-K or the 8-K at bond issuance (424B filing includes indenture as exhibit) |
| Available in | Filed at issuance; summarised in Debt Footnote |
| Exact location | High-yield bond indentures contain: (a) Debt incurrence covenant: "Issuer may not incur additional debt unless on a pro forma basis the Fixed Charge Coverage Ratio is at least [X.Xx] to 1.00." (b) Restricted payments covenant: limits dividends and share buybacks. (c) Asset sale covenant. (d) Merger covenant. These are summarised in the Debt Footnote in language such as: "The indenture governing the Senior Notes contains covenants that, among other things, restrict our ability to incur additional indebtedness..." |
| What LLM should extract | (1) Fixed charge coverage ratio threshold for debt incurrence, (2) current ratio vs threshold — is the company able to incur additional debt under the indenture, (3) whether the restricted payments basket is being used (dividends, buybacks reducing the basket), (4) any fallen angel provisions — covenants that tighten if the bonds are downgraded below a certain rating |
| Critical distinction | Incurrence covenants do not trigger acceleration if breached — they only prohibit the company from taking the specified action. If a company cannot pass the debt incurrence test, it cannot issue new debt under the general basket (though it may use other permitted debt baskets). This is a financial flexibility constraint, not a default trigger. Flag clearly: "incurrence covenant — does not trigger acceleration; limits future debt issuance capacity." |

---

**Covenant Compliance Disclosure — Where Management States It**

Beyond the individual covenant term locations, companies are required under US GAAP (ASC 470) to disclose whether they are in compliance with debt covenants and whether any covenant violations have occurred. This compliance statement is the highest-priority LLM extraction target because it directly answers the binary breach question without requiring ratio computation.

| Disclosure Type | Where it Lives | What to Look For |
|---|---|---|
| Compliance affirmation | Debt Footnote — end of covenant description | "As of [date], we were in compliance with all financial covenants." This is the standard boilerplate for compliant companies — important to confirm it is present. |
| Breach disclosure | Debt Footnote OR MD&A OR separate Going Concern disclosure | "As of [date], we were not in compliance with the [covenant name] financial covenant..." — triggers immediate Critical alert |
| Waiver disclosure | Debt Footnote | "On [date], we obtained a waiver from our lenders with respect to [covenant]..." — breach confirmed; waiver obtained |
| Amendment disclosure | Debt Footnote OR 8-K Item 1.01 | "On [date], we amended our credit agreement to [modify covenant threshold / add addbacks / reset step-down schedule]..." — financial flexibility being renegotiated |
| Substantial doubt | Auditor's Report OR MD&A | Going concern language — highest urgency signal; already monitored via keyword search in Liquidity and Maturity Wall metrics |

---

**Headroom Voluntary Disclosure**

Some companies — particularly those with thin headroom managing investor relations — voluntarily disclose their covenant headroom explicitly rather than requiring the analyst to compute it. This is the most reliable source when available.

| Field | Detail |
|---|---|
| Where it lives | MD&A — Liquidity and Capital Resources subsection AND investor presentations (not in SEC filings — external source only) |
| Available in | 10-K and 10-Q (MD&A); investor day presentations (external — not monitored by this system) |
| Exact location | MD&A Liquidity section. Look for sentences such as: "As of [date], our Consolidated Net Leverage Ratio was [X.Xx]x compared to a maximum permitted ratio of [Y.Yy]x, providing headroom of [Z.Zz]x." Or a compliance table showing actual vs required for each covenant. |
| What LLM should extract | Any explicitly disclosed headroom figures. Store as "management-disclosed headroom" separately from system-computed headroom. Compare the two — if management-disclosed headroom differs materially from system-computed headroom, flag: "management-disclosed headroom diverges from system computation — verify covenant definition differences." |
| Note on voluntary disclosure | Companies with ample headroom rarely disclose it explicitly — there is no incentive. Companies with thin headroom sometimes disclose it to reassure investors. The very act of voluntary headroom disclosure can itself be a signal that the company is aware investors are concerned. |

---

**Summary Table — Where Each Item Lives**

| Item | Covenant Type | Primary Document | Section | Available In |
|---|---|---|---|---|
| Maximum leverage threshold | Leverage covenant | Debt Footnote | Covenant compliance section | 10-K and 10-Q |
| Full leverage covenant definition (addbacks) | Leverage covenant | Credit Agreement (Exhibit 10.x) | Financial Covenants + Definitions sections | 10-K (at origination or amendment) |
| Covenant step-down schedule | Leverage covenant | Debt Footnote + Credit Agreement | Covenant section + Financial Covenants | 10-K primarily |
| Minimum coverage threshold | Coverage covenant | Debt Footnote | Covenant compliance section | 10-K and 10-Q |
| Coverage covenant definition | Coverage covenant | Credit Agreement | Financial Covenants + Definitions | 10-K (at origination) |
| Minimum liquidity / cash threshold | Liquidity covenant | Debt Footnote | Covenant compliance section | 10-K and 10-Q |
| Springing covenant trigger level | Liquidity covenant | Debt Footnote + Credit Agreement | Covenant section + Financial Covenants | 10-K primarily |
| Maximum capex limit | Capex covenant | Debt Footnote | Covenant section | 10-K and 10-Q |
| Incurrence covenant threshold | High-yield indenture | Indenture (Exhibit 4.x) + Debt Footnote | Restricted payments / debt incurrence | 10-K (at issuance) |
| Covenant compliance affirmation | All types | Debt Footnote | End of covenant description | 10-K and 10-Q |
| Covenant breach disclosure | All types | Debt Footnote + MD&A | Covenant section + Liquidity discussion | 10-K and 10-Q |
| Waiver or amendment disclosure | All types | Debt Footnote + 8-K Item 1.01 | Covenant section + material agreement | 10-K, 10-Q, and 8-K |
| Voluntary headroom disclosure | All types | MD&A | Liquidity and Capital Resources | 10-K and 10-Q |
| Addback cap | Leverage covenant | Credit Agreement | Definitions section — Consolidated EBITDA | 10-K (at origination) |
| Equity cure rights | All types | Credit Agreement | Financial Covenants | 10-K (at origination) |
| Pro forma treatment rules | Leverage covenant | Credit Agreement | Definitions section | 10-K (at origination) |

---

**Critical Note on Credit Agreement Availability**

The Credit Agreement is filed as an exhibit (Exhibit 10.x) with the 10-K or with the 8-K Item 1.01 at the time the facility is entered into or materially amended. Subsequent 10-K filings incorporate it by reference rather than refiling the full document — meaning the most current version of the credit agreement may be in an 8-K filed months or years before the current 10-K.

```
Credit Agreement location strategy:

Step 1 — Check current 10-K exhibit index for
          Exhibit 10.x files with titles containing:
          "Credit Agreement," "Loan Agreement,"
          "Credit and Guaranty Agreement,"
          "Revolving Credit Agreement"

Step 2 — If current 10-K incorporates by reference:
          Trace back to the original filing date of
          the credit agreement — this is the 8-K Item
          1.01 filing when the facility was entered into

Step 3 — Check for subsequent amendments:
          Search 8-K Item 1.01 filings since the
          original credit agreement date for
          "Amendment No. [X] to Credit Agreement"
          The most recent amendment is the operative
          document — prior versions may be superseded

Step 4 — EDGAR full-text search:
          Use EDGAR EFTS (full-text search) to search
          for the company's CIK + "credit agreement"
          to find all related filings in chronological
          order

Step 5 — If credit agreement is not publicly filed:
          Some private credit facilities are not filed
          as exhibits (particularly bilateral facilities
          below materiality thresholds).
          Fall back to Debt Footnote summary only.
          Flag: "credit agreement not publicly filed —
          covenant definition based on footnote
          summary only; addback list may be incomplete"
```

## Structured or Unstructured — Covenant Headroom Metric (All Three Formulas)

| Input / Component | Formula | Source Document | Structured or Unstructured | Notes |
|---|---|---|---|---|
| **Current Leverage Ratio** | F1, F2, F3 | See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored Net Debt/EBITDA ratio; no re-extraction required. | Structured — reused from prior metric | Net Debt / EBITDA computed deterministically from XBRL. No re-extraction needed — pull from stored Leverage metric output for same period. If Leverage Formula 1 null for this period: Covenant Headroom F1 = null; flag: "leverage ratio unavailable — headroom cannot be computed." |
| **Current Coverage Ratio** | F1, F2, F3 | See INTEREST_COVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored EBITDA/Interest ratio; no re-extraction required. | Structured — reused from prior metric | EBITDA / Interest Expense computed deterministically. Pull from stored Coverage metric output. Same null propagation rule as leverage ratio. |
| **Current Cash / Available Liquidity** | F1, F2, F3 | See LIQUIDITY.md → Section "Formula" → Formula 1 outputs — reuse stored values; no re-extraction required. | Structured — reused from prior metric | Cash and available liquidity already extracted. Pull from stored Liquidity metric output. For liquidity covenant headroom only. |
| **Current Capex** | F1 (capex covenant only) | Cash Flow Statement — Investing Activities | Structured — XBRL tagged | `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` — already extracted for FCF metric. Reuse stored value. |
| **Covenant Compliance Text** | F1, F2, F3 | XBRL — DebtInstrumentCovenantCompliance | **Semi-structured — XBRL tag exists; content is free text requiring keyword analysis** | Tag exists in US GAAP taxonomy. Returns a text string, not a binary flag. Filer adoption inconsistent. When populated: keyword scan for breach/compliance. When null: fall back to LLM Debt Footnote extraction. Never treat null as compliance. |
| **Maximum Leverage Covenant Threshold** | F1, F2, F3 | Debt Footnote — covenant compliance section | **Unstructured — LLM required** | No XBRL tag exists. LLM reads Debt Footnote covenant section. Extracts numeric threshold (e.g. 5.5x) and exact covenant name as stated in filing. If not found in Debt Footnote: escalate to Credit Agreement Exhibit 10.x. If neither source yields threshold: headroom = null; flag: "leverage covenant threshold not extracted — headroom computation not possible." |
| **Minimum Coverage Covenant Threshold** | F1, F2, F3 | Debt Footnote — covenant compliance section | **Unstructured — LLM required** | Same extraction approach as leverage threshold. LLM must also identify whether this is a maintenance covenant (tested every period — relevant for headroom) or an incurrence covenant (tested only on action — flag as non-maintenance; not a default trigger). |
| **Minimum Liquidity Covenant Threshold** | F1, F2, F3 | Debt Footnote — covenant compliance section | **Unstructured — LLM required** | Dollar amount not a ratio. LLM extracts minimum cash balance or minimum revolver availability required. Must also identify whether springing covenant — if so, extract trigger level as well as threshold. Flag springing covenant existence even if currently inactive. |
| **Maximum Capex Covenant Threshold** | F1 (if present) | Debt Footnote — covenant compliance section | **Unstructured — LLM required** | Less common than leverage and coverage covenants. LLM extracts annual capex limit in dollars. Also extracts rollover provisions if present. If no capex covenant found: flag as absent — not an error. |
| **Covenant Testing Frequency** | F1, F2, F3 | Debt Footnote | **Unstructured — LLM required** | Most maintenance covenants tested quarterly. Some tested semi-annually or annually. LLM extracts: "tested as of the last day of each fiscal quarter" or equivalent. Flag if non-quarterly: "covenant tested [frequency] — headroom alerts only actionable at test dates." |
| **Covenant Compliance Affirmation** | F1, F2, F3 | Debt Footnote — end of covenant description | **Unstructured — LLM required** | LLM searches for standard compliance boilerplate: "As of [date], we were in compliance with all financial covenants." Absence of this statement is itself a flag — most companies include it if compliant. Flag if absent: "no covenant compliance affirmation found — verify whether company is in compliance." |
| **Covenant Breach Disclosure** | F1, F2, F3 | Debt Footnote + MD&A + Auditor's Report | **Unstructured — LLM required** | Highest priority extraction in this metric. LLM searches for: "not in compliance," "covenant violation," "event of default," "waiver," "breach." If any breach language found: IMMEDIATE CRITICAL ALERT regardless of all other metric outputs. |
| **Waiver or Amendment Disclosure** | F1, F2, F3 | Debt Footnote + 8-K Item 1.01 | **Unstructured — LLM required** | LLM extracts: waiver date, which covenant was waived, waiver expiry date if any, and any conditions attached to waiver. Amendment: new threshold values, new step-down schedule, new addback list. Store waiver as confirmed breach signal even after resolution. |
| **Covenant Step-Down Schedule** | F1, F2, F3 | Debt Footnote + Credit Agreement | **Unstructured — LLM required** | LLM extracts future threshold values and their effective dates. Example: "maximum leverage of 5.5x through Q2 2025, reducing to 5.0x thereafter." Store as array of {date, threshold} pairs. Used in Formula 3 forward stress test. Available in 10-K primarily; may be updated in 10-Q if amendment occurs. |
| **Voluntary Headroom Disclosure** | F1, F2, F3 | MD&A — Liquidity and Capital Resources | **Unstructured — LLM required** | LLM searches for explicit headroom figures disclosed by management. Store separately as "management-disclosed headroom" — do not replace system-computed headroom. Flag divergence > 10% between management-disclosed and system-computed headroom. |
| **Covenant EBITDA Definition** | F2, F3 | Credit Agreement — Definitions section (Exhibit 10.x) | **Unstructured — LLM required (extensive)** | Most complex extraction in this metric. LLM reads full "Consolidated EBITDA" or "Consolidated Adjusted EBITDA" definition from credit agreement. Extracts: (1) starting point, (2) each addback item individually, (3) any addback caps with specific percentages, (4) look-back period. Returns structured JSON list of addback items. May require reading 5–15 pages of legal definitions. Flag: "covenant EBITDA definition extracted from credit agreement dated [date] — verify most recent amendment." |
| **Individual Addback Items** | F2, F3 | Credit Agreement — Consolidated EBITDA definition | **Unstructured — LLM required** | LLM extracts each addback item separately: restructuring charges, non-recurring items, SBC, management fees, pro forma synergies, etc. System applies each addback to GAAP EBITDA to compute Covenant EBITDA. Addback cap check: if cap present, verify sum of capped addbacks does not exceed cap. Flag: "addbacks at [X]% of cap — [Y]% of addback capacity remaining." |
| **Addback Cap** | F2, F3 | Credit Agreement — Consolidated EBITDA definition | **Unstructured — LLM required** | LLM extracts cap percentage and the base to which it applies (e.g. "25% of Consolidated EBITDA before such addbacks"). Critical for companies where addbacks are large — a binding cap means GAAP EBITDA deterioration flows through fully to Covenant Leverage once the cap is reached. |
| **Covenant Net Debt Definition** | F2, F3 | Credit Agreement — Definitions section | **Unstructured — LLM required** | LLM extracts any differences between credit agreement Net Debt and GAAP Net Debt. Common differences: restricted cash treatment, guarantees included or excluded, certain off-balance sheet items. Usually minor for straightforward capital structures; material for complex ones. |
| **Pro Forma Treatment Rules** | F2, F3 | Credit Agreement — Definitions section | **Unstructured — LLM required** | LLM extracts rules for treating recent acquisitions and dispositions on a pro forma basis when computing covenant ratios. Example: "EBITDA of any acquired entity may be included on a pro forma basis if the acquisition closed within the trailing twelve-month period." These rules can materially increase Covenant EBITDA for acquisitive companies. |
| **Equity Cure Rights** | F2, F3 | Credit Agreement — Financial Covenants section | **Unstructured — LLM required** | LLM extracts whether company has the right to inject equity to cure a covenant breach, the mechanics (amount required, timing, frequency limits), and whether cure has been used in prior periods. Flag if cure has been used: "equity cure previously exercised — repeat use may be restricted; verify remaining cure capacity." |
| **Incurrence Covenant Threshold** | F1 (informational) | Indenture (Exhibit 4.x) + Debt Footnote | **Unstructured — LLM required** | High-yield bond indentures only. LLM extracts fixed charge coverage ratio threshold for debt incurrence test. Determines whether company can issue additional debt under the general basket. Flag clearly as incurrence (not maintenance) — does not trigger acceleration. Current ratio vs threshold indicates remaining debt capacity. |
| **Springing Covenant Trigger Level** | F1, F3 | Credit Agreement + Debt Footnote | **Unstructured — LLM required** | LLM extracts the availability level at which the springing covenant activates. Example: "this covenant is only tested when revolver availability falls below $50 million." Store trigger level separately from the covenant threshold itself. Daily monitoring: if revolver availability approaches trigger level, pre-flag as "springing covenant risk — availability at [X]% of trigger level." |
| **Forward EBITDA Projection** | F3 | MD&A — Liquidity and Capital Resources | **Unstructured — LLM required** | LLM extracts management guidance on expected EBITDA or FCF if disclosed. If not disclosed: system uses trailing twelve-month EBITDA as base case. Flag all projections: "forward EBITDA based on [management guidance / TTM run-rate]." |
| **Covenant Headroom — Basic** (derived F1) | F1 | Derived from LLM threshold + structured ratio | **Hybrid — unstructured threshold + structured ratio** | Headroom = Covenant Threshold − Current Ratio (maximum covenants) or Current Ratio − Covenant Threshold (minimum covenants). If either input null → headroom null. Computation is deterministic once threshold is extracted. |
| **Covenant Headroom — Adjusted** (derived F2) | F2 | Derived from LLM covenant definition + structured inputs | **Hybrid — extensive unstructured inputs** | Headroom = Covenant Threshold − Covenant Leverage (using Covenant EBITDA and Covenant Net Debt). Requires full addback computation. All addback amounts sourced from XBRL where tagged (restructuring: `us-gaap:RestructuringCharges`; SBC: `us-gaap:ShareBasedCompensation`) or LLM where not tagged. |
| **Forward Stress Test Results** (derived F3) | F3 | Derived from all prior inputs + scenarios | **Hybrid — all inputs combined** | Scenario outputs are deterministic computations once all inputs are established. The inputs themselves are the unstructured bottleneck. Each scenario result stored separately with scenario label, assumption set, and breach flag. |

---

**Quick Reference — Structured vs Unstructured Summary**

| Category | Items | Method | Phase |
|---|---|---|---|
| **Fully structured (reused from prior metrics)** | Current leverage, coverage, liquidity, capex | XBRL — already extracted | Phase 2 (proxy only) / Phase 3 |
| **Fully unstructured — Debt Footnote LLM** | Covenant thresholds (all types), compliance affirmation, breach disclosure, waiver, step-down schedule, voluntary headroom, testing frequency | LLM — Debt Footnote | Phase 3 |
| **Fully unstructured — Credit Agreement LLM** | Covenant EBITDA definition, addback list, addback cap, Net Debt definition, pro forma rules, equity cure rights, springing covenant trigger | LLM — Exhibit 10.x | Phase 3 |
| **Fully unstructured — Indenture LLM** | Incurrence covenant threshold | LLM — Exhibit 4.x | Phase 3 |
| **Fully unstructured — MD&A LLM** | Voluntary headroom disclosure, forward EBITDA guidance | LLM — MD&A section | Phase 3 |
| **Hybrid (unstructured threshold + structured ratio)** | Basic headroom computation, adjusted headroom computation, forward stress test | LLM threshold + XBRL ratio → deterministic computation | Phase 3 |
| **XBRL tagged addback components** | Restructuring charges, SBC, D&A, pension contributions | XBRL — already extracted for prior metrics | Phase 3 (reused) |

---

**Key Difference From All Prior Metrics**

Every prior metric has at least one Formula 1 output that is fully structured from XBRL with no LLM dependency. Covenant Headroom has no such output. The minimum viable computation — basic headroom — requires at minimum one LLM extraction (the covenant threshold) that cannot be sourced from any structured data. This makes Covenant Headroom the only metric in the spec that is entirely dependent on LLM extraction for its primary analytical output and the only metric with no Phase 2 structured equivalent beyond the proxy approach of monitoring whether ratios cross market-convention covenant levels.

The Phase 2 proxy approach (flagging when leverage exceeds 5.5x or coverage falls below 2.0x as approximate covenant breach signals) provides a rough directional signal but will produce both false positives (companies with covenants above 5.5x) and false negatives (companies with covenants below 5.5x). It should be clearly labeled in all Phase 2 outputs as a proxy, not a covenant headroom computation.


## Extraction Fallback Logic — Covenant Headroom Metric

---

### Design Principles

Same four universal rules apply, plus five additional rules specific to Covenant Headroom:

**Rule 1 — Never substitute zero for a missing input.** A missing covenant threshold does not mean no covenant exists. Mark null and escalate.

**Rule 2 — Try every fallback before giving up.** Debt Footnote → Credit Agreement → MD&A → prior filing → proxy. Exhaust all sources before declaring failure.

**Rule 3 — Log what you used.** Every headroom figure records which document was the source of the threshold and which formula version was applied.

**Rule 4 — Never compute headroom against an assumed threshold.** Do not default to industry-average covenant levels. A 5.5x assumed leverage covenant for a company that actually has a 4.0x covenant would produce dangerously misleading headroom. Null is always safer than an assumed value.

**Rule 5 — Covenant breach disclosure overrides all other logic.** If any filing contains language indicating a covenant breach, waiver, or amendment, this triggers an immediate Critical alert before any headroom computation. Do not attempt to compute headroom after a breach is detected — the ratio comparison is irrelevant once the legal event has occurred.

**Rule 6 — Maintenance vs incurrence distinction is mandatory.** Extracting a covenant threshold without correctly classifying it as maintenance or incurrence produces a fundamentally misleading output. A maintenance coverage covenant of 2.0x is a default trigger. An incurrence coverage covenant of 2.0x is a borrowing constraint. The system must never conflate the two.

**Rule 7 — Credit agreement version control is critical.** The most recent amendment to the credit agreement supersedes all prior versions. If the system uses an outdated threshold from a prior credit agreement version — without applying subsequent amendments — it will compute headroom against the wrong number. Every extracted threshold must be tagged with the date of the credit agreement version from which it was sourced, and the system must check for amendments since that date.

**Rule 8 — The Phase 2 proxy is clearly labeled and never upgraded.** The proxy approach (flagging leverage > 5.5x or coverage < 2.0x) is an interim measure only. It must be labeled "proxy — actual covenant terms not yet extracted" on every output. It must never be silently upgraded to appear as if actual covenant terms were used. When Phase 3 LLM extraction produces actual terms, the proxy is replaced — not supplemented — and the output label updated.

---

### Detection Priority Table (Updated)

The original design had keyword scanning of the Debt Footnote as the first breach detection step. With this tag added, the updated detection priority is:

| Priority | Method | Speed | Reliability | Phase |
|---|---|---|---|---|
| 1 | `DebtInstrumentCovenantCompliance` XBRL tag keyword scan | Fastest — API query + keyword match | Moderate — only works if filer populates tag | Phase 2 |
| 2 | 8-K Item 1.01 keyword scan (waiver / amendment) | Fast — within 4 business days of event | High — companies file 8-K when seeking waiver | Phase 2 |
| 3 | LLM keyword scan of Debt Footnote | Medium — requires LLM call per filing | Highest — directly reads disclosure text | Phase 3 |
| 4 | LLM keyword scan of MD&A | Medium | High | Phase 3 |
| 5 | LLM keyword scan of Auditor's Report | Medium | High — auditor language is precise | Phase 3 |
| 6 | Ratio-based breach inference (ratio > covenant threshold) | Same as quarterly filing lag | Moderate — requires threshold already extracted | Phase 3 |

---

### Pre-Extraction Step — Covenant Existence Check

Before attempting any threshold extraction, the system must first establish whether financial maintenance covenants exist for this issuer. Not all debt carries maintenance covenants.

```
Step 0 — Covenant existence screening:

Check issuer's debt profile (from Debt Maturity
Wall extraction):
   Revolving credit facility: almost always has
   maintenance covenants → proceed to extraction
   Term loan A (amortising): almost always has
   maintenance covenants → proceed
   Term loan B (leveraged): usually has maintenance
   covenants but may be "covenant-lite" → check
   High-yield bonds: almost never have maintenance
   covenants → extract incurrence covenants only;
   flag: "high-yield bond issuer — maintenance
   covenants unlikely; incurrence covenants extracted"
   Investment-grade revolving facility: often has
   maintenance covenants but may be looser →
   proceed with lower urgency

"Covenant-lite" detection:
   LLM reads Debt Footnote for language indicating:
   "covenant-lite," "cov-lite," "no financial
   maintenance covenants," or absence of any
   covenant compliance statement.
   If covenant-lite confirmed:
      Flag: "covenant-lite facility — no financial
      maintenance covenants; acceleration risk from
      financial ratios absent; incurrence covenants
      only"
      Skip maintenance covenant extraction
      Proceed to incurrence covenant extraction only
      This is important context — covenant-lite
      issuers have more operational flexibility
      but lenders have less protection
```

---


### Input 0 — Covenant Compliance XBRL Tag

```
Input 0 — Covenant Compliance XBRL Tag
(runs before all other covenant extraction)

Step 0A — Query EDGAR companyconcept API:
   https://data.sec.gov/api/xbrl/companyconcept/
   CIK{number}/us-gaap/
   DebtInstrumentCovenantCompliance.json

   Select the entry matching current filing
   period end date.
   Extract the string value.

Step 0B — If tag returns a non-null string:
   Apply keyword scan to the string value:

   Breach keywords (trigger Critical alert):
   "not in compliance"
   "covenant violation"
   "event of default"
   "failed to comply"
   "breach"
   "waiver"
   "forbearance"

   Compliance keywords (positive signal):
   "in compliance with all"
   "in compliance with each"
   "satisfied all"
   "met all financial covenant"

   Ambiguous / needs LLM:
   Any string longer than 200 characters
   Any string not matching either keyword set
   Any string containing "however," "except,"
   "subject to," "notwithstanding" — these
   hedging terms may qualify a compliance
   statement with undisclosed exceptions

Step 0C — Classify result:

   If breach keyword found:
      IMMEDIATE CRITICAL ALERT
      Flag: "covenant breach language detected
      in DebtInstrumentCovenantCompliance
      XBRL tag — [keyword found]; LLM extraction
      required to confirm and detail"
      Escalate to full LLM extraction (Input 1
      in prior fallback logic) for detail
      Do NOT stop at tag value alone — get full
      footnote context

   If compliance keyword found AND string
   is short and unambiguous (< 100 chars):
      Store as: "compliance_confirmed_xbrl = true"
      Source: "us-gaap:DebtInstrumentCovenantCompliance"
      Still proceed to LLM extraction for
      threshold and headroom computation
      Tag this as a fast compliance signal
      not a substitute for full extraction

   If ambiguous or long string:
      Pass full string to LLM for interpretation
      LLM determines: compliant / breach /
      waiver / ambiguous
      Log: "XBRL covenant tag value passed to LLM
      for interpretation — string length [N] chars"

Step 0D — If tag returns null:
   Log: "DebtInstrumentCovenantCompliance tag
   absent — filer did not populate; proceeding
   to LLM Debt Footnote extraction"
   Do NOT treat null as compliance confirmation
   Proceed to Input 1 (Debt Footnote LLM)
   without generating any alert from this step

Step 0E — Coverage across portfolio:
   Track which issuers in the 30-name portfolio
   populate this tag and which do not.
   At Phase 2 onboarding: check each issuer's
   most recent 10-K for tag presence.
   Issuers that populate it: activate XBRL
   pre-screening at each quarterly filing.
   Issuers that do not: skip Step 0A-0C;
   go directly to Phase 2 proxy or Phase 3 LLM.
```
---

### Input 1 — Covenant Thresholds (All Types)

**Primary path — Debt Footnote LLM extraction:**

```
Step 1 — LLM reads Debt Footnote covenant section.
          Target language patterns:
          "not to exceed [X.Xx] to 1.00"
          "not less than [X.Xx] to 1.00"
          "maintain a [ratio name] of at least [X.Xx]"
          "maximum [ratio name] of [X.Xx]"
          "minimum [amount] of $[X] million"

          For each covenant found, extract:
          {
            "covenant_type": "leverage/coverage/
                             liquidity/capex/other",
            "covenant_class": "maintenance/incurrence",
            "threshold_value": X.Xx or $X million,
            "threshold_direction": "maximum/minimum",
            "ratio_name_as_stated": "exact name in filing",
            "testing_frequency": "quarterly/semi-annual/
                                  annual/continuous",
            "effective_date": "YYYY-MM-DD",
            "source_document": "Debt Footnote",
            "source_quote": "verbatim sentence from filing",
            "compliance_confirmed": true/false/null,
            "breach_disclosed": true/false
          }

Step 2 — Verify threshold against compliance
          statement if present:
          If company discloses actual ratio AND
          threshold in the same table or sentence:
          Cross-check: extracted threshold should
          match disclosed threshold exactly.
          If mismatch: flag and use disclosed figure
          as authoritative.

Step 3 — Check for step-down schedule:
          LLM looks for language like:
          "reducing to [X.Xx] on [date]"
          "stepping down to [X.Xx] as of [quarter]"
          Extract array:
          [{"effective_date": "YYYY-MM-DD",
            "threshold": X.Xx}, ...]
          Flag if step-down within 4 quarters:
          "covenant step-down approaching [date] —
          headroom will narrow by [X.Xx]x at step-down
          even if financial performance is unchanged"

Step 4 — If Debt Footnote yields partial or no results:
          Proceed to Credit Agreement extraction (Step 5)
```

**Secondary path — Credit Agreement LLM extraction:**

```
Step 5 — Identify most recent credit agreement version:
          Check 10-K exhibit index for Exhibit 10.x
          containing "Credit Agreement"
          Check 8-K Item 1.01 filings since
          credit agreement date for amendments
          Use most recent version — flag document
          date: "threshold from Credit Agreement
          dated [date], Amendment No. [X] dated [date]"

Step 6 — LLM reads Financial Covenants section:
          Typically Section 7.11 or Section 6.11
          or titled "Financial Covenants"
          Extract same fields as Step 1
          Additionally extract:
          Full ratio definition (numerator and
          denominator as defined in agreement)

Step 7 — LLM reads Definitions section for
          Consolidated EBITDA definition:
          (Formula 2 only — not required for F1)
          Returns structured addback list:
          {
            "starting_point": "GAAP net income /
                               GAAP EBITDA / other",
            "addbacks": [
              {"item": "restructuring charges",
               "cap": null,
               "notes": "no cap specified"},
              {"item": "non-recurring charges",
               "cap": "25% of Consolidated EBITDA",
               "notes": "capped addback"},
              {"item": "stock-based compensation",
               "cap": null,
               "notes": "uncapped"},
              ...
            ],
            "look_back_period": "trailing twelve months",
            "addback_cap_aggregate":
               "25% of pre-addback EBITDA",
            "source_document": "Credit Agreement
                                 dated [date]",
            "confidence": "high/medium/low"
          }

Step 8 — If Credit Agreement not publicly filed:
          Flag: "credit agreement not publicly filed —
          threshold from Debt Footnote only; addback
          list unavailable; Formula 2 not computable"
          Proceed with Formula 1 only
```

**Tertiary path — MD&A voluntary disclosure:**

```
Step 9 — LLM reads MD&A Liquidity and Capital
          Resources section for explicit headroom
          disclosure:
          Look for: actual ratio disclosed alongside
          covenant threshold in same sentence or table.
          If found: extract both actual ratio and
          threshold; compute headroom from MD&A figures
          Store as "management-disclosed" separately
          from system-computed.
          Flag if management figures diverge from
          system computation by >10%.

Step 10 — Check prior filing for unchanged covenant:
           If current filing's Debt Footnote contains
           no covenant threshold but prior filing did:
           Check whether credit agreement has been
           amended since prior filing.
           If no amendment detected:
              Use prior filing threshold with flag:
              "threshold from [prior filing date] —
              no amendment detected; verify unchanged"
           If amendment detected but new threshold
           not extractable:
              Set threshold = null
              Flag: "credit agreement amended —
              prior threshold superseded; new threshold
              not extracted; headroom computation
              suspended pending manual review"
```

**Failure path:**

```
Step 11 — If all paths return null for threshold:
           Set Threshold = null
           Set Headroom = null
           Flag: "covenant threshold not extracted
           from any available source"

           Apply Phase 2 proxy ONLY if in Phase 2:
           Proxy_Flag = true if:
             Current Leverage > 5.5x (proxy for
             typical leveraged loan covenant level)
             OR Current Coverage < 2.0x
           Flag prominently:
           "PROXY ALERT — actual covenant terms
           not extracted; alert based on market-
           convention threshold approximation only;
           actual covenant may differ materially"

           Do NOT apply proxy in Phase 3 after
           LLM extraction has been attempted —
           a failed Phase 3 extraction should
           result in null, not a proxy fallback
```

---

### Input 2 — Addback Computation (Formula 2)

```
Once Covenant EBITDA definition extracted:

For each addback item in extracted list:

Step 1 — Identify XBRL tag for this addback:
   Restructuring: us-gaap:RestructuringCharges
   SBC: us-gaap:ShareBasedCompensation
   D&A: us-gaap:DepreciationDepletionAndAmortization
   Pension: us-gaap:PensionContributions
   Non-cash impairment: us-gaap:AssetImpairmentCharges

Step 2 — If XBRL tag available and non-null:
   Use XBRL value for this addback item.
   Log: "addback [item] from XBRL tag [tag]"

Step 3 — If XBRL tag null or addback not
   covered by a standard tag:
   LLM extracts from income statement,
   cash flow statement, or relevant footnote.
   Log: "addback [item] from LLM extraction"

Step 4 — Apply addback cap if present:
   Capped_Addback = min(raw_addback, cap_amount)
   If raw addback exceeds cap:
      Flag: "addback [item] capped at [cap amount] —
      full amount of $X excluded from Covenant EBITDA;
      $Y addback capacity consumed at cap"

Step 5 — Check aggregate addback cap:
   If aggregate cap present (e.g. 25% of pre-addback
   EBITDA):
      Total_Capped_Addbacks = sum of all capped addbacks
      Cap_Limit = GAAP_EBITDA × cap_percentage
      If Total_Capped_Addbacks > Cap_Limit:
         Apply cap to total:
         Allowed_Addbacks = Cap_Limit
         Flag: "aggregate addback cap binding —
         total addbacks of $X capped at $Y (Z% of
         pre-addback EBITDA); cap is [W]% utilised"
      If Total_Capped_Addbacks approaching cap:
         Flag: "aggregate addback cap [X]% utilised —
         [Y]% remaining; further EBITDA deterioration
         will flow through fully to Covenant Leverage
         once cap is fully consumed"

Step 6 — Compute Covenant EBITDA:
   Covenant EBITDA =
       GAAP EBITDA
     + Sum of allowed addbacks
     (after individual and aggregate caps)

Step 7 — Compute divergence:
   Divergence = Covenant EBITDA − GAAP EBITDA
   Divergence % = Divergence / GAAP EBITDA × 100
   Flag if > 20%: "material EBITDA addback —
   Covenant EBITDA exceeds GAAP EBITDA by [X]%;
   headline leverage understates covenant leverage
   gap"
   Flag if > 40%: "very large addback — verify
   individual items; addback magnitude may
   indicate earnings quality concern"
```

---

### Input 3 — Headroom Computation

```
Basic Headroom (Formula 1):

For maximum covenants (leverage, capex):
   Headroom_Abs = Threshold − Current_Ratio
   Headroom_Pct = Headroom_Abs / Threshold × 100
   If Headroom_Abs < 0: BREACH — immediate Critical alert

For minimum covenants (coverage, liquidity):
   Headroom_Abs = Current_Ratio − Threshold
   Headroom_Pct = Headroom_Abs / Threshold × 100
   If Headroom_Abs < 0: BREACH — immediate Critical alert

Null propagation:
   If Threshold null → Headroom null
   If Current_Ratio null → Headroom null
   If both non-null → compute

EBITDA cushion (leverage covenant only):
   EBITDA_for_breach = Net_Debt / Covenant_Threshold
   EBITDA_Cushion = Current_EBITDA − EBITDA_for_breach
   EBITDA_Cushion_Pct =
       EBITDA_Cushion / Current_EBITDA × 100
   This translates the ratio headroom into a dollar
   amount of EBITDA the company can afford to lose
   before breaching — more intuitive than ratio alone.
   Negative cushion = breach already occurred.

Adjusted Headroom (Formula 2):
   Same computation as above but using:
   Covenant_Leverage instead of GAAP Leverage
   (Covenant Net Debt / Covenant EBITDA)
   Covenant_Threshold (same as Formula 1)

Forward Headroom (Formula 3):
   For each scenario:
   Forward_Headroom(scenario) =
       Threshold(applicable_date) −
       Projected_Ratio(scenario, date)
   Where Threshold(date) reflects step-downs
   and Projected_Ratio reflects scenario assumptions
```

---

### Input 4 — Covenant Breach and Waiver Detection

This runs independently of and takes priority over all headroom computations. It is a keyword-based scan, not a ratio comparison.

```
Step 1 — Keyword scan across all filing sections:
   Debt Footnote, MD&A, Auditor's Report,
   Going Concern footnote, Subsequent Events
   footnote, Risk Factors

   Breach keywords:
   "not in compliance"
   "covenant violation"
   "event of default"
   "technical default"
   "failed to comply"
   "breach of covenant"

   Waiver keywords:
   "obtained a waiver"
   "waiver agreement"
   "forbearance agreement"
   "amendment and waiver"
   "lender consent"

   Amendment keywords (may indicate prior breach
   or proactive restructuring):
   "Amendment No. [X]"
   "amended and restated"
   "covenant relief"
   "covenant reset"
   "relaxed the financial covenant"
   "increased the maximum permitted"

Step 2 — If breach keyword found:
   IMMEDIATE CRITICAL ALERT
   Extract:
   Which covenant was breached
   Date of breach
   Whether waiver was obtained (and expiry)
   Whether amendment replaced waiver
   Store as permanent record even after
   waiver or amendment resolves the breach

Step 3 — If waiver keyword found without
   explicit breach language:
   Stress alert — waiver implies breach occurred
   Flag: "waiver language detected — breach
   implied; extract waiver details and
   monitor for covenant compliance going forward"

Step 4 — If amendment keyword found:
   Extract new covenant terms
   Update stored threshold with new value
   Flag: "covenant amended — threshold updated;
   prior headroom computations superseded"
   Check whether amendment tightens or loosens
   the covenant:
   Loosened: "covenant relief obtained —
   negative signal; lenders conceded terms"
   Tightened: "covenant tightened — monitor
   carefully; new threshold may reduce headroom"
```

---

### Cross-Level Validation Rules

**Check 1 — Threshold reasonableness**
```
After extracting any covenant threshold:
Compare to market convention for this issuer type:
   Investment-grade revolver: leverage threshold
   typically 3.0x–4.5x if present at all
   BB-rated leveraged loan: typically 4.5x–6.5x
   B-rated leveraged loan: typically 5.5x–7.5x
   Coverage covenant: typically 1.75x–3.0x minimum

If extracted threshold falls outside these ranges:
   Flag: "extracted covenant threshold of [X.Xx]x
   appears unusual for [issuer type] — verify
   extraction accuracy; possible definition or
   extraction error"
   Do NOT override — flag only; proceed with
   extracted value
```

**Check 2 — Headroom vs filing-date ratio consistency**
```
If company discloses both current ratio AND headroom
in the same filing:
   Verify: Disclosed_Ratio + Headroom ≈ Threshold
   If inconsistent:
      Flag: "disclosed ratio and headroom do not
      reconcile to extracted threshold — verify
      extraction; using disclosed figures as
      authoritative"
      Use management-disclosed figures and log
      system computation as secondary
```

**Check 3 — Step-down proximity alert**
```
For any covenant with a step-down schedule:
   Days_to_Step_Down = step_down_date − filing_date
   Headroom_after_step_down =
       New_Threshold − Current_Ratio
   If Headroom_after_step_down < 0:
      Flag: "step-down on [date] will result in
      immediate covenant breach at current
      ratio — breach timing: [days] days"
   If Headroom_after_step_down < 10% of
   New_Threshold:
      Flag: "step-down on [date] will reduce
      headroom to [X]% — very thin post-step-
      down headroom"
```

**Check 4 — Addback cap utilisation trend**
```
If addback cap present:
   Compare cap utilisation across last three periods:
   If utilisation increasing each period:
      Flag: "addback cap utilisation increasing —
      [prior-2]: X%, [prior-1]: Y%, [current]: Z%;
      approaching binding cap; future EBITDA
      deterioration will not be offsettable
      through addbacks once cap is reached"
```

**Check 5 — Multi-covenant breach proximity**
```
If issuer has multiple maintenance covenants:
   Check whether multiple covenants are
   simultaneously approaching their thresholds:
   If two or more covenants at < 15% headroom:
      Flag: "multiple covenant stress —
      [covenant 1] at [X]% headroom and
      [covenant 2] at [Y]% headroom simultaneously;
      elevated breach risk across credit facility"
   This multi-covenant stress is more severe than
   single covenant stress because it reduces
   the likelihood that the company can fix one
   ratio without inadvertently worsening another
```

---

### Audit Log Output Format (per company, per period)

```
{
  "ticker": "RAD",
  "period": "2023-03-04",
  "filing": "10-K",

  "covenant_existence": {
    "maintenance_covenants_present": true,
    "covenant_lite": false,
    "source": "Debt Footnote — Note 7"
  },

  "covenant_compliance_xbrl": {
    "tag": "us-gaap:DebtInstrumentCovenantCompliance",
    "populated": true/false,
    "raw_value": "[string if populated, null if not]",
    "keyword_scan_result": "compliant/breach/waiver/ambiguous/null",
    "breach_keyword_found": true/false,
    "compliance_keyword_found": true/false,
    "passed_to_llm": true/false,
    "llm_interpretation": "[if passed to LLM]"
  },

  "covenants": [
    {
      "covenant_type": "leverage",
      "covenant_class": "maintenance",
      "threshold": 5.50,
      "threshold_direction": "maximum",
      "testing_frequency": "quarterly",
      "step_down": [
        {"date": "2024-03-01", "threshold": 5.25},
        {"date": "2024-09-01", "threshold": 5.00}
      ],
      "source_document": "Debt Footnote — Note 7",
      "source_quote": "The credit agreement requires
                       us to maintain a Consolidated
                       Net Leverage Ratio not to exceed
                       5.50 to 1.00",
      "credit_agreement_version": "Fourth Amended and
                                   Restated Credit
                                   Agreement dated
                                   2021-01-15",
      "compliance_confirmed": false,
      "breach_disclosed": true,
      "waiver_obtained": true,
      "waiver_details": "Waiver obtained January 2023;
                         expires June 2023"
    },
    {
      "covenant_type": "coverage",
      "covenant_class": "maintenance",
      "threshold": 1.75,
      "threshold_direction": "minimum",
      "testing_frequency": "quarterly",
      "step_down": null,
      "source_document": "Debt Footnote — Note 7",
      "compliance_confirmed": false,
      "breach_disclosed": true,
      "waiver_obtained": true
    }
  ],

  "formula_1_headroom": [
    {
      "covenant_type": "leverage",
      "current_ratio": 10.2,
      "threshold": 5.50,
      "headroom_absolute": -4.70,
      "headroom_pct": -85.5,
      "ebitda_cushion_pct": null,
      "status": "BREACH"
    },
    {
      "covenant_type": "coverage",
      "current_ratio": -0.69,
      "threshold": 1.75,
      "headroom_absolute": -2.44,
      "headroom_pct": -139.4,
      "status": "BREACH"
    }
  ],

  "formula_2_headroom": null,
  "formula_2_note": "Covenant EBITDA definition
                     extraction deferred — breach
                     already confirmed; Formula 2
                     not required for alert",

  "alerts": [
    "CRITICAL — leverage covenant breach disclosed;
     waiver obtained January 2023 expiring June 2023",
    "CRITICAL — coverage covenant breach disclosed;
     same waiver",
    "CRITICAL — waiver expiry June 2023 represents
     near-term covenant cliff; breach will recur
     unless financial performance improves or
     permanent amendment obtained"
  ],

  "flags": [
    "Step-down schedule: leverage threshold reduces
     to 5.25x in March 2024 and 5.00x in September
     2024 — moot given current breach but would
     tighten further post-waiver if performance
     does not recover",
    "Breach disclosure confirmed in both Debt
     Footnote and Auditor's Report"
  ],

  "nulls": ["formula_2_covenant_ebitda",
            "formula_3_stress_test"]
}
```

This Rite Aid example confirms that the covenant breach detection logic would have generated Critical alerts from the fiscal 2023 10-K — consistent with all prior metric validations and with the October 2023 bankruptcy outcome.


## Stress Threshold — Covenant Headroom

---

### Structural Difference From Prior Metrics

Covenant headroom thresholds differ from all prior metrics in two fundamental ways.

**First difference — the threshold is issuer-specific and contract-defined.** For leverage, the stress threshold is 5.0x–6.0x depending on volatility category — a market convention applied uniformly. For covenant headroom, the threshold that matters most is the one written in the credit agreement. A company with 4% headroom to its contractual limit is in acute stress regardless of where that limit sits in absolute terms. The alert framework therefore operates on the percentage headroom relative to the contract, not on the absolute ratio level.

**Second difference — the binary breach event supersedes all graduated thresholds.** Every prior metric uses graduated bands (Watch, Flag, Stress, Critical) based on how far a ratio has moved. Covenant headroom has those graduated bands for the pre-breach monitoring phase, but the moment of breach itself is a discrete legal event that bypasses all graduations. There is no "mild breach" — a breach is either occurring or it is not, and its occurrence triggers the maximum alert level regardless of how small the headroom violation is.

---

### Threshold Dimension 1 — Headroom Percentage (Primary Dimension)

Source: S&P liquidity descriptor framework (covenant headroom below 15% as a negative qualitative factor) and Moody's guidance on covenant cushion in leveraged loan analysis. The percentage bands below reflect market practice for leveraged finance monitoring.

**For all maintenance covenant types (leverage, coverage, liquidity, capex):**

| Headroom Percentage | Interpretation | Alert Level |
|---|---|---|
| ≥ 30% | Ample — significant buffer against deterioration | No alert |
| 20% – 30% | Adequate — comfortable but monitor trend | Watch |
| 15% – 20% | Below adequate — S&P negative liquidity factor threshold | Watch — elevated |
| 10% – 15% | Thin — one bad quarter could breach | Flag |
| 5% – 10% | Very thin — imminent breach risk | Stress |
| 0% – 5% | Near-breach — covenant likely to be breached next test | Critical |
| < 0% | Breach — covenant already violated | Critical — immediate escalation |

**EBITDA cushion supplementary thresholds (leverage covenant only):**

| EBITDA Can Fall By | Interpretation | Alert Level |
|---|---|---|
| ≥ 25% | Robust cushion | No alert |
| 15% – 25% | Adequate — manageable deterioration | Watch |
| 10% – 15% | Thin — one meaningful revenue miss | Flag |
| 5% – 10% | Very thin — any operational setback risks breach | Stress |
| < 5% | Near-breach — essentially no EBITDA buffer | Critical |
| Negative | Breach — current EBITDA already insufficient | Critical — immediate |

---

### Threshold Dimension 2 — Headroom Trend (Second Most Important Dimension)

Consistent with the approach in leverage and FCF, the trend in headroom is often more informative than the absolute level. A company with 25% headroom that has declined from 45% over four quarters is more concerning than a company stable at 18%.

| Headroom Trend | Alert Level |
|---|---|
| Headroom stable or increasing | No trend alert |
| Headroom declining for 1 quarter | No alert — single data point |
| Headroom declining for 2 consecutive quarters | Watch — compression trend beginning |
| Headroom declining for 3 consecutive quarters | Flag — sustained compression regardless of absolute level |
| Headroom declining for 4+ consecutive quarters | Stress — persistent deterioration |
| Headroom declining AND absolute headroom < 15% | Escalate one level beyond trend-only alert |
| Headroom declining AND step-down approaching | Escalate one additional level — dual compression risk |

---

### Threshold Dimension 3 — Step-Down Proximity

Covenant step-downs are scheduled contractual tightenings of the threshold. They compress headroom automatically even if the company's financial performance is unchanged. The step-down proximity alert is unique to this metric.

| Days to Next Step-Down AND Post-Step-Down Headroom | Interpretation | Alert Level |
|---|---|---|
| Step-down > 365 days away OR post-step-down headroom ≥ 20% | No near-term concern | No alert |
| Step-down 180–365 days away AND post-step-down headroom 10%–20% | Approaching tightening | Watch |
| Step-down 90–180 days away AND post-step-down headroom 5%–10% | Tightening imminent | Flag |
| Step-down < 90 days away AND post-step-down headroom < 5% | Near-breach at step-down | Stress |
| Post-step-down headroom < 0% at current ratio | Breach will occur at step-down at current performance | Critical — projected breach |

**Important note:** A projected breach at step-down is not a current breach. The Critical alert for this scenario must be clearly labeled: "Projected covenant breach at step-down on [date] — breach has not yet occurred; [N] days until threshold tightens; current headroom [X]%." Do not label this the same as an actual breach.

---

### Threshold Dimension 4 — Addback Cap Utilisation (Formula 2 Only)

The addback cap utilisation measures how dependent the company is on contractual EBITDA addbacks to maintain covenant compliance. A company at 90% of its addback cap has exhausted most of its buffer — future EBITDA deterioration will flow through fully to Covenant Leverage once the cap is reached.

| Addback Cap Utilisation | Interpretation | Alert Level |
|---|---|---|
| < 50% | Addback capacity ample | No alert |
| 50% – 70% | Moderate utilisation | Watch |
| 70% – 85% | High utilisation — limited remaining buffer | Flag |
| 85% – 100% | Near-binding — addback capacity nearly exhausted | Stress |
| > 100% | Cap binding — addbacks being clipped; full EBITDA deterioration flowing through | Critical |
| Cap binding AND headroom < 15% | Combined stress — no addback buffer remaining and thin headroom | Critical — escalate immediately |

---

### Threshold Dimension 5 — Covenant Type Severity Weighting

Not all covenant breaches have the same consequence. The severity of a breach depends on which covenant is breached and what acceleration rights it triggers.

| Covenant Type | Breach Consequence | Alert Weight |
|---|---|---|
| Leverage maintenance covenant (revolving credit) | Revolver unavailable for draws; lender may accelerate term debt | Highest — full credit facility at risk |
| Coverage maintenance covenant (term loan) | Lender may accelerate term loan; cross-default possible | High — significant debt at risk |
| Liquidity / minimum cash covenant | Same as coverage — lender may accelerate | High — may trigger cross-default |
| Capex covenant | Limits future investment; lender may accelerate in some agreements | Medium — operational constraint + potential acceleration |
| Incurrence covenant (high-yield bond) | Prohibits new debt issuance; does NOT trigger acceleration | Low — financial flexibility constraint only |
| Springing covenant (currently inactive) | No current consequence; activates if trigger breached | Low currently — monitor trigger level |

**System rule:** When a breach is detected, the alert level is always Critical. However the urgency description in the alert output must reflect the covenant type severity — a leverage maintenance covenant breach on a revolving credit facility is more operationally urgent than a capex covenant breach, and the analyst notification should reflect this.

---

### Threshold Dimension 6 — Multi-Covenant Stress

When multiple maintenance covenants are simultaneously below threshold on headroom, the combined risk is greater than the sum of the individual risks — because a single underlying deterioration (falling EBITDA) simultaneously compresses all earnings-based covenants at once.

| Multi-Covenant Condition | Alert Level |
|---|---|
| One covenant at Flag or above | Standard single-covenant alert |
| Two covenants simultaneously at Flag or above | Escalate both to next level — "dual covenant stress" |
| Three or more covenants simultaneously at Flag or above | Escalate all to Critical — "multi-covenant stress; entire credit facility at risk" |
| Any covenant at Stress AND a second covenant at Watch | Flag both — deterioration affecting entire covenant package |

---

### Threshold Dimension 7 — Waiver and Amendment Signals

Waivers and amendments are lagging confirmations of stress that has already occurred. Their presence in a filing is itself a threshold signal independent of the current headroom level.

| Condition | Alert Level | Rationale |
|---|---|---|
| Covenant breach disclosed + waiver obtained | Critical — sustained | Breach confirmed; waiver temporary; underlying stress persists |
| Covenant breach disclosed + no waiver | Critical — acute | Breach with no resolution; lenders may accelerate immediately |
| Amendment relaxing covenant threshold | Stress | Lenders conceded terms — confirms financial trajectory worse than originally expected |
| Amendment tightening covenant threshold | Watch — monitor | Company accepted tighter terms — may signal improved position or may reflect lender-imposed discipline |
| Waiver expiry within 90 days without permanent amendment | Critical — cliff approaching | Temporary waiver expiring; breach will recur unless performance improves or permanent amendment obtained |
| Second waiver obtained for same covenant within 12 months | Critical | Repeat waiver signals structural not temporary deterioration |
| Equity cure exercised | Stress | Company injected equity to cure breach — breach occurred; equity cure is a one-time remedy with limits |

---

### Combined Alert Trigger Rules

The most severe alert across all seven dimensions governs the overall covenant headroom alert level.

| Alert Level | Any of These Conditions | Action |
|---|---|---|
| **Watch** | Headroom 20%–30%; OR headroom declining 2 consecutive quarters; OR step-down 180–365 days away with post-step-down headroom 10%–20%; OR addback cap 50%–70% utilised | Log; weekly review |
| **Flag** | Headroom 10%–15%; OR headroom declining 3 consecutive quarters; OR EBITDA cushion 10%–15%; OR step-down 90–180 days with post-step-down headroom 5%–10%; OR addback cap 70%–85% utilised; OR covenant amendment relaxing terms | Generate alert; daily monitoring |
| **Stress** | Headroom 5%–10%; OR headroom declining 4+ quarters; OR EBITDA cushion 5%–10%; OR step-down < 90 days with post-step-down headroom < 5%; OR addback cap 85%–100% utilised; OR waiver obtained; OR equity cure exercised; OR two covenants simultaneously at Flag | Immediate alert; escalate same day |
| **Critical** | Headroom 0%–5%; OR any covenant breach disclosed; OR waiver expiry within 90 days; OR repeat waiver within 12 months; OR EBITDA cushion < 5%; OR addback cap binding with headroom < 15%; OR three or more covenants at Flag or above; OR projected breach at upcoming step-down | Immediate escalation; cross-reference all metrics |
| **Critical — Immediate** | Headroom < 0% (breach confirmed); OR breach disclosed without waiver; OR going concern language in any filing | Highest urgency; same-day analyst notification; no further computation required |
| **Trend Flag** | Headroom declining any three consecutive quarters regardless of absolute level | Alert regardless of band |
| **Extraction Failure** | Threshold null after all fallbacks in Phase 3 | Apply Phase 2 proxy; label prominently as proxy; escalate to manual review |

---

### Sector Exceptions and Adjustments

**Investment-grade issuers:** Many investment-grade revolving credit facilities contain maintenance covenants but with very wide thresholds — leverage covenants of 3.5x–4.5x for companies currently at 1.0x–2.0x leverage provide so much headroom that they function as a distant backstop rather than a real constraint. For investment-grade issuers confirmed to have leverage below 2.5x, the covenant headroom metric is largely informational in Phase 3 — monitor but apply a one-level downward adjustment to all alerts given the structural distance from any threshold.

**Covenant-lite leveraged issuers:** As flagged in the extraction logic, covenant-lite facilities have no maintenance covenants. For these issuers the metric produces no headroom computation and no graduated alerts. The only signal available is the incurrence covenant test — whether the company can issue additional debt. Flag covenant-lite status on every output: "covenant-lite facility — no financial maintenance covenant acceleration risk; incurrence covenant capacity monitored only."

**Asset-based lending (ABL) facilities:** ABL facilities use a borrowing base (eligible receivables and inventory) rather than financial ratio covenants. The primary constraint is the availability under the borrowing base — not a leverage or coverage ratio. For ABL borrowers, the relevant threshold is the availability block (minimum availability required) and the springing covenant trigger. These are already covered under the minimum liquidity covenant framework but should be clearly labeled as ABL-specific: "ABL facility — borrowing base availability is the primary covenant constraint; financial ratio covenants secondary or absent."

**Financial institutions:** Same exception as all prior metrics — not applicable.

---

### Empirical Context and Backtest Anchor

**Historical reference — Rite Aid:**
As confirmed in the audit log example in Extraction Fallback Logic: Rite Aid's fiscal 2023 10-K disclosed breaches of both its leverage covenant (threshold 5.50x, actual 10.2x) and its coverage covenant (threshold 1.75x minimum, actual −0.69x). Both breaches were accompanied by waivers expiring June 2023. Under the threshold framework, both would generate Critical — Immediate alerts from the breach disclosure alone, with the waiver expiry creating a secondary Critical cliff event. This is fully consistent with the October 2023 bankruptcy — the waiver was not permanently resolved, the underlying deterioration continued, and the company filed for Chapter 11 approximately four months after the waiver expiry. The covenant headroom metric would have generated its first Critical alerts in fiscal 2023 — confirming the pattern established across all prior metrics.

**Historical reference — general empirical evidence:**
Moody's research on leveraged loan defaults confirms that companies that obtain covenant waivers default at rates approximately 30–40% higher within the following 12 months than companies that maintain covenant compliance. This directly validates the Stress-level alert for waiver disclosure and the Critical-level alert for repeat waivers. The 15% headroom threshold for S&P's liquidity descriptor negative factor is published in S&P's Corporate Methodology and is the most directly sourced of all the thresholds in this metric.

**Phase 3 backtest validation targets:**

| Metric | Target |
|---|---|
| Breach detection precision | 100% of disclosed covenant breaches generate Critical alert — zero tolerance for missed breach signals; keyword detection is the mechanism |
| Waiver predictive value | ≥ 70% of issuers obtaining covenant waivers should experience a credit event (default, distressed exchange, or bankruptcy) within 18 months |
| Headroom compression catch rate | ≥ 75% of eventual defaulters should show covenant headroom below 15% at least two quarters before the credit event |
| Step-down projection accuracy | ≥ 80% of projected step-down breaches (headroom < 0% post-step-down) should either be resolved by amendment or confirmed as actual breaches within two quarters |
| False positive rate | ≤ 20% of issuers flagged at Stress or above on headroom should remain in compliance without a credit event for more than four quarters — reflecting the urgency of thin headroom signals |


## Signal Timing — Covenant Headroom

---

### Classification

**Dual nature — gradual leading indicator during compression phase; instantaneous cliff event at breach.**

Covenant headroom has a more complex timing structure than any other metric in this spec because it operates in two completely different modes depending on where the company sits in its stress trajectory. During the pre-breach compression phase it behaves like a slow-moving leading indicator — headroom narrows gradually over multiple quarters and the signal is directional. At the moment of breach it switches instantaneously to a coincident indicator — the legal event and the alert occur simultaneously with no lag. No other metric in this spec has this dual-mode characteristic.

This dual nature means the system must treat covenant headroom differently depending on which mode is active. In compression mode the system is tracking a trend and the value of the signal is proportional to how far in advance it detects deterioration. In breach mode the system is detecting a discrete legal event and the value of the signal is in its immediacy — every hour of delay between breach occurrence and alert generation is a failure of the monitoring function.

---

### The Compression Phase — Leading Indicator Characteristics

During the compression phase, covenant headroom typically narrows over 4–8 quarters before a breach occurs. This makes it a genuine leading indicator for the specific event of covenant breach and subsequent debt acceleration — the most acute form of credit stress.

The compression phase has a specific relationship with the other metrics in this spec that creates a predictable detection sequence:

```
Typical sequence leading to covenant breach:

Quarter −6 to −4:
FCF compression begins (FCF metric flags first)
EBITDA stable but declining
Leverage ratio begins rising
Coverage begins declining
Covenant headroom begins narrowing from ample levels
→ System: FCF Watch; Leverage Watch; Coverage Watch;
           Covenant Headroom: no alert yet (>30%)

Quarter −4 to −2:
EBITDA declining materially
Leverage in Significant or Aggressive band
Coverage in Aggressive band
Covenant headroom approaching 15%
→ System: FCF Stress; Leverage Flag; Coverage Flag;
           Covenant Headroom: Watch then Flag

Quarter −2 to 0:
EBITDA deterioration accelerating
Leverage in Highly Leveraged band
Coverage below 2.0x
Covenant headroom below 10%
→ System: All metrics at Stress or Critical;
           Covenant Headroom: Stress then Critical (near-breach)

Quarter 0 (breach):
Covenant threshold crossed
Disclosure in next quarterly filing
→ System: IMMEDIATE CRITICAL — breach disclosed
```

The compression phase gives the system 4–8 quarters of warning before the breach event — a longer lead time than leverage or coverage alone because covenant headroom is the formalisation of exactly the thresholds that lenders have determined are unacceptable. When the ratio approaches the covenant threshold it is approaching the line that lenders will act on.

---

### The Breach Event — Coincident Indicator

At the moment of breach the signal becomes coincident — it arrives simultaneously with the event rather than predicting it. The breach is disclosed in the next quarterly or annual filing, which arrives 40 days after quarter-end for a 10-Q and 60 days after year-end for a 10-K. The actual breach may have occurred at any point during the quarter — the filing discloses it but the system does not see it until the filing arrives.

This filing lag — identical to every other metric — is the primary limitation of breach detection from structured filings. A company that breaches a covenant on day 1 of the quarter does not disclose it until the 10-Q is filed 40+ days after quarter-end. During the intervening period the lenders know about the breach and are negotiating privately, but the public filing system does not reflect it until the disclosure arrives.

The partial mitigation for this lag is 8-K monitoring. An 8-K Item 1.01 filing for a covenant amendment or waiver confirms that a breach has occurred — even before the 10-Q discloses it formally. This is the most important intra-quarter signal for covenant headroom and provides detection up to several weeks earlier than waiting for the quarterly filing.

```
Breach detection timeline:

Day 0: Breach occurs (ratio crosses threshold
       at quarter-end measurement date)
Day 1–30: Private negotiation between company
          and lenders
Day 1–30: 8-K Item 1.01 may be filed if waiver
          or amendment is entered into
          → System detects: Watch to Critical
            escalation from 8-K keyword
Day 40: 10-Q filed — breach formally disclosed
        → System detects: CRITICAL from breach
          keyword in Debt Footnote
Day 40–60: Rating agency downgrades likely
           → External confirmation

Best case detection: Day 1–30 via 8-K
Worst case detection: Day 40–45 via 10-Q
Typical detection: Day 40 via 10-Q
```

---

### Three-Tier Timing Structure

| Tier | Source | Data Quality | Lag After Breach / Quarter-End | Use in System |
|---|---|---|---|---|
| **Tier 1 — Quarterly headroom update** | 10-Q / 10-K | Reviewed / audited; current ratio from XBRL; threshold from prior LLM extraction | **+40 days** after quarter-end (10-Q) | Headroom recomputed each quarter using updated ratios against stored thresholds; compression trend tracked |
| **Tier 1b — Annual threshold refresh** | 10-K | Audited; full LLM re-extraction of covenant terms | **+60 days** after fiscal year-end | Full covenant terms re-extracted; thresholds updated for amendments; step-down schedule updated |
| **Tier 2 — Intra-quarter breach signal** | 8-K Item 1.01 (amendment/waiver) | Event disclosure; confirms breach occurred | **Within 4 business days** of amendment/waiver signing | Earliest possible breach detection; keyword-triggered Critical alert before 10-Q arrives |
| **Tier 3 — Earnings press release** | 8-K Item 2.02 | Preliminary; company may disclose covenant status | **+14 to +25 days** after quarter-end | Covenant compliance commentary if voluntarily disclosed; Phase 3 only |

**Critical asymmetry vs prior metrics:** For leverage and coverage, Tier 1 (quarterly filing) provides a ratio update and Tier 2 (intra-quarter events) provides partial updates. For covenant headroom, Tier 1 provides both a ratio update AND the covenant compliance disclosure — the most important output. The ratio update alone (from XBRL) is secondary to the compliance disclosure (from LLM). This means that for covenant headroom, the LLM extraction at each quarterly filing is not a Phase 3 enhancement — it is the primary detection mechanism for the most important signal this metric produces.

---

### Staleness Analysis — Two Separate Components

Unlike all prior metrics which have a single staleness profile, covenant headroom has two components with different staleness characteristics:

**Component 1 — Current ratio (changes quarterly):**
Same staleness as leverage and coverage — the ratio is between 40 and 130 days old at the time of download, depending on where in the quarterly cycle the filing arrives. The Q4 dark window applies identically.

**Component 2 — Covenant threshold (changes only on amendment):**
The threshold is stable between amendments. A leverage covenant of 5.5x set in January 2022 is still 5.5x in March 2024 unless the credit agreement was amended. This means the threshold component has very low staleness in normal conditions — the last extracted value remains valid until a new 8-K Item 1.01 or 10-K signals an amendment.

```
Threshold staleness management:

After each 10-K: re-extract threshold via LLM
                 (confirms no amendment occurred
                 during the year or captures any
                 amendment since last extraction)
After each 8-K Item 1.01: re-extract threshold
                           immediately if amendment
                           keywords detected
Between filings: use stored threshold
                 Flag: "threshold from [last
                 extraction date] — valid unless
                 credit agreement amended since"

If more than 12 months since last threshold
extraction and no amendment detected:
   Flag: "threshold extraction more than 12
   months old — re-extraction recommended at
   next 10-K; verify no unreported amendments"
```

---

### The Q4 Dark Window — Moderate Impact

The Q4 dark window affects covenant headroom differently from prior metrics:

**Ratio component:** The dark window applies — the Q4 ratio update is not available until the 10-K is filed approximately 60 days after fiscal year-end. A company that crosses its covenant threshold in Q4 is not visible from the ratio perspective until the 10-K arrives.

**Threshold component:** Unaffected — thresholds do not change between filings unless an amendment occurs.

**Breach detection:** Partially mitigated. If a Q4 covenant breach occurs and the company seeks a waiver or amendment before year-end, the 8-K Item 1.01 for the waiver/amendment will be filed within 4 business days — providing breach detection well before the 10-K. If the company breaches but takes no action (banking on the ratio improving before year-end or deciding not to seek a waiver), the breach is only visible when the 10-K discloses it.

The Q4 dark window for covenant headroom is therefore:
```
Best case: 4 business days (8-K waiver filed promptly)
Typical case: 60 days after year-end (10-K)
Worst case: 60 days after year-end (no 8-K filed)

Mitigation: Monitor 8-K Item 1.01 filings daily
for issuers with headroom below 15% during
the Q4 dark window period (November through
March for calendar-year companies)
```

---

### Comparison: Covenant Headroom vs Other Metrics Signal Characteristics

| Characteristic | Covenant Headroom | FCF | Coverage | Leverage | Liquidity | Maturity Wall |
|---|---|---|---|---|---|---|
| **Signal type in compression phase** | Gradual — ratio approaching fixed contract threshold | Flow deterioration | Flow deterioration | Stock accumulation | Stock depletion | Calendar countdown |
| **Signal type at event** | Discrete legal event — instantaneous | N/A — no discrete event | N/A | N/A | Possible cliff event | Calendar cliff event |
| **Lead time — compression phase** | 4–8 quarters | 4–6 quarters | 2–4 quarters | 2–4 quarters | 1–2 quarters | 2–5 years |
| **Lead time — event detection** | 0–40 days (8-K to 10-Q) | N/A | N/A | N/A | 0–40 days (revolver pull) | 0 (breach) or known (maturity) |
| **Filing lag at event** | 0–40 days | N/A | N/A | N/A | 0–40 days | 0 (known in advance) |
| **Threshold is issuer-specific** | ✅ Yes — contractual | ❌ No — market convention | ❌ No | ❌ No | ❌ No | ❌ No |
| **Threshold changes over time** | ✅ Yes — step-downs | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Intra-quarter real-time signal** | ✅ Yes — 8-K Item 1.01 | ❌ No | ❌ No | Partial (Item 2.03) | ✅ Yes (Item 1.01) | ✅ Yes (424B, countdown) |
| **Q4 dark window severity** | Moderate — 8-K partially mitigates | Severe | Significant | Moderate | Moderate | Minimal |
| **Dual-mode timing** | ✅ Yes — compression then discrete | ❌ No | ❌ No | ❌ No | Partial | Partial |

---

### Cross-Metric Timing Interactions

The covenant headroom metric's timing interacts with other metrics in ways that create combined signals more informative than any individual metric:

**Interaction with Leverage and Coverage:**
See LEVERAGE.md → Section "Signal Timing" and INTEREST_COVERAGE.md → Section "Signal Timing" — covenant headroom compression trend mirrors these metrics' deterioration; use stored alert levels for combined signal assessment. When both the standalone ratio alert (e.g. leverage in Aggressive band) and the covenant headroom alert (e.g. 12% headroom) are active simultaneously, the combined signal confirms that the deterioration is both economically significant and legally consequential. Neither alone is as informative as both together.

**Interaction with Debt Maturity Wall:**
The interest rate reset stress test in Covenant Headroom Formula 3 uses the maturity schedule from the Debt Maturity Wall metric. When a large maturity is approaching and the interest rate reset would compress coverage below the covenant minimum, the covenant headroom metric quantifies exactly how many basis points of rate increase the company can absorb before breaching. This is the most precise forward-looking stress computation the system produces.

**Interaction with FCF:**
The EBITDA cushion computation in covenant headroom (how much EBITDA can fall before breach) is the inverse of the FCF compression signal (EBITDA is already falling). When FCF compression is visible for 3+ quarters and the covenant EBITDA cushion is below 10%, the system can estimate the number of quarters until breach:

```
Estimated quarters to breach =
    EBITDA Cushion ($)
    / Quarterly EBITDA Decline ($)
    (using trailing three-quarter average decline)

Flag: "at current EBITDA deterioration rate of
$X million per quarter, leverage covenant breach
projected in approximately [N] quarters"

This computation requires:
   EBITDA Cushion from Covenant Headroom F1
   Quarterly EBITDA decline from Coverage/Leverage
   stored time series

Phase 3 only — requires historical EBITDA series
and extracted covenant threshold.
```

---

### Updated Signal Timing Summary

> **Signal Timing — Dual-mode: gradual leading indicator during compression (4–8 quarters lead time) switching to instantaneous coincident indicator at breach.**
>
> In the compression phase, covenant headroom narrows gradually over multiple quarters and gives 4–8 quarters of lead time before the breach event — longer than leverage or coverage alone because the covenant threshold is the contractual formalisation of the line that lenders will act on. The compression signal is best detected through the quarterly headroom percentage trend, the EBITDA cushion trend, and the step-down proximity calculation.
>
> At the breach event, the mode switches instantly. The breach is a discrete legal event that bypasses all graduated alert levels and triggers an immediate Critical escalation. Detection lag is 0–40 days — best case via 8-K Item 1.01 when a waiver or amendment is filed within days of breach; worst case via 10-Q filed 40 days after quarter-end.
>
> The Q4 dark window is moderately mitigated by 8-K Item 1.01 monitoring — any waiver or amendment filed during the dark window provides earlier breach detection than waiting for the 10-K. For issuers with headroom below 15% at Q3, daily 8-K monitoring should be activated through the November–March window.
>
> Covenant headroom is the only metric in the spec with an issuer-specific threshold that changes over time through step-downs and amendments. Threshold version control — tracking which credit agreement version the stored threshold comes from and monitoring for amendments — is the most operationally important maintenance task for this metric and has no equivalent in any other metric in the spec.

## Frequency — Covenant Headroom

---

### Overview

Covenant headroom has a more complex update structure than prior metrics in two specific ways. First, it has two distinct update cycles running simultaneously — the ratio component updates quarterly from XBRL (same as all prior metrics) while the threshold component updates only on covenant amendments, which are event-driven and unpredictable. Second, the most important signal this metric produces — breach disclosure — is not generated by a scheduled filing but by a discrete event that can occur at any point in the quarter and is only partially visible through real-time 8-K monitoring.

The Leverage Frequency section covers the baseline filing schedule, EDGAR availability, and 8-K filtering rules that apply to all metrics. This section documents only the differences and covenant-specific considerations.

---

### What Is the Same as Prior Metrics (See LEVERAGE.md → Section "Frequency" → full section — apply identical baseline framework; this section documents covenant-specific differences only)

| Channel | Filing Type | Phase 2 | Phase 3 |
|---|---|---|---|
| Quarterly ratio update | 10-Q | ✅ XBRL ratio recompute; proxy headroom only | ✅ XBRL ratio + stored threshold → headroom computation |
| Annual full refresh | 10-K | ✅ XBRL ratio + LLM threshold extraction | ✅ Full LLM re-extraction of all covenant terms |
| Earnings press release | 8-K Item 2.02 | ❌ Ignore | ✅ Add — covenant compliance commentary |
| Debt acceleration / default | 8-K Item 2.04 | ✅ Immediate Critical alert | ✅ Same |

---

### Covenant Headroom-Specific Differences

**Difference 1 — Threshold update cycle is amendment-driven, not filing-driven**

For every prior metric, data updates arrive on a predictable schedule tied to filing deadlines. Covenant thresholds update only when the credit agreement is amended — which can happen at any time, with no advance notice, triggered by either a covenant breach (waiver/amendment to cure) or a proactive refinancing (new facility with different terms).

```
Threshold version control system:

At each 10-K filing:
   Full LLM re-extraction of all covenant terms
   Compare extracted thresholds to stored values:
   If unchanged: confirm stored values; update
   extraction date
   If changed: update stored values; log amendment:
   {
     "amendment_detected": true,
     "prior_threshold": X.Xx,
     "new_threshold": Y.Yy,
     "change_type": "tightened/loosened/reset",
     "detected_in": "10-K [date]",
     "credit_agreement_version": "[version string]"
   }

At each 8-K Item 1.01 (amendment/waiver):
   Immediate LLM re-extraction of new covenant terms
   Update stored thresholds immediately
   Do not wait for next quarterly filing
   Flag: "covenant terms updated from 8-K
   Item 1.01 dated [date] — thresholds supersede
   prior stored values"

Between amendments:
   Use stored thresholds without re-extraction
   Flag on each output: "threshold from [source
   document] dated [date] — valid unless
   credit agreement amended since [date]"

If more than 365 days since last extraction
with no amendment detected:
   Trigger re-extraction at next 10-K
   Flag: "threshold extraction age exceeds
   12 months — re-extraction required"
```

---

**Difference 2 — 8-K Item 1.01 is a primary detection channel**

For all prior metrics, 8-K Item 1.01 is a secondary channel monitored with keyword filters. For covenant headroom, Item 1.01 is the primary real-time breach detection channel — it provides the earliest possible signal that a covenant breach has occurred, typically 2–6 weeks before the quarterly filing discloses it formally.

```
Item 1.01 covenant headroom processing:

Phase 2 — keyword monitoring for flagged issuers:
   Monitor issuers with proxy headroom alerts
   Keywords: "waiver", "amendment", "covenant",
   "forbearance", "lender consent", "default"
   If keywords detected:
      Generate immediate Watch-to-Critical escalation
      depending on keyword severity
      Flag: "8-K Item 1.01 covenant event detected —
      [keyword]; manual review required pending
      Phase 3 LLM extraction"

Phase 3 — full LLM extraction for all issuers:
   All Item 1.01 filings processed by LLM
   regardless of prior alert level
   LLM determines:
   Is this a covenant amendment? → update threshold
   Is this a waiver? → breach confirmed; Critical
   Is this a routine facility renewal? → update
   maturity and terms; no breach signal
   Is this a new facility replacing existing?
   → extract new covenant terms; replace stored
   values; compare new to old for tightening/
   loosening signal

   Output structure for each Item 1.01:
   {
     "filing_type": "8-K Item 1.01",
     "event_type": "waiver/amendment/new_facility/
                    renewal/other",
     "covenant_breach_implied": true/false,
     "new_threshold": X.Xx (if amended),
     "prior_threshold": Y.Yy,
     "change_direction": "tightened/loosened/unchanged",
     "waiver_expiry": "YYYY-MM-DD" (if waiver),
     "alert_generated": "level"
   }
```

---

**Difference 3 — Waiver expiry monitoring requires a calendar trigger**

When a covenant waiver is obtained, it has an expiry date. If the company's financial condition has not improved by that date and no permanent amendment is obtained, the breach recurs automatically. Waiver expiry monitoring is the covenant-equivalent of the debt maturity countdown — a fixed future date that generates an escalating alert as it approaches.

> See DEBT_MATURITY_WALL.md → Section "Frequency" → Difference 1 (Daily Countdown) — apply identical daily countdown computation logic to waiver expiry dates

```
Waiver expiry monitoring:

When waiver is detected (from 8-K Item 1.01
or Debt Footnote):
   Store:
   {
     "waiver_date": "YYYY-MM-DD",
     "waiver_expiry": "YYYY-MM-DD",
     "covenant_type": "leverage/coverage/other",
     "waiver_status": "active/expired/replaced"
   }

Daily computation (same as maturity countdown):
   Days_to_expiry = waiver_expiry - current_date

   If Days_to_expiry > 180: Stress (waiver active)
   If Days_to_expiry 90–180: Stress — escalating
   If Days_to_expiry 30–90: Critical
   If Days_to_expiry < 30: Critical — highest urgency
   Flag: "waiver expires [date] — [N] days remaining;
   breach recurs if no amendment or improvement"

   If Days_to_expiry < 0 (waiver expired):
      Check whether permanent amendment obtained:
      If yes: update stored covenant; close waiver
      If no: Critical — "waiver expired without
      permanent resolution; breach status unknown;
      manual review required"

Resolution signals:
   8-K Item 1.01 with amendment language after
   waiver: waiver replaced by amendment;
   update threshold; close waiver monitoring
   10-Q/10-K compliance affirmation after waiver:
   waiver expired without breach recurrence;
   close waiver monitoring
```

---

**Difference 4 — 8-K Item 2.02 provides genuine covenant signal**

For FCF and leverage, the earnings press release (Item 2.02) rarely discloses the specific metric inputs needed. For covenant headroom, many companies explicitly state covenant compliance in their earnings press releases — particularly those with thin headroom managing investor expectations.

```
Item 2.02 covenant headroom processing:

Phase 3 only:
LLM reads Item 2.02 text for:
   Covenant compliance statement:
   "We were in compliance with all financial
   covenants as of [date]" → positive confirmation;
   store as interim compliance signal 14–25 days
   before 10-Q
   Headroom disclosure:
   "Our leverage ratio was [X.Xx]x compared to a
   covenant maximum of [Y.Yy]x" → update headroom
   computation with preliminary figures
   Waiver or amendment announcement:
   Immediate Critical alert regardless of
   other disclosures

Priority: Item 2.02 covenant compliance statement
is one of the most valuable Tier 2 signals in
the system — it provides covenant status 14–25
days earlier than the 10-Q and does not require
ratio computation to interpret.

Storage: Store as "preliminary compliance status"
separately from Tier 1 10-Q confirmed status.
Do not overwrite Tier 1 with Tier 2 data.
```

---

**Difference 5 — Step-down schedule generates independent calendar-based alerts**

Covenant step-downs are fixed future threshold changes that generate alerts through proximity, not through ratio movement. Like the maturity wall countdown, step-down proximity alerts run daily against a stored step-down schedule (See DEBT_MATURITY_WALL.md → Section "Frequency" → Difference 1 (Daily Countdown) — apply identical daily computation; substitute step-down date for maturity date).

```
Step-down proximity monitoring:

When step-down schedule extracted (from 10-K
or credit agreement):
   Store array of {date, new_threshold} pairs

Daily computation:
   For each upcoming step-down:
      Days_to_step_down = step_down_date - current_date
      Post_step_down_headroom =
         new_threshold − current_ratio (if maximum)
         OR current_ratio − new_threshold (if minimum)

      Alert logic per Stress Threshold Dimension 3:
      > 365 days: No alert
      180–365 days AND post-headroom 10%–20%: Watch
      90–180 days AND post-headroom 5%–10%: Flag
      < 90 days AND post-headroom < 5%: Stress
      Post-headroom < 0% at any horizon: Critical
      (projected breach)

Resolution: if ratio improves before step-down,
recompute post-step-down headroom and
downgrade alert if appropriate
```

---

**Difference 6 — Credit agreement exhibit monitoring**

When a new credit agreement or amendment is filed as an exhibit (Exhibit 10.x) to a 10-K or as an 8-K Item 1.01 attachment, it contains the most complete covenant information available. Monitoring for new exhibit filings is unique to this metric.

```
Credit agreement exhibit monitoring:

Phase 3:
At each 10-K filing:
   Check exhibit index for new or amended
   Exhibit 10.x with covenant-relevant titles:
   "Credit Agreement," "Loan Agreement,"
   "Amendment No. X to Credit Agreement,"
   "Amended and Restated Credit Agreement"

   If new or amended exhibit found:
      LLM extracts full covenant definitions
      including Consolidated EBITDA definition
      with complete addback list
      Updates stored covenant terms
      Computes Formula 2 headroom with new terms
      Flags any changes from prior version:
      "Credit agreement amended — covenant
      EBITDA definition updated; [X] addback
      items added/removed; addback cap changed
      from [prior] to [new]"

At each 8-K Item 1.01:
   If exhibit attached (most material amendments
   include the full amended agreement as an exhibit):
      Same LLM extraction as 10-K exhibit
      Processed immediately on filing date
      Do not wait for next quarterly filing

If no exhibit attached to 8-K Item 1.01:
   Use Debt Footnote at next quarterly filing
   for updated threshold
   Flag: "amendment disclosed in 8-K but full
   agreement not filed as exhibit — covenant
   terms update deferred to next 10-K/10-Q
   LLM extraction"
```

---

### Full Update Schedule — Calendar Year Large Accelerated Filer

| Timing | Event | Channel | Covenant Headroom Update Type |
|---|---|---|---|
| Every business day | Step-down proximity countdown | Internal computation | Days-to-step-down updated; threshold crossing alerts if post-step-down headroom deteriorates |
| Every business day | Waiver expiry countdown | Internal computation | Days-to-waiver-expiry updated; escalating alerts as expiry approaches |
| ~Jan 30 – Feb 15 | Q4 earnings press release | 8-K Item 2.02 | Covenant compliance statement if disclosed; headroom if voluntarily disclosed; Phase 3 only |
| ~Mar 31 | 10-K filed | 10-K | Full LLM re-extraction of all covenant terms; threshold version confirmed or updated; Formula 1, 2, and 3 headroom computed; step-down schedule refreshed; breach/waiver/amendment disclosure checked |
| ~Apr 14–25 | Q1 earnings press release | 8-K Item 2.02 | Covenant compliance statement; Phase 3 only |
| ~May 10 | Q1 10-Q filed | 10-Q | Ratio updated from XBRL; headroom recomputed against stored threshold; breach/waiver disclosure checked via LLM; compliance affirmation confirmed |
| ~Jul 15–25 | Q2 earnings press release | 8-K Item 2.02 | Covenant compliance statement; Phase 3 only |
| ~Aug 9 | Q2 10-Q filed | 10-Q | Same as Q1 10-Q |
| ~Oct 14–25 | Q3 earnings press release | 8-K Item 2.02 | Covenant compliance statement; Phase 3 only |
| ~Nov 9 | Q3 10-Q filed | 10-Q | Same as Q1 10-Q |
| Nov 9 – Mar 31 | Q4 dark window | Limited | Ratio not updated; threshold unchanged unless amendment; monitor 8-K Item 1.01 daily for flagged issuers; waiver and step-down countdowns continue |
| Any business day | Covenant waiver or amendment | 8-K Item 1.01 | IMMEDIATE: breach confirmed (if waiver); threshold updated (if amendment); full LLM extraction of new terms; Critical alert generated |
| Any business day | New credit facility | 8-K Item 1.01 + Exhibit 10.x | Full LLM extraction of new covenant terms; replace stored thresholds; compute headroom under new terms; compare new terms to prior for tightening/loosening signal |
| Any business day | Debt acceleration / default | 8-K Item 2.04 | IMMEDIATE CRITICAL — acceleration confirmed; covenant breach cause |
| Any business day | Going concern disclosure | Any filing | IMMEDIATE CRITICAL — same as all prior metrics |

---

### Phase Summary

**Phase 2:**

Proxy headroom only — flag when leverage exceeds 5.5x or coverage falls below 2.0x as market-convention approximations of typical covenant thresholds. Label all proxy outputs prominently as "proxy — actual covenant terms not extracted." Monitor 8-K Item 1.01 with keyword filter for issuers already at proxy alert levels — detect waiver and amendment events. Monitor 8-K Item 2.04 as automatic Critical escalation. Run waiver expiry countdown for any waivers identified through keyword monitoring. Run going concern keyword search across all filing types. Apply step-down proximity alerts only if step-down schedule was manually entered at onboarding (cannot be extracted automatically in Phase 2 without LLM).

**Phase 3:**

Replace proxy approach with actual LLM-extracted thresholds at each 10-K and event-driven update at each 8-K Item 1.01. Compute Formula 1 basic headroom quarterly using XBRL ratios and stored thresholds. Compute Formula 2 adjusted headroom annually using full Consolidated EBITDA definition and addback list from credit agreement exhibit. Compute Formula 3 forward stress test quarterly using projected ratios from FCF and Leverage time series combined with step-down schedule. Monitor 8-K Item 2.02 for voluntary covenant compliance and headroom disclosures. Monitor credit agreement exhibits at each 10-K for addback list changes. Run daily step-down proximity countdown and waiver expiry countdown. Implement estimated quarters-to-breach computation using EBITDA cushion and trailing EBITDA decline rate.

