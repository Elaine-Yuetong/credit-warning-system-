# Liquidity 

## What it is

### Core Definition

Liquidity measures whether a company has enough cash and near-cash assets to meet its obligations that are due within the next 12 months. It answers: *"if the company had to pay everything it owes in the next year using only what it already has on hand or can quickly convert to cash, could it do it?"*

---

### Liquidity vs Solvency

The distinction between liquidity and solvency is the most important concept to understand before defining this metric.

| Concept | Definition | Time Horizon |
|---------|------------|--------------|
| **Solvency** | Does the company's asset base exceed its total liabilities? | Long-term |
| **Liquidity** | Does the company have enough cash and near-cash assets to meet near-term obligations? | Short-term |

**Key insights:**
- A company can be solvent on paper (assets exceed liabilities) but illiquid in practice (cash and near-cash insufficient to meet near-term obligations)
- A company can be technically insolvent (liabilities exceed assets) but remain liquid for an extended period if it continues generating operating cash flow
- Most corporate defaults are triggered by **illiquidity, not insolvency** — the company runs out of cash before it runs out of assets
- This is why liquidity is tracked as a standalone metric rather than subsumed into leverage or coverage

---

### The Mechanics of Liquidity Stress

A company under stress typically experiences a simultaneous tightening from **three directions**:

| Direction | Description |
|-----------|-------------|
| **1. Operating cash generation declines** | FCF compresses, reducing the internal source of cash |
| **2. Near-term debt obligations increase** | Maturities arrive; revolving credit facilities come up for renewal; covenant breaches accelerate debt that was not expected to be due |
| **3. Access to external liquidity contracts** | Lenders become cautious; credit lines are pulled or not renewed; capital markets become less accessible precisely when the company needs them most |

> The combination of reduced inflows, increased outflows, and restricted external access defines a liquidity crisis. None of the three alone is necessarily fatal. **All three together, arriving simultaneously, is how companies default.**

---

### The Two Complementary Lenses

Liquidity is measured through two lenses that your system tracks simultaneously.

#### Lens 1 — Stock of Liquidity (what the company currently holds)

| Component | Description |
|-----------|-------------|
| Unrestricted cash and cash equivalents | Balance sheet current assets |
| Short-term investments | Can be liquidated quickly |
| **Undrawn portion of committed revolving credit facilities** | Contractually committed source of cash that the company can draw on at short notice — not a balance sheet asset but functions as one for liquidity purposes |

> A company with $200M of cash and a $500M undrawn revolver has **$700M of immediately available liquidity** even though the balance sheet shows only $200M.

#### Lens 2 — Flow of Obligations (what the company owes in the near term)

| Component | Description |
|-----------|-------------|
| Current liabilities (balance sheet) | Accounts payable, accrued liabilities, short-term debt, current portion of long-term debt |
| Other contractual obligations due within 12 months | Any other obligations with contractual due dates |

> **Core liquidity metric:** Available liquidity (stock) divided by near-term obligations (flow)

---

### The Time Dimension

Balance sheet ratios alone cannot capture intra-year timing risk.

- A company might have adequate current assets to cover current liabilities in aggregate
- But if obligations come due in the next **30 days** and assets will not be converted to cash for **90 days**, the company faces a short-term cash crunch
- Even though its 12-month liquidity looks acceptable

> This intra-year timing risk is what the **Debt Maturity Wall** metric captures in more detail. Liquidity and maturity wall are companion metrics that together give a complete picture of near-term cash adequacy.

---

### Role in Your Credit Warning System

Liquidity serves two distinct analytical functions:

| Condition | Function |
|-----------|----------|
| **Normal conditions** | Baseline adequacy check — confirming that the company has sufficient near-term resources to operate without relying on new financing |
| **Stressed conditions** | **Most urgent metric in the entire spec** — once liquidity falls to a level where the company cannot meet near-term obligations from available resources, the timeline to a potential credit event is measured in **months rather than years** |

> The system must escalate immediately when liquidity reaches stress levels.

**Note on relationship to Quick Ratio and Current Ratio:**
Those ratios are the most commonly used quantitative liquidity metrics,
computed directly from balance sheet line items.
This Liquidity metric incorporates the same current/quick ratio logic,
then extends it by adding undrawn committed facilities and
cross-referencing the Debt Maturity Wall for timing precision.


## Why it signals stress

Liquidity signals stress through five mechanisms, each operating on a different timeline and with a different relationship to the other metrics in this spec.

---

### Mechanism 1 — The payment cliff (most immediate)

**Core logic:**
- Unlike leverage, coverage, and FCF — which describe the **trajectory** of a company's financial condition — liquidity describes its **current capacity to survive**
- A company that cannot meet a payment due tomorrow defaults tomorrow. There is no lag, no trend, no leading indicator dynamic
- When liquidity falls below the level needed to cover an imminent obligation, the credit event is not approaching — it has arrived

**System implication:**
- Liquidity is the most operationally critical metric in the system
- Every other metric in this spec is a predictor of eventual stress
- Liquidity tells you whether stress has already crossed the threshold into acute crisis

| Metric Type | Example | Action |
|-------------|---------|--------|
| Predictor | Leverage enters Highly Leveraged band | Alert and escalate |
| Acute crisis | Liquidity ratio < 1.0x + debt maturity due within 30 days | Emergency notification — monitoring an active event, not predicting one |

**The immediate signal:**
- Current liquidity ratio below 1.0x combined with any near-term debt obligation due within 90 days
- No trend analysis required
- A single observation at this level is sufficient to trigger the highest alert

---

### Mechanism 2 — The credit facility canary (early warning)

**Core logic:**
- Revolving credit facilities are among the most sensitive leading indicators of lender confidence
- When a company draws heavily on its revolver — particularly when FCF is negative and the draw funds operating losses rather than working capital — it signals that internal cash generation is insufficient and the company is consuming its committed liquidity buffer

**Why a fully drawn revolver is a critical warning sign:**

| Reason | Description |
|--------|-------------|
| **1. Exhausted liquidity** | The company has exhausted its most flexible source of liquidity — the emergency reserve that exists precisely for stress situations |
| **2. Covenant proximity** | Revolvers are subject to financial maintenance covenants. A company drawing heavily is often simultaneously approaching covenant limits |
| **3. Unavailability risk** | When a revolver is both fully drawn and close to covenant breach, the facility may be unavailable for further draws at exactly the moment the company needs it most |

**System detection:**
- Visible through the balance sheet — short-term borrowings or commercial paper balances increasing quarter over quarter while FCF is negative indicates revolver consumption
- This early warning signal typically precedes a liquidity crisis by **2–4 quarters**

**The early warning signal:**
- Revolver utilisation increasing for **2+ consecutive quarters** while FCF is negative
- Flag even if absolute liquidity levels appear adequate
- The direction of revolver draw combined with negative FCF is the pattern that precedes crisis

---

### Mechanism 3 — The refinancing wall interaction (medium term)

**Core logic:**
- Liquidity and the debt maturity wall are inseparable
- A company with strong current liquidity can appear safe while a large debt maturity looms 12 months ahead — the balance sheet snapshot looks fine but the forward picture is alarming
- Conversely, a company with thin current liquidity may be safe if no debt matures for three years and FCF is positive and improving

**The stress signal requires integration with the maturity profile:**

| Liquidity Condition | Maturity Profile | Risk Level |
|---------------------|------------------|------------|
| Strong current liquidity | Large maturity 12 months ahead | Balance sheet looks fine, forward picture alarming |
| Thin current liquidity | No maturities for 3 years + FCF improving | May be safe |

**When available liquidity (cash + undrawn revolver) is insufficient to cover upcoming debt maturities:**
- In benign credit markets → usually manageable (companies routinely refinance maturing debt)
- In stressed conditions, when credit quality has deteriorated → refinancing becomes difficult or prohibitively expensive

> The combination of thin liquidity and a near-term maturity wall is the classic precursor to a distressed exchange or bankruptcy filing.

**The medium-term signal:**
- Available liquidity (cash plus undrawn revolver) **less than 1.5× the debt maturities due within 12 months**
- This is not an immediate crisis but it means the company has little margin for error on refinancing
- Any market disruption, covenant issue, or operational setback could convert a manageable refinancing into a crisis

---

### Mechanism 4 — The working capital trap (often overlooked)

**Core logic:**
- Current liabilities include not just financial debt but also operating liabilities — accounts payable, accrued expenses, deferred revenue
- Under stress, companies frequently **stretch their payables** to preserve cash — paying suppliers later to avoid drawing on the revolver or depleting cash
- This temporarily improves the cash balance but deteriorates the payables balance (also a current liability)

**The trap:**
A company has stretched payables to the maximum extent suppliers will tolerate, has drawn its revolver, and still has insufficient liquidity to operate.

| Stage | Consequence |
|-------|-------------|
| Suppliers begin demanding faster payment or cash on delivery | Accelerates cash consumption precisely when cash is most scarce |
| This dynamic can collapse a company's liquidity position | Within a **single quarter** |

**System detection:**
- Accounts payable days outstanding — if payables days are increasing while the cash balance is stable or declining, the company is likely stretching payables to preserve liquidity
- This is not directly captured in the liquidity ratio but is visible in the working capital components of the **OCF/EBITDA conversion ratio** (from FCF metric)

**The overlooked signal:**
- Accounts payable days outstanding increasing for **2+ consecutive quarters** combined with **declining cash balance**
- This pattern indicates payables stretching — a form of emergency liquidity management that creates future vulnerability
- Cross-reference with FCF conversion ratio deterioration

---

### Mechanism 5 — The covenant-liquidity feedback loop (self-reinforcing)

**Core logic:**

Financial maintenance covenants create a direct feedback loop between liquidity deterioration and debt acceleration:
Liquidity falls below covenant threshold
↓
Covenant breached
↓
Lenders have right to accelerate debt
↓
Debt becomes immediately due in full
↓
Eliminates remaining liquidity
↓
Triggers cross-default provisions
↓
Accelerates other debt instruments


**Example:**
- Company has $300M of cash and $2B of debt
- Covenant requires minimum $250M cash
- **Only $50M buffer** between current cash position and a covenant breach that could accelerate $2B of obligations

**Covenant visibility:**
- The covenant is **not visible in the standard liquidity ratio**
- Requires **footnote extraction via the LLM layer** to identify the specific threshold and compute headroom

**The feedback loop signal:**
- Available liquidity within **15% of any disclosed minimum liquidity covenant**
- This is the **Covenant Headroom metric** applied specifically to liquidity-based covenants
- It is the **highest-urgency early warning** this system produces because the feedback loop, once triggered, can accelerate a credit event within **days rather than quarters**

---

### Institutional validation

| Source | Content |
|--------|---------|
| **Moody's** | Liquidity analysis is conducted separately from leverage and coverage analysis precisely because a company can satisfy leverage and coverage thresholds while facing an imminent liquidity crisis. The **Speculative Grade Liquidity (SGL)** rating system — a standalone assessment of near-term liquidity for high-yield issuers — uses a four-point scale (SGL-1 through SGL-4) that assesses cash, revolver availability, near-term maturities, and covenant headroom independently of the senior unsecured rating. |
| **S&P** | Publishes a **liquidity descriptor** (Exceptional, Strong, Adequate, Less than Adequate, Weak) as a component of its credit analysis that is assessed separately from the financial risk profile. |

Both agencies treat a deterioration in liquidity assessment as a potential rating trigger independent of leverage and coverage trends — confirming that liquidity provides information about credit stress that the other metrics do not capture.

---

### Summary of Liquidity Alert Signals

| Mechanism | Signal | Timeline | Alert Level |
|-----------|--------|----------|-------------|
| M1 — Payment cliff | Liquidity ratio < 1.0x + debt due within 90 days | Immediate | Highest alert |
| M2 — Credit facility canary | Revolver utilisation ↑ 2+ quarters + FCF negative | 2–4 quarters lead | Early warning |
| M3 — Refinancing wall | Available liquidity < 1.5× 12-month maturities | Medium term | Flag |
| M4 — Working capital trap | Payables days ↑ 2+ quarters + cash declining | Medium term | Cross-reference with FCF |
| M5 — Covenant feedback loop | Liquidity within 15% of covenant minimum | Days to quarters | Highest-urgency early warning |

## Formula

---

**Liquidity is not a single ratio — it is a set of four complementary measures that together answer the question of whether a company can meet its near-term obligations.**

Unlike leverage (one ratio), coverage (one ratio), and FCF (one primary metric with two derived outputs), liquidity requires four simultaneous computations because each captures a different dimension of near-term cash adequacy. No single liquidity ratio is sufficient alone. A company can appear liquid on one measure and illiquid on another — and the combination tells a more complete story than any individual ratio.

---

**Formula 1 — Automated Baseline (XBRL / Deterministic)**

Four outputs are computed simultaneously:

---

**Output 1A — Current Ratio**

```
Current Ratio = Current Assets / Current Liabilities

Current Assets  = us-gaap:AssetsCurrent
Current Liabilities = us-gaap:LiabilitiesCurrent
```

The broadest liquidity measure. Answers: for every $1 of obligations due within 12 months, how many dollars of assets will be converted to cash within 12 months? Includes inventory, prepaid expenses, and other current assets that may not be quickly convertible to cash — which is why it is the least conservative of the four measures.

---

**Output 1B — Quick Ratio**

```
Quick Ratio = (Current Assets − Inventory − Prepaid Expenses)
              / Current Liabilities

Inventory       = us-gaap:InventoryNet
Prepaid Expenses = us-gaap:PrepaidExpenseAndOtherAssetsCurrent
```

More conservative than the current ratio because it excludes inventory (which may take months to sell and collect) and prepaid expenses (which cannot be converted to cash at all). Answers: excluding assets that cannot be quickly liquidated, can the company cover its current liabilities? For non-manufacturing companies with minimal inventory, the quick ratio and current ratio will be nearly identical. For retailers, manufacturers, and distributors, the gap between the two is meaningful.

---

**Output 1C — Cash Ratio**

```
Cash Ratio = (Cash & Equivalents + Short-Term Investments)
             / Current Liabilities

Cash & Equivalents    = us-gaap:CashAndCashEquivalentsAtCarryingValue
Short-Term Investments = us-gaap:ShortTermInvestments
```

The most conservative liquidity measure. Answers: using only cash and instruments immediately convertible to cash, can the company cover its current liabilities? Most companies operate with a cash ratio well below 1.0x — this is normal and expected. The cash ratio is most useful as a stress indicator when it falls to very low levels (below 0.10x) indicating the company has almost no cash buffer, or when it is tracked as a trend showing consistent depletion.

---

**Output 1D — Available Liquidity to Near-Term Debt Coverage**

```
Available Liquidity =
    Cash & Equivalents
  + Short-Term Investments
  + Undrawn Revolving Credit Facility

Near-Term Debt Obligations =
    Current Portion of Long-Term Debt
  + Short-Term Borrowings
  + Commercial Paper

Coverage =
    Available Liquidity / Near-Term Debt Obligations
```

This is the most credit-analytically relevant of the four measures. It answers: can the company cover its financial debt obligations due within 12 months using all immediately available liquidity sources including committed but undrawn credit facilities? It is more informative than the current ratio because it focuses on financial debt obligations specifically (not all current liabilities) and includes the revolver as a liquidity source (not shown on the balance sheet as an asset).

**Note on denominator choice:** Output 1D excludes operating liabilities (accounts payable, accrued expenses) because financial debt obligations are the relevant near-term liquidity risk for credit analysis. Operating liabilities are self-liquidating through the operating cycle and are not typically a source of default risk.

**Critical limitation:** The undrawn revolving credit facility is not directly available as an XBRL tag — it requires LLM extraction from the debt footnote or a separate credit agreement disclosure. For Phase 2, this output is computed without the revolver component and flagged as incomplete. For Phase 3, the LLM layer extracts the revolver commitment and drawn amount.

```
Phase 2 version (incomplete — no revolver):
Available Liquidity = Cash & Equivalents + Short-Term Investments
Flag: "revolver not included — available liquidity understated;
       full computation requires Phase 3 LLM extraction"

Phase 3 version (complete):
Available Liquidity = Cash + Short-Term Investments
                    + (Revolver Commitment − Drawn Amount)
```

**XBRL tags for Formula 1:**

| Input | Primary XBRL Tag | Fallback Tag |
|---|---|---|
| Current Assets | `us-gaap:AssetsCurrent` | Sum of current asset components |
| Current Liabilities | `us-gaap:LiabilitiesCurrent` | Sum of current liability components |
| Inventory | `us-gaap:InventoryNet` | `us-gaap:InventoryGross` |
| Prepaid Expenses | `us-gaap:PrepaidExpenseAndOtherAssetsCurrent` | `us-gaap:PrepaidExpenseCurrent` |
| Cash & Equivalents | `us-gaap:CashAndCashEquivalentsAtCarryingValue` | `us-gaap:CashCashEquivalentsAndShortTermInvestments` |
| Short-Term Investments | `us-gaap:ShortTermInvestments` | `us-gaap:MarketableSecuritiesCurrent` |
| Current Portion of LT Debt | `us-gaap:LongTermDebtCurrent` | `us-gaap:DebtCurrent` |
| Short-Term Borrowings | `us-gaap:ShortTermBorrowings` | `us-gaap:CommercialPaper` |

**What is excluded from Formula 1:** Undrawn revolving credit facility (Phase 3 only), committed but undrawn term loan facilities, receivables financing facilities, letters of credit, and any other off-balance-sheet liquidity sources. All of these require LLM extraction.

**Error handling:** If Current Assets is null, Current Ratio = null. If Current Liabilities is null or zero, all ratios = null — a company cannot have zero current liabilities. Log all nulls individually. Never compute a ratio with a zero denominator.

---

**Formula 2 — Moody's-Style (Adjusted, requires LLM footnote extraction)**

Moody's liquidity analysis focuses on the twelve-month forward liquidity assessment — comparing all sources of liquidity against all uses over the next four quarters. This is more comprehensive than the balance sheet snapshot ratios of Formula 1 because it incorporates the revolving credit facility, upcoming debt maturities, and projected FCF as a liquidity source.

```
Moody's Twelve-Month Liquidity Assessment:

Sources of Liquidity =
    Current Cash & Equivalents (unrestricted)
  + Undrawn Committed Revolving Credit Facility
    (net of letters of credit and other holdbacks)
  + Projected FCF over next 12 months
    (from most recent FCF run-rate, adjusted for
     management guidance if available)
  + Proceeds from confirmed asset sales
    (if announced and expected within 12 months)

Uses of Liquidity (next 12 months) =
    Debt maturities due within 12 months
  + Required capex (maintenance only)
  + Scheduled dividend payments
  + Scheduled debt amortisation payments
  + Working capital seasonal requirements
    (if applicable — retail, agriculture)

Liquidity Surplus / (Deficit) =
    Sources − Uses

Liquidity Coverage Ratio (Moody's) =
    Sources / Uses
```

**What LLM must extract from footnotes:**
- Revolving credit facility: total commitment, current drawn amount, maturity date, key covenants (from Debt Footnote — typically Note 5–9)
- Debt maturities due within 12 months (from Debt Maturity Schedule in Debt Footnote — same as Debt Maturity Wall metric)
- Confirmed asset sale proceeds (from MD&A or 8-K disclosures)
- Management FCF guidance (from MD&A Liquidity and Capital Resources section)
- Letters of credit and other revolver holdbacks reducing net availability (from Debt Footnote)

---

**Formula 3 — S&P-Style (Conservative, requires LLM footnote extraction)**

S&P's liquidity assessment uses a qualitative descriptor (Exceptional, Strong, Adequate, Less than Adequate, Weak) derived from a quantitative sources-and-uses analysis combined with qualitative factors. The quantitative component is similar to Moody's twelve-month assessment but adds a second twelve-month window (months 13–24) and explicitly includes covenant headroom as a liquidity constraint.

```
S&P Liquidity Assessment Inputs:

Quantitative — Year 1 (next 12 months):
    Sources / Uses ratio (same definition as Moody's)
    Threshold for "Adequate": Sources / Uses ≥ 1.2x
    Threshold for "Strong": Sources / Uses ≥ 1.5x
    Threshold for "Exceptional": Sources / Uses ≥ 2.0x

Quantitative — Year 2 (months 13–24):
    Sources / Uses ratio for second year
    Sources include: projected FCF year 2,
    undrawn facilities with maturity > 12 months
    Uses include: debt maturities in months 13–24,
    maintenance capex year 2, dividends year 2

Qualitative factors that can reduce descriptor:
    — Covenant headroom < 15% on any maintenance covenant
      → reduces descriptor by one level
    — Revolving credit facility matures within 12 months
      → reduces descriptor to "Less than Adequate" or worse
    — Company reliant on capital markets for refinancing
      with deteriorating credit quality
      → reduces descriptor by one level
    — No committed backup liquidity (no revolver)
      → cap at "Adequate" regardless of quantitative score

S&P Liquidity Descriptor Mapping:
    Exceptional: Y1 ≥ 2.0x, Y2 adequate, no qualitative flags
    Strong:      Y1 ≥ 1.5x, Y2 positive, minor flags only
    Adequate:    Y1 ≥ 1.2x, Y2 positive or neutral
    Less than Adequate: Y1 1.0x–1.2x OR qualitative concerns
    Weak:        Y1 < 1.0x OR covenant breach imminent
```

Source: S&P Corporate Methodology and S&P Liquidity Descriptors framework. S&P publishes the liquidity descriptor as part of its credit rating rationale for most rated issuers — this allows Phase 3 validation by comparing system-computed descriptors against published S&P assessments.

**What LLM must extract from footnotes:**
- All items from Formula 2 plus:
- Covenant headroom on all financial maintenance covenants (from Debt Footnote covenant description)
- Revolver maturity date (to assess whether it matures within 12 months)
- Year 2 debt maturities (months 13–24, from Debt Maturity Schedule)
- Capital markets access assessment (from MD&A and rating agency commentary — qualitative)

---

**Companion Metric — Days Cash on Hand**

```
Days Cash on Hand =
    (Cash & Equivalents + Short-Term Investments)
    / (Operating Expenses / 365)

Operating Expenses =
    Cost of Revenue + SG&A + R&D
    (excludes D&A — non-cash)
    (excludes interest expense — financing cost)
```

This metric answers: how many days can the company fund its operations from cash alone, with no new revenue or external funding? It is most relevant for companies with thin or negative FCF margins and is a direct operationalisation of the liquidity runway concept described in the FCF metric. It is not a standalone metric but a supplementary output computed alongside the four primary liquidity measures.

---

**Comparison Table**

| | Formula 1 — Baseline | Formula 2 — Moody's | Formula 3 — S&P |
|---|---|---|---|
| **Primary output** | Four ratios (Current, Quick, Cash, Available Liquidity Coverage) | Twelve-month Sources/Uses surplus or deficit | Liquidity descriptor (Exceptional to Weak) |
| **Revolver included** | ❌ Phase 2 (❌ → ✅ Phase 3) | ✅ Yes | ✅ Yes |
| **Forward FCF included** | ❌ No | ✅ Yes (12-month projection) | ✅ Yes (24-month projection) |
| **Debt maturities included** | Partially (current portion only) | ✅ Full 12-month schedule | ✅ Full 24-month schedule |
| **Covenant headroom** | ❌ No | Partially (covenant limits revolver availability) | ✅ Explicit qualitative factor |
| **Year 2 assessment** | ❌ No | ❌ No | ✅ Yes |
| **Requires LLM** | Partially (revolver in Phase 3) | ✅ Yes | ✅ Yes |
| **Output type** | Ratios | Dollar surplus / coverage ratio | Qualitative descriptor + quantitative inputs |
| **Implementation phase** | Phase 2 (partial) / Phase 3 (full) | Phase 3 | Phase 3 |

---

**Implementation Guidance**

Formula 1 outputs 1A, 1B, and 1C (Current, Quick, and Cash ratios) are fully computable from XBRL in Phase 2 with high extraction reliability — all inputs are standard balance sheet items consistently tagged. Output 1D (Available Liquidity Coverage) is partially computable in Phase 2 without the revolver component and should be flagged as an underestimate.

The four Formula 1 outputs should always be displayed together — presenting only the current ratio without the cash ratio and available liquidity coverage understates the analytical picture. A company can have a current ratio above 2.0x while its cash ratio is 0.05x and its available liquidity coverage (without revolver) is 0.30x — three very different pictures of the same balance sheet.

Formulas 2 and 3 are reserved for Phase 3 and require the LLM layer for revolver details, maturity schedules, and covenant headroom. Once implemented, the S&P liquidity descriptor is particularly valuable for portfolio monitoring because it condenses the multi-dimensional liquidity assessment into a single comparable signal across all 30 issuers — enabling quick identification of which names have deteriorated from Strong to Adequate or from Adequate to Less than Adequate in a given quarter.

---


## Where it lives

---

**Formula 1 — Automated Baseline**

All items are structured, on the face of financial statements, available in both 10-K and 10-Q.

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Current Assets | Balance Sheet | "Total current assets" — subtotal at the bottom of the current assets section | 10-K and 10-Q |
| Current Liabilities | Balance Sheet | "Total current liabilities" — subtotal at the bottom of the current liabilities section | 10-K and 10-Q |
| Inventory | Balance Sheet — Current Assets section | "Inventories" or "Inventory, net" — line item within current assets | 10-K and 10-Q |
| Prepaid Expenses | Balance Sheet — Current Assets section | "Prepaid expenses and other current assets" or "Prepaid expenses" — line item within current assets | 10-K and 10-Q |
| Cash & Equivalents | Balance Sheet — Current Assets section | "Cash and cash equivalents" — first line item in current assets for most companies | 10-K and 10-Q |
| Short-Term Investments | Balance Sheet — Current Assets section | "Short-term investments" or "Marketable securities, current" — line item within current assets | 10-K and 10-Q |
| Current Portion of LT Debt | Balance Sheet — Current Liabilities section | "Current portion of long-term debt" or "Current maturities of long-term debt" — line item within current liabilities | 10-K and 10-Q |
| Short-Term Borrowings | Balance Sheet — Current Liabilities section | "Short-term borrowings" or "Commercial paper" or "Notes payable" — line item within current liabilities | 10-K and 10-Q |

**Note on Current Assets and Current Liabilities subtotals:** These are among the most reliably tagged items in XBRL — required subtotals under US GAAP balance sheet presentation. The individual components within each subtotal are less consistently tagged. Your system should always attempt the subtotal tag first and fall back to summing components only if the subtotal is absent.

**Note on short-term investment classification:** Some companies classify short-term investments as cash equivalents (if maturity is under 90 days) and include them in the cash line. Others separate them as a distinct current asset. The system must check both `us-gaap:CashAndCashEquivalentsAtCarryingValue` and `us-gaap:ShortTermInvestments` to avoid double-counting when both are tagged. If `us-gaap:CashCashEquivalentsAndShortTermInvestments` is used as the primary tag it already bundles both — do not add `ShortTermInvestments` separately.

**Note on restricted cash in current assets:** Some companies include restricted cash as a current asset — amounts held in escrow, collateral accounts, or legally restricted for specific purposes. This should not be included in liquidity calculations because it is not freely available. Post-2018 US GAAP filings (ASC 230) require a reconciliation at the bottom of the cash flow statement separating restricted from unrestricted cash. Flag if restricted cash is material relative to total cash.

---

**Formula 2 — Moody's-Style Adjustments**

All adjustment items below are unstructured — they require LLM extraction from footnotes. All items are in addition to or modifications of the Formula 1 base inputs.

**Item 2a — Revolving Credit Facility: Commitment, Drawn Amount, and Net Availability**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote (typically Note 5–9, titled "Debt," "Long-Term Debt," "Credit Facilities," or "Borrowings") AND MD&A — Liquidity and Capital Resources subsection |
| Available in | 10-K and 10-Q |
| Exact location in footnote | The Debt Footnote will describe the revolving credit facility in a dedicated paragraph or sub-table. Look for: (1) total commitment amount, (2) amount currently drawn or outstanding, (3) letters of credit issued against the facility (which reduce net availability), (4) maturity date of the facility. The MD&A Liquidity section typically summarises net availability with a sentence like: "As of [date], we had $X million available under our revolving credit facility." |
| What LLM should extract | Four numbers: (1) total revolver commitment, (2) amount drawn, (3) letters of credit issued, (4) net availability = commitment − drawn − letters of credit. Also extract maturity date — if the revolver matures within 12 months, flag as a critical liquidity concern. |
| Why this matters | The undrawn revolver is often the single largest component of a company's available liquidity. A company with $200M cash and a $500M revolver ($0 drawn) has $700M of available liquidity — the balance sheet shows only $200M. Omitting the revolver in Phase 2 systematically understates liquidity for most investment-grade companies. |

**Item 2b — Projected FCF Over Next 12 Months**

| Field | Detail |
|---|---|
| Where it lives | MD&A — Liquidity and Capital Resources subsection AND Management Guidance (if company provides formal guidance) |
| Available in | 10-K primarily; sometimes 10-Q for companies with formal guidance programmes |
| Exact location | MD&A Liquidity section typically includes forward-looking language about expected cash generation, capex plans, and working capital requirements. Look for sentences disclosing: expected capex for the next fiscal year, expected FCF range, or management commentary on cash generation outlook. Companies with formal guidance programmes (typically large-cap) publish specific FCF guidance figures. |
| What LLM should extract | Management's disclosed FCF guidance or expected capex for the forward period. If not explicitly disclosed: use trailing twelve-month FCF from Formula 1 as proxy; flag: "forward FCF estimated from TTM run-rate — management guidance not found." |

**Item 2c — Confirmed Asset Sale Proceeds**

| Field | Detail |
|---|---|
| Where it lives | MD&A AND 8-K filings (Item 1.01 for material agreements, Item 8.01 for other events) |
| Available in | 10-K and 10-Q; 8-K when announced |
| Exact location | MD&A strategic section or subsequent events footnote (typically the last note in the financial statements — "Subsequent Events") will disclose confirmed asset sales expected to close within 12 months. 8-K Item 1.01 filings disclose material asset sale agreements on the day they are signed. |
| What LLM should extract | Confirmed (signed agreement) asset sale proceeds expected within 12 months. Exclude announced but unsigned transactions — too uncertain. Flag: "asset sale proceeds included in liquidity sources — verify transaction has closed or has signed agreement." |

---

**Formula 3 — S&P-Style Adjustments**

All Formula 2 items apply plus the following additional items.

**Item 3a — Covenant Headroom on Liquidity-Specific Covenants**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — covenant description section AND MD&A — covenant compliance discussion |
| Available in | 10-K and 10-Q |
| Exact location | Debt Footnote covenant section: look for minimum cash balance covenants, minimum liquidity covenants, or springing covenants triggered by revolver availability falling below a threshold. These are typically stated as: "the credit agreement requires us to maintain minimum liquidity of $X million at all times" or "a springing covenant is triggered if availability under the revolving facility falls below $X million." MD&A will often include a covenant compliance table showing actual vs required levels. |
| What LLM should extract | For each liquidity-related covenant: (1) covenant type (minimum cash, minimum liquidity, springing), (2) threshold amount, (3) current actual level, (4) headroom = actual − threshold, (5) headroom as percentage of threshold. Flag if headroom < 15% of threshold — S&P treats this as a qualitative negative factor reducing the liquidity descriptor. |

**Item 3b — Year 2 Debt Maturities (Months 13–24)**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — maturity schedule table |
| Available in | 10-K (full maturity schedule); 10-Q (partial — some companies update quarterly, others only annually) |
| Exact location | Same maturity table as Debt Maturity Wall metric. The second row of the annual maturity schedule shows debt due in year 2. For a December 31 fiscal year company filing a 10-K, this is debt maturing in the calendar year two years forward. |
| What LLM should extract | Total debt maturing in months 13–24. Used in S&P's Year 2 sources/uses assessment. If the 10-Q does not include an updated maturity schedule, use the most recent 10-K figure adjusted for any debt events since that filing. |

**Item 3c — Revolver Maturity Assessment**

| Field | Detail |
|---|---|
| Where it lives | Debt Footnote — revolving credit facility description (same location as Item 2a) |
| Available in | 10-K and 10-Q |
| Exact location | Maturity date disclosed in the revolving credit facility description paragraph. |
| What LLM should extract | Revolver maturity date. S&P automatically reduces the liquidity descriptor if the revolver matures within 12 months — a maturing revolver that has not been renewed represents the elimination of the company's primary liquidity backstop. Flag: "revolving credit facility matures within 12 months — S&P liquidity descriptor reduction triggered; refinancing of facility required." |

**Item 3d — Capital Markets Access Assessment**

| Field | Detail |
|---|---|
| Where it lives | MD&A — Liquidity and Capital Resources section AND Rating Agency Reports (external, not in filing) |
| Available in | 10-K and 10-Q |
| Exact location | MD&A Liquidity section will often include management's assessment of capital markets access. Look for language such as: "we believe we have adequate access to capital markets," "we may seek to access capital markets opportunistically," or conversely "market conditions have limited our ability to access external financing." Rating agency commentary on the issuer's capital markets access can be extracted from published rating rationales. |
| What LLM should extract | Management's characterisation of capital markets access — positive, neutral, or cautious. Any language indicating limited or uncertain access should be flagged as a qualitative liquidity negative. This input is entirely qualitative — no number is extracted. |

**Caveat:** Management characterisation of capital markets access is typically optimistic. If the filing does not contain any explicit discussion of capital markets access, assume neutral (no positive or negative adjustment). Only flag as negative if language explicitly indicates concern (e.g., "uncertain access," "market conditions have limited our ability," "refinancing risk").

---

**Days Cash on Hand — Where It Lives**

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Cash & Equivalents | Balance Sheet | Same as Formula 1 | 10-K and 10-Q |
| Short-Term Investments | Balance Sheet | Same as Formula 1 | 10-K and 10-Q |
| Cost of Revenue | Income Statement | "Cost of goods sold" or "Cost of revenues" | 10-K and 10-Q |
| SG&A | Income Statement | "Selling, general and administrative expenses" | 10-K and 10-Q |
| R&D | Income Statement | "Research and development" — if applicable | 10-K and 10-Q |
| D&A (to exclude) | Cash Flow Statement | Same as Leverage Formula 1 — excluded from operating expenses denominator | 10-K and 10-Q |

---

**Summary Table — Where Each Item Lives**

| Item | Formula | Statement / Document | Section | 10-K Only or Both |
|---|---|---|---|---|
| Current Assets (subtotal) | F1 | Balance Sheet | Current Assets subtotal | Both |
| Current Liabilities (subtotal) | F1 | Balance Sheet | Current Liabilities subtotal | Both |
| Inventory | F1 | Balance Sheet | Current Assets — individual line | Both |
| Prepaid Expenses | F1 | Balance Sheet | Current Assets — individual line | Both |
| Cash & Equivalents | F1, F2, F3 | Balance Sheet | Current Assets — first line | Both |
| Short-Term Investments | F1, F2, F3 | Balance Sheet | Current Assets — individual line | Both |
| Current Portion of LT Debt | F1, F2, F3 | Balance Sheet | Current Liabilities — individual line | Both |
| Short-Term Borrowings / CP | F1, F2, F3 | Balance Sheet | Current Liabilities — individual line | Both |
| Revolving credit facility details | F2, F3 | Debt Footnote + MD&A | Facility description paragraph + Liquidity section | Both |
| Forward FCF projection | F2, F3 | MD&A | Liquidity and Capital Resources subsection | 10-K primarily |
| Confirmed asset sale proceeds | F2, F3 | MD&A + Subsequent Events footnote + 8-K | Strategic section + last footnote + Item 1.01 | Both |
| Liquidity covenant thresholds | F3 | Debt Footnote + MD&A | Covenant section + covenant compliance table | Both |
| Year 2 debt maturities | F3 | Debt Footnote | Maturity schedule — Year 2 row | 10-K primarily |
| Revolver maturity date | F3 | Debt Footnote | Facility description paragraph | Both |
| Capital markets access | F3 | MD&A | Liquidity and Capital Resources subsection | Both |
| Operating expenses (for days cash) | F1 supplementary | Income Statement | Cost of revenue + SG&A + R&D | Both |

---

**Structured or Unstructured — Liquidity Metric (All Three Formulas)**

| Input / Component | Formula | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|---|
| **Current Assets (subtotal)** | F1 | Primary: `us-gaap:AssetsCurrent` | Structured — required GAAP subtotal | Among the most reliably tagged balance sheet items. Virtually always present. Use subtotal first — fall back to summing components only if subtotal tag absent. |
| **Current Liabilities (subtotal)** | F1 | Primary: `us-gaap:LiabilitiesCurrent` | Structured — required GAAP subtotal | Same reliability as Current Assets. If null after primary tag attempt, sum: `us-gaap:AccountsPayableCurrent` + `us-gaap:AccruedLiabilitiesCurrent` + `us-gaap:LongTermDebtCurrent` + `us-gaap:ShortTermBorrowings` + `us-gaap:DeferredRevenueCurrent` + `us-gaap:OtherLiabilitiesCurrent`. Flag: "current liabilities derived from components — verify completeness." |
| **Inventory** | F1 | Primary: `us-gaap:InventoryNet` Fallback: `us-gaap:InventoryGross` | Structured — with valuation method risk | Net of valuation allowances. If only gross inventory is tagged, flag: "gross inventory used — inventory write-down allowance not deducted; quick ratio may be overstated." For companies with no inventory (service companies, financials, software), tag will be absent — treat as zero with no flag needed; verify SIC code confirms no-inventory business model. |
| **Prepaid Expenses** | F1 | Primary: `us-gaap:PrepaidExpenseAndOtherAssetsCurrent` Fallback: `us-gaap:PrepaidExpenseCurrent` | Structured — sometimes bundled with other current assets | Fallback tag excludes "other current assets" component. If neither tag present, attempt: `us-gaap:OtherAssetsCurrent` as proxy. Flag if used: "prepaid expenses proxied by other current assets — quick ratio may be slightly understated." If all tags null and company is a service business: treat as zero; flag. |
| **Cash & Equivalents** | F1, F2, F3 | Primary: `us-gaap:CashAndCashEquivalentsAtCarryingValue` Fallback 1: `us-gaap:CashCashEquivalentsAndShortTermInvestments` Fallback 2: `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | Structured — with restriction and bundling risk | See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 5 (Unrestricted Cash) — apply identical four-step fallback chain including restricted cash detection and subtraction. Fallback 1 bundles short-term investments — do not double-count with Short-Term Investments tag. Fallback 2 includes restricted cash — subtract `us-gaap:RestrictedCashAndCashEquivalents` if available; flag if not. Restricted cash is not freely available and must not be included in liquidity calculations. |
| **Short-Term Investments** | F1, F2, F3 | Primary: `us-gaap:ShortTermInvestments` Fallback: `us-gaap:MarketableSecuritiesCurrent` | Structured — with bundling risk | Check for overlap with cash tag. If `us-gaap:CashCashEquivalentsAndShortTermInvestments` was used for cash, do not add Short-Term Investments separately — already included. Flag: "short-term investments already bundled in cash tag — not added separately to avoid double-count." |
| **Current Portion of LT Debt** | F1, F2, F3 | Primary: `us-gaap:LongTermDebtCurrent` Fallback: `us-gaap:DebtCurrent` | Structured — with double-count risk | See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 2 (Current Portion of Long-Term Debt) — apply identical double-count check. `DebtCurrent` may aggregate short-term borrowings already captured separately. Verify before summing. |
| **Short-Term Borrowings / Commercial Paper** | F1, F2, F3 | Primary: `us-gaap:ShortTermBorrowings` Fallback 1: `us-gaap:CommercialPaper` Fallback 2: `us-gaap:NotesPayableCurrent` Fallback 3: `us-gaap:LineOfCreditCurrent` | Structured — must sum all non-null values | Same Apple validation finding applies here: `ShortTermBorrowings` alone misses CP issuers. Sum all non-null tags — a company can have both CP and a drawn revolver simultaneously. |
| **Current Ratio** (derived) | F1 | No standard tag | Structured inputs, derived result | Current Ratio = AssetsCurrent / LiabilitiesCurrent. If either input null → ratio null. If LiabilitiesCurrent = 0 → undefined; flag: "zero current liabilities — verify filing completeness." |
| **Quick Ratio** (derived) | F1 | No standard tag | Structured inputs, derived result | Quick Ratio = (AssetsCurrent − InventoryNet − PrepaidExpense) / LiabilitiesCurrent. If Inventory null: use AssetsCurrent without deduction and flag: "inventory not found — quick ratio equals current ratio; may be overstated for manufacturing/retail issuers." If Prepaid null: omit deduction silently for service companies; flag for others. |
| **Cash Ratio** (derived) | F1 | No standard tag | Structured inputs, derived result | Cash Ratio = (Cash + ShortTermInvestments) / LiabilitiesCurrent. Most conservative measure. Expected to be well below 1.0x for most companies — do not flag low cash ratio alone as stress without context. |
| **Available Liquidity Coverage** (derived, partial Phase 2) | F1 (partial), F2/F3 (full) | No standard tag | Structured inputs (Phase 2 partial) / Semi-structured (Phase 3 full) | Phase 2: (Cash + ShortTermInvestments) / (LongTermDebtCurrent + ShortTermBorrowings + CommercialPaper). Flag: "revolver excluded — available liquidity understated." Phase 3: adds undrawn revolver from LLM extraction. |
| **Days Cash on Hand** (derived) | F1 supplementary | No standard tag | Structured inputs, derived result | = (Cash + ShortTermInvestments) / (Daily Operating Expenses). Daily OpEx = (CostOfRevenue + SGA + RD − DA) / 365. If DA null: use (CostOfRevenue + SGA + RD) / 365 and flag: "D&A not excluded from operating expenses — days cash on hand slightly understated." **Caveat:** D&A may be embedded within Cost of Revenue and SG&A, not separately identifiable. If the company does not disclose D&A by segment, exclude this adjustment and flag: "D&A embedded in operating expenses — days cash on hand may be understated." |
| **Revolving Credit Facility — Commitment** | F2, F3 | No standard tag | **Unstructured — LLM required** | Lives in Debt Footnote (Note 5–9). LLM should read the revolving credit facility description paragraph. Extract: total commitment amount, typically stated as "$X billion revolving credit facility." Verify against MD&A Liquidity section which usually summarises. |
| **Revolving Credit Facility — Drawn Amount** | F2, F3 | Partial: `us-gaap:LineOfCreditCurrent` or `us-gaap:LongTermLineOfCredit` | Semi-structured — sometimes tagged, often in footnote | If XBRL tag present: use and verify against footnote. If absent: LLM extracts from Debt Footnote — look for "outstanding borrowings under the revolving credit facility" or "amount drawn." If zero drawn: footnote will state "no amounts outstanding" or similar. |
| **Revolving Credit Facility — Letters of Credit** | F2, F3 | No standard tag | **Unstructured — LLM required** | Letters of credit reduce net revolver availability but are not a cash draw. LLM should extract from Debt Footnote: "letters of credit issued under the facility totaling $X million." If not mentioned: assume zero; flag: "letters of credit not disclosed — net revolver availability may be slightly overstated." |
| **Revolving Credit Facility — Maturity Date** | F2, F3 | No standard tag | **Unstructured — LLM required** | LLM extracts from Debt Footnote facility description. Critical for S&P liquidity descriptor — revolver maturing within 12 months triggers descriptor reduction. Store as date field not dollar amount. |
| **Forward FCF Projection** | F2, F3 | No standard tag | **Unstructured — LLM required** | LLM reads MD&A Liquidity and Capital Resources section. Extract explicit management guidance if present. If absent: system uses TTM FCF run-rate as proxy. Flag all projections: "forward FCF estimated from [management guidance / TTM run-rate] — subject to revision." |
| **Confirmed Asset Sale Proceeds** | F2, F3 | No standard tag | **Unstructured — LLM required** | LLM reads MD&A strategic section and Subsequent Events footnote. Only include signed transactions. Flag: "asset sale proceeds included — verify transaction status before relying on as liquidity source." |
| **Liquidity Covenant Thresholds** | F3 | No standard tag | **Unstructured — LLM required** | LLM reads Debt Footnote covenant section and MD&A covenant compliance discussion. Extract: covenant type, threshold amount, current actual level, headroom. Minimum cash and minimum availability covenants are the most common types. If no liquidity covenant found: flag "no liquidity covenant identified — covenant-liquidity feedback loop risk not applicable." |
| **Year 2 Debt Maturities (months 13–24)** | F3 | No standard tag at year-2 granularity | **Unstructured — LLM required** | LLM reads Debt Footnote maturity schedule table — second row (Year 2). Same table as Debt Maturity Wall metric. Store Year 1 and Year 2 simultaneously to avoid duplicate LLM calls. Available in 10-K; may not be updated in 10-Q. |
| **Capital Markets Access Assessment** | F3 | No standard tag | **Unstructured — LLM required** | Fully qualitative. LLM reads MD&A Liquidity section and extracts management tone on capital markets access. Output is a three-value classification: Positive / Neutral / Cautious. No number extracted. Flag all cautious assessments as qualitative liquidity negative in S&P descriptor computation. |
| **Operating Expenses (for Days Cash)** | F1 supplementary | `us-gaap:CostOfRevenue` + `us-gaap:SellingGeneralAndAdministrativeExpense` + `us-gaap:ResearchAndDevelopmentExpense` | Structured — sum of three reliably tagged items | Exclude D&A (`us-gaap:DepreciationDepletionAndAmortization`) from the sum — Days Cash on Hand measures cash operating expenses only. If any component null: sum available components and flag which were missing. |


**Mapping: Capital Markets Access Assessment to S&P Liquidity Descriptor**

| Assessment | S&P Liquidity Descriptor Impact |
|------------|-------------------------------|
| Positive | No negative adjustment |
| Neutral | No adjustment |
| Cautious | Reduce liquidity descriptor by one level |

*Note:* This is a qualitative negative factor, not a deterministic rule. The final descriptor reduction may be overridden by other qualitative factors (e.g., revolver maturity within 12 months, covenant headroom < 15%) in the full S&P framework.

---



**Quick Reference — Structured vs Unstructured by Formula**

| | F1 — Baseline | F2 — Moody's | F3 — S&P |
|---|---|---|---|
| **Fully structured (XBRL)** | All four ratio inputs, Days Cash inputs | Inherits F1 + drawn revolver (when tagged) | Inherits F1 and F2 structured items |
| **Semi-structured (tag exists but needs verification)** | Short-term investments (bundling risk), restricted cash, current LT debt (double-count risk) | Drawn revolver (sometimes tagged, sometimes footnote) | Year 2 maturities (from prior 10-K if not updated in 10-Q) |
| **Fully unstructured (LLM required)** | Revolver commitment and net availability (Phase 3) | Revolver commitment, letters of credit, revolver maturity, forward FCF, asset sales | All F2 items + liquidity covenants, revolver maturity, capital markets access |
| **Qualitative output (no number)** | None | None | Capital markets access (Positive/Neutral/Cautious) |
| **LLM needed?** | Partially (revolver in Phase 3) | ✅ Yes | ✅ Yes |
| **Phase** | Phase 2 (partial) / Phase 3 (full) | Phase 3 | Phase 3 |

---

## Extraction Fallback Logic — Liquidity Metric

---

### Design Principles

Same four rules as prior metrics apply, plus three additional rules specific to Liquidity:

**Rule 1 — Never substitute zero for a missing input.** Missing inventory does not mean zero inventory for a manufacturer. Missing short-term investments does not mean the company holds none. Mark null and log.

**Rule 2 — Try every fallback before giving up.** Exhaust all tag options before escalating to LLM or declaring failure.

**Rule 3 — Log what you used.** Every computed ratio records which tag path was used for each input.

**Rule 4 — Never compute a ratio with zero current liabilities.** Zero current liabilities indicates an extraction failure, not a genuine balance sheet position. Every operating company has current liabilities. Mark all ratios null and escalate.

**Rule 5 — Partial computation is permitted and analytically valuable.** Unlike leverage where a missing EBITDA nullifies the entire ratio, liquidity has four outputs that can be computed independently. If inventory is missing, the current ratio can still be computed. If the revolver is missing (Phase 2), the available liquidity coverage can be computed as a partial figure. Each output has its own null propagation logic — a missing input for one output does not suppress the others.

**Rule 6 — Restricted cash must never be included in liquidity.** If the cash tag used includes restricted cash and no restricted cash subtraction is possible, flag the output as potentially overstated. Never use a potentially restricted cash figure to trigger a positive liquidity signal — only use it for stress signals (where overstatement is conservative). Reverse this logic for alert suppression: do not suppress a liquidity alert because cash appears adequate if that cash figure may include restricted amounts.

**Rule 7 — Double-counting between current assets and their components must be actively prevented.** Current Assets subtotal already includes cash, inventory, prepaid expenses, and all other current asset components. If the system uses the subtotal for the current ratio and then separately extracts components for the quick ratio, it must not re-add those components to the subtotal. Each ratio uses its own input set independently.

---

### Input 1 — Current Assets

**What we are trying to capture:** The total value of assets the company expects to convert to cash or consume within 12 months.

```
Step 1 — Try: us-gaap:AssetsCurrent
           Primary — required GAAP subtotal.
           Use whenever available.

Step 2 — If null, sum components:
           us-gaap:CashAndCashEquivalentsAtCarryingValue
           + us-gaap:ShortTermInvestments
           + us-gaap:AccountsReceivableNetCurrent
           + us-gaap:InventoryNet
           + us-gaap:PrepaidExpenseAndOtherAssetsCurrent
           + us-gaap:OtherAssetsCurrent
           Flag: "current assets derived from components —
           verify no current asset lines omitted"

Step 3 — If fewer than three components found in Step 2:
           Set Current Assets = null
           Flag: "current assets extraction failed —
           insufficient components found to derive subtotal"
           Current Ratio = null
           Quick Ratio = null
           (Cash Ratio and Available Liquidity Coverage
           can still be computed independently)

Step 4 — If all steps return null → log "current assets: no tag found"
           Set Current Assets = null
           Escalate to manual review
```

---

### Input 2 — Current Liabilities

**What we are trying to capture:** The total value of obligations the company must settle within 12 months.

**The most critical input in this metric.** A zero or null current liabilities figure makes all four ratio outputs impossible. Given its importance, the fallback chain is more extensive than for any other input.

```
Step 1 — Try: us-gaap:LiabilitiesCurrent
           Primary — required GAAP subtotal.
           Use whenever available.

Step 2 — If null, sum components:
           us-gaap:AccountsPayableCurrent
           + us-gaap:AccruedLiabilitiesCurrent
           + us-gaap:LongTermDebtCurrent
           + us-gaap:ShortTermBorrowings
           + us-gaap:CommercialPaper
           + us-gaap:DeferredRevenueCurrent
           + us-gaap:TaxesPayableCurrent
           + us-gaap:EmployeeRelatedLiabilitiesCurrent
           + us-gaap:OtherLiabilitiesCurrent
           Flag: "current liabilities derived from
           components — verify no current liability
           lines omitted"

Step 3 — Sanity check after Step 1 or Step 2:
           If Current Liabilities < 1% of Total Assets:
           Flag: "current liabilities appear implausibly
           low relative to total assets — verify extraction
           completeness; possible balance sheet
           presentation issue"
           Do NOT set to null — proceed with flagged value

Step 4 — If Current Liabilities = 0 exactly:
           Set all ratios = null
           Flag: "zero current liabilities — extraction
           failure; every operating company has current
           liabilities; manual review required"

Step 5 — If all steps return null → log "current liabilities: no tag found"
           Set all four ratio outputs = null
           Escalate to manual review — this is the
           most critical extraction failure in this metric
```

---

### Input 3 — Inventory

**What we are trying to capture:** The value of goods held for sale or use in production that will eventually be converted to cash through sales but cannot be immediately liquidated.

```
Step 1 — Try: us-gaap:InventoryNet
           Preferred — net of write-down allowances

Step 2 — If null, try: us-gaap:InventoryGross
           Flag: "gross inventory used — write-down
           allowance not deducted; quick ratio may
           be marginally overstated"

Step 3 — If null, try summing inventory components:
           us-gaap:InventoryRawMaterialsNetOfReserves
           + us-gaap:InventoryWorkInProcessNetOfReserves
           + us-gaap:InventoryFinishedGoodsNetOfReserves
           Flag: "inventory derived from raw materials,
           WIP, and finished goods components"

Step 4 — If all steps return null:
           Check SIC code / industry classification:
           If service company, software, financial
           institution, or other non-inventory business:
             Set Inventory = 0
             No flag needed — expected absence
             Quick Ratio = Current Ratio (expected)
           If manufacturer, retailer, or distributor:
             Set Inventory = null
             Flag: "inventory null for inventory-holding
             business — quick ratio cannot be computed;
             current ratio used as substitute but
             likely overstated"
             Quick Ratio = null (not Current Ratio)
```

---

### Input 4 — Prepaid Expenses

**What we are trying to capture:** Cash already paid for future expenses (insurance, rent, subscriptions) that cannot be converted back to cash.

```
Step 1 — Try: us-gaap:PrepaidExpenseAndOtherAssetsCurrent
           Broadest tag — includes prepaid and other
           current assets

Step 2 — If null, try: us-gaap:PrepaidExpenseCurrent
           Narrower — prepaid only

Step 3 — If null, try: us-gaap:OtherAssetsCurrent
           Proxy — may include items beyond prepaid
           Flag: "prepaid expenses proxied by other
           current assets — quick ratio may be
           marginally understated"

Step 4 — If all steps return null:
           For most companies prepaid expenses are
           small relative to total current assets.
           Set Prepaid = 0
           Flag: "prepaid expenses not found —
           treated as zero; quick ratio may be
           marginally overstated"
           This is the one input in this metric
           where zero substitution is acceptable
           because prepaid is typically immaterial
           and its absence from XBRL is common
           for companies that bundle it into
           other current assets.
           Exception: if AssetsCurrent is known and
           (Cash + Receivables + Inventory) already
           account for >95% of AssetsCurrent, then
           residual is approximately prepaid —
           compute as: Prepaid ≈ AssetsCurrent
           − Cash − Receivables − Inventory
```

---

### Input 5 — Cash & Equivalents

**What we are trying to capture:** Freely available cash and instruments convertible to cash within 90 days.

See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 5 (Unrestricted Cash) — apply identical four-step fallback chain including restricted cash detection. Summarised here for completeness:

```
Step 1 — Try: us-gaap:CashAndCashEquivalentsAtCarryingValue
Step 2 — Try: us-gaap:CashCashEquivalentsAndShortTermInvestments
           (bundles short-term investments — flag;
           do not add ShortTermInvestments separately)
Step 3 — Try: us-gaap:CashCashEquivalentsRestrictedCash
           AndRestrictedCashEquivalents
           (includes restricted cash — attempt to subtract
           us-gaap:RestrictedCashAndCashEquivalents;
           if not found, flag and use gross figure
           only for stress signals, not positive
           liquidity signals)
Step 4 — If all null → Cash = null → Cash Ratio = null
           Available Liquidity Coverage = null
           Current Ratio and Quick Ratio can still
           be computed if Current Assets is available
```

---

### Input 6 — Short-Term Investments

**What we are trying to capture:** Marketable securities and other liquid investments maturing or realisable within 12 months, beyond what is classified as cash equivalents.

```
Step 1 — Try: us-gaap:ShortTermInvestments

Step 2 — If null, try:
           us-gaap:MarketableSecuritiesCurrent

Step 3 — If null, try:
           us-gaap:AvailableForSaleSecuritiesCurrent

Step 4 — Double-count prevention (all steps):
           Before using any short-term investment tag value,
           verify that Cash tag used was NOT
           us-gaap:CashCashEquivalentsAndShortTermInvestments
           If it was: set Short-Term Investments = 0
           Flag: "short-term investments already included
           in bundled cash tag — set to zero to prevent
           double-count"

Step 5 — If all steps null and no bundling detected:
           Set Short-Term Investments = 0
           Flag: "short-term investments not found —
           treated as zero; cash ratio may be understated
           if company holds material short-term securities
           outside cash equivalents"
```

---

### Input 7 — Near-Term Debt Components (for Available Liquidity Coverage)

See LEVERAGE.md → Section "Extraction Fallback Logic" → Input 1 through Input 3 (Short-Term Borrowings, Current LT Debt, Long-Term Debt) — apply identical fallback chains; sum all non-null values; apply double-count check. Summarised here:

```
Short-Term Borrowings / CP:
Step 1: us-gaap:ShortTermBorrowings
Step 2: us-gaap:CommercialPaper
Step 3: us-gaap:NotesPayableCurrent
Step 4: us-gaap:LineOfCreditCurrent
Sum all non-null values — not mutually exclusive

Current Portion of LT Debt:
Step 1: us-gaap:LongTermDebtCurrent
Step 2: us-gaap:DebtCurrent
        (check for overlap with short-term borrowings
        before summing — see Leverage fallback logic)

Near-Term Debt Total = sum of all non-null debt components
If all debt components null:
   Near-Term Debt = null
   Available Liquidity Coverage = null
   Flag: "near-term debt not extractable — available
   liquidity coverage ratio cannot be computed"
   (Current, Quick, and Cash ratios unaffected)
```

---

### Input 8 — Revolving Credit Facility (Phase 3, LLM)

```
LLM extraction target: Debt Footnote

Step 1 — LLM reads Debt Footnote revolving credit
           facility description paragraph.
           Extract:
           (a) Total commitment: "$X billion revolving
               credit facility"
           (b) Drawn amount: "as of [date], $X million
               was outstanding" or "no amounts were
               outstanding"
           (c) Letters of credit: "$X million in letters
               of credit issued" — reduces availability
           (d) Other holdbacks: any other reductions
               to gross availability
           (e) Maturity date

Step 2 — Verify against MD&A Liquidity section:
           MD&A typically states net availability
           explicitly: "we had $X million available
           under our revolving credit facility"
           If MD&A figure differs from Debt Footnote
           derived figure: use MD&A figure as authoritative
           and flag discrepancy for review

Step 3 — Compute net availability:
           Net Revolver Availability =
           Total Commitment
           − Drawn Amount
           − Letters of Credit
           − Other Holdbacks

Step 4 — If LLM cannot find revolving credit facility:
           Set Revolver = null
           Flag: "no revolving credit facility found —
           available liquidity may be materially
           understated for companies relying on
           revolver as primary liquidity backstop"
           Available Liquidity Coverage remains
           computable as cash-only version with flag

Step 5 — Maturity date check:
           If Revolver Maturity Date within 12 months:
           Set Net Revolver Availability = 0 for
           liquidity calculation purposes
           Flag: "revolving credit facility matures
           within 12 months — excluded from available
           liquidity; refinancing of facility required
           to maintain liquidity position"
           S&P descriptor: reduce one level
```

---

### Ratio Computation and Null Propagation

```
Current Ratio = AssetsCurrent / LiabilitiesCurrent
  If AssetsCurrent null → null
  If LiabilitiesCurrent null or zero → null
  If both non-null → compute

Quick Ratio = (AssetsCurrent − Inventory − Prepaid)
              / LiabilitiesCurrent
  If AssetsCurrent null → null
  If LiabilitiesCurrent null or zero → null
  If Inventory null AND inventory-holding business → null
  If Inventory null AND non-inventory business → use zero
  If Prepaid null → use zero with flag
  If all inputs valid → compute

Cash Ratio = (Cash + ShortTermInvestments)
             / LiabilitiesCurrent
  If Cash null → null
  If LiabilitiesCurrent null or zero → null
  ShortTermInvestments null → treat as zero with flag
  If all inputs valid → compute

Available Liquidity Coverage =
  (Cash + ShortTermInvestments + NetRevolverAvailability)
  / (LongTermDebtCurrent + ShortTermBorrowings + CP)
  Phase 2: NetRevolverAvailability = 0 with flag
  Phase 3: NetRevolverAvailability from LLM
  If near-term debt = 0: ratio = undefined
    Flag: "no near-term financial debt — available
    liquidity coverage not meaningful; company has
    no near-term debt obligations"
    This is a positive signal not an error — log as
    "no near-term debt; liquidity adequate by definition"
  If Cash + Investments + Revolver = 0: ratio = 0
    Flag: "zero available liquidity — critical alert"

Days Cash on Hand =
  (Cash + ShortTermInvestments) /
  ((CostOfRevenue + SGA + RD − DA) / 365)
  If operating expense sum = 0 → undefined
    Flag: "zero operating expenses — days cash
    computation undefined; verify company is operating"
  If DA null → use (CostOfRevenue + SGA + RD) / 365
    Flag: "D&A not excluded — days cash slightly
    understated"
```

---

### Cross-Level Validation Rules

**Check 1 — Current ratio vs quick ratio gap**
```
Gap = Current Ratio − Quick Ratio
If Gap > 1.0:
   Flag: "large gap between current and quick ratio —
   significant inventory or prepaid assets; liquidity
   quality lower than current ratio suggests;
   quick ratio is more conservative measure for
   this issuer"
If Gap > 2.0:
   Flag: "very large current/quick ratio gap —
   verify inventory valuation and turnover;
   inventory may not be quickly convertible to cash"
```

**Check 2 — Cash ratio vs reported cash balance**
```
If Cash Ratio > 1.0:
   Flag: "cash ratio above 1.0x — company holds
   more cash than total current liabilities;
   verify no large upcoming debt maturity or
   capex commitment is misclassified as non-current"
   This is unusual and may indicate a large cash
   accumulation ahead of a known future payment.
```

**Check 3 — Available liquidity coverage vs current ratio divergence**
```
If Current Ratio > 2.0 AND
Available Liquidity Coverage (cash only, Phase 2) < 0.5:
   Flag: "current ratio appears healthy but cash-only
   liquidity coverage is low — current assets likely
   dominated by inventory or receivables rather than
   cash; liquidity quality concerns; verify revolver
   availability"
```

**Check 4 — Period consistency**
```
All liquidity inputs are instant (balance sheet) items.
They must all reference the same balance sheet date.
If any input references a different period context:
   Flag: "period mismatch in liquidity inputs —
   ratios computed from mixed balance sheet dates;
   results unreliable"
   Do NOT compute ratios from mixed periods.
```

**Check 5 — Trend deterioration cross-check**
```
Compare current period ratios to prior two periods:
If Current Ratio declines for 3 consecutive quarters:
   Watch alert (regardless of absolute level)
If Quick Ratio falls below prior period Current Ratio:
   Flag: "quick ratio now below prior period current
   ratio — inventory or prepaid growth consuming
   current assets; liquidity quality deteriorating"
If Cash Ratio declines for 2 consecutive quarters
while Current Ratio is stable:
   Flag: "cash ratio declining while current ratio
   stable — cash being replaced by less liquid
   current assets (inventory, receivables);
   underlying liquidity quality deteriorating"
```

---

### Audit Log Output Format (per company, per period)

```
{
  "ticker": "RAD",
  "period": "2023-03-04",
  "filing": "10-K",

  "inputs": {
    "current_assets": {
      "value": 3241.2,
      "tag_used": "us-gaap:AssetsCurrent",
      "path": "primary",
      "unit": "millions USD"
    },
    "current_liabilities": {
      "value": 2876.4,
      "tag_used": "us-gaap:LiabilitiesCurrent",
      "path": "primary",
      "unit": "millions USD"
    },
    "inventory": {
      "value": 1876.3,
      "tag_used": "us-gaap:InventoryNet",
      "path": "primary",
      "unit": "millions USD"
    },
    "prepaid_expenses": {
      "value": 142.1,
      "tag_used": "us-gaap:PrepaidExpenseAndOtherAssetsCurrent",
      "path": "primary",
      "unit": "millions USD"
    },
    "cash": {
      "value": 188.4,
      "tag_used": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
      "path": "primary",
      "unit": "millions USD"
    },
    "short_term_investments": {
      "value": 0,
      "tag_used": "us-gaap:ShortTermInvestments",
      "path": "primary",
      "note": "zero — no short-term investments held"
    },
    "current_lt_debt": {
      "value": 166.5,
      "tag_used": "us-gaap:LongTermDebtCurrent",
      "path": "primary",
      "unit": "millions USD"
    },
    "short_term_borrowings": {
      "value": 0,
      "tag_used": "us-gaap:ShortTermBorrowings",
      "path": "primary",
      "note": "zero — no short-term borrowings"
    },
    "revolver_availability": {
      "value": null,
      "source": "Phase 2 — LLM extraction not yet active",
      "flag": "revolver excluded — available liquidity understated"
    }
  },

  "derived": {
    "current_ratio": 1.13,
    "quick_ratio": 0.42,
    "cash_ratio": 0.07,
    "available_liquidity_coverage_partial": 1.13,
    "days_cash_on_hand": 4.2,
    "current_quick_gap": 0.71
  },

  "flags": [
    "Quick ratio 0.42 — significantly below current ratio 1.13;
     inventory-heavy balance sheet; liquidity quality
     lower than current ratio suggests",
    "Cash ratio 0.07 — very low; company has minimal
     cash buffer relative to current obligations",
    "Days cash on hand 4.2 — critically low; company can
     fund operations from cash alone for only 4 days",
    "Revolver excluded from available liquidity — Phase 2
     limitation; full liquidity assessment requires
     Phase 3 LLM extraction"
  ],

  "alerts": [
    "STRESS — Quick ratio 0.42; below 0.5x threshold",
    "CRITICAL — Days cash on hand 4.2; below 7-day threshold",
    "WATCH — Current ratio declining trend (1.31 → 1.21 → 1.13)"
  ],

  "warnings": [],
  "nulls": ["revolver_availability", "short_term_investments_confirmed"]
}
```

---
## Stress Threshold — Liquidity

---

### Structural Difference From Prior Metrics

Leverage, coverage, and FCF thresholds are calibrated to S&P's financial risk profile tables or market convention ratios that describe a company's long-term financial health trajectory. Liquidity thresholds are different in one fundamental way: they describe near-term survival capacity, not long-term trajectory. This means the alert logic is more binary and more urgent than for any other metric in this spec.

A leverage ratio of 6.5x is alarming but does not mean the company defaults next quarter. A cash ratio of 0.03x with a $500M debt maturity due in 60 days may mean exactly that. The threshold framework for liquidity must reflect this difference — lower severity alerts are still useful for early warning, but the upper end of the alert scale is more operationally urgent than for any other metric.

---

### Five Threshold Dimensions

Liquidity stress thresholds operate across five dimensions simultaneously corresponding to the four ratio outputs and the days cash on hand supplementary metric. All five must be evaluated together.

---

**Dimension 1 — Current Ratio**

Source: S&P Corporate Methodology and market convention. S&P treats a current ratio below 1.0x as a negative qualitative factor in its liquidity descriptor assessment. Academic literature (Altman 1968; Ohlson 1980) consistently identifies current ratio as one of the strongest predictors of financial distress in multivariate default models.

| Current Ratio | Financial Risk Interpretation | Alert Level |
|---|---|---|
| ≥ 2.0x | Strong — ample current asset buffer | No alert |
| 1.5x – 2.0x | Adequate — comfortable margin | No alert — monitor trend |
| 1.2x – 1.5x | Acceptable — thin but manageable | Watch |
| 1.0x – 1.2x | Weak — minimal buffer | Flag |
| 0.8x – 1.0x | Below parity — current liabilities exceed current assets | Stress |
| < 0.8x | Severely below parity | Critical |

**Formula 1 calibration note:** Current ratio uses balance sheet book values for current assets including inventory at cost. For companies in distress, inventory may be worth significantly less than book value if liquidated quickly. The current ratio therefore overstates liquidity quality for inventory-heavy companies under stress. Apply the quick ratio threshold in parallel — the more conservative of the two governs the alert level.

---

**Dimension 2 — Quick Ratio**

Source: Same as current ratio. The quick ratio is the more analytically reliable measure for credit purposes because it excludes inventory which may not be quickly convertible.

| Quick Ratio | Financial Risk Interpretation | Alert Level |
|---|---|---|
| ≥ 1.0x | Strong — liquid assets cover all current liabilities | No alert |
| 0.8x – 1.0x | Adequate — slight shortfall offset by operating cash generation | Watch |
| 0.6x – 0.8x | Below adequate — meaningful reliance on inventory conversion | Flag |
| 0.4x – 0.6x | Weak — significant reliance on inventory or new financing | Stress |
| < 0.4x | Severely weak — liquid assets deeply insufficient | Critical |

**Sector adjustment — retail and manufacturing:** These sectors structurally operate with quick ratios below 1.0x because their business model depends on inventory turnover. Apply a 0.2x downward adjustment to all thresholds for confirmed retail and manufacturing issuers:

| Sector Adjustment | Adjusted Quick Ratio Thresholds |
|---|---|
| Retail / Manufacturing Watch | < 0.6x (vs standard 0.8x) |
| Retail / Manufacturing Flag | < 0.4x (vs standard 0.6x) |
| Retail / Manufacturing Stress | < 0.3x (vs standard 0.4x) |
| Retail / Manufacturing Critical | < 0.2x (vs standard 0.4x) |

---

**Dimension 3 — Cash Ratio**

Source: Market convention for distressed credit analysis. No single published threshold table — the ranges below reflect investment banking and distressed debt practice.

| Cash Ratio | Financial Risk Interpretation | Alert Level |
|---|---|---|
| ≥ 0.5x | Strong cash position — significant buffer | No alert |
| 0.3x – 0.5x | Adequate — reasonable cash relative to current liabilities | No alert — monitor trend |
| 0.15x – 0.3x | Below adequate — limited cash buffer | Watch |
| 0.08x – 0.15x | Weak — minimal cash relative to obligations | Flag |
| 0.03x – 0.08x | Very weak — cash nearly exhausted relative to obligations | Stress |
| < 0.03x | Critical — essentially no cash buffer | Critical |

**Important context:** Most investment-grade companies operate with cash ratios in the 0.10x–0.30x range and rely on operating cash generation and revolving credit facilities rather than large cash balances to meet obligations. A low cash ratio is not automatically alarming for a company with strong FCF and an undrawn revolver. The cash ratio alert should always be cross-referenced with FCF and Available Liquidity Coverage before escalating. A cash ratio alert combined with negative FCF and a drawn revolver is critical. A cash ratio alert combined with positive FCF and an undrawn revolver may not require escalation beyond Watch.

---

**Dimension 4 — Available Liquidity Coverage**

Source: Moody's Speculative Grade Liquidity (SGL) rating framework and S&P Liquidity Descriptor framework. Both agencies treat available liquidity relative to near-term maturities as the primary quantitative liquidity metric. The thresholds below are consistent with the SGL and liquidity descriptor frameworks.

*Phase 2 (cash only — revolver excluded):*

| Available Liquidity Coverage (cash only) | Interpretation | Alert Level |
|---|---|---|
| ≥ 2.0x | Cash alone covers near-term debt twice over | No alert |
| 1.5x – 2.0x | Cash comfortably covers near-term debt | No alert — monitor trend |
| 1.0x – 1.5x | Cash covers near-term debt with thin margin | Watch |
| 0.5x – 1.0x | Cash insufficient to cover near-term debt alone | Flag — revolver dependency confirmed |
| 0.2x – 0.5x | Cash severely insufficient | Stress |
| < 0.2x | Cash almost non-existent relative to near-term debt | Critical |

*Phase 3 (full — revolver included):*

| Available Liquidity Coverage (cash + revolver) | S&P Descriptor Equivalent | Alert Level |
|---|---|---|
| ≥ 2.0x | Exceptional / Strong | No alert |
| 1.5x – 2.0x | Strong | No alert — monitor trend |
| 1.2x – 1.5x | Adequate | Watch |
| 1.0x – 1.2x | Less than Adequate | Flag |
| < 1.0x | Weak | Stress |
| < 0.5x | Weak — acute | Critical |

**Phase 2 flag:** All Available Liquidity Coverage alerts generated in Phase 2 must be flagged with: "alert based on cash only — revolver not included; actual available liquidity may be higher; verify revolver availability before escalating." Do not suppress the alert — flag it but note the limitation.

---

**Dimension 5 — Days Cash on Hand**

Source: Healthcare and non-profit financial analysis convention; adopted in distressed corporate credit analysis. Particularly relevant for companies with thin or negative FCF margins.

| Days Cash on Hand | Interpretation | Alert Level |
|---|---|---|
| ≥ 90 days | Strong — more than one quarter of operations fundable from cash | No alert |
| 60 – 90 days | Adequate — two months of operational runway | No alert — monitor trend |
| 30 – 60 days | Below adequate — less than two months of runway | Watch |
| 14 – 30 days | Weak — two to four weeks of operational runway | Flag |
| 7 – 14 days | Very weak — one to two weeks | Stress |
| < 7 days | Critical — less than one week of cash to fund operations | Critical — immediate escalation |

**Context dependency:** Days cash on hand is most meaningful for companies with negative or near-zero FCF where operating cash generation cannot be relied upon to supplement the cash balance. For companies with strong positive FCF, a low days-cash figure is less alarming because operating cash inflows replenish the balance continuously. Cross-reference with FCF metric before escalating days-cash alerts.

---

### Combined Alert Trigger Rules

The most severe alert across all five dimensions governs the overall liquidity alert level. Two additional combined rules apply:

| Alert Level | Any of These Conditions | Action |
|---|---|---|
| **Watch** | Current ratio 1.2x–1.5x; OR Quick ratio 0.8x–1.0x (standard) / 0.6x–0.8x (retail/manufacturing); OR Cash ratio 0.15x–0.30x; OR Available liquidity coverage 1.0x–1.5x (Phase 2) / 1.2x–1.5x (Phase 3); OR Days cash 30–60 | Log; weekly review |
| **Flag** | Current ratio 1.0x–1.2x; OR Quick ratio 0.6x–0.8x; OR Cash ratio 0.08x–0.15x; OR Available liquidity coverage 0.5x–1.0x (Phase 2) / 1.0x–1.2x (Phase 3); OR Days cash 14–30 | Generate alert; daily monitoring |
| **Stress** | Current ratio 0.8x–1.0x; OR Quick ratio 0.4x–0.6x; OR Cash ratio 0.03x–0.08x; OR Available liquidity coverage 0.2x–0.5x (Phase 2) / < 1.0x (Phase 3); OR Days cash 7–14 | Immediate alert; escalate to analyst same day |
| **Critical** | Current ratio < 0.8x; OR Quick ratio < 0.4x; OR Cash ratio < 0.03x; OR Available liquidity coverage < 0.2x (Phase 2) / < 0.5x (Phase 3); OR Days cash < 7; OR Zero available liquidity | Highest priority alert; cross-reference all metrics immediately |
| **Trend Flag** | Any ratio deteriorating for 3 consecutive quarters regardless of absolute level | Alert regardless of band |
| **Covenant Breach Imminent** | Available liquidity within 15% of any disclosed minimum liquidity covenant | Immediate escalation — covenant-liquidity feedback loop risk |
| **Revolver Maturing** | Revolving credit facility maturity within 12 months (Phase 3) | Immediate flag — primary liquidity backstop at risk |
| **Extraction Failure** | Current Liabilities null after all fallbacks | All ratios null; escalate to manual review |

---

**Combined Liquidity-FCF Rule:**
When both a liquidity alert and a negative FCF alert are active simultaneously for the same issuer in the same quarter, escalate the combined signal to the next alert level. A company that is both illiquid and burning cash has no internal mechanism to restore liquidity — it is entirely dependent on external financing or asset sales.

**Combined Liquidity-Maturity Rule:**
When an Available Liquidity Coverage alert is active AND the Debt Maturity Wall metric shows maturities exceeding available liquidity within 12 months, escalate to Critical regardless of the individual dimensions. This is the combination most directly associated with near-term default.

---

### Sector Exceptions and Adjustments

**Financial institutions:** Balance sheet liquidity ratios are not applicable in the same form — banks hold current liabilities (deposits) as their business model, producing structurally extreme leverage ratios that are meaningless under this framework. Flag for manual review. Do not apply these thresholds.

**Utilities and regulated infrastructure:** These sectors operate with relatively low current ratios (often 0.8x–1.1x) because their stable, predictable operating cash flows mean they do not need to hold large liquid asset buffers. Apply the following adjustment: reduce all threshold boundaries by 0.2x for confirmed utility issuers. A current ratio of 0.9x for a utility is Watch rather than Stress.

**Seasonal businesses (retail, agriculture, hospitality):** Current ratio and quick ratio fluctuate dramatically within the year. A retailer's current ratio in August (pre-holiday inventory build) will be far lower than in January (post-holiday cash collection). Always compare to the same quarter of the prior year rather than the sequential prior quarter. Flag when year-over-year same-quarter deterioration exceeds 0.3x on the current ratio.

**Companies in planned investment cycles:** A company deliberately consuming liquidity to fund a capex programme may show deteriorating liquidity ratios without being in distress. The distinguishing feature is whether leverage and coverage are stable and FCF compression is accompanied by clear management guidance on investment cycle completion. Apply analyst judgment — flag but do not automatically escalate if investment cycle context is confirmed.

---

### Empirical Context and Backtest Anchor

**Historical reference — Rite Aid:**
Using the audit log figures validated above: Rite Aid fiscal 2023 current ratio = 1.13x (Watch), quick ratio = 0.42x (Stress — below 0.4x threshold for retail adjustment, Critical), cash ratio = 0.07x (Stress), days cash on hand = 4.2 days (Critical). The combined alert level would be Critical driven by days cash on hand and the retail-adjusted quick ratio. Available liquidity coverage without revolver = 1.13x (Watch for Phase 2 cash-only version). This confirms the liquidity metric would have generated a Critical alert for Rite Aid in fiscal 2023 — consistent with its October 2023 bankruptcy and with the stress signals already documented in the Leverage, Coverage, and FCF sections.

**Historical reference — general empirical evidence:**
Ohlson (1980) identified the current ratio as one of nine financial ratios with significant predictive power for corporate bankruptcy in a logistic regression model. His O-score model explicitly includes a working capital to total assets ratio and a current liabilities to current assets ratio — both of which are directly captured by the current and quick ratio thresholds above. More recent empirical work on leveraged loan defaults consistently identifies current ratio below 1.0x as a threshold above which default frequency increases materially, holding leverage and coverage constant.

Moody's SGL rating data confirms that companies rated SGL-4 (weakest liquidity) default at rates approximately 8–10 times higher than SGL-1 companies within 12 months — directly validating the urgency of liquidity alerts relative to leverage and coverage alerts for near-term default prediction.

**Phase 3 backtest validation targets:**

| Metric | Target |
|---|---|
| Catch rate (any dimension at Flag or above) | ≥ 85% of known distressed cases flagged at Flag or above at least one quarter before credit event — higher than leverage/coverage because liquidity deteriorates faster near the event |
| Lead time | Median lead time of ≥ 1 quarter between first liquidity flag and credit event — shorter than leverage/coverage because liquidity is a coincident-to-lagging indicator relative to those metrics but a leading indicator relative to the actual credit event |
| Critical alert precision | ≥ 70% of Critical liquidity alerts should be followed by a credit event within 2 quarters — high precision requirement given the urgency of Critical alerts |
| False positive rate | ≤ 25% of healthy issuers falsely flagged at Flag or above — slightly higher tolerance than leverage/coverage because sector-specific threshold adjustments need calibration |
| Combined alert precision | ≥ 90% of cases where both liquidity Critical and FCF Critical alerts are active simultaneously should result in a credit event within 2 quarters |

---

## Signal Timing — Liquidity

---

### Classification

**Coincident to lagging — the latest of the primary metrics, but the most urgent when it moves.**

Liquidity is the only metric in this spec that operates on two completely different timescales simultaneously. In early and middle stages of corporate distress, liquidity ratios move slowly and lag behind FCF, coverage, and leverage deterioration — companies have cash reserves that absorb stress for multiple quarters before balance sheet liquidity ratios visibly deteriorate. In late-stage distress, liquidity can collapse within a single quarter — a debt maturity arrives, a covenant is breached, a revolver is pulled — and the system has almost no lead time before the credit event occurs.

This dual nature means liquidity serves a different function in your system than the other metrics. FCF, coverage, and leverage are early warning indicators — they give you 2–6 quarters of lead time to identify and monitor a deteriorating credit. Liquidity is the confirmation indicator — when it deteriorates sharply, the credit event is no longer a future risk but an imminent reality. The two functions are complementary. The earlier metrics tell you a company is heading toward a cliff. The liquidity metric tells you it has reached the edge.

---

### The Absorption Phase and the Cliff Phase

Understanding liquidity signal timing requires understanding how companies manage liquidity under stress. There are two distinct phases:

**Phase A — The Absorption Phase (months −18 to −3 before credit event)**

During this phase the company is experiencing financial stress — FCF is negative or compressing, EBITDA is declining, leverage is rising — but the liquidity ratios are relatively stable. The company is absorbing the stress through three mechanisms: drawing down cash reserves accumulated in better times, drawing on the revolving credit facility, and stretching payables. All three consume liquidity silently without immediately triggering deterioration in the balance sheet ratios your system monitors. The current ratio may even remain above 1.0x throughout this phase because current assets (including inventory and receivables) are still substantial even as cash depletes.

During the Absorption Phase, the FCF, coverage, and leverage metrics are your primary signals. Liquidity ratios are providing false comfort — they appear stable while the underlying liquidity position is deteriorating. The signals visible in this phase are: declining cash balance quarter over quarter, increasing short-term borrowings (revolver draws), and working capital stretching. These are component-level signals within the liquidity metric rather than ratio-level signals. Your system should monitor these component trends separately from the ratio outputs.

**Phase B — The Cliff Phase (months −3 to 0 before credit event)**

The cliff arrives when the absorption mechanisms are exhausted. The revolver is fully drawn. Cash is nearly depleted. Payables cannot be stretched further without supplier action. At this point one of three triggering events typically occurs: a debt maturity arrives that the company cannot refinance, a covenant is breached triggering acceleration, or a supplier or lender pulls a facility. Any of these collapses the liquidity position within days to weeks — not quarters. The balance sheet ratios that were stable throughout the Absorption Phase deteriorate sharply in a single period.

During the Cliff Phase the liquidity metric becomes the primary signal. FCF, leverage, and coverage are already at stress levels — they are confirming what is already known. The liquidity metric is now telling you how much time remains and whether a credit event is imminent.

---

### Three-Tier Timing Structure

| Tier | Source | Data Quality | Lag After Quarter-End | Lead Before 10-Q | Use in System |
|---|---|---|---|---|---|
| **Tier 1 — Full recompute** | 10-Q / 10-K | Reviewed (10-Q) or audited (10-K); structured XBRL; Formula 1 computable | **+40 days** (large accelerated filer) | n/a | Primary liquidity ratios; triggers all alerts |
| **Tier 2 — Early directional signal** | 8-K Item 2.02 earnings press release | Preliminary; unaudited; company may disclose cash balance and revolver availability; unstructured text | **+14 to +25 days** | **−15 to −25 days before 10-Q** | Cash balance and revolver availability if disclosed; Phase 3 only |
| **Tier 3 — Real-time event trigger** | 8-K Items 2.03 / 2.04 / 1.01 / 8.01 (keyword filtered) | Event disclosure; no full balance sheet | **Within 4 business days** | Any time intra-quarter | Debt draws, maturity extensions, covenant waivers, revolver amendments — all are real-time liquidity signals |

**Liquidity-specific note on Tier 2:** Unlike coverage and FCF where the press release rarely discloses the primary metric inputs directly, many companies — particularly investment-grade and high-yield issuers under investor scrutiny — voluntarily disclose cash balances and revolver availability in their earnings press releases. For these issuers, Tier 2 provides a genuine liquidity signal rather than just an indirect EBITDA-based estimate. In Phase 3, the LLM should specifically search Item 2.02 text for cash balance, revolver availability, and any commentary on liquidity position.

**Liquidity-specific note on Tier 3:** Liquidity has more real-time event triggers than any other metric in this spec. The following 8-K events are direct liquidity signals that your system should monitor even in Phase 2 for issuers already flagged:

```
8-K events with direct liquidity implications:

Item 1.01 — Entry into material agreement:
   Keywords: "credit facility", "revolving credit",
   "amendment", "waiver", "extension", "covenant relief"
   Signal: revolver amendment may increase or decrease
   available liquidity; waiver may prevent imminent
   covenant breach

Item 2.03 — Material debt creation:
   Signal: new debt increases cash immediately
   (temporary positive liquidity signal) but increases
   future debt service obligations

Item 2.04 — Debt acceleration / default:
   Signal: AUTOMATIC CRITICAL ALERT
   A triggered acceleration eliminates liquidity
   by making debt immediately due

Item 8.01 — Other events (keyword filtered):
   Keywords: "liquidity", "cash", "revolver", "facility",
   "covenant", "waiver", "amendment", "maturity",
   "refinanc", "default"
   Signal: companies sometimes voluntarily disclose
   liquidity updates via 8.01 when not required
   by a specific item — particularly for distressed
   issuers managing investor relations around
   a liquidity concern
```

---

### The Staleness Problem Is Worst for Liquidity

The 40-day filing lag affects liquidity more severely than any other metric because liquidity can change dramatically within a single quarter in ways that are invisible to your system until the next filing.

**Scenario illustrating maximum staleness risk:**

```
Day 0 (Quarter-end, e.g. September 30):
   10-Q will show: Cash = $800M, Revolver = $500M undrawn
   Liquidity ratios: healthy — no alerts

Day 15:
   Company draws $400M on revolver to fund operations
   Cash effectively = $800M + $400M drawn = still $800M cash
   but revolver now $100M available
   Available liquidity has fallen from $1.3B to $900M
   INVISIBLE TO YOUR SYSTEM — no 8-K required if
   revolver draw is not material at entity level

Day 30:
   Company misses a supplier payment
   Working capital stress building
   INVISIBLE — no filing required

Day 40 (10-Q filing deadline):
   10-Q filed showing:
   Cash = $650M (depleted during quarter)
   Short-term borrowings (revolver drawn) = $400M
   Current liabilities increased
   Liquidity ratios: deteriorated
   YOUR SYSTEM SEES THIS — 40 days after quarter-end

Net result: your system is seeing liquidity data that is
40 days old on the best day. For a company entering the
Cliff Phase, 40 days is enough time for a complete
liquidity collapse to have occurred and partially reversed —
or to have become irreversible.
```

**This staleness asymmetry is the most important signal timing limitation in the entire spec.** It means that for companies already in the Flag or Stress band on liquidity, the 40-day filing lag represents a meaningful blind spot. Your system's response should be heightened monitoring frequency — checking for 8-K triggers daily rather than waiting for the next quarterly filing.

---

### Component-Level Early Warning Signals

Because ratio-level liquidity signals are lagging, the most valuable early warning from the liquidity metric comes from monitoring component trends that precede ratio deterioration. These are visible in the quarterly XBRL data and do not require LLM extraction:

```
Signal 1 — Cash balance declining for 3 consecutive quarters:
   Flag even if current ratio remains healthy.
   Indicates absorption phase — cash being consumed
   while other current assets mask ratio stability.

Signal 2 — Short-term borrowings increasing for
   2 consecutive quarters while FCF is negative:
   Flag — revolver draw pattern; company funding
   operations from credit facility.
   This is the most reliable Absorption Phase indicator.

Signal 3 — Current portion of LT debt increasing
   disproportionately:
   Indicates approaching debt maturities being
   reclassified to current — precursor to maturity
   wall stress. Cross-reference Debt Maturity Wall
   metric.

Signal 4 — Current assets growing faster than revenue
   while cash is stable or declining:
   Indicates receivables or inventory build —
   working capital trap developing.
   Cross-reference FCF OCF/EBITDA conversion ratio.

Signal 5 — Current liabilities growing faster than
   current assets for 2 consecutive quarters:
   Direct precursor to current ratio deterioration.
   Flag before the ratio itself crosses a threshold.
```

These five component signals should be computed and stored alongside the four ratio outputs in every quarterly extraction. They provide 1–3 quarters of lead time over the ratio thresholds and are the liquidity metric's contribution to the early warning sequence.

---

### Comparison: Liquidity vs Other Metrics Signal Speed

| Scenario | Liquidity Signal | FCF Signal | Coverage Signal | Leverage Signal | Earliest |
|---|---|---|---|---|---|
| Working capital deterioration | Lagging — 2–4 quarters behind cash flow | **Early — 1–2 quarters** | None initially | None initially | **FCF leads** |
| Revolver draw acceleration | **Medium — component signal 1–2 quarters** | Coincident | None | Slight increase | **Liquidity component leads** |
| Debt maturity reclassification to current | **Immediate — same quarter as reclassification** | None | None | None | **Liquidity leads** |
| Cash depletion from operations | Medium — ratio deteriorates as cash falls | **Early — FCF negative precedes** | Medium | None directly | **FCF leads** |
| Covenant breach | **Immediate — same period** | None directly | Coincident | Coincident | **Liquidity leads** |
| Cliff phase collapse | **Immediate — single quarter** | Confirming | Confirming | Confirming | **Liquidity is the signal** |
| Revolver pulled by lender | **Immediate — 8-K trigger** | None | None | None | **Liquidity leads — only metric that captures this** |

**Key insight:** Liquidity leads only in two scenarios — debt maturity reclassification and the cliff phase collapse. In all other scenarios it lags or is coincident. This confirms that liquidity is a confirmation and late-stage indicator, not a general early warning indicator. Its value is in the right tail of the distress distribution — when other metrics have already been flagging for multiple quarters and the system needs to assess how close a credit event actually is.

---

### Updated Signal Timing Summary

> **Signal Timing — Coincident to lagging in early distress; immediate and most urgent in late-stage distress.**
>
> Liquidity ratios absorb stress silently for 2–6 quarters through cash depletion, revolver draws, and payables stretching — during this Absorption Phase, FCF, coverage, and leverage are your primary signals and liquidity ratios provide false comfort. When the absorption mechanisms are exhausted the liquidity ratios enter the Cliff Phase and can collapse within a single quarter — at this point liquidity becomes the most urgent metric in the system and the other metrics are confirming signals.
>
> The 40-day filing lag is most damaging for liquidity of all the metrics because the Cliff Phase can complete within a single quarter. For issuers already at Flag or Stress on liquidity, monitor for 8-K triggers daily — particularly Items 2.04, 1.01 (credit facility amendments), and keyword-filtered 8.01 filings. These provide real-time liquidity signals that are unavailable for any other metric.
>
> Component-level signals — declining cash balance, increasing revolver draws, current liabilities growing faster than current assets — provide 1–3 quarters of lead time over ratio-level liquidity alerts and should be monitored as upstream signals in their own right. They are the liquidity metric's contribution to the early warning sequence alongside FCF compression and coverage deterioration.
>
> The combination of a liquidity Critical alert and a FCF Critical alert active simultaneously is the highest-confidence near-term default signal this system can generate from structured data alone. When both are active, the probability of a credit event within two quarters is high enough to warrant immediate escalation regardless of leverage and coverage levels.


## Frequency — Liquidity

---

### Overview

Liquidity shares the same six-channel update structure as all prior metrics. Filing deadlines, EDGAR availability rules, and the Phase 2 vs Phase 3 priority framework are identical — See LEVERAGE.md → Section "Frequency" → full section — apply identical six-channel framework, filing deadlines, EDGAR availability, and 8-K filtering rules; this section documents liquidity-specific differences only. 8-K filtering rules, and expected filing volumes by issuer type.

This section documents only the differences and liquidity-specific considerations that do not appear in prior frequency sections. There are more differences here than for any prior metric because liquidity has more real-time event triggers than any other metric in this spec.

---

### What Is the Same as Prior Metrics

| Channel | Filing Type | Phase 2 | Phase 3 |
|---|---|---|---|
| Quarterly financials | 10-Q | ✅ Primary source | ✅ Primary source |
| Annual financials | 10-K | ✅ Primary source | ✅ Primary source |
| Earnings press release | 8-K Item 2.02 | ❌ Ignore | ✅ Add |
| Material debt creation | 8-K Item 2.03 | ❌ Ignore | ✅ Add |
| Debt acceleration / default | 8-K Item 2.04 | ✅ Monitor (alert only) | ✅ Monitor |
| New bond issuance | 424B prospectus | ❌ Ignore | ✅ Add |

> For filing deadlines, EDGAR availability rules, and full 8-K filtering details, refer to the Leverage Frequency section.

---

### Liquidity-Specific Differences

**Difference 1 — Item 2.02 provides stronger liquidity signal than for FCF**

As noted in Signal Timing, many companies voluntarily disclose cash balances and revolver availability in earnings press releases — particularly investment-grade companies managing investor expectations and high-yield issuers under scrutiny. This makes Item 2.02 more useful for liquidity than for FCF (where OCF and capex are rarely disclosed) and approximately equivalent to coverage (where EBITDA is commonly disclosed).

**System behavior in Phase 3 when Item 2.02 is detected:**

```
Step 1 — LLM reads Item 2.02 text
Step 2 — Search for liquidity disclosures:
         Keywords: "cash and cash equivalents",
         "liquidity", "available liquidity",
         "revolving credit", "available under",
         "cash balance", "total liquidity"
Step 3 — If explicit cash balance found:
         Store as Tier 2 preliminary cash figure
         Flag: "cash balance from earnings press
         release — preliminary, unaudited;
         treat as directional signal only;
         do not replace Tier 1 XBRL figure"
Step 4 — If explicit revolver availability found:
         Store as Tier 2 preliminary revolver figure
         Flag: "revolver availability from press
         release — preliminary; verify against
         Debt Footnote in subsequent 10-Q"
Step 5 — Compute Tier 2 Available Liquidity:
         Cash (press release) + Revolver (press release)
         Flag: "Tier 2 available liquidity estimate —
         14–25 days before 10-Q; preliminary figures"
Step 6 — If neither cash nor revolver disclosed:
         No liquidity signal from this Item 2.02
         Flag: "no liquidity data in press release —
         Tier 1 10-Q remains sole liquidity source"
```

**Industries where Item 2.02 liquidity disclosure is most common:**
Investment-grade industrials, utilities, energy companies, and any issuer currently flagged at Watch or above on liquidity — stressed companies typically provide explicit liquidity reassurance in press releases to manage investor concern.

---

**Difference 2 — Item 1.01 is a primary liquidity update channel**

For leverage, coverage, and FCF, Item 1.01 (entry into material agreement) is a secondary keyword-filtered channel — occasionally relevant if the agreement involves debt. For liquidity, Item 1.01 is a primary channel because credit facility amendments, revolver renewals, and covenant waivers — all filed under Item 1.01 — directly and immediately change available liquidity.

```
Item 1.01 liquidity triggers — process immediately
when any of these keywords appear in the filing text:

Primary triggers (always process):
   "revolving credit facility"
   "credit agreement"
   "amendment" + "credit"
   "waiver" + "covenant"
   "extension" + "maturity"
   "commitment" + "credit"

Secondary triggers (process if issuer already flagged):
   "term loan"
   "letter of credit"
   "borrowing base"
   "springing covenant"
   "availability block"

LLM extraction targets when triggered:
   (1) New revolver commitment amount
       (increased, decreased, or unchanged)
   (2) New maturity date of facility
   (3) Any new covenant terms affecting availability
   (4) Any waiver of existing covenant breach
       (confirms breach occurred — escalate alert)
   (5) Any reduction in commitment (lender pulling back)
       — immediate liquidity reduction signal

System action:
   Update Phase 3 revolver availability figure
   immediately — do not wait for next 10-Q
   Flag: "revolver availability updated from
   8-K Item 1.01 filed [date] — verify against
   next 10-Q filing"
```

**Why this matters operationally:** A company whose revolver is amended — commitment reduced, maturity extended under duress, or covenant waived — is sending a clear signal that lenders are actively managing their exposure. Each of these events changes available liquidity immediately and may precede further deterioration. A covenant waiver in particular is a confirmed stress signal because it means a covenant was breached — the breach is real, the lender chose to waive rather than accelerate, but the underlying financial deterioration that caused the breach is visible.

---

**Difference 3 — Item 8.01 keyword filter is broader for liquidity**

For leverage and coverage, the Item 8.01 keyword filter uses a narrow set of debt-related terms. For liquidity, the filter is broader because companies sometimes voluntarily disclose liquidity updates — particularly liquidity reassurances directed at investors — through Item 8.01 when no specific required item applies.

```
Liquidity-specific 8.01 keyword filter:

Tier 1 keywords (always process):
   "liquidity"
   "cash position"
   "available liquidity"
   "revolving credit"
   "covenant"
   "default"
   "waiver"
   "going concern"

Tier 2 keywords (process if issuer already flagged):
   "cash"
   "refinanc"
   "maturity"
   "borrow"
   "facility"
   "credit agreement"

Going concern flag — highest priority:
   If "going concern" appears in any 8-K filing:
   IMMEDIATE CRITICAL ALERT regardless of item number
   "Going concern" language in a filing means
   the auditor or management has doubts about
   the company's ability to continue as a going concern
   This is one of the strongest default predictors
   in structured filing data
   No further keyword processing needed — escalate
```

---

**Difference 4 — The 10-K provides liquidity data not available in 10-Q**

For most metrics, the 10-K and 10-Q are interchangeable as structured data sources — the 10-K provides the same balance sheet and income statement data as the 10-Q, just for the full year. For liquidity, the 10-K provides several items that are either absent or incomplete in quarterly 10-Q filings:

```
10-K exclusive liquidity data:

(1) Full revolving credit facility description
    with complete covenant schedule
    (10-Q often shows abbreviated version)

(2) Complete debt maturity schedule
    (all years, not just Year 1)
    Critical for S&P Year 2 liquidity assessment

(3) Full pension funded status
    (affects available cash if pension contributions
    are contractually required)

(4) Full operating lease maturity schedule
    (Year 1 through Year 5 plus thereafter)
    Used in Moody's and S&P sources/uses calculation

(5) Subsequent events footnote
    (discloses material events between fiscal year-end
    and filing date — may include liquidity events
    that occurred in Q1 of the new fiscal year)

System action for 10-K filing:
   Trigger full LLM liquidity extraction
   (revolver, covenants, maturity schedule,
   subsequent events) in addition to XBRL extraction
   Store complete liquidity picture as annual baseline
   Update quarterly with 10-Q XBRL data
   Flag items that are 10-K only and not updated
   in 10-Q until next annual filing
```

---

**Difference 5 — Going concern disclosure is an independent monitoring channel**

Going concern language can appear in multiple filing types and locations — not just 8-K filings. It is the single highest-priority liquidity signal in this system and must be monitored across all filing channels.

```
Going concern monitoring — all channels:

10-K — Auditor's Report:
   Independent auditor's report section
   Look for: "substantial doubt about the company's
   ability to continue as a going concern"
   This is the formal going concern qualification
   Triggers: IMMEDIATE CRITICAL ALERT
   Available: annually only

10-K / 10-Q — Management's Discussion:
   MD&A section — Liquidity and Capital Resources
   Look for: "raise substantial doubt",
   "ability to continue as a going concern",
   "substantial doubt exists"
   Management may flag going concern before
   auditor does — this is an earlier signal
   Triggers: IMMEDIATE CRITICAL ALERT

10-K / 10-Q — Footnote 1 (Going Concern):
   Post-ASU 2014-15, companies must disclose
   going concern assessment in footnotes
   Same language as auditor's report
   Triggers: IMMEDIATE CRITICAL ALERT

8-K — Any item:
   If going concern language appears in any
   8-K filing — press release, agreement
   disclosure, or other event
   Triggers: IMMEDIATE CRITICAL ALERT

Phase 2 implementation:
   Going concern detection is a simple keyword
   search requiring no LLM — implement as
   a text search across all filing types
   from day one of Phase 2
   Cost: negligible
   Value: catches the most urgent late-stage
   liquidity signal with no false positive risk
   (going concern language is never accidental)
```

---

### Full Update Schedule — Calendar Year Large Accelerated Filer

| Month | Event | Channel | Liquidity Update Type |
|---|---|---|---|
| ~Jan 30 – Feb 15 | Q4 / full year earnings press release | 8-K Item 2.02 | Cash balance + revolver availability if disclosed; Phase 3 only |
| ~Mar 31 | 10-K filed | 10-K | Full structured recompute all four ratios; full LLM extraction (revolver, covenants, maturity schedule, subsequent events); annual baseline established |
| ~Apr 14–25 | Q1 earnings press release | 8-K Item 2.02 | Cash balance + revolver if disclosed; Phase 3 only |
| ~May 10 | Q1 10-Q filed | 10-Q | Full structured recompute; partial LLM update (revolver drawn amount update) |
| ~Jul 15–25 | Q2 earnings press release | 8-K Item 2.02 | Cash balance + revolver if disclosed; Phase 3 only |
| ~Aug 9 | Q2 10-Q filed | 10-Q | Full structured recompute; partial LLM update |
| ~Oct 14–25 | Q3 earnings press release | 8-K Item 2.02 | Cash balance + revolver if disclosed; Phase 3 only |
| ~Nov 9 | Q3 10-Q filed | 10-Q | Full structured recompute; partial LLM update |
| Nov 9 – Mar 31 | **Q4 dark window** | Limited | No structured update; monitor 8-K Items 1.01, 2.03, 2.04, 8.01 (keyword filtered) daily for flagged issuers |
| Any business day | Credit facility amendment or renewal | 8-K Item 1.01 | Immediate revolver availability update; Phase 3 (Phase 2 for flagged issuers) |
| Any business day | Material debt creation | 8-K Item 2.03 | Temporary cash increase; future OCF reduction noted |
| Any business day | Debt acceleration / default | 8-K Item 2.04 | IMMEDIATE CRITICAL ALERT |
| Any business day | Going concern disclosure | Any filing type | IMMEDIATE CRITICAL ALERT — keyword search Phase 2 |
| Any business day | Voluntary liquidity update | 8-K Item 8.01 (keyword filtered) | Process if liquidity keywords present |

---

### Phase Summary

**Phase 2:** Monitor 10-Q and 10-K for all four ratio computations from XBRL. Available Liquidity Coverage computed as cash-only partial figure — flag revolver exclusion on every output. Implement going concern keyword search across all filing types from day one — highest value, lowest cost monitoring addition. Monitor 8-K Item 2.04 as automatic escalation. Monitor 8-K Item 1.01 with keyword filter for credit facility events for issuers already flagged at Watch or above.

**Phase 3:** Add full LLM revolver extraction from 10-K and 10-Q Debt Footnotes — completes Available Liquidity Coverage from partial to full. Add 8-K Item 2.02 LLM processing for cash and revolver disclosures. Expand Item 1.01 monitoring to all issuers regardless of current alert level. Add keyword-filtered Item 8.01 processing with broader liquidity keyword set. Implement Moody's twelve-month sources/uses and S&P liquidity descriptor computations using LLM-extracted inputs. Add component-level trend monitoring (cash depletion, revolver draw pattern, current liabilities growth) as standalone signals separate from ratio outputs.

