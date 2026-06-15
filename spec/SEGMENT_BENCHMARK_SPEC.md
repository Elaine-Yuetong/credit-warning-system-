Section 1: Company Size Classification

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

## Known Limitations

- **Point-in-time vs onboarding:** Size category is computed from the most recent filing, not historically. A company that grew from Mid to Large over the backtest period is classified as Large for all historical comparisons, which may slightly distort early-period peer comparisons. This is acceptable for Phase 4 — historical size reclassification is a Phase 5 enhancement.

- **Financial institutions:** Total assets for banks and insurers includes policyholder liabilities and deposit balances that inflate the asset base relative to non-financial companies. A mid-size bank with $50B in deposits appears as Large by total assets but is not comparable to a $50B industrial company. Financial institution size classification uses the same breakpoints for consistency but benchmark comparisons for financial institutions are suppressed entirely per the financial institution suppression rules in `SECTION_6.md`.

- **Post-bankruptcy shells:** Some distressed companies in the case library (JCPenney → Old Copper Company, Bed Bath → DK-Butterfly) have minimal assets after emergence. Their size classification reflects the post-bankruptcy entity, not the pre-bankruptcy operating company. This is noted in the case library annotations.

---

## Cross-references

- Benchmark table construction using `size_category` as a segmentation dimension: see `SEGMENT_BENCHMARK_SPEC.md` → Section 3 (Benchmark Table Construction)
- Financial institution suppression that excludes size-tier benchmarks for SIC 6000–6499: see `SECTION_6.md` → Section 6.5
- `issuers` table schema: see `SECTION_6.md` → Section 6.3 (Table 1: issuers)
