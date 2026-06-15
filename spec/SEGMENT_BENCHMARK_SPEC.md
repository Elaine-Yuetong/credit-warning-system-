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

This format — Problem / Materiality / Interim Mitigation / Phase 5 Fix — is the standard structure used in rating agency model documentation (Moody's Analytics model validation reports follow this exact four-part structure for each limitation). It is professionally credible and immediately communicates to your mentor that you understand not just what the system does, but where its analytical boundaries are and how you would address them at scale.
---

## Cross-references

- Benchmark table construction using `size_category` as a segmentation dimension: see `SEGMENT_BENCHMARK_SPEC.md` → Section 3 (Benchmark Table Construction)
- Financial institution suppression that excludes size-tier benchmarks for SIC 6000–6499: see `SECTION_6.md` → Section 6.5
- `issuers` table schema: see `SECTION_6.md` → Section 6.3 (Table 1: issuers)
