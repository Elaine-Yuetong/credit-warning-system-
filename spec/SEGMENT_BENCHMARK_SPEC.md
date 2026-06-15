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
