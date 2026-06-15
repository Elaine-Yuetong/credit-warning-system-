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

