# Revenue Trend

---

## What it is

### Core Definition

Revenue Trend measures the direction, velocity, and consistency of change in a company's top-line revenue over time. It answers: *"is this company's core income stream growing, stable, or shrinking — and how fast?"*

### Relationship to EBITDA Margin Trend

Where EBITDA Margin Trend measures how efficiently a company converts revenue to earnings, Revenue Trend measures the raw scale of the business. Revenue is the input to everything else — EBITDA, FCF, debt serviceability.

### The Most Upstream Quantitative Signal

A company can defend margins temporarily through cost-cutting even as revenue declines, but sustained revenue compression eventually overwhelms any cost response and flows through to every downstream metric. This makes revenue trend the most upstream quantitative signal in the entire spec — it precedes margin compression, which precedes EBITDA decline, which precedes leverage deterioration.

### Metric Nature

Revenue trend is not a ratio in the traditional sense. It is a growth rate — the percentage change in revenue over a defined period — tracked as a time series. The signal is not whether revenue is high or low in absolute terms but whether it is moving in the right direction and at what speed.

---

## Why it signals stress

Revenue trend signals stress through four mechanisms.

---

### Mechanism 1 — The upstream cascade

Revenue decline initiates the stress sequence that eventually appears in every other metric in this spec.

The cascade is:
- revenue declines
- → margins compress (costs are stickier than revenue)
- → EBITDA falls
- → leverage rises and coverage falls
- → FCF turns negative
- → liquidity depletes
- → covenant headroom narrows
- → maturity wall becomes unfinanceable

Revenue trend is visible at the top of this cascade, typically **3–6 quarters before the downstream metrics reach stress thresholds**.

**Conclusion:** Revenue trend is the earliest upstream signal — it triggers before any other metric detects stress.

---

### Mechanism 2 — The fixed cost amplifier

For companies with high fixed cost structures, revenue decline produces disproportionately large EBITDA and FCF impacts.

Example: A company with 70% fixed costs experiencing a 10% revenue decline may see a **30%–40% EBITDA decline**.

Revenue trend, combined with a rough understanding of the company's operating leverage, allows the system to project how severe downstream deterioration will be before it appears in filed ratios.

**Conclusion:** Revenue trend quantifies operating leverage risk — small revenue drops can produce large EBITDA crashes.

---

### Mechanism 3 — The refinancing signal

Lenders and rating agencies use revenue trajectory as a primary input to credit quality assessment — not because revenue itself services debt but because it drives the earnings and cash flow that do.

A company whose revenue has been declining for multiple years faces structurally higher refinancing risk even if current leverage and coverage ratios are still acceptable, because lenders are projecting forward and discounting the value of a shrinking business.

**Conclusion:** Revenue trend affects refinancing capacity independently of current leverage — lenders discount future earnings.

---

### Mechanism 4 — The sector context signal

Revenue decline in a growing sector is more alarming than revenue decline in a contracting sector.

| Pattern | Interpretation |
|---------|----------------|
| Revenue decline + sector growing | Company-specific deterioration (market share loss) |
| Revenue decline in line with sector contraction | Cyclical rather than structural stress |
| Revenue decline + worse margin compression | Company-specific deterioration (vs volume-driven cyclical decline) |

Your system cannot fully separate these without external industry data, but the pattern of revenue decline relative to EBITDA margin movement provides a partial signal.

**Conclusion:** Sector context distinguishes company-specific distress from cyclical downturns — an essential calibration for accurate alerting.

---

**Summary — Why Revenue Trend Signals Stress**

| Mechanism | Lead Time | Key Insight |
|---|---|---|
| Upstream cascade | 3–6 quarters before downstream metrics | Earliest signal in the spec |
| Fixed cost amplifier | Immediate — projects forward | Small revenue drops → large EBITDA crashes |
| Refinancing signal | Structural (multi-year) | Lenders discount shrinking businesses |
| Sector context | Critical for calibration | Distinguishes company-specific vs cyclical |

---

## Formula

```
Revenue Growth Rate (quarter-over-quarter) =
    (Current Quarter Revenue − Prior Quarter Revenue)
    / Prior Quarter Revenue × 100

Revenue Growth Rate (year-over-year) =
    (Current Quarter Revenue − Same Quarter Prior Year)
    / Same Quarter Prior Year × 100

Preferred for trend analysis: year-over-year
(removes seasonal distortion for retail,
consumer, and agricultural issuers)

Trailing four-quarter revenue trend =
    Average of four consecutive YoY growth rates
    Classified as:
    Growing:    average > +3%
    Stable:     average −3% to +3%
    Declining:  average < −3%
    Accelerating decline: each quarter's YoY rate
                         more negative than prior
```

**Three derived outputs:**

```
Output 1 — Current period YoY revenue growth rate (%)
Output 2 — Trailing four-quarter average YoY growth (%)
Output 3 — Trend classification:
           Growing / Stable / Declining /
           Accelerating Decline / Recovering
```

**Extraction note:** See FREE_CASH_FLOW.md → Section "Formula" → Revenue input (us-gaap:Revenues) and EBITDA_MARGIN_TREND.md → Section "Formula" → Revenue input — reuse stored values; no re-extraction required.

**XBRL tags (for reference only — already extracted):**

| Input | Primary Tag | Already Extracted In |
|---|---|---|
| Revenue — current period | `us-gaap:Revenues` | FREE_CASH_FLOW.md, EBITDA_MARGIN_TREND.md |
| Revenue — prior period | Same tag, prior period context | Stored in 8-quarter time series |

**Period handling note:** Revenue is a duration item (covers the full reporting period). For 10-Q filings where revenue may be reported year-to-date rather than quarterly, the system must derive the standalone quarter figure by subtracting the prior period cumulative.

See FREE_CASH_FLOW.md → Section "Frequency" → Difference 3 (cumulative vs quarterly period subtraction logic) — apply identical period handling to revenue.

---

## Where it lives

Income Statement — top line. No new filing locations beyond what is already documented in prior metrics.

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Revenue | Income Statement | "Net revenues," "Total revenues," "Net sales," "Revenue" | 10-K and 10-Q |

**One incremental location — segment revenue (Phase 3 only):**

Total revenue masks segment-level deterioration. A company with stable consolidated revenue may have a core segment declining sharply while a non-core segment grows. Segment revenue lives in the Segment Footnote (typically Note 14–18, titled "Segment Information" or "Business Segments") and is required under ASC 280 for companies with multiple reportable segments.

| Field | Location | Available In | Method |
|---|---|---|---|
| Segment revenue by reportable segment | Segment Footnote — revenue by segment table | 10-K and 10-Q | Semi-structured — XBRL dimensional tagging inconsistent; LLM extraction preferred for Phase 3 |

For Phase 2, use total consolidated revenue only. For Phase 3, add segment-level tracking for issuers with multiple reportable segments where segment revenue divergence is material.

---

## Structured or Unstructured

Fully structured for consolidated revenue. Semi-structured for segment revenue (Phase 3 only).

| Input | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|
| Consolidated Revenue | `us-gaap:Revenues` or `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | Structured — reliably tagged | Already extracted for prior metrics; reuse stored value |
| Segment Revenue | `us-gaap:Revenues` with `us-gaap:StatementBusinessSegmentsAxis` dimension | Semi-structured — dimensional tagging inconsistent | Phase 3 only; LLM extraction from Segment Footnote more reliable than XBRL dimensional query |

---

## Extraction Fallback Logic

No incremental fallback logic required for consolidated revenue. All covered in prior metrics.

See FREE_CASH_FLOW.md → Section "Extraction Fallback Logic" → Revenue input — apply identical fallback sequence including the `RevenueFromContractWithCustomerExcludingAssessedTax` fallback tag.

**One incremental null handling rule for the time series:**

```
For YoY growth rate computation:
   Requires current period AND same quarter
   prior year revenue.

If prior year same-quarter revenue is null:
   YoY growth rate = null for that quarter
   Flag: "YoY growth rate null — prior year
   revenue not available for comparison period"
   Fall back to QoQ growth rate for that quarter
   Flag: "QoQ growth rate used as substitute —
   may reflect seasonal distortion for this issuer"

If fewer than 4 non-null YoY data points
in trailing 8 quarters:
   Trend classification = null
   Flag: "insufficient history for YoY trend
   classification — minimum 4 data points required"

For companies with recent IPO or major restructuring
where prior-year revenue is not comparable:
   Flag: "revenue comparability limited — [reason];
   trend classification may be misleading"
   Store values but do not trigger trend alerts
   until 4 comparable quarters are available
```

---

## Stress Threshold

Revenue trend thresholds operate across three dimensions. Unlike most prior metrics, the most important thresholds are trend-based and sector-context-adjusted rather than absolute level-based — a 5% revenue decline means very different things in a growing vs contracting industry.

---

**Dimension 1 — YoY Revenue Growth Rate (absolute)**

These thresholds are sector-independent starting points, adjusted by Dimension 3 context.

| YoY Revenue Growth | Interpretation | Alert Level |
|---|---|---|
| > +5% | Healthy growth | No alert |
| +2% to +5% | Modest growth — stable | No alert |
| 0% to +2% | Near-flat — monitor direction | Watch |
| −2% to 0% | Mild decline | Watch |
| −5% to −2% | Moderate decline | Flag |
| −10% to −5% | Material decline | Stress |
| < −10% | Severe decline | Critical |
| Accelerating: each quarter more negative | Escalate one level regardless of absolute rate | Trend escalation |

---

**Dimension 2 — Trend Duration and Consistency**

Duration matters more than any single quarter's rate. A company declining at −3% for six consecutive quarters is more stressed than one declining at −8% in a single quarter after years of growth.

| Trend Condition | Alert Level |
|---|---|
| Revenue growing or stable for 4+ consecutive quarters | No alert — healthy baseline |
| First quarter of YoY decline | Watch — monitor; may be one-off |
| YoY decline for 2 consecutive quarters | Watch — trend emerging |
| YoY decline for 3 consecutive quarters | Flag — sustained; operating stress likely |
| YoY decline for 4 consecutive quarters | Stress — structural deterioration likely |
| YoY decline for 6+ consecutive quarters | Critical — prolonged revenue erosion |
| Accelerating decline: decline rate worsening each quarter for 3 quarters | Stress regardless of absolute rate |
| Revenue recovering after decline: 2 consecutive quarters of improvement | Downgrade alert one level |

---

**Dimension 3 — Sector Context Adjustment**

This is the most important dimension for revenue trend because it separates company-specific stress from industry-wide cyclicality.

```
Sector context classification (Phase 3):
   Compare issuer revenue trend to sector
   revenue trend over same period.

   If issuer declining AND sector growing:
      Company-specific stress — escalate
      alert one level above Dimension 1/2 base
      Flag: "revenue declining in growing sector —
      market share loss signal; company-specific
      deterioration"

   If issuer declining AND sector declining
   at similar rate:
      Cyclical — do not escalate
      Flag: "revenue decline consistent with
      sector contraction — cyclical signal;
      monitor for outperformance or
      underperformance vs peers"

   If issuer declining faster than sector:
      Company losing share within declining sector
      Flag: "declining faster than sector — dual
      pressure: cyclical headwind plus company-
      specific deterioration"

   If issuer growing despite sector decline:
      Market share gain — positive signal;
      may offset other stress indicators

Phase 2 approximation:
   Sector context not available without
   external data.
   Apply Dimensions 1 and 2 thresholds without
   adjustment.
   Flag all revenue decline alerts with:
   "Sector context not assessed — Phase 2
   limitation; cyclical vs structural
   classification pending Phase 3"
```

---

**Dimension 4 — Revenue Trend × EBITDA Margin Interaction**

The combination of revenue decline and margin compression is the strongest early warning signal in the upstream metrics group.

```
If Revenue declining for 2+ quarters
AND EBITDA Margin compressing for 2+ quarters:
   Dual compression confirmed
   Escalate both Revenue Trend and EBITDA
   Margin Trend alerts one level each
   Flag: "dual compression — revenue and margin
   both deteriorating; EBITDA decline likely in
   next 1–2 quarters; leverage and coverage
   deterioration to follow"

Projected EBITDA impact:
   Projected_EBITDA =
       Projected_Revenue × Projected_Margin
   where:
   Projected_Revenue =
       Current Revenue × (1 + avg quarterly
       decline rate × 2 quarters forward)
   Projected_Margin =
       See EBITDA_MARGIN_TREND.md → Section "Formula" → Output 1 (Current EBITDA Margin) — use stored current margin value for dual compression projection
       − (avg quarterly margin compression
       × 2 quarters forward)

   Compare Projected_EBITDA to current EBITDA:
   Flag if projected decline > 15% in 2 quarters:
   "Projected EBITDA decline of [X]% in
   approximately 2 quarters at current
   revenue and margin trajectory — leverage
   and coverage deterioration likely"
```

---

**Dimension 5 — Revenue Decline vs Debt Maturity Interaction**

A company with declining revenue facing a near-term debt maturity has reduced refinancing capacity — lenders will project forward and discount the company's ability to service debt.

```
If Revenue declining for 3+ quarters
AND See DEBT_MATURITY_WALL.md → Section "Stress Threshold" → Dimension 2 (Days to Nearest Maturity) — check stored maturity schedule for maturities within 18 months:
   Escalate Revenue Trend alert to next level
   Flag: "declining revenue combined with
   near-term debt maturity — refinancing
   capacity likely impaired; lenders will
   project revenue decline forward"
```

---

## Signal Timing

**Earliest leading indicator in the spec — upstream of all other metrics.**

Revenue trend is the most upstream quantitative signal in the system. In the typical corporate distress sequence, revenue deterioration is visible before margin compression, before EBITDA decline, before leverage deterioration, and before FCF compression. The lead time over leverage and coverage is typically 4–8 quarters. The lead time over a credit event is typically 6–12 quarters for structural revenue decline cases.

This lead time advantage is why revenue trend is included despite being a simpler metric than the primary six. Its analytical value is not in its complexity but in its timing — it provides the earliest possible structured signal from SEC filing data.

**Lead time comparison:**

| Metric | Typical Lead Before Credit Event |
|---|---|
| Revenue Trend (3+ quarter decline) | 6–12 quarters |
| EBITDA Margin Trend (3+ quarter compression) | 5–8 quarters |
| Free Cash Flow (compression) | 4–6 quarters |
| Interest Coverage (deterioration) | 2–4 quarters |
| Leverage (ratio rising) | 2–4 quarters |
| Liquidity (ratio falling) | 1–2 quarters |
| Covenant Headroom (compression) | 2–4 quarters |

**One important caveat on lead time:** Revenue decline is also the metric most prone to false positives from cyclical or one-time factors. A company with a large non-recurring contract that expires, a voluntary product line divestiture, or a cyclical industry downturn will show revenue decline that does not predict credit stress. This is why the sector context adjustment (Dimension 3) and the duration threshold (minimum 3 consecutive quarters before Flag) are essential — they filter out single-quarter noise and cyclical movements.

**Filing lag:** 40 days after quarter-end for large accelerated filers. Revenue is a duration item on the income statement — same filing schedule as all income statement metrics. No intra-quarter structured updates available.

**Item 2.02 lead advantage (Phase 3):** Earnings press releases typically disclose revenue prominently — it is one of the most commonly pre-released metrics. This makes Item 2.02 particularly valuable for the Revenue Trend metric, providing a directional signal 14–25 days before the 10-Q. For companies already in the Watch or Flag band on revenue trend, Item 2.02 processing in Phase 3 provides meaningful early escalation capability.

**The Q4 dark window:** Same impact as EBITDA Margin Trend — Q4 revenue is invisible until the 10-K is filed. The Item 2.02 earnings release (typically January–February for calendar-year companies) partially mitigates this. For companies already showing 3+ quarters of revenue decline at Q3, activate heightened 8-K monitoring during the Q4 dark window.

---

## Frequency

Updates quarterly via 10-Q (3× per year) and annually via 10-K. Revenue is a duration item; no intra-quarter structured updates available.

**Rolling window maintenance:** See EBITDA_MARGIN_TREND.md → Section "Frequency" → rolling window maintenance — apply identical 8-quarter series management; store prior-year quarterly values alongside current for YoY computation. See SECTION_6.md → Section "6.3 Data Storage Schema" → Table 4 (time_series) — store Revenue YoY growth rate series as individual rows alongside EBITDA margin series.

**Period subtraction requirement:** For YoY comparisons using quarterly standalone revenue, the system must apply the period subtraction logic documented in FREE_CASH_FLOW.md → Section "Frequency" → Difference 3. A Q3 10-Q reporting nine-month YTD revenue requires subtracting the six-month YTD figure from the Q2 filing to derive the standalone Q3 quarter. Both current year and prior year require this treatment for a valid YoY comparison.

**Phase 2:** Monitor consolidated revenue quarterly. Compute QoQ and YoY growth rates. Track 8-quarter series. Apply Dimensions 1 and 2 thresholds. No sector context adjustment.

**Phase 3:** Add Dimension 3 sector context by computing sector median revenue growth from the portfolio at onboarding and supplementing with industry data where available. Add Item 2.02 press release monitoring for early directional signal. Add Dimension 4 dual compression computation combining revenue and EBITDA margin trend series. Add Dimension 5 revenue-maturity wall interaction using stored maturity schedule from See DEBT_MATURITY_WALL.md → Section "Formula" → Full Maturity Schedule (Formula 2)

