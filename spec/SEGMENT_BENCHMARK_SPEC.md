# Section 1: Company Size Classification

---

## What it is

Company size classification assigns each issuer to one of three size tiers — **Large**, **Mid**, or **Small** — based on total assets. The size tier is computed once at onboarding and stored as `size_category` in the `issuers` table. It is used as a segmentation dimension for all sector benchmark computations: rather than comparing a small energy E&P company against ExxonMobil, the system compares it against small-cap peers in the same sector.

Size classification is a **permanent issuer attribute**, not a period metric. It does not generate alerts. It is a grouping key used exclusively by the benchmark computation layer.

---

## Why it matters

A leverage ratio of 6x carries different credit implications for a $500M-asset mid-market retailer than for a $50B-asset investment-grade industrial. Fixed thresholds applied uniformly across all sizes systematically under-flag large companies (which can sustain higher leverage through capital market access) and over-flag small companies (which routinely operate at higher leverage due to limited equity market access). Size-adjusted benchmarks correct for this by computing peer medians within size tiers, not across the full population.

Academic foundation: Fama and French (1992) demonstrated that firm size is a persistent explanatory variable for financial outcomes, introducing the SMB (Small Minus Big) factor using NYSE median market capitalisation as the size breakpoint. For credit analysis where market data may be unavailable (private issuers, post-bankruptcy shells), total assets is the preferred size proxy because it measures the collateral base and operating scale without requiring equity market data.

Reference: Fama, E.F. and French, K.R. (1992). "The Cross-Section of Expected Stock Returns." *Journal of Finance*, 47(2), 427–465.

---

## Formula

```
Size Category = f(Total Assets at most recent period end)

Where:
  Total Assets ≥ $10,000,000,000  →  "Large"
  Total Assets ≥  $1,000,000,000  →  "Mid"
  Total Assets  <  $1,000,000,000  →  "Small"
  Total Assets unavailable         →  "Unknown"
```

**Breakpoint rationale:**

| Tier | Breakpoint | Rationale |
|---|---|---|
| Large | > $10B | Approximate S&P 500 / investment-grade large-cap threshold. Companies above this level have consistent capital market access, can issue public bonds, and have analyst coverage. |
| Mid | $1B–$10B | Broadly corresponds to high-yield / leveraged loan market participants. Most of the distressed case library falls here. |
| Small | < $1B | Below this level, companies are often bank-dependent, have limited refinancing options, and face more acute liquidity cliffs when stress occurs. |

Note: These breakpoints use total assets, not market capitalisation. This is intentional — total assets is available for all companies from XBRL without requiring equity market data, and measures the asset base that secures creditor claims. For credit analysis, total assets is the more analytically relevant size metric.

---

## Where it lives

Total assets is a balance sheet instant item, filed in every 10-K and 10-Q.

| Input | XBRL Tag | Filing location | Available in |
|---|---|---|---|
| Total Assets | `us-gaap:Assets` | Balance Sheet — top-level total | 10-K and 10-Q |

No LLM extraction required. Total assets is one of the most reliably tagged items in XBRL — it is present in virtually every SEC filer's submission.

---

## Structured or Unstructured

| Input | Classification | Reason |
|---|---|---|
| Total Assets | **Fully Structured** | `us-gaap:Assets` is a mandatory balance sheet line item, reliably tagged across all filing types and company sizes |

---

## Extraction Fallback Logic

```
Step 1 — Try: us-gaap:Assets
           Standard total assets tag. Present in 99%+ of filings.
           Use the most recent period end value available.

Step 2 — If Step 1 returns null:
           Try: us-gaap:AssetsCurrent + us-gaap:AssetsNoncurrent
           Sum of current and noncurrent assets equals total assets.
           Flag: "total assets derived from current + noncurrent components"

Step 3 — If both steps return null:
           Set size_category = "Unknown"
           Log: "total assets tag absent — size classification unavailable;
                 benchmark comparisons will use sector-only (no size dimension)"
           Do not block onboarding — proceed with sector-only benchmarks.
```

---

## Implementation

**Database change:**

Add `size_category` column to the `issuers` table:

```sql
ALTER TABLE issuers ADD COLUMN size_category TEXT DEFAULT 'Unknown';
-- Values: 'Large', 'Mid', 'Small', 'Unknown'
```

**Computation timing:**

Size category is computed at onboarding (first `cli.py` run for a CIK) and stored immediately. It is recomputed on any subsequent run where the stored value is `Unknown` or where total assets has changed by more than 20% from the stored baseline (indicating a major acquisition or divestiture that crosses a size tier boundary).

**Display:**

Size category appears as a tag in the company header of the CLI output and Streamlit app alongside the sector group:

```
Credit Warning System — RITE AID (RAD)
Sector: Retail / Wholesale  |  Size: Mid  |  Type: Corporate
```

---
### Boundary Smoothing — Size Transition Zones**

Hard breakpoints create discontinuities where a $1 difference in total assets changes the entire peer group. To avoid this, companies within ±25% of a breakpoint are classified as transitional and draw benchmarks from both adjacent size tiers using linear interpolation.

| Zone | Assets | Classification |
|---|---|---|
| Pure Small | < $750M | 100% Small benchmarks |
| Small-Mid transition | $750M – $1.25B | Linear blend: 0–100% Mid |
| Pure Mid | $1.25B – $8B | 100% Mid benchmarks |
| Mid-Large transition | $8B – $12.5B | Linear blend: 0–100% Large |
| Pure Large | > $12.5B | 100% Large benchmarks |

```
For companies in a transition zone:
  
  weight_upper = (assets - zone_lower) / (zone_upper - zone_lower)
  weight_lower = 1 - weight_upper
  
  blended_benchmark(metric) = 
      weight_upper × upper_tier_median(metric)
      + weight_lower × lower_tier_median(metric)

Flag: "size boundary transition — benchmarks blended 
       {weight_lower:.0%} {lower_tier} / 
       {weight_upper:.0%} {upper_tier}"
```

This is consistent with Moody's RiskCalc smooth-transition methodology and avoids artificial discontinuities at size tier boundaries

## Known Limitations

You are right. The current limitations section is too casual — it reads like a footnote rather than a proper analytical disclosure. A professional credit risk system documents limitations with the same rigor as the methodology itself.

Here is the professional format for limitations, modeled on how rating agencies and academic credit risk papers document model limitations:

---

## Known Limitations and Model Boundary Conditions

---

### Limitation 1 — Point-in-Time Size Classification

**Problem:**
Size category is assigned at onboarding using the most recent filing's total assets and remains static unless manually updated. A company that crossed from Mid to Large through organic growth or acquisition during the backtest period is classified as Large for all historical peer comparisons, including periods when it was genuinely a Mid-tier issuer. This introduces **look-ahead bias in the benchmark assignment** — historical metric values are compared against a peer group that did not exist at the time of measurement.

**Materiality:**
Moderate. Affects companies that crossed a size tier boundary during the analysis window (typically 8 quarters). Companies that remained within a single tier throughout the period are unaffected. In the current 75-company database, approximately 3–5 companies are estimated to have crossed a tier boundary during their observed history (e.g. Conduent grew then contracted; WeWork crossed from Large to Small post-bankruptcy).

**Interim mitigation:**
The transition zone blending (Section 1, Boundary Smoothing) reduces the severity of misclassification near tier boundaries. A company incorrectly classified as Large that is actually near the Mid-Large boundary will still draw partial Mid-tier benchmarks, limiting distortion.

**Phase 5 fix:**
Implement rolling size classification — recompute `size_category` at each quarterly period end using the total assets value from that period's filing, store as a time series in the `issuer_size_history` table, and join against the benchmark computation by period. This converts size from a static attribute to a point-in-time variable, fully eliminating look-ahead bias in benchmark assignment.

---

### Limitation 2 — Financial Institution Size Inflation

**Problem:**
Total assets for banks, insurers, and other financial institutions (SIC 6000–6499) includes policyholder reserves, deposit liabilities netted on the asset side, and investment portfolios that have no equivalent in non-financial companies. A mid-size regional bank with $30B in deposits appears as Large by total assets but is not economically comparable to a $30B industrial company. Applying the same size breakpoints across financial and non-financial companies produces **systematically inflated size classifications for financial institutions**.

**Materiality:**
High for financial institutions. In the current database, Aflac (SIC 6321, $130B total assets) classifies as Large, placing it in the same peer tier as Apple ($370B) and Exxon ($380B). This comparison is analytically meaningless.

**Interim mitigation:**
Financial institution benchmark comparisons are suppressed entirely per `SECTION_6.md` Section 6.5. Size classification for financial institutions is computed and stored but is flagged as `size_category_fi_adjusted = True` and excluded from all cross-sector peer comparisons. Size is retained for intra-financial-institution comparisons only (comparing Aflac against other insurers, not against industrial companies).

**Phase 5 fix:**
Implement sector-specific size metrics for financial institutions. For banks: use Tier 1 capital or risk-weighted assets rather than total assets as the size proxy. For insurers: use net premiums written or policyholder surplus. These metrics are available from XBRL for SEC-registered financial institutions and provide economically meaningful size comparisons within the financial sector.

---

### Limitation 3 — Minimum Sample Requirement Creates Coverage Gaps

**Problem:**
The benchmark computation requires a minimum of 3 companies per sector × size cell to produce a statistically meaningful median. Many cells in the current database fall below this threshold — particularly Small-tier companies in niche sectors (Small Healthcare/Pharma, Small Media/Entertainment, Small Business Services). When a cell falls below the minimum, the system falls back to sector-only benchmarks ignoring the size dimension. This **partially defeats the purpose of size-adjusted benchmarking** for underrepresented cells.

**Materiality:**
Moderate to high for small-cap distressed companies, which are the most analytically important use case. The current 75-company database produces robust benchmarks for Large and Mid tiers in Retail, Energy, and Industrials, but sparse or unavailable benchmarks for Small tiers in most sectors.

**Interim mitigation:**
Document cell population counts alongside each benchmark value. Flag benchmarks derived from 3–5 companies as "sparse — directional only" and benchmarks derived from 6–10 companies as "limited — use with caution." Only benchmarks with 10+ companies per cell are presented without qualification.

**Phase 5 fix:**
Expand the company database to 200+ issuers with deliberate coverage of Small-tier companies across all sectors. Additionally, implement **Bayesian shrinkage** — when a cell has fewer than 10 companies, shrink the cell median toward the sector-wide median by a factor proportional to the inverse of the sample size. This borrows statistical strength from the larger sector population without discarding sparse cell data entirely. Reference: James-Stein shrinkage estimator (Stein, 1956) adapted for median estimation.

---

### Limitation 4 — Static Breakpoints Do Not Adjust for Inflation or Secular Growth

**Problem:**
The $1B and $10B total assets breakpoints are fixed constants. Over time, as the general price level and corporate balance sheet sizes grow with inflation and economic expansion, the real economic meaning of these thresholds shifts. A company classified as Mid-tier today at $5B total assets occupies a different relative position in the corporate universe than a $5B company did in 1992 when Fama-French established their size factor. **Fixed nominal breakpoints introduce secular drift in classification accuracy** over multi-decade analysis windows.

**Materiality:**
Low for current use (8-quarter analysis windows). High for long-term studies or when comparing companies across different economic eras.

**Interim mitigation:**
Document the effective date of the breakpoints. Current breakpoints are calibrated to the 2020–2026 corporate bond universe. Apply them only to companies with filing dates within this window.

**Phase 5 fix:**
Index the breakpoints to a normalisation factor — either nominal GDP or the median total assets of all S&P 500 companies at the analysis date. Recompute breakpoints annually. This converts the classification system from fixed-nominal to **time-normalised**, maintaining consistent economic meaning across periods.

---

### Limitation 5 — Transition Zone Blending Assumes Linear Interpolation

**Problem:**
The boundary smoothing methodology (Section 1, Boundary Smoothing) uses linear interpolation between adjacent tier benchmarks within the transition zone. Linear interpolation assumes that the relationship between size and benchmark values is uniform across the transition zone — that a company at the midpoint of the transition zone should draw exactly 50% from each tier. In practice, the distribution of company characteristics is not linear across size boundaries: there are often clusters near tier midpoints and sparse populations near the boundaries, making a non-linear interpolation more accurate.

**Materiality:**
Low. Linear interpolation is a well-established approximation that produces negligible error for the granularity of analysis performed here. The error introduced by linear vs non-linear interpolation is smaller than the estimation error from limited sample sizes in most cells.

**Interim mitigation:**
None required given low materiality. Document the linear assumption explicitly so users can assess its impact in specific cases.

**Phase 5 fix:**
Replace linear interpolation with a **sigmoid (logistic) weighting function**:

```
weight_upper = 1 / (1 + exp(-k × (log(assets) - log(breakpoint))))
```

Where k is calibrated empirically to minimise classification discontinuities across the observed company database. This produces a smooth, mathematically principled transition that matches the actual distribution of company sizes more accurately than linear interpolation. The sigmoid approach is consistent with Moody's RiskCalc continuous-score methodology.

---

## Cross-references

- Benchmark table construction using `size_category` as a segmentation dimension: see `SEGMENT_BENCHMARK_SPEC.md` → Section 3 (Benchmark Table Construction)
- Financial institution suppression that excludes size-tier benchmarks for SIC 6000–6499: see `SECTION_6.md` → Section 6.5
- `issuers` table schema: see `SECTION_6.md` → Section 6.3 (Table 1: issuers)

Let me check what sectors `thresholds.py` currently covers before writing Section 2.Now I have the full picture. Here is my answer to your question first, then Section 2.

---


## Section 2 — Sector Classification

---

### What it is

Sector classification assigns each issuer to one of nine sector groups based on SIC code. The sector group drives three analytical functions: volatility category assignment for leverage and coverage thresholds (already implemented in `thresholds.py`), D/E threshold group selection (already implemented in `DEBT_TO_EQUITY.md`), and benchmark peer group assignment for the sector median comparison tables defined in Section 3 of this spec.

Sector classification operates at two levels of precision:

**Level 1 — Single sector classification:** A company is assigned to exactly one sector group based on its primary SIC code. This is the default and covers approximately 85% of the company universe.

**Level 2 — Multi-segment blended classification:** A company with two or more reportable segments under ASC 280, where no single segment exceeds 80% of total revenue, receives a revenue-weighted blend of two or more sector benchmarks. This requires Group 8 segment footnote extraction (LLM) and is deferred to Phase 5.

---

### The Nine Sector Groups

The existing eight groups in `thresholds.py` are extended to nine. Technology/Services is split into two distinct groups because their credit profiles are structurally incomparable:

| Sector Group | SIC Range | Key industries | Volatility | D/E Group |
|---|---|---|---|---|
| **Retail / Wholesale** | 5000–5999 | Grocery, pharmacy, department stores, specialty retail, wholesale distributors | Medial | Standard |
| **Energy / Mining** | 1040–1499, 1311–1389, 2910–2911 | E&P, oil majors, natural gas, coal, metals mining, gold | Medial | Standard |
| **Manufacturing / Industrials** | 2000–3999 (excl. energy SICs) | Aerospace, auto parts, chemicals, consumer products, food & beverage, packaging | Standard / Medial | Standard |
| **Media / Entertainment** | 4800–4899, 7810–7999 | Broadcasting, cable, publishing, film, gaming, music | Medial | Standard |
| **Healthcare / Pharma** | 2830–2836, 5047, 8000–8099 | Pharmaceuticals, biotech, medical devices, hospitals, health services | Standard | Asset-light |
| **Technology / Services** | 7370–7379, 3570–3579, 3670–3679 | Software, semiconductors, hardware, IT services, cloud infrastructure | Standard | Asset-light |
| **Business / Consumer Services** | 7000–7369, 7380–7809, 8100–8999 | Restaurants, hotels, logistics, professional services, education | Standard | Standard |
| **Financial Institutions** | 6000–6499 | Banks, insurance, broker-dealers, diversified financials | Not applicable | Not applicable |
| **Telecom / Utilities** | 4810–4813, 4900–4999 | Wireline, wireless, cable (telco), electric, gas, water utilities | Medial / Low | Capital-intensive |

**Note — Real Estate:** SIC 6500–6799 (REITs, real estate services) is treated as a sub-category of Financial Institutions for suppression purposes but uses its own D/E threshold table (Real estate / REITs) as defined in `DEBT_TO_EQUITY.md`. It does not participate in cross-sector benchmark comparisons.

---

### SIC Mapping — Detailed Rules

**Rule 1 — Primary SIC governs:**
Use the SIC code from the EDGAR submissions API (`sic` field). This is the company's self-reported primary business classification and is the only automated input.

**Rule 2 — Technology / Services split:**
SIC 7000–8999 in the current `thresholds.py` maps all services and technology together. This spec splits them:

```
SIC 7370–7379 (Computer programming, data processing) → Technology/Services
SIC 3570–3579 (Computer and office equipment)         → Technology/Services
SIC 3670–3679 (Electronic components)                 → Technology/Services
SIC 7000–7369 (Hotels, personal services, amusement)  → Business/Consumer Services
SIC 7380–7809 (Misc business services)                → Business/Consumer Services
SIC 8100–8999 (Legal, accounting, healthcare services) → Business/Consumer Services
   EXCEPT SIC 8000–8099 → Healthcare/Pharma
```

**Rule 3 — Energy carve-out from Manufacturing:**
Several energy SICs sit within the 2000–3999 Manufacturing block. These are carved out:

```
SIC 1311 (Crude petroleum & natural gas)    → Energy/Mining
SIC 1381–1389 (Oil & gas field services)    → Energy/Mining
SIC 2910–2911 (Petroleum refining)          → Energy/Mining
SIC 1040–1094 (Metal mining)                → Energy/Mining
SIC 1200–1299 (Coal mining)                 → Energy/Mining
All other 2000–3999                         → Manufacturing/Industrials
```

**Rule 4 — Holding company override:**
SIC 6719 (Offices of holding companies) cannot be automatically classified. Apply manual override at onboarding based on the company's primary operating subsidiary:

```
If SIC = 6719:
   Set sector_group = "Unknown — manual classification required"
   Flag: "holding company SIC — sector classification requires
          manual review of primary operating subsidiaries"
   Do not apply any benchmark comparisons until overridden
```

**Rule 5 — Conglomerate flag:**
If a company's 10-K discloses 3 or more reportable segments under ASC 280 with no single segment exceeding 50% of revenue, flag it as a conglomerate regardless of SIC:

```
conglomerate_flag = True
sector_group = [primary SIC sector]  (kept for threshold purposes)
benchmark_note = "conglomerate — single-sector benchmark is 
                  approximate; multi-segment blending required 
                  for accurate peer comparison (Phase 5)"
```

---

### Multi-Segment Blended Classification (Phase 5)

When a company has two or more reportable segments under ASC 280 with no single segment exceeding 80% of total revenue, a single sector assignment misrepresents its credit profile. A company that is 60% retail and 40% technology has fundamentally different benchmark peers than either a pure retailer or a pure technology company.

**Trigger condition:**
```
IF segment_count >= 2
AND max(segment_revenue_fraction) < 0.80
THEN apply multi-segment blending
```

**Blending formula:**
```
For each metric M:
blended_benchmark(M) = Σ (segment_i_revenue_fraction × 
                          sector_benchmark_i(M))

Where:
  segment_i_revenue_fraction = segment_i_revenue / total_revenue
  sector_benchmark_i = median value of metric M for sector i
                       in the same size tier

Example (60% Retail / 40% Technology company):
  blended_leverage_median = 0.60 × retail_median_leverage
                           + 0.40 × tech_median_leverage
```

**Display:**
```
Sector: Retail/Wholesale (60%) + Technology/Services (40%)
Benchmarks: blended — see component breakdown
```

**Data requirement:** Segment revenue by reportable segment from the ASC 280 Segment Footnote. Requires Group 8 LLM extraction (deferred to Phase 5). Until Group 8 is implemented, use Level 1 single-sector classification with the conglomerate flag.

Reference: Berger, P.G. and Ofek, E. (1995). "Diversification's Effect on Firm Value." *Journal of Financial Economics*, 37(1), 39–65.

---

### Structured or Unstructured

| Input | Classification | Phase |
|---|---|---|
| Primary SIC code | **Fully Structured** — from EDGAR submissions API | Phase 2 (already implemented) |
| Segment revenue by segment | **Fully Unstructured** — ASC 280 footnote, LLM required | Phase 5 (Group 8) |
| Holding company primary business | **Unstructured** — manual override | Phase 2 (manual) |

---

### Known Limitations and Model Boundary Conditions

---

**Limitation 1 — SIC Code Reflects Legal Registration, Not Economic Reality**

**Problem:**
SIC codes are assigned by the SEC based on the company's primary business at registration and are rarely updated. A company that pivoted from hardware manufacturing (SIC 3570) to cloud software services retains its hardware SIC code indefinitely unless it files an amendment. This produces **systematic sector misclassification for companies that have undergone business model transformation** — a growing problem in the technology and healthcare sectors where companies frequently pivot.

**Materiality:**
Moderate. Affects approximately 5–10% of the corporate universe, concentrated in technology and healthcare. In the current 75-company database, Motorola Solutions (SIC 3663, radio communications equipment) is classified as Manufacturing/Industrials but operates primarily as a software and services company — its credit profile is more comparable to Technology/Services peers.

**Interim mitigation:**
Manual override field (`issuers.notes`) allows an analyst to document and correct SIC misclassifications at onboarding. The override is noted in all benchmark outputs.

**Phase 5 fix:**
Implement automatic SIC validation against the company's reported segment descriptions from the ASC 280 footnote. If the primary segment description contains keywords inconsistent with the assigned SIC sector (e.g., a company with SIC 3570 whose primary segment is described as "cloud software subscriptions"), flag for manual review. Reference: NAICS (North American Industry Classification System) provides more granular and frequently updated industry codes — consider migrating to NAICS as an alternative to SIC for new onboardings.

---

**Limitation 2 — Single-Sector Classification Overstates Benchmark Precision for Diversified Companies**

**Problem:**
Approximately 20–30% of large-cap companies in the S&P 500 derive material revenue (10–40%) from a secondary sector that is structurally different from their primary sector. For these companies, the single-sector benchmark comparison produces a peer group that does not accurately represent their actual risk profile. A company classified as Manufacturing/Industrials that derives 35% of revenue from financial services (e.g., GE Capital, Caterpillar Financial Products) has leverage characteristics that are incomparable to pure manufacturing peers.

**Materiality:**
High for conglomerates and diversified industrials. In the current database, General Electric (pre-2018) and Caterpillar are the most significant cases. The conglomerate flag (Rule 5 above) identifies these companies but does not correct the benchmark comparison.

**Interim mitigation:**
Conglomerate flag displayed prominently in the UI. Benchmark comparisons for flagged companies labeled "approximate — single-sector." Analyst discretion advised.

**Phase 5 fix:**
Implement multi-segment blended classification as described in the Multi-Segment Blended Classification section above. This requires Group 8 LLM extraction of segment revenue data.

---

**Limitation 3 — Nine Sector Groups Are Insufficient for Within-Sector Variation**

**Problem:**
The Healthcare/Pharma sector group contains both pre-revenue biotechs (negative EBITDA, cash-burning, equity-funded) and mature pharmaceutical companies (25–35% EBITDA margins, investment-grade rated, dividend-paying). These two sub-types have completely different credit profiles and benchmark comparisons between them are misleading. The same problem exists within Energy/Mining (E&P companies vs integrated majors vs oilfield services) and within Technology/Services (semiconductor capex-intensive companies vs asset-light software companies).

**Materiality:**
High for Healthcare/Pharma and Energy/Mining. The current 75-company database includes both Lilis Energy (small E&P, bankrupt) and Chesapeake/Expand Energy (large E&P, post-emergence) in the same Energy sector group — their benchmark medians are heavily influenced by which sub-type dominates the cell.

**Interim mitigation:**
Size tier segmentation (Section 1) partially addresses this — a pre-revenue biotech is typically Small-tier while a mature pharma is Large-tier, so they fall into different benchmark cells. This is an imperfect but functional approximation.

**Phase 5 fix:**
Implement sub-sector classification within the nine groups using NAICS 6-digit codes or manually defined sub-sector tags. Minimum viable sub-sectors: Healthcare (Pharma/Biotech vs Healthcare Services vs Medical Devices), Energy (E&P vs Integrated vs Midstream vs Oilfield Services), Technology (Software vs Semiconductor vs Hardware). Each sub-sector maintains its own benchmark table when sample size permits (minimum 3 companies per cell).

---

***Sub-Sector Classification — Hybrid Manual/LLM Approach***
**Sub-sector classification uses a two-tier approach:**

*Tier 1 — Static assignment for known companies:*

> Companies already in the database are manually assigned a sub-sector tag based on analyst knowledge. This is hardcoded in the database at onboarding and requires no LLM quota. Applicable to the three sectors with material within-sector variation: Healthcare/Pharma, Energy/Mining, and Technology/Services.

*Tier 2 — LLM on-demand for new companies:*

> When a new company is onboarded via the Streamlit search interface and the analyst triggers LLM extraction, Group 8 (segment footnote extraction) automatically assigns the sub-sector tag based on segment descriptions and revenue weights from the ASC 280 footnote. The assignment is stored permanently and does not require re-extraction on subsequent visits.

- *Fallback*  If neither manual assignment nor LLM extraction has been run, sub_sector = null and the system uses sector-level benchmarks only (Level 1 classification). A flag is displayed: "sub-sector not classified — sector-level benchmarks applied; press LLM button for refined classification."

- This hybrid approach ensures the 75-company database has immediate sub-sector benchmark coverage without LLM cost, while ensuring all future companies receive accurate sub-sector classification automatically.

---

### Cross-References

- Volatility category assignment using sector group: `LEVERAGE.md` → Section "Stress Threshold" → Step 1
- D/E threshold group using sector group: `DEBT_TO_EQUITY.md` → Section "Stress Threshold" → Step 1
- Benchmark table construction using sector group as segmentation dimension: `SEGMENT_BENCHMARK_SPEC.md` → Section 3
- Financial institution suppression rules: `SECTION_6.md` → Section 6.5
- Group 8 segment footnote LLM extraction (required for multi-segment blending): deferred to Phase 5







**Here is the full sub-sector spec text to add to Section 2:**

---

## Sub-Sector Classification Definitions

Sub-sector classification is defined for three sector groups where within-sector variation is large enough to make single-sector benchmarks misleading. All other sector groups use single-sector Level 1 classification only.

---

### Healthcare / Pharma Sub-Sectors

| Sub-Sector Tag | Definition | Key Characteristics | Examples in Database |
|---|---|---|---|
| `branded_pharma` | Companies with primary revenue from patent-protected branded drugs. Revenue is concentrated in a small number of blockbuster drugs. High EBITDA margins (25–40%). Cash-generative but exposed to patent cliff risk. | High leverage tolerance (acquisition-driven), strong FCF, low capex, high R&D | Amgen, Eli Lilly, Pfizer, Johnson & Johnson |
| `generic_pharma` | Companies with primary revenue from off-patent generic drug manufacturing and distribution. High competition, thin margins (5–15% EBITDA), volume-driven business model. Highly sensitive to pricing pressure and FDA approval timing. | Lower leverage tolerance, thin margins, working capital intensive, regulatory risk | Mallinckrodt, Lannett, Akorn |
| `healthcare_services` | Companies providing healthcare delivery, pharmacy retail, or managed care services. Asset-intensive relative to pure pharma. Revenue is recurring but margin-thin (1–5% for pharmacy retail). | Retail-like working capital structure, low EBITDA margins, high volume | Rite Aid |
| `medical_devices` | Companies manufacturing medical equipment, implants, diagnostics, or instruments. Capital-intensive manufacturing, recurring consumables revenue, strong pricing power with hospitals. EBITDA margins 20–30%. | Moderate leverage tolerance, recurring consumables, acquisition-driven growth | Becton Dickinson |

**Classification rule:**
```
If primary revenue source = branded patent-protected drugs    → branded_pharma
If primary revenue source = generic/off-patent drugs          → generic_pharma
If primary revenue source = pharmacy retail / health services → healthcare_services
If primary revenue source = medical equipment / devices       → medical_devices
If ambiguous (diversified across sub-types):
   Apply dominant sub-sector if one segment > 60% of revenue
   Apply conglomerate flag if no segment > 60%
```

**Edge cases:**
- **AbbVie:** branded_pharma (Humira + Skyrizi dominant, > 60% immunology branded drugs)
- **Rite Aid:** healthcare_services (pharmacy retail — classified here despite SIC 5912 Retail Drug Stores; the credit profile matches healthcare services, not general retail)
- **Bausch Health:** generic_pharma (Bausch + Lomb devices + generic pharma mix → dominant generic_pharma given debt structure and margin profile)

---

### Energy / Mining Sub-Sectors

| Sub-Sector Tag | Definition | Key Characteristics | Examples in Database |
|---|---|---|---|
| `ep_independent` | Pure exploration and production companies. Revenue entirely from commodity prices (oil, natural gas, NGL). No downstream processing. Highly cyclical — EBITDA swings 50–80% with commodity prices. | High leverage in downturns, capex-intensive, no pricing power, commodity price pass-through | Chesapeake Energy, Whiting Petroleum, Denbury Resources, Lilis Energy, Sanchez Energy, Extraction Oil |
| `integrated_major` | Vertically integrated oil and gas companies with upstream (E&P), midstream (pipelines), and downstream (refining, chemicals) operations. Downstream partially hedges upstream commodity exposure. | Lower volatility than pure E&P, investment-grade rated, dividend-paying, very large asset base | Exxon Mobil, Occidental Petroleum |
| `midstream_services` | Pipeline, storage, processing, and transportation companies. Revenue is largely fee-based with long-term contracts. Commodity price exposure is minimal. Regulated or quasi-regulated cash flows. | Low volatility, high leverage tolerance (similar to utilities), stable FCF, MLP structures common | None currently in database |
| `metals_mining` | Companies extracting metals, minerals, or coal. Revenue driven by commodity prices but with different cycles than oil and gas. Higher capex intensity, longer project timelines, environmental liability exposure. | Cyclical like E&P but different commodity cycle, large asset base, environmental tail risk | None currently in database |

**Classification rule:**
```
If revenue > 80% from oil/gas production with no refining    → ep_independent
If revenue includes refining OR chemicals > 15%              → integrated_major
If revenue > 70% from transportation/processing fees         → midstream_services
If primary revenue from metals, minerals, or coal            → metals_mining
```

**Edge cases:**
- **Chesapeake Energy (pre-bankruptcy) vs Expand Energy (post-bankruptcy):** Both classified `ep_independent`. The post-bankruptcy entity is larger and better capitalized but the business model is identical — benchmark comparison should use the same sub-sector peer group.
- **Occidental Petroleum:** `integrated_major` — has E&P, OxyChem (chemicals), and midstream segments. No single segment > 80% but chemical segment provides meaningful revenue stabilization vs pure E&P peers.

---

### Technology / Services Sub-Sectors

| Sub-Sector Tag | Definition | Key Characteristics | Examples in Database |
|---|---|---|---|
| `software_saas` | Companies with primary revenue from software licenses, subscriptions, or IT services. Asset-light — minimal physical capital. High EBITDA margins (20–35%) at scale. Recurring revenue provides cash flow predictability. | Low capex, high margins, negative working capital (subscriptions paid upfront), acquisition-driven growth common | Accenture, ADP, Paychex, Motorola Solutions |
| `semiconductor` | Companies designing or manufacturing integrated circuits, processors, or electronic components. Capital-intensive manufacturing (fabs) or asset-light design (fabless). Highly cyclical — revenue swings 20–40% in down-cycles. | High capex (fab companies), cyclical revenue, long product development cycles, inventory risk | Texas Instruments |
| `hardware_devices` | Companies manufacturing physical technology products — computers, networking equipment, consumer electronics. Lower margins than software. Subject to supply chain risk and product obsolescence. | Moderate capex, inventory risk, shorter product cycles, commoditisation pressure | None dominant in database |
| `it_services` | Companies providing outsourced IT services, consulting, systems integration, or business process outsourcing. Revenue is contract-based and recurring. Lower margins than software (8–15% EBITDA) but stable. | Low capex, contract-based revenue, labour cost dominant, offshore delivery models | Conduent, Accenture (partially) |

**Classification rule:**
```
If primary revenue from software licenses or SaaS subscriptions → software_saas
If primary revenue from chip design or manufacturing            → semiconductor
If primary revenue from physical technology hardware            → hardware_devices
If primary revenue from outsourced IT or BPO services          → it_services
If ambiguous (e.g. Accenture = consulting + tech services):
   Use dominant revenue segment if > 60%
   Otherwise: software_saas if margins > 20%, it_services if margins < 15%
```

**Edge cases:**
- **Accenture:** `it_services` primarily but with significant technology consulting. EBITDA margins (~15%) confirm it_services classification despite technology positioning.
- **Conduent:** `it_services` — business process outsourcing, document management. Distressed case — high leverage on thin IT services margins.
- **Motorola Solutions:** `software_saas` — pivoted from hardware radios to software and services for public safety. Revenue now majority software/services despite SIC 3663 (radio equipment). Manual override of SIC classification.

---

### Sectors Using Single-Sector Classification Only

The following sectors do not have defined sub-sectors in this spec. All companies in these sectors are benchmarked at the sector level only:

| Sector | Reason no sub-sectors defined |
|---|---|
| Retail / Wholesale | Within-sector variation (grocery vs specialty vs department) is captured adequately by the size dimension. A small specialty retailer and a large grocer have different benchmarks through the size tier alone. |
| Manufacturing / Industrials | Too broad to define sub-sectors with current database size. Minimum 3 companies per sub-sector cell is not achievable for most industrial sub-categories at n=75. |
| Media / Entertainment | Current database has 4 media companies — insufficient sample for sub-sector cells. |
| Business / Consumer Services | High heterogeneity but small sample. Single-sector classification with size dimension is adequate approximation. |
| Financial Institutions | Benchmark comparisons suppressed entirely. Sub-sectors irrelevant for cross-sector comparison. |
| Telecom / Utilities | Telecom and Utilities are already implicitly separated by SIC within this group (4810–4813 vs 4900–4999). The size dimension handles the remaining variation adequately. |

**Phase 5 note:** As the database expands beyond 200 companies, sub-sector definitions should be added for Manufacturing/Industrials (aerospace vs auto vs chemicals vs consumer products) and Retail (grocery vs pharmacy vs specialty vs department). The minimum viable sample for a sub-sector benchmark cell is 5 companies; 10+ is preferred.

---

## Section 3 — Benchmark Table Construction

---

### What it is

The benchmark table is a pre-computed statistical summary of metric distributions across all companies in each sector × size × sub-sector cell. It answers the question: "for a company of this type and size, what is the normal range of values for each of the 19 metrics?" The benchmark table is the analytical foundation for all peer-relative comparisons in the Streamlit app and dashboard.

The benchmark table does not generate alerts. It is a reference layer — a statistical description of peer behavior that provides context for interpreting a specific company's metrics. A leverage ratio of 5x is unambiguously Critical by absolute threshold. But whether 5x is typical or unusual for a Large-cap Energy/E&P company requires the benchmark table to answer.

---

### What it is not

The benchmark table is not a replacement for the existing volatility-adjusted alert thresholds defined in `LEVERAGE.md`, `INTEREST_COVERAGE.md`, and `thresholds.py`. Those thresholds remain the primary alert generation mechanism. The benchmark table is supplementary context — displayed alongside metric values to show relative position within the peer group, not to override the alert level.

---

### Cell Definition

Each benchmark is computed for a specific combination of three segmentation dimensions:

```
Cell key = (sector_group, size_category, sub_sector)

Where:
  sector_group   — one of the 9 sector groups from Section 2
  size_category  — Large / Mid / Small (Section 1)
  sub_sector     — sub-sector tag if defined (Section 2), or NULL for 
                   sectors without sub-sector definitions

Examples:
  ("Healthcare/Pharma", "Large", "branded_pharma")
  ("Energy/Mining",     "Small", "ep_independent")
  ("Retail/Wholesale",  "Mid",   NULL)
  ("Manufacturing",     "Large", NULL)
```

---

### Metric Selection for Benchmarking

Not all 19 metrics are appropriate for peer comparison. Three metrics are excluded from benchmark computation:

| Metric | Reason excluded |
|---|---|
| `covenant_headroom_leverage` | Depends on individual covenant threshold — not comparable across companies without knowing each company's specific covenant level |
| `covenant_headroom_coverage` | Same reason |
| `loss_provisions_balance` | Dollar amount — not comparable across companies of different sizes without normalisation; the alert tier (1–5) is the meaningful signal, not the absolute dollar amount |

The remaining **16 metrics** are included in the benchmark table:

`leverage`, `interest_coverage`, `free_cash_flow`, `fcf_margin`, `moody_adjusted_fcf`, `rcf_net_debt`, `ocf_ebitda_conversion`, `current_ratio`, `quick_ratio`, `debt_to_equity`, `ebitda_margin`, `revenue_yoy_growth`, `asset_coverage`, `tangible_asset_coverage`, `liquidation_asset_coverage`, `maturity_coverage_near_term`

Note: `free_cash_flow` and `moody_adjusted_fcf` are dollar amounts. For these two metrics the benchmark is computed as a percentage of revenue (i.e. FCF margin equivalent) rather than the raw dollar value, to enable cross-company comparison regardless of company size. Store both the raw dollar benchmark and the revenue-normalised benchmark.

---

### Computation Methodology

**Step 1 — Data selection:**

For each company in the database, select the single most recent non-null value for each metric across all stored periods:

```sql
SELECT m.cik, m.metric_name, m.value, m.period_end_date
FROM metric_values m
INNER JOIN (
    SELECT cik, metric_name, MAX(period_end_date) as latest
    FROM metric_values
    WHERE value IS NOT NULL
    AND alert_level IS NOT NULL          -- exclude suppressed metrics
    AND metric_name NOT IN (
        'covenant_headroom_leverage',
        'covenant_headroom_coverage',
        'loss_provisions_balance'
    )
    GROUP BY cik, metric_name
) latest ON m.cik = latest.cik
    AND m.metric_name = latest.metric_name
    AND m.period_end_date = latest.latest
WHERE m.value IS NOT NULL
```

**Step 2 — Group by cell:**

Join against the `issuers` table to get `sector_group`, `size_category`, and `sub_sector` for each CIK. Group the metric values by cell key.

**Step 3 — Apply minimum sample rule:**

```
For each (sector_group, size_category, sub_sector, metric_name) cell:

IF company_count >= 3:
    Compute p25, p50 (median), p75 using the values in the cell
    Store with the full cell key
    
IF company_count == 2:
    Fall back to (sector_group, size_category, NULL) — ignore sub_sector
    Recheck company_count at this broader cell
    
IF company_count == 1 at sector+size level:
    Fall back to (sector_group, NULL, NULL) — ignore size dimension
    Recheck company_count at sector-only level
    
IF company_count < 3 at sector-only level:
    No benchmark available for this metric in this sector
    Store as NULL with note: "insufficient sample — 
    sector has fewer than 3 companies with data for this metric"
```

The fallback cascade ensures the system always uses the most specific available benchmark without producing statistically meaningless single-company "benchmarks."

**Step 4 — Compute percentiles:**

```python
from statistics import quantiles

def compute_percentiles(values: list[float]) -> tuple[float, float, float]:
    """Returns (p25, p50, p75). Requires len(values) >= 3."""
    if len(values) < 3:
        return None, None, None
    qs = quantiles(values, n=4)   # returns [p25, p50, p75]
    return qs[0], qs[1], qs[2]
```

Use Python's `statistics.quantiles` with `n=4` for quartile computation. Do not use numpy — the system uses stdlib only for the benchmark computation layer.

**Step 5 — Exclude outliers before computing percentiles:**

Companies in active bankruptcy or post-emergence restructuring produce metric values (leverage of 50x, negative equity) that distort the peer distribution. Exclude values beyond 3 standard deviations from the cell mean before computing percentiles:

```python
def exclude_outliers(values: list[float]) -> list[float]:
    """Winsorise at 3 standard deviations. Applied before percentile computation."""
    if len(values) < 4:
        return values   # too few to reliably detect outliers
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    return [v for v in values if abs(v - mean) <= 3 * std]
```

Flag when outliers were excluded: "N outlier values excluded from benchmark — distressed/post-bankruptcy values removed from peer distribution."

---

### Database Schema

Add a new table `sector_benchmarks` to `credit_warning.db`:

```sql
CREATE TABLE sector_benchmarks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_group    TEXT NOT NULL,
    size_category   TEXT NOT NULL,       -- Large / Mid / Small / ALL
    sub_sector      TEXT,                -- NULL for sectors without sub-sectors
    metric_name     TEXT NOT NULL,
    p25             REAL,
    p50             REAL,
    p75             REAL,
    company_count   INTEGER NOT NULL,
    fallback_level  TEXT NOT NULL,       -- full / no_subsector / sector_only
    outliers_excluded INTEGER DEFAULT 0, -- count of outlier values removed
    computed_at     TEXT NOT NULL,       -- ISO datetime of last computation
    UNIQUE (sector_group, size_category, sub_sector, metric_name)
);
```

`fallback_level` records which level of the cascade was used:
- `full` — computed at the full (sector × size × sub_sector) cell
- `no_subsector` — sub_sector dimension dropped, computed at (sector × size)
- `sector_only` — size dimension also dropped, computed at sector level only

This allows the display layer to communicate benchmark precision to the analyst: "benchmark from 12 companies in same sector/size/sub-sector" vs "benchmark from 8 companies in same sector/size (sub-sector insufficient)" vs "benchmark from 23 companies in same sector only."


Add distressed_count INTEGER DEFAULT 0 to the sector_benchmarks table, computed during recompute_all_benchmarks() by joining against a benchmark_exclude or classification flag on the issuers table.

---

### Update Trigger

The benchmark table is recomputed in full whenever:

1. A new company is added to the database (any `cli.py` run for a new CIK)
2. The `sub_sector` column is updated for any issuer
3. The `size_category` column is updated for any issuer
4. The analyst explicitly calls `python benchmarks.py --recompute`

Partial recomputation (updating only the affected cell) is not implemented in Phase 4. Full recomputation across all cells takes less than 1 second for a 75-company database and less than 10 seconds at 500 companies. Partial recomputation is a Phase 5 optimisation for databases exceeding 1,000 companies.

---

### Implementation File

The benchmark computation is implemented in a new file `benchmarks.py` — not in `extractor.py`, `metrics.py`, or `thresholds.py`. This keeps the benchmark layer cleanly separated from the extraction and alert layers.

`benchmarks.py` exposes two public functions:

```python
def recompute_all_benchmarks(db_path: str = "credit_warning.db") -> dict:
    """Recompute all sector_benchmarks rows from current metric_values data.
    Returns a summary dict: {cell_key: company_count} for all computed cells."""

def get_benchmark(db_path: str, cik: str, metric_name: str) -> dict | None:
    """Return the benchmark row for a specific company and metric.
    Automatically applies the fallback cascade to find the most specific
    available benchmark. Returns None if no benchmark available.
    
    Return format:
    {
        "p25": float,
        "p50": float,
        "p75": float,
        "company_count": int,
        "fallback_level": str,
        "cell_description": str   # e.g. "Large Healthcare/Pharma — branded_pharma (8 companies)"
    }
    """
```

`recompute_all_benchmarks()` is called automatically at the end of every `cli.py` run for a new CIK. `get_benchmark()` is called by the Streamlit monitor page and the dashboard generator when displaying the "vs peer median" indicator.

---

### Metric Polarity

The benchmark comparison must know which direction is better for each metric. This is defined once here and referenced by all display components.

| Metric | Polarity | Why |
|---|---|---|
| `leverage` | Lower is better | Higher leverage = more debt relative to earnings |
| `interest_coverage` | Higher is better | Higher coverage = more earnings buffer above interest costs |
| `free_cash_flow` | Higher is better | More FCF = more cash generated |
| `fcf_margin` | Higher is better | More FCF per dollar of revenue |
| `moody_adjusted_fcf` | Higher is better | More adjusted FCF after debt service obligations |
| `rcf_net_debt` | Higher is better | More retained cash flow relative to debt |
| `ocf_ebitda_conversion` | Higher is better | Better conversion of accounting earnings to cash |
| `current_ratio` | Higher is better | More current assets relative to current liabilities |
| `quick_ratio` | Higher is better | More liquid assets relative to current liabilities |
| `debt_to_equity` | Lower is better | Less debt relative to equity cushion |
| `ebitda_margin` | Higher is better | More operating earnings per dollar of revenue |
| `revenue_yoy_growth` | Higher is better | Growing revenue reduces refinancing risk |
| `asset_coverage` | Higher is better | More assets backing each dollar of debt |
| `tangible_asset_coverage` | Higher is better | More tangible assets backing each dollar of debt |
| `liquidation_asset_coverage` | Higher is better | More recoverable asset value in distress scenario |
| `maturity_coverage_near_term` | Higher is better | More liquidity coverage of near-term debt maturities |

**Polarity-adjusted quartile classification:**

```
For higher-is-better metrics:
  value > p75  →  Top quartile    (green — above peer median + buffer)
  p50–p75      →  Upper middle    (neutral)
  p25–p50      →  Lower middle    (neutral)
  value < p25  →  Bottom quartile (red — below most peers)

For lower-is-better metrics (leverage, debt_to_equity):
  value < p25  →  Top quartile    (green — lower leverage than most peers)
  p25–p50      →  Upper middle    (neutral)
  p50–p75      →  Lower middle    (neutral)
  value > p75  →  Bottom quartile (red — higher leverage than most peers)
```

---

### Known Limitations and Model Boundary Conditions

---

**Limitation 1 — Sparse Cells Dominate the Current Database**

**Problem:**
At n=75 companies across 9 sectors × 3 size tiers × up to 4 sub-sectors, most cells have fewer than 3 companies and trigger the fallback cascade. The effective benchmark for most companies is sector-only (no size dimension), which partially defeats the purpose of size-adjusted benchmarking described in Section 1.

**Materiality:**
High for the current database. A representative cell count by sector and size:

| Sector | Large | Mid | Small |
|---|---|---|---|
| Retail/Wholesale | 3 | 5 | 0 |
| Energy/Mining | 2 | 5 | 1 |
| Manufacturing/Industrials | 5 | 4 | 1 |
| Healthcare/Pharma | 3 | 2 | 2 |
| Technology/Services | 2 | 3 | 0 |

Most cells fall below the 3-company minimum when the sub_sector dimension is added. The fallback to sector-only is the common path, not the exception.

**Interim mitigation:**
`fallback_level` field in the `sector_benchmarks` table and in the display output communicates benchmark precision to the analyst. Sparse benchmarks are labeled "directional only — fewer than 5 companies in peer group."

**Phase 5 fix:**
Expand the company database to 200+ issuers with deliberate coverage of all sector × size cells. Target minimum 5 companies per cell before sub_sector is added; 10+ companies per sub_sector cell. This is a data expansion task, not an analytical methodology change.

---

**Limitation 2 — Latest-Period Selection Introduces Point-in-Time Bias**

**Problem:**
The benchmark uses the most recent available value for each company. If the database contains a distressed company whose latest period reflects severe stress (leverage 15x, negative coverage), that value is included in the peer distribution even though the company is no longer operating normally. This pulls the peer distribution toward distress and makes the benchmarks appear more stressed than they would be for a healthy-company-only peer group.

**Materiality:**
Moderate. The 30 distressed companies in the current database contribute stressed values to the sector benchmarks. A retailer searching for Retail sector benchmarks will see a distribution that includes Rite Aid, Bed Bath & Beyond, Sears, and Party City — all of which had severely stressed metrics before bankruptcy. This may make a mildly leveraged healthy retailer appear above the sector median when the comparison is actually against a distress-skewed distribution.

**Interim mitigation:**
The outlier exclusion step (±3 standard deviations) removes the most extreme distressed values. Additionally, the `fallback_level` display notes how many companies contributed to the benchmark — if the analyst sees "8 companies in peer group" and knows the database contains 8 retailers, they can infer the benchmark includes distressed names.

**Phase 5 fix:**
Implement a `benchmark_exclude` flag in the `issuers` table. Companies with `benchmark_exclude = True` are omitted from benchmark computation but retained for all other system functions. Set `benchmark_exclude = True` for all distressed companies in the case library — their metrics reflect pre-bankruptcy deterioration, not healthy peer behavior. Compute two benchmark sets: all-companies (current behavior) and healthy-only (excluding distressed cases). Display both with clear labeling.

---

**Limitation 3 — Single Latest Period Does Not Capture Cyclical Context**

**Problem:**
The benchmark uses a single latest-period value per company. For highly cyclical sectors (Energy, Media, Manufacturing), a single period's metrics reflect the cyclical position at that moment — not the through-the-cycle average that credit analysts typically use. An energy company benchmark computed in Q2 2020 (oil price collapse) produces completely different medians than the same benchmark computed in Q3 2022 (oil price peak). The benchmark is therefore sensitive to when it was last computed.

**Materiality:**
High for Energy/Mining. Moderate for Manufacturing and Media. Low for Technology and Healthcare.

**Interim mitigation:**
Document the `computed_at` timestamp on all benchmarks. Flag energy and cyclical sector benchmarks with "cyclical sector — benchmark reflects conditions at [date]; interpret with awareness of commodity cycle position."

**Phase 5 fix:**
Implement through-the-cycle benchmarks for cyclical sectors: compute the median of each company's 8-quarter average value (rather than the latest single value) before computing the peer distribution. This produces a benchmark that represents mid-cycle behavior rather than a point-in-time snapshot. Requires all 75 companies to have a full 8-quarter history in the database, which the current system already stores.

---

### Cross-References

- Size category used as benchmark cell dimension: `SEGMENT_BENCHMARK_SPEC.md` → Section 1
- Sector group and sub-sector used as benchmark cell dimensions: `SEGMENT_BENCHMARK_SPEC.md` → Section 2
- `metric_values` table schema (source data for benchmark computation): `SECTION_6.md` → Section 6.3 → Table 3
- `issuers` table schema (sector_group, size_category, sub_sector fields): `SECTION_6.md` → Section 6.3 → Table 1
- Financial institution suppression (excluded from all benchmark cells): `SECTION_6.md` → Section 6.5
- Metric polarity used by display layer: referenced by `generate_dashboard.py` and `pages/02_monitor.py` (Streamlit)


---

**Addition A — `get_benchmark()` fallback implementation (add after the function signature):**

> The fallback cascade can be implemented in a single SQL query using `ORDER BY` on the `fallback_level` column. The following is one correct implementation — application-level cascade logic with separate queries is equally valid:
>
> ```sql
> SELECT p25, p50, p75, company_count, fallback_level,
>        sector_group, size_category, sub_sector
> FROM sector_benchmarks
> WHERE metric_name = :metric_name
>   AND sector_group = :sector_group
>   AND (
>       (size_category = :size_category AND sub_sector = :sub_sector)
>    OR (size_category = :size_category AND sub_sector IS NULL)
>    OR (size_category = 'ALL'          AND sub_sector IS NULL)
>   )
> ORDER BY
>   CASE fallback_level
>     WHEN 'full'          THEN 1
>     WHEN 'no_subsector'  THEN 2
>     WHEN 'sector_only'   THEN 3
>   END
> LIMIT 1
> ```
>
> Note: `size_category = 'ALL'` is the stored value for sector-only rows (no size dimension). This must match the value written by `recompute_all_benchmarks()` when the size dimension is dropped during the fallback cascade.

---

**Addition B — `benchmark_exclude` column (add to database schema section):**

> Add to `issuers` table: `benchmark_exclude INTEGER DEFAULT 0`. When set to 1, the company is excluded from all `recompute_all_benchmarks()` computations but retained for all other system functions (extraction, alerts, display, backtest). Default 0 for all companies. Set to 1 manually for known distressed cases in the current database — this is a Phase 5 task; do not set at Phase 4 implementation time.

---

**Addition C — Testing strategy (add as a new subsection at the end of Section 3):**

> **Verification requirements for `benchmarks.py`:**
>
> Before committing, verify three behaviors with a hand-curated test case:
>
> 1. **Percentile correctness:** Insert 5 companies into a single cell with known metric values `[1.0, 2.0, 3.0, 4.0, 5.0]`. Assert `p25 = 1.75`, `p50 = 3.0`, `p75 = 4.25` (Python `statistics.quantiles` with `n=4`). Verify these match the stored `sector_benchmarks` row after `recompute_all_benchmarks()`.
>
> 2. **Fallback cascade:** Insert 2 companies in a full cell (below minimum). Assert `get_benchmark()` returns a row with `fallback_level = 'no_subsector'` or `'sector_only'`, not `'full'`. Assert `get_benchmark()` returns `None` when no level has 3+ companies.
>
> 3. **Outlier exclusion:** Insert a cell with values `[1.0, 2.0, 3.0, 4.0, 100.0]`. Assert the 100.0 outlier is excluded and `outliers_excluded = 1` in the stored row.
>
> These three checks cover the core logic paths. Add to `test_manual.py` as a new test group — do not create a separate test file.


## Section 4 — Metric Evaluation Framework

---

### What it is

The metric evaluation framework defines how a company's metric value is interpreted relative to its peer benchmark. It has two components: **polarity** (which direction is better for each metric) and **quartile classification** (where the company's value falls within the peer distribution).

Together these answer a single question for each metric: is this company performing better or worse than its peers, and by how much?

The evaluation framework is applied after `get_benchmark()` returns a peer distribution for the company's cell. It is purely a display and interpretation layer — it does not modify alert levels, does not feed back into the extraction pipeline, and does not override the existing volatility-adjusted thresholds from `thresholds.py`.

---

### Polarity Definition

Polarity is a permanent property of each metric — it does not change by sector, size, or company. A metric either measures something where more is better (coverage, liquidity, profitability) or something where less is better (leverage, debt burden).

**One exception — polarity inversion for distressed companies:**

For companies already at Critical alert level, `revenue_yoy_growth` polarity inverts in a narrow case: a company with sharply negative revenue that is now declining less quickly (i.e. the rate of decline is slowing) is directionally improving even though growth is still negative. The standard "higher is better" polarity handles this correctly — a less negative growth rate is a higher value, so no inversion is needed. No exception is required; the standard polarity holds.

---

### Full Polarity Table — All 19 Metrics

| # | Metric | `metric_name` | Polarity | Analytical Rationale |
|---|---|---|---|---|
| 1 | Leverage | `leverage` | **Lower is better** | Higher leverage = more debt relative to earnings = greater default risk. A company at 8x leverage is more stressed than one at 3x. |
| 2 | Interest Coverage | `interest_coverage` | **Higher is better** | Higher coverage = more EBITDA buffer above interest obligations. Coverage below 1.0x means EBITDA does not cover interest — acute stress. |
| 3 | Free Cash Flow | `free_cash_flow` | **Higher is better** | More FCF = more cash generated after operating expenditure and capex. Negative FCF means the company is burning cash. Dollar amount — normalise to FCF margin for cross-company comparison. |
| 4 | FCF Margin | `fcf_margin` | **Higher is better** | FCF as a percentage of revenue. Higher margin = more cash generated per dollar of revenue. Negative FCF margin = cash-burning operations. |
| 5 | Moody's Adjusted FCF | `moody_adjusted_fcf` | **Higher is better** | FCF after pension contributions, dividends, and maintenance capex — the cash available to service debt. Negative = insufficient cash generation for debt obligations after baseline commitments. Dollar amount — normalise to revenue for cross-company comparison. |
| 6 | RCF / Net Debt | `rcf_net_debt` | **Higher is better** | Retained cash flow as a fraction of net debt. Higher ratio = faster de-leveraging capacity. Negative = company is accumulating debt, not repaying it. |
| 7 | OCF / EBITDA Conversion | `ocf_ebitda_conversion` | **Higher is better** | Fraction of EBITDA that converts to operating cash flow. Higher conversion = earnings quality is high. Very high (>1.5x) may indicate working capital release — review context. Very low (<0.5x) indicates poor earnings quality or large non-cash charges. |
| 8 | Current Ratio | `current_ratio` | **Higher is better** | More current assets relative to current liabilities = stronger near-term liquidity. Below 1.0x means current liabilities exceed current assets — liquidity stress. |
| 9 | Quick Ratio | `quick_ratio` | **Higher is better** | Liquid assets (excl. inventory and prepaid) relative to current liabilities. More conservative and analytically preferred over current ratio for credit purposes. |
| 10 | Debt / Equity | `debt_to_equity` | **Lower is better** | More debt relative to equity cushion = less protection for creditors. Higher D/E means equity absorbs less of a loss before debt is impaired. Exception: negative equity from buybacks makes the ratio meaningless — see special handling below. |
| 11 | EBITDA Margin | `ebitda_margin` | **Higher is better** | Profitability of core operations. Negative EBITDA margin = operating losses. Highly sector-dependent — compare only within sector using sector-calibrated benchmarks. |
| 12 | Revenue YoY Growth | `revenue_yoy_growth` | **Higher is better** | Growing revenue provides more operating leverage and reduces refinancing risk. Sustained revenue decline is a leading indicator of credit deterioration. Sector context required — a 5% decline in E&P during a commodity downturn is different from a 5% decline in a pharmacy retail company. |
| 13 | Asset Coverage | `asset_coverage` | **Higher is better** | Total assets backing each dollar of total debt. More asset coverage = more collateral buffer for creditors. Below 1.0x means total assets are insufficient to cover all debt — acute stress. |
| 14 | Tangible Asset Coverage | `tangible_asset_coverage` | **Higher is better** | Tangible assets (excluding goodwill, intangibles, DTA) backing each dollar of debt. More conservative than total asset coverage. Negative tangible equity is common for acquisition-heavy companies — flag but do not suppress. |
| 15 | Liquidation Asset Coverage | `liquidation_asset_coverage` | **Higher is better** | Haircut-adjusted asset value backing each dollar of debt. Represents recovery value in a distress scenario. The most conservative asset coverage metric. Below 0.5x suggests creditors face meaningful principal loss in liquidation. |
| 16 | Maturity Coverage (near-term) | `maturity_coverage_near_term` | **Higher is better** | Liquidity sources (cash + revolver) relative to debt maturing in Year 1. Coverage > 1.0x means the company can meet near-term maturities from existing liquidity. Coverage < 0.5x is acute liquidity stress — cannot refinance without market access. |
| 17 | Covenant Headroom (leverage) | `covenant_headroom_leverage` | **Higher is better** | Distance from covenant breach — more headroom = more buffer before a covenant violation. Negative = covenant is already breached. **Excluded from benchmark comparison** — covenant thresholds vary by company and credit agreement; peer comparison is not meaningful. |
| 18 | Covenant Headroom (coverage) | `covenant_headroom_coverage` | **Higher is better** | Same as covenant headroom leverage. **Excluded from benchmark comparison** for the same reason. |
| 19 | Loss Provisions Balance | `loss_provisions_balance` | **Lower is better** | Larger loss provision = more probable legal/regulatory liability. However the dollar amount is not comparable across companies of different sizes. **Excluded from benchmark comparison** — use tier classification (1–5) as the primary signal, not the absolute dollar amount. |

---

### Special Handling — Polarity Edge Cases

Three metrics require additional handling beyond simple polarity.

**Debt / Equity — negative equity:**

When shareholders' equity is negative (common for companies with aggressive buyback programs — Apple, Home Depot, McDonald's), the D/E ratio is negative or undefined. A negative D/E does not mean the company is deleveraging — it means book equity has been eliminated by buybacks. Standard polarity ("lower is better") breaks down in this case.

```
If equity < 0:
    Set debt_to_equity = null for benchmark comparison purposes
    Flag: "negative equity — D/E ratio not comparable to peers;
           capital structure reflects buyback program, not financial stress"
    Use asset_coverage and leverage as primary debt burden metrics instead

Do NOT exclude the company from the benchmark cell for other metrics.
Do NOT use the negative D/E value in the peer distribution computation.
```

This is consistent with the analytical decision to exclude `debt_to_equity` from the confirmation rule (documented in the dashboard Section 3 calibration tables).

**Revenue YoY Growth — first four quarters null:**

Revenue YoY growth requires a prior-year comparison period. For a newly onboarded company, the first four quarters will be null (no prior year data). These null values are excluded from the peer distribution. The benchmark for `revenue_yoy_growth` is therefore computed only from companies that have at least 5 quarters of data in the database.

```
If value is null for revenue_yoy_growth:
    Exclude from benchmark distribution computation
    Display as "— (insufficient history)" in peer comparison
```

**OCF / EBITDA Conversion — extreme values:**

OCF/EBITDA conversion values above 3.0x or below −1.0x almost always indicate a one-time working capital event (a large receivables collection, a prepayment, or a restructuring charge) rather than a genuine earnings quality signal. These extreme values distort the peer distribution significantly.

```
For benchmark computation only:
    Winsorise OCF/EBITDA conversion to the range [−1.0, 3.0]
    before computing percentiles
    Flag: "OCF/EBITDA conversion winsorised at [−1.0, 3.0] 
           for benchmark computation — extreme values excluded"

For individual company display:
    Show the actual value without winsorisation
    But note when the value falls outside the benchmark range
```

---

### Quartile Classification

After `get_benchmark()` returns `{p25, p50, p75}` for the company's cell, the quartile classification is computed as follows.

**For higher-is-better metrics:**

```
value > p75              →  "Top quartile"       display: ↑ green
p50 < value ≤ p75        →  "Upper middle"       display: ↗ light green  
p25 < value ≤ p50        →  "Lower middle"       display: ↘ light red
value ≤ p25              →  "Bottom quartile"    display: ↓ red
```

**For lower-is-better metrics (leverage, debt_to_equity):**

```
value < p25              →  "Top quartile"       display: ↑ green
p25 ≤ value < p50        →  "Upper middle"       display: ↗ light green
p50 ≤ value < p75        →  "Lower middle"       display: ↘ light red
value ≥ p75              →  "Bottom quartile"    display: ↓ red
```

**When no benchmark is available:**

```
benchmark is None        →  "No peer data"       display: — grey
```

This occurs when the company's sector has fewer than 3 companies with data for that metric, even after the full fallback cascade.

---

### Composite Peer Score

In addition to per-metric quartile classification, compute a **composite peer score** that summarises the company's overall position relative to peers across all benchmarked metrics.

**Computation:**

```
For each of the 16 benchmarked metrics:
    Assign a raw score:
        Top quartile    →  3
        Upper middle    →  2
        Lower middle    →  1
        Bottom quartile →  0
        No peer data    →  excluded from computation

Apply metric weights (see table below):
    weighted_score_i = raw_score_i × weight_i

Composite peer score = Σ(weighted_score_i) / Σ(weight_i for included metrics)
Scale to 0–100: composite_score = composite_peer_score × (100/3)
```

**Metric weights for composite peer score:**

Weights reflect analytical importance established by the Cohen's d statistical analysis and the confirmation rule calibration from the backtest.

| Metric | Weight | Basis |
|---|---|---|
| `leverage` | 3 | Highest Cohen's d (+1.76), in confirmation rule |
| `interest_coverage` | 3 | Second highest Cohen's d (+1.68), in confirmation rule |
| `free_cash_flow` | 2 | Medium-large Cohen's d (+0.80), in confirmation rule |
| `fcf_margin` | 2 | FCF signal, correlated with free_cash_flow |
| `moody_adjusted_fcf` | 2 | Moody's methodology — primary FCF signal |
| `rcf_net_debt` | 1 | Excluded from confirmation rule (low sensitivity) |
| `ocf_ebitda_conversion` | 1 | Supplementary earnings quality signal |
| `current_ratio` | 1 | Excluded from confirmation rule (statistically inert) |
| `quick_ratio` | 2 | In confirmation rule, sector-adjusted |
| `debt_to_equity` | 1 | Excluded from confirmation rule (capital structure artifact) |
| `ebitda_margin` | 2 | In confirmation rule |
| `revenue_yoy_growth` | 2 | In confirmation rule |
| `asset_coverage` | 2 | In confirmation rule |
| `tangible_asset_coverage` | 1 | Supplementary to asset_coverage |
| `liquidation_asset_coverage` | 2 | Formula 2 — distress-scenario recovery |
| `maturity_coverage_near_term` | 2 | Structural liquidity signal |

Quick ratio weight = 2 and current ratio weight = 1 because the backtest statistical analysis showed materially different discrimination: quick ratio Cohen's d = +0.49 (medium effect, in the confirmation rule) vs current ratio Cohen's d = −0.05 (statistically inert, p=0.92, excluded from confirmation rule — see dashboard Section 3, Table B). Current ratio is more susceptible to inventory accounting distortions and does not reliably separate distressed from healthy companies in the backtest sample.

**Composite score interpretation:**

| Score | Interpretation | Display |
|---|---|---|
| 75–100 | Strong relative to peers | ✅ Above peer group |
| 50–74 | In line with peers | 〜 Peer group average |
| 25–49 | Weak relative to peers | ⚠️ Below peer group |
| 0–24 | Significantly below peers | 🔴 Materially below peer group |

> **Note:** Metric weights are derived from a backtest of n=75 companies (30 distressed, 31 healthy controls, 12 stressed survivors). Individual metric Cohen's d estimates have wide confidence intervals at this sample size — only leverage and interest_coverage have CI lower bounds above the medium effect threshold. The composite score weights are therefore directional guidance, not statistically precise multipliers. Do not interpret composite score differences of less than 10 points as meaningful. Phase 5 will recalibrate weights with a target database of n≥200 distressed cases.

**Important caveat — composite score supplements, does not replace, alert levels:**

A company can score well on the composite peer score while still having Critical alert levels if its absolute metric values cross the volatility-adjusted thresholds in `thresholds.py`. The composite score answers "how does this company compare to peers?" — the alert level answers "does this company cross the absolute stress threshold?" Both are displayed. Neither overrides the other.

---

### Known Limitations and Model Boundary Conditions

---

**Limitation 1 — Equal-Weighted Sectors Within Composite Score**

**Problem:**
The composite peer score weights metrics by analytical importance but does not adjust weights by sector. For an Energy/E&P company, `leverage` and `interest_coverage` are overwhelmingly the most important metrics — FCF and revenue trend are secondary because commodity cycles make them highly volatile. For a Healthcare/Pharma company, `ebitda_margin` and `fcf_margin` are more important than `maturity_coverage` because pharma companies typically have long-dated debt and ample liquidity. Fixed weights across all sectors apply Energy-appropriate weights to Healthcare companies and vice versa.

**Materiality:**
Moderate. The composite score will directionally rank companies correctly within a sector but may over-weight or under-weight specific metrics relative to what a sector specialist analyst would prioritise.

**Interim mitigation:**
Composite score is displayed with a note: "weights reflect cross-sector statistical analysis (Cohen's d); sector-specialist analysts should prioritise sector-relevant metrics directly." Per-metric quartile classifications are always shown alongside the composite score so analysts can weight metrics themselves.

**Phase 5 fix:**
Implement sector-specific weight tables. For each sector, define a weight vector calibrated to that sector's credit driver literature. Reference: Moody's industry-specific rating methodologies (published publicly at moodys.com) define the weight each financial ratio receives in the rating scorecard for each industry — use these as the calibration source for sector-specific weights.

---

**Limitation 2 — Quartile Boundaries Are Not Credit-Calibrated**

**Problem:**
The quartile boundaries (p25/p50/p75) are statistical properties of the peer distribution — they describe where a company falls relative to its peers, not whether its absolute metric value is safe or stressed. A company in the "Top quartile" for leverage in the Energy/E&P sector might have leverage of 4x — which is below the peer median for that sector but still in the Significant financial risk band by S&P's absolute standards. The quartile classification can create false comfort: "top quartile" does not mean "not stressed."

**Materiality:**
High — this is the most important limitation of the framework to communicate to users. A distressed-sector peer comparison will always show relative rankings that look better than the absolute credit picture.

**Interim mitigation:**
Always display the absolute alert level (🔴 Critical, 🟠 Stress, etc.) alongside the peer quartile classification. Never display peer quartile without the absolute alert level. The display rule is: alert level first, quartile second. In the Streamlit UI, the quartile indicator is shown as a small secondary tag, not a primary signal.

**Phase 5 fix:**
Implement a combined score that integrates both absolute threshold position and peer quartile position. For example: a company at Critical alert level that is also in the Bottom quartile vs peers receives a combined score of "Acute" — both absolute and relative signals agree. A company at Critical alert level that is in the Top quartile vs peers receives "Sector-wide stress" — the absolute threshold is breached but the company is performing better than distressed peers. This combined classification is more actionable than either signal alone.

---

### Cross-References

- Metric polarity used by `get_benchmark()` in `benchmarks.py`: this section is the authoritative source
- Metric weights for composite score derived from: `analyze_backtest.py` Cohen's d output and dashboard Section 3 calibration tables
- Absolute alert thresholds that composite score does not replace: `LEVERAGE.md`, `INTEREST_COVERAGE.md`, and `thresholds.py`
- Debt-to-equity exclusion from confirmation rule (basis for weight = 1): dashboard Section 3, Table B
- Current ratio exclusion from confirmation rule (basis for weight = 1): dashboard Section 3, Table B
- `sector_benchmarks` table (p25/p50/p75 source): `SEGMENT_BENCHMARK_SPEC.md` → Section 3



## Section 5 — Multi-Segment Blending

---

### What it is

Multi-segment blending is the mechanism by which a company with two or more materially distinct business segments receives a benchmark comparison that reflects its actual business mix rather than a single SIC-code classification. Instead of comparing a company that is 60% technology and 40% retail against pure-play technology peers, the system constructs a blended benchmark — 60% of the technology sector median plus 40% of the retail sector median — and compares the company against that composite peer.

This section defines when blending triggers, how the blended benchmark is computed, how it is displayed, and what happens at the boundaries where blending produces ambiguous or unreliable results.

---

### Dependency — Group 8 LLM Extraction

Multi-segment blending cannot be implemented without Group 8 (segment footnote LLM extraction). The segment revenue weights required for the blending formula are disclosed in the ASC 280 Segment Footnote of each 10-K and 10-Q. They are not available in XBRL in a usable form — companies tag segment data inconsistently and many do not tag it at all. The LLM is the only reliable extraction path.

Until Group 8 is implemented:

```
If Group 8 extraction has not been run for a company:
    Use Level 1 single-sector classification (Section 2)
    Display flag: "single-sector benchmark — press LLM button
                   to extract segment data for blended benchmark"
    Do NOT attempt to infer segment weights from SIC code alone
```

Group 8 is triggered by the LLM button in the Streamlit app. It runs alongside the existing Groups 1–7a extractions when the analyst explicitly requests LLM extraction for a company. Segment data is stored permanently and does not require re-extraction on subsequent visits unless the analyst manually triggers a refresh.

---

### Trigger Conditions

Blending applies when all three of the following conditions are met:

**Condition 1 — Multiple reportable segments:**
The company discloses two or more reportable operating segments under ASC 280 in its most recent annual 10-K. Interim 10-Q segment disclosures may be used if the 10-K data is stale (more than 15 months old).

**Condition 2 — No dominant segment:**
No single segment accounts for ≥ 80% of total disclosed segment revenue. A company with one segment at 85% is treated as a single-sector company — the secondary segment is immaterial to the credit profile.

```
dominant_fraction = max(segment_revenue_i / total_segment_revenue)

If dominant_fraction >= 0.80:
    Use single-sector classification (dominant segment's sector)
    Flag: "dominant segment ({name}, {fraction:.0%}) — 
           single-sector benchmark applied"

If dominant_fraction < 0.80 AND segment_count >= 2:
    Apply multi-segment blending
```

**Condition 3 — Segments map to at least two distinct sector groups:**
If all segments map to the same sector group (e.g. a pharma company with Immunology and Oncology segments — both Healthcare/Pharma), blending does not apply because both segments share the same peer benchmark. The sub-sector classification from Section 2 handles within-sector variation for these cases.

```
sector_groups = {classify_sic(segment_primary_sic) 
                 for segment in segments}

If len(sector_groups) == 1:
    Use single-sector classification with sub-sector tag
    from the dominant segment description
    
If len(sector_groups) >= 2:
    Apply multi-segment blending across distinct sector groups
```

---

### Blending Formula

For each metric M, the blended benchmark is a revenue-weighted average of the sector medians for each segment's sector group:

```
blended_p50(M) = Σ_i [ weight_i × sector_p50(M, sector_i, size_category) ]

blended_p25(M) = Σ_i [ weight_i × sector_p25(M, sector_i, size_category) ]

blended_p75(M) = Σ_i [ weight_i × sector_p75(M, sector_i, size_category) ]

Where:
    weight_i         = segment_i_revenue / total_disclosed_revenue
    sector_p50(M, S) = median value of metric M for sector S
                       at the company's size_category
                       (from sector_benchmarks table)
    Σ weights        = 1.0 (weights sum to 100%)
```

**Normalisation when segment revenues do not sum to total revenue:**

Companies sometimes disclose segment revenue that does not perfectly reconcile to consolidated revenue (due to intersegment eliminations, corporate/unallocated segments, or rounding). Normalise weights to sum to 1.0 using disclosed segment revenue only:

```
weight_i = segment_i_revenue / Σ(all_disclosed_segment_revenues)
```

Exclude segments classified as "Corporate / Unallocated / Eliminations" from the weight computation — these are not operating segments and do not map to a sector benchmark.

**Size category for blending:**

Use the company's overall size category (from Section 1, based on total assets) for all segment benchmarks. Do not attempt to assign different size categories to different segments — segment-level asset data is not reliably disclosed in a form that permits per-segment size classification.

---

### Segment Data Structure (Group 8 Output)

Group 8 LLM extraction returns a structured JSON object with the following fields relevant to Section 5:

```json
{
  "segments": [
    {
      "name": "Pharmaceutical",
      "revenue": 38000,
      "revenue_unit": "millions_usd",
      "fraction": 0.56,
      "primary_sic_inferred": "2836",
      "sector_group": "Healthcare/Pharma",
      "sub_sector": "branded_pharma",
      "description_excerpt": "patented specialty medicines..."
    },
    {
      "name": "MedTech",
      "revenue": 30000,
      "revenue_unit": "millions_usd",
      "fraction": 0.44,
      "primary_sic_inferred": "3841",
      "sector_group": "Manufacturing/Industrials",
      "sub_sector": null,
      "description_excerpt": "surgical instruments, diagnostics..."
    }
  ],
  "total_segment_revenue": 68000,
  "corporate_eliminations": 700,
  "dominant_segment": "Pharmaceutical",
  "dominant_fraction": 0.56,
  "blending_trigger": true,
  "filing_period": "2024-12-31",
  "evidence": "Segment revenues for the year ended..."
}
```

The `sector_group` field is assigned by the LLM based on the segment description and inferred SIC. The LLM prompt instructs the model to assign sector groups from the fixed list defined in Section 2 — it does not invent new sector groups.

---

### Storage

Segment data extracted by Group 8 is stored in a new table `segment_extractions`:

```sql
CREATE TABLE segment_extractions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cik                 TEXT NOT NULL,
    filing_period       TEXT NOT NULL,
    segment_name        TEXT NOT NULL,
    revenue_millions    REAL,
    revenue_fraction    REAL NOT NULL,
    sector_group        TEXT NOT NULL,
    sub_sector          TEXT,
    description_excerpt TEXT,
    evidence            TEXT,
    extracted_at        TEXT NOT NULL,
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);
```

One row per segment per filing period. When Group 8 is re-run for a company, existing rows for that CIK and filing period are deleted and replaced.

The `issuers` table gains two new columns:

```sql
ALTER TABLE issuers ADD COLUMN blending_active INTEGER DEFAULT 0;
-- 1 when multi-segment blending is in use for this company

ALTER TABLE issuers ADD COLUMN segment_extraction_date TEXT;
-- ISO date of most recent Group 8 extraction
```

---

### Display

When blending is active for a company, the sector label in the company header changes from a single sector to a blend description:

```
Without blending:
  Sector: Healthcare / Pharma  |  Size: Large  |  Sub-sector: branded_pharma

With blending:
  Sector: Healthcare/Pharma (56%) + Manufacturing/Industrials (44%) blend
  Size: Large  |  Benchmark: blended — see segment breakdown
```

In the metric table, the peer comparison column header changes from "vs sector median" to "vs blended median" and shows the composite blended value with expandable detail section using st.expander(), collapsed by default, showing the component breakdown:

```
Metric: leverage
Company value:        4.2x
Blended p50:          3.8x  (56% × Healthcare p50 3.5x + 44% × Manufacturing p50 4.2x)
Quartile:             Lower middle ↘

[▶ Show blend components]
  Healthcare/Pharma (56%):   p25=2.1x  p50=3.5x  p75=5.2x  (8 companies)
  Manufacturing/Industrials (44%):   p25=2.8x  p50=4.2x  p75=6.1x  (12 companies)
```

The component breakdown is collapsed by default. The analyst can expand it to see what each sector contributes to the blended benchmark and how many companies underlie each component.

---

### Boundary Conditions and Edge Cases

**Edge case 1 — Segment maps to Financial Institutions sector:**

If one of a company's segments is classified as Financial Institutions (e.g. GE Capital, Caterpillar Financial Products), that segment is excluded from blending. Financial institution benchmarks are suppressed throughout the system and cannot participate in a cross-sector blend.

```
If sector_group_i == "Financial Institutions":
    Exclude segment_i from blending
    Redistribute its weight proportionally to remaining segments
    Flag: "financial services segment excluded from benchmark blend —
           {segment_name} ({fraction:.0%} of revenue) not benchmarked"
```

**Edge case 2 — One segment has no benchmark available:**

If a segment's sector group has fewer than 3 companies in the benchmark table (even after the fallback cascade), no benchmark exists for that component. The blend cannot be computed as specified.

```
If sector_p50(M, sector_i) is None for any segment_i:
    Option A (preferred): compute partial blend using available segments only,
                          renormalise weights to sum to 1.0 across available segments
                          Flag: "{sector_i} component excluded — insufficient peer data;
                                 blended benchmark uses {remaining_weight:.0%} of revenue"
    
    Option B: fall back to single-sector classification using dominant segment
              Flag: "blended benchmark unavailable — insufficient peer data for
                     {sector_i} component; single-sector benchmark applied"

Apply Option A when the missing component is < 30% of revenue.
Apply Option B when the missing component is >= 30% of revenue — 
a 30%+ exclusion would make the partial blend materially unrepresentative.
```

**Edge case 3 — Segment revenue not disclosed in 10-Q:**

ASC 280 requires full segment disclosure in annual 10-Ks but permits abbreviated segment disclosure in 10-Qs. If Group 8 runs on a 10-Q that does not contain full segment revenue data, use the most recent 10-K segment data with a staleness flag.

```
If segment_data.source == "10-K" AND segment_data.filing_period older than 15 months:
    Flag: "segment data from {filing_period} 10-K — may not reflect current 
           business mix; re-run LLM extraction on latest 10-K for updated blend"
```

**Edge case 4 — Three or more segments across three or more sectors:**

The blending formula handles any number of segments — it is a weighted sum. No special handling is needed for 3+ segment companies. The display component breakdown shows one row per segment regardless of count. The composite weight constraint (Σ weights = 1.0) is enforced by normalisation.

---

### Relationship to Berger and Ofek (1995)

The multi-segment blending methodology is grounded in the diversification discount literature. Berger and Ofek (1995) demonstrated that diversified conglomerates trade at a 13–15% discount to the sum of their pure-play segment values, using exactly the revenue-weighted benchmark approach defined here — comparing each segment against pure-play peers in the same industry and weighting by segment revenue.

The credit risk application differs from the equity valuation application in one important respect: Berger and Ofek measured value destruction from diversification; this system uses the same blending methodology to construct a benchmark, not to measure a discount. The system does not assert that a conglomerate is penalised for diversification — it simply constructs the most accurate available peer comparison given the company's actual business mix.

Reference: Berger, P.G. and Ofek, E. (1995). "Diversification's Effect on Firm Value." *Journal of Financial Economics*, 37(1), 39–65.

---

### Known Limitations and Model Boundary Conditions

---

**Limitation 1 — Segment Classification Relies on LLM Judgment**

**Problem:**
The `sector_group` assignment for each segment is made by the LLM based on the segment description text in the ASC 280 footnote. The LLM prompt constrains assignments to the nine sector groups defined in Section 2, but the assignment for ambiguous segments is a judgment call. A segment described as "digital health platforms and connected devices" could reasonably be classified as Healthcare/Pharma or Technology/Services. Different LLM runs or different prompt phrasings might produce different classifications for the same segment.

**Materiality:**
Moderate. For clear-cut segments (oil and gas production → Energy/Mining, retail pharmacy → Healthcare/Pharma) the classification is unambiguous. For technology-enabled healthcare, fintech, or industrial software segments the classification is genuinely ambiguous and reasonable analysts would disagree.

**Interim mitigation:**
Group 8 extraction returns a `description_excerpt` and `evidence` field for each segment classification. The analyst can review the LLM's reasoning in the Streamlit expandable detail panel. A manual override field (`segment_sector_override`) is available in the `segment_extractions` table for cases where the analyst disagrees with the LLM classification.

```sql
ALTER TABLE segment_extractions 
ADD COLUMN sector_group_override TEXT DEFAULT NULL;
-- When not null, use this value instead of sector_group for blending
```

**Phase 5 fix:**
Build a segment classification validation layer — after LLM extraction, run a secondary check that compares the LLM's segment classification against the segment's reported SIC code (when available) and flags cases where the two disagree. Disagreements trigger a manual review prompt in the Streamlit UI.

---

**Limitation 2 — Revenue Weights Do Not Reflect Credit Risk Contribution**

**Problem:**
The blending formula weights each sector benchmark by segment revenue fraction. Revenue is the most readily available and consistently disclosed segment metric, making it the natural choice for weights. However revenue weighting may not accurately reflect each segment's contribution to the company's credit risk profile. A company with 60% revenue from a low-margin, asset-intensive retail segment and 40% revenue from a high-margin, asset-light software segment has a credit profile more heavily influenced by the retail segment's debt burden than the 60/40 revenue split suggests.

More analytically correct weights would use segment EBITDA (for earnings contribution) or segment assets (for debt-backing contribution). However segment EBITDA and segment assets are disclosed less consistently than segment revenue, and are often presented before corporate allocations in ways that make them unreliable for mechanical weighting.

**Materiality:**
Moderate for companies where segment margin profiles differ significantly. Low for companies with similar margins across segments.

**Interim mitigation:**
When segment EBITDA is available from Group 8 extraction, compute an alternative EBITDA-weighted blend alongside the revenue-weighted blend and display both. Flag when the two blends differ by more than 10 percentage points on any weight: "revenue-weighted and EBITDA-weighted blends differ materially — review segment profitability breakdown."

**Phase 5 fix:**
Default to EBITDA-weighted blending when segment EBITDA is reliably available from Group 8 extraction. Use revenue weighting only as a fallback when EBITDA is not disclosed at segment level. Add a toggle in the Streamlit UI allowing the analyst to switch between revenue-weighted and EBITDA-weighted benchmarks.

Reference: Damodaran, A. (2002). *Investment Valuation*, Chapter 24 — "Valuing Firms with Multiple Businesses." Discusses EBITDA-weighted vs revenue-weighted approaches to sum-of-parts analysis.

---

**Limitation 3 — Segment Mix Changes Are Not Retroactively Applied**

**Problem:**
Segment data is extracted from the most recent filing and applied as a static attribute. If a company's business mix changes materially — through acquisition, divestiture, or organic growth shifting revenue mix — the stored segment weights become stale. The blended benchmark continues to reflect the old business mix until the analyst manually re-runs Group 8 extraction.

More importantly, for historical analysis (the 8-quarter display window in the Company Monitor), the current segment mix is applied uniformly to all historical periods. A company that acquired a technology division in Q3 2024 will have its pre-acquisition quarters benchmarked against a blend that includes the technology segment — which did not exist during those quarters.

**Materiality:**
High for companies undergoing active portfolio transformation. Low for stable conglomerates with consistent segment mix over time.

**Interim mitigation:**
Display the segment extraction date prominently in the Company Monitor. Flag when the extraction date is more than 12 months old. For historical quarters predating a known acquisition, show a note: "segment mix reflects current filing — historical periods may not reflect current business composition."

**Phase 5 fix:**
Implement point-in-time segment extraction — store segment weights by filing period in the `segment_extractions` table and join against the benchmark computation by period. This requires running Group 8 extraction for each historical 10-K in the analysis window, not just the most recent one. The `extracted_at` and `filing_period` columns in `segment_extractions` already support this — the Phase 5 work is building the historical extraction loop and the period-matched benchmark join logic.

---

### Cross-References

- Sector group definitions used for segment classification: `SEGMENT_BENCHMARK_SPEC.md` → Section 2
- Size category used for per-segment benchmark lookup: `SEGMENT_BENCHMARK_SPEC.md` → Section 1
- `sector_benchmarks` table (source of sector_p25/p50/p75 values): `SEGMENT_BENCHMARK_SPEC.md` → Section 3
- Group 8 LLM extraction implementation: deferred to Phase 5; prompt design to follow `llm_extractor.py` pattern from Groups 1–7a
- Sub-sector classification for within-sector variation (alternative to blending when all segments share one sector group): `SEGMENT_BENCHMARK_SPEC.md` → Section 2 → Sub-Sector Classification Definitions
- Financial institution suppression applied to segment blending: `SECTION_6.md` → Section 6.5



## Section 6 — Known Limitations

---

### Purpose of this Section

This section consolidates system-level limitations that span multiple components of the benchmark framework. Component-specific limitations are documented within their respective sections (Section 1 through Section 5). This section addresses limitations that cannot be attributed to a single component — they emerge from the interaction between components, from data availability constraints outside the system's control, or from fundamental methodological choices that affect the entire framework.

Each limitation follows the standard format established in Section 1: Problem / Materiality / Interim Mitigation / Phase 5 Fix.

---

### Limitation 6.1 — Minimum Sample Sizes Produce Directional-Only Benchmarks for Most Cells

**Problem:**

The benchmark framework defines cells at three levels of specificity: sector × size × sub_sector (full), sector × size (no sub_sector), and sector only. The fallback cascade in Section 3 ensures the system always returns the most specific available benchmark. However at the current database size of 75 companies distributed across 9 sectors, 3 size tiers, and up to 4 sub_sectors per sector, the majority of full cells contain fewer than 3 companies and trigger the fallback cascade. Many sector × size cells also fall below the 3-company minimum, forcing a further fallback to sector-only benchmarks.

The consequence is that the percentile values (p25/p50/p75) in most cells are computed from 3–7 companies rather than the 10–20 required for statistically stable quartile estimates. At n=3, the p25 and p75 values are essentially the minimum and maximum of the sample — they provide directional information but no meaningful distributional precision. A p75 leverage of 6.2x computed from 4 companies in the Small Retail cell could shift by 1–2x with the addition of a single new company.

**Materiality:**

High for Small-tier companies across all sectors and for all companies in Media/Entertainment, Healthcare/Pharma sub-sectors, and Technology/Services. Lower for Large and Mid-tier Manufacturing/Industrials, Retail/Wholesale, and Energy/Mining where the current database has 5–12 companies per sector × size cell.

Estimated cell population from the current 75-company database after excluding financial institutions (Aflac, JPMorgan) and applying the size breakpoints from Section 1:

| Sector | Large (>$10B) | Mid ($1B–$10B) | Small (<$1B) |
|---|---|---|---|
| Retail/Wholesale | 3 | 5 | 2 |
| Energy/Mining | 3 | 4 | 2 |
| Manufacturing/Industrials | 6 | 5 | 1 |
| Healthcare/Pharma | 4 | 3 | 2 |
| Technology/Services | 3 | 3 | 1 |
| Media/Entertainment | 2 | 2 | 1 |
| Business/Consumer Services | 1 | 2 | 1 |
| Telecom/Utilities | 2 | 2 | 1 |

Cells with fewer than 3 companies trigger fallback. Cells with 3–5 companies produce directional-only benchmarks. Only Manufacturing/Industrials Large has sufficient sample for reliable quartile estimates in the current database.

**Interim Mitigation:**

The `company_count` and `fallback_level` columns in the `sector_benchmarks` table are propagated to every benchmark display. The Streamlit UI and dashboard display a precision qualifier alongside every benchmark comparison:

```
≥ 10 companies:  "robust benchmark"          — no qualifier shown
5–9 companies:   "limited benchmark (N companies)" — shown in grey
3–4 companies:   "directional only (N companies)"  — shown in amber
< 3 companies:   "no benchmark available"           — shown in grey, no comparison
```

Analysts are instructed to treat benchmarks from fewer than 5 companies as directional signals only — confirming a known concern rather than establishing a new one.

**Phase 5 Fix:**

Expand the company database to a minimum of 200 issuers with deliberate coverage of all sector × size cells. Target cell populations:

```
Minimum viable:     3 companies per cell  (enables percentile computation)
Directional:        5 companies per cell  (p25/p75 stable to ±20%)
Reliable:          10 companies per cell  (p25/p75 stable to ±10%)
Production-grade:  20 companies per cell  (p25/p75 stable to ±5%)
```

Cell expansion priority: Small-tier companies across all sectors (currently the most sparse), followed by Media/Entertainment and Business/Consumer Services at all tiers. Use the `check_xbrl_coverage.py` diagnostic tool to pre-screen new companies before onboarding to ensure XBRL tag coverage is sufficient for the 16 benchmarked metrics.

Additionally implement Bayesian shrinkage for sparse cells — shrink sparse cell percentiles toward the sector-only percentiles by a factor proportional to the inverse of sample size. This borrows statistical strength from the larger sector population without discarding sparse cell data entirely. Reference: James and Stein (1961), "Estimation with Quadratic Loss," *Proceedings of the Fourth Berkeley Symposium on Mathematical Statistics and Probability*, 1, 361–379.

---

### Limitation 6.2 — Multi-Segment Blending Deferred Until Group 8 Is Implemented

**Problem:**

Approximately 20–30% of large-cap companies in the investment-grade universe have two or more materially distinct business segments with no single segment exceeding 80% of revenue. For these companies, Level 1 single-sector classification produces a benchmark peer group that does not accurately represent the company's actual credit profile. A company that is 60% industrial manufacturing and 40% financial services will be benchmarked against pure-play industrials — systematically underweighting the financial services component's contribution to the company's risk profile.

Until Group 8 (segment footnote LLM extraction) is implemented, the system has no mechanism to identify which companies require blending or what weights to apply. Every company in the database receives Level 1 single-sector classification regardless of its actual business mix.

**Materiality:**

Moderate for the current 75-company database. The most affected companies in the current database are Conduent (IT services + BPO — borderline Technology/Business Services), Coty (consumer beauty + prestige fragrance — single sector but different sub-sector profiles), and any holding company manually classified. The distressed case library was selected for sector clarity so cross-sector conglomerates are underrepresented. Materiality increases significantly as the database expands to include large-cap conglomerates (GE, Honeywell, 3M, Berkshire Hathaway subsidiaries).

**Interim Mitigation:**

The `conglomerate_flag` field in the `issuers` table (defined in Section 2, Rule 5) identifies companies that require blending once Group 8 is available. For currently flagged conglomerates, display a persistent note in the Company Monitor:

```
"⚠ Multi-segment company — benchmark uses primary SIC sector only.
 Press LLM button to extract segment data for blended benchmark
 once Group 8 extraction is available."
```

This ensures analysts are aware of the limitation for specific companies rather than discovering it through unexplained benchmark divergence.

**Phase 5 Fix:**

Implement Group 8 segment footnote LLM extraction as defined in Section 5. Build the extraction prompt to return segment names, revenues, and sector group classifications from the ASC 280 footnote. Integrate with the existing LLM button trigger in the Streamlit app so segment extraction runs alongside Groups 1–7a when the analyst requests LLM extraction. Store results in `segment_extractions` table and update `blending_active` flag in `issuers` table. Full methodology defined in Section 5.

---

### Limitation 6.3 — Financial Institution Benchmarks Excluded from Cross-Sector Comparison

**Problem:**

Financial institutions (SIC 6000–6499, primarily banks and insurers) are excluded from all benchmark cell computations throughout this framework. This exclusion is correct and intentional — financial institution leverage, margins, and liquidity metrics are structurally incomparable to corporate metrics because their balance sheets include deposits, policyholder reserves, and regulatory capital requirements that have no corporate equivalent. Including Aflac's $130B total assets in a benchmark cell with Apple and Exxon would produce meaningless distributions.

The consequence is that financial institution issuers in the database (currently Aflac and JPMorgan) receive no benchmark comparisons at all. Their metric values are displayed in the Company Monitor but without the peer quartile classification and composite peer score that other issuers receive. This creates an asymmetric user experience — financial institution issuers appear analytically underserved relative to corporate issuers.

**Materiality:**

Low for the current database (2 financial institution issuers out of 75). Moderate if the database expands to include a significant number of insurance companies or regional banks. High if the system is ever deployed for a portfolio with substantial financial institution exposure.

**Interim Mitigation:**

Display a clear explanation in the Company Monitor when a financial institution is selected:

```
"Financial institution — standard corporate benchmarks not applicable.
 Regulatory capital ratios (CET1, Tier 1 capital ratio, LCR) govern
 credit assessment for this institution type. Peer comparison requires
 a separate financial institution benchmark framework."
```

Metrics that are computed for financial institutions despite the suppression rules (D/E ratio, asset coverage, loss provisions, revenue trend) continue to display their absolute alert levels without peer quartile classification.

**Phase 5 Fix:**

Implement a separate financial institution benchmark framework using institution-appropriate metrics. The corporate metric set is replaced or supplemented by:

```
Regulatory capital:   CET1 ratio, Tier 1 capital ratio
Asset quality:        Non-performing loan ratio, loan loss reserve coverage ratio
Liquidity:            LCR (Liquidity Coverage Ratio), NSFR (Net Stable Funding Ratio)
Profitability:        Return on assets (ROA), net interest margin (NIM)
Funding stability:    Deposit-to-asset ratio, wholesale funding reliance
```

These metrics are available from SEC filings for bank holding companies (Call Report data is publicly available via FFIEC) and from 10-K disclosures for insurance companies (statutory filings via NAIC, supplemented by GAAP 10-K). The framework architecture (cell definition, percentile computation, fallback cascade) is identical to the corporate framework — only the metric set changes. Reference: Basel Committee on Banking Supervision (2019), "Minimum Capital Requirements for Market Risk" — defines the regulatory capital metrics that serve as the primary credit signal for financial institutions.

---

### Limitation 6.4 — Benchmark Reflects Current Database Composition, Not the Full Credit Universe

**Problem:**

The sector benchmark medians are computed exclusively from the 75 companies in the current database. This database was constructed for backtest validation purposes — it over-represents distressed companies (30 of 75 are bankrupt or severely stressed) and under-represents investment-grade companies in certain sectors. The resulting benchmark distributions are systematically skewed toward stress relative to the true population of all US corporate bond issuers.

A concrete example: the Retail/Wholesale sector benchmark for leverage is computed from approximately 10 retail companies, of which 8 are distressed (Rite Aid, Bed Bath & Beyond, JCPenney, Sears, Party City, Pier 1, Tailored Brands, Tupperware) and 2 are healthy (Walmart, Costco). The resulting p50 leverage for Retail is pulled substantially higher than the actual retail sector median across all issuers. A healthy mid-cap retailer with leverage of 3x would appear in the top quartile of this benchmark — which is correct relative to this database but misleading relative to the actual retail universe.

**Materiality:**

High for all sectors where distressed companies constitute more than 30% of the cell population. In the current database this affects Retail, Energy, Media, and Pharma cells at all size tiers. Low for Manufacturing/Industrials and Technology/Services where the healthy controls dominate.

**Interim Mitigation:**

The `benchmark_exclude` flag defined in Section 3 (Limitation 2) can be set to 1 for distressed companies to produce a healthy-company-only benchmark. However this is not implemented in Phase 4 — it is designated as a Phase 5 task to avoid removing distressed companies from the distribution before the impact is understood.

Display a database composition note in the benchmark section of the UI. Display cell-level composition in the benchmark expandable detail: 'Cell: N companies (D distressed, H healthy).' This requires distressed_count alongside company_count in the sector_benchmarks table — a single additional column computed at benchmark generation time.:

```
"Benchmark database: 75 companies (30 distressed, 31 healthy controls,
 12 stressed survivors, 2 financial institutions).
 Distressed companies are included in peer distributions — benchmarks
 reflect a stress-weighted sample, not the full investment-grade universe."
```

**Phase 5 Fix:**

Implement dual benchmark computation as described in Section 3 Limitation 2: compute both an all-companies benchmark and a healthy-only benchmark (using `benchmark_exclude` to filter distressed cases). Display both in the Streamlit UI with clear labeling. For investment-grade portfolio monitoring, the healthy-only benchmark is the more appropriate reference. For distressed debt analysis, the all-companies benchmark (including peer distressed companies) is more informative.

Additionally expand the database to include a representative sample of investment-grade issuers across all sectors — not selected for distress history — to bring the benchmark distribution closer to the true corporate universe.

---

### Limitation 6.5 — Static Benchmark Computation Does Not Reflect Market Cycle Position

**Problem:**

The benchmark table is computed from a snapshot of the database at a single point in time. For cyclical sectors (Energy/Mining, Manufacturing/Industrials, Media/Entertainment), the peer metric distributions shift substantially across the economic cycle. An Energy/E&P benchmark computed in 2020 (commodity price collapse, widespread bankruptcies) reflects a severely stressed distribution. The same benchmark computed in 2022 (commodity price peak, high margins) reflects a healthy distribution. A company analyzed in 2024 using a benchmark computed from 2022 data will appear more stressed than it actually is relative to current peers.

This is distinct from Limitation 3 in Section 3 (latest-period selection for individual companies) — that limitation addresses which period's value is used for a specific company. This limitation addresses the broader issue that the entire benchmark distribution reflects the cycle position at the time of database population, not the current cycle position.

**Materiality:**

High for Energy/Mining and Manufacturing/Industrials over multi-year analysis windows. Moderate for Retail and Media. Low for Healthcare/Pharma, Technology/Services, and Telecom/Utilities which are less cyclical.

**Interim Mitigation:**

Display the `computed_at` timestamp on all benchmarks. For Energy/Mining and Manufacturing/Industrials benchmarks, add a cyclicality warning:

```
"Cyclical sector — benchmark reflects database conditions as of {computed_at}.
 Interpret leverage and coverage benchmarks with awareness of commodity/
 industrial cycle position at that date."
```

**Phase 5 Fix:**

Implement through-the-cycle benchmark computation for cyclical sectors. Rather than using the latest single period value for each company, compute each company's median value across its full 8-quarter history before computing the peer distribution. This produces a mid-cycle benchmark that is less sensitive to point-in-time cycle position. The methodology is available in the current database — every company has 8 quarters of `metric_values` stored — but requires changes to the `recompute_all_benchmarks()` query to aggregate across periods rather than using only the latest period. Reference: Standard and Poor's (2013), "Corporate Methodology," Section 4 — "Through-the-Cycle Assessment" — describes the rationale for cycle-adjusted financial ratio analysis in credit rating.

---

### Limitation 6.6 — Composite Peer Score Weights Are Derived from a Small Backtest Sample

**Problem:**

The metric weights used in the composite peer score (Section 4) are derived from Cohen's d values computed on a backtest of 30 distressed and 31 healthy companies. At this sample size, individual Cohen's d estimates have wide confidence intervals — only leverage and interest_coverage have CI lower bounds above the medium effect threshold (d > 0.5). The remaining 14 metrics have Cohen's d estimates that could plausibly be zero or negative at the 95% confidence level. Weights assigned to these metrics (ranging from 1 to 2) are therefore directional guidance based on limited statistical evidence, not precisely calibrated multipliers.

The composite peer score inherits this uncertainty — it is a weighted sum of 16 uncertain components. A composite score difference of less than 10 points between two companies should not be interpreted as analytically meaningful given the underlying parameter uncertainty.

**Materiality:**

Moderate for the composite score itself. The absolute alert levels (from `thresholds.py`) are unaffected — this limitation applies only to the peer-relative composite score. Individual metric quartile classifications are also unaffected — they depend on the benchmark distributions, not on Cohen's d weights.

**Interim Mitigation:**

Display the sample size disclosure defined in Section 4 alongside the composite score. Do not present composite score differences of less than 10 points as significant. In the Streamlit UI, round composite scores to the nearest 5 to discourage false precision.

**Phase 5 Fix:**

Recalibrate composite score weights with a target backtest database of n ≥ 200 distressed cases across multiple credit cycles. At n=200, Cohen's d confidence intervals narrow sufficiently that medium-effect metrics (d ≈ 0.5) can be distinguished from zero-effect metrics with reasonable confidence. Use logistic regression with cross-validation rather than Cohen's d as the primary calibration method at this sample size — logistic regression weights are directly interpretable as relative predictive contribution and are more appropriate for a multi-metric composite score than pairwise effect sizes. Reference: Hosmer, D.W. and Lemeshow, S. (2000), *Applied Logistic Regression*, 2nd edition — Chapter 5, "Assessing the Fit of the Model."

---

### Cross-References

- Component-specific limitations (by section):
  - Size classification boundary conditions: Section 1 — Known Limitations
  - Sector classification SIC accuracy and conglomerate handling: Section 2 — Known Limitations
  - Benchmark computation sparse cells, point-in-time bias, cyclical context: Section 3 — Known Limitations
  - Composite score sector weights, quartile calibration, sample size: Section 4 — Known Limitations
  - Segment classification LLM judgment, revenue vs EBITDA weighting, segment staleness: Section 5 — Known Limitations

- System-wide limitations referenced elsewhere in the project:
  - Financial institution suppression rules: `SECTION_6.md` → Section 6.5
  - XBRL tag coverage gaps across 75 issuers: `run_coverage_check.py` batch diagnostic output
  - LLM extraction point-in-time limitation (Groups 1–7a): project `README.md` → Known Limitations
  - Backtest sector coverage weighting (retail 27%, energy 23%): project `README.md` → Known Limitations

