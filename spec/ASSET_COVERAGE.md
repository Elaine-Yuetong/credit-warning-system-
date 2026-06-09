# Asset Coverage

---

## What it is

Asset Coverage measures whether a company's assets are sufficient to repay its debt obligations if those assets were liquidated. It answers: *"if this company had to sell everything it owns to pay off its debt, would there be enough?"*

Unlike leverage (which measures debt relative to earnings) and liquidity (which measures near-term cash adequacy), asset coverage measures balance sheet solvency from a creditor recovery perspective. It is most relevant for secured debt analysis — when a lender holds a lien on specific assets, asset coverage tells them whether the collateral value is sufficient to recover the outstanding loan balance in a default scenario.

Asset coverage is meaningful at two levels. At the consolidated level it assesses whether total assets cover total debt — a solvency floor. At the secured debt level it assesses whether the specific assets pledged as collateral cover the secured obligations against them — a recovery rate estimate. The two levels produce different ratios and serve different analytical purposes. For a corporate bond portfolio of investment-grade and sub-investment-grade names, the consolidated level is the primary signal. The secured debt level becomes relevant when a company has materially secured its debt against identifiable asset pools.

A critical caveat governs the entire metric: **book value is not liquidation value.** Financial statements report assets at historical cost less depreciation (PP&E), at fair value (marketable securities), or at acquisition cost less impairment (goodwill and intangibles). None of these equals what those assets would actually fetch in a distressed sale. A factory carried at $500M book value might sell for $150M in a forced liquidation. Goodwill — often the largest asset on a technology or services company's balance sheet — has zero recovery value in most distress scenarios. This gap between book value and liquidation value is the central analytical challenge of this metric and the primary reason it requires judgment and LLM-assisted haircut application rather than simple ratio computation.

---

## Why it signals stress

**Mechanism 1 — The recovery floor signal.**
For creditors holding unsecured debt, asset coverage tells them what recovery rate to expect in a worst-case scenario. A company with asset coverage of 0.4x — meaning assets cover only 40% of total debt at book value — signals that even before applying liquidation haircuts, creditors face significant losses in a default. After applying realistic haircuts to intangibles and fixed assets, the recovery rate may be materially lower. This is not a trigger for imminent default but it is a fundamental assessment of how much is at stake if other metrics deteriorate to crisis levels.

**Mechanism 2 — Equity cushion deterioration.**
Asset coverage declining toward 1.0x means the gap between assets and liabilities is shrinking — equity is being eroded. When asset coverage falls below 1.0x on a book value basis, the company is technically insolvent by balance sheet measures even if it continues to service debt from operating cash flows. This condition, combined with deteriorating coverage and leverage ratios, significantly elevates near-term default risk.

**Mechanism 3 — Secured creditor advantage indicator.**
When a company has both secured and unsecured debt, asset coverage at the secured debt level reveals how much of the asset base is encumbered. Heavily secured balance sheets leave unsecured bondholders with little recovery prospect in default — a material consideration for a portfolio holding those unsecured bonds. A company with $2B of assets, $1.5B of secured debt against $1.8B of specific collateral, and $500M of unsecured bonds effectively has almost no unencumbered asset coverage for the unsecured holders.

**Mechanism 4 — Asset-light business deterioration.**
For asset-light companies (technology, services, software), the majority of balance sheet assets are intangibles and goodwill with near-zero liquidation value. A low asset coverage ratio for these companies reflects structural characteristics rather than stress. The signal value of asset coverage for asset-light companies is therefore limited for absolute level assessment but valuable for trend monitoring — a declining trend in an already low ratio indicates equity erosion that is not captured as clearly by other metrics.

---

## Formula

**Formula 1 — Book Value Asset Coverage (XBRL / Deterministic)**

```
Asset Coverage Ratio =
    Total Assets / Total Debt

Total Assets = us-gaap:Assets
Total Debt   = See LEVERAGE.md → Section "Formula" → Formula 1 (Total Debt = Short-Term Borrowings + Current LT Debt + Long-Term Debt) — apply identical three-component definition
               (Short-Term Borrowings + Current LT Debt
               + Non-Current LT Debt)

Tangible Asset Coverage Ratio =
    Tangible Assets / Total Debt

Tangible Assets =
    Total Assets
    − Goodwill
    − Intangible Assets (net)
    − Deferred Tax Assets (net)
    − Other non-recoverable assets

Goodwill           = us-gaap:Goodwill
Intangible Assets  = us-gaap:IntangibleAssetsNetExcludingGoodwill
Deferred Tax Asset = us-gaap:DeferredTaxAssetsNet
```

**Why two versions:** Total Asset Coverage is the broadest measure and the simplest to compute. Tangible Asset Coverage is more analytically meaningful for credit purposes because it excludes assets with minimal liquidation value. For most credit stress assessments, Tangible Asset Coverage is the primary ratio. Total Asset Coverage is computed as a supplementary cross-check.

**Extraction note:** See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table and Section "Extraction Fallback Logic" → Inputs 1–4 — reuse all stored Total Debt values; only Total Assets, Goodwill, Intangibles, and DTA are incremental extractions.

**XBRL tags:**

| Input | Primary Tag | Fallback Tag |
|---|---|---|
| Total Assets | `us-gaap:Assets` | Derived: Current Assets + Non-Current Assets |
| Total Debt | See LEVERAGE.md → Section "Formula" → Formula 1 XBRL Tags table — reuse stored debt tag values; no re-extraction required | — |
| Goodwill | `us-gaap:Goodwill` | `us-gaap:GoodwillNet` |
| Intangible Assets (net) | `us-gaap:IntangibleAssetsNetExcludingGoodwill` | `us-gaap:FiniteLivedIntangibleAssetsNet` + `us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill` |
| Deferred Tax Asset (net) | `us-gaap:DeferredTaxAssetsLiabilitiesNet` | `us-gaap:DeferredTaxAssetsNet` |

**Formula 2 — Liquidation-Adjusted Asset Coverage (LLM-assisted, Phase 3)**

Book value systematically overstates liquidation value. Formula 2 applies asset-type-specific haircuts to produce an estimated recovery-basis coverage ratio.

```
Liquidation Asset Coverage =
    Liquidation Value of Assets / Total Debt

Liquidation Value =
    Cash & Short-Term Investments × 100%
    (no haircut — fully recoverable)

  + Accounts Receivable × 70%–85%
    (haircut for collectibility in distress)

  + Inventory × 40%–60%
    (haircut for forced-sale discount;
     lower for specialised inventory,
     higher for commodity inventory)

  + PP&E (net) × 30%–60%
    (haircut depends on asset type:
     real estate: 60%–80%
     general manufacturing equipment: 30%–50%
     specialised industrial equipment: 10%–30%
     leasehold improvements: 0%–10%)

  + Goodwill × 0%
    (zero recovery — no standalone value)

  + Intangible Assets × 0%–20%
    (patents/IP with licensing value: 10%–20%
     customer lists / trade names: 0%–10%
     capitalised software: 0%–5%)

  + Investments & Other × case-by-case
```

**Haircut source:** These ranges reflect standard distressed lending practice and are consistent with ABL (asset-based lending) advance rate conventions used by commercial banks. They are not published by S&P or Moody's in a single table but are consistent with recovery rate research published by both agencies across default studies.

**What LLM must extract for Formula 2:**
- PP&E composition by asset type (from PP&E Footnote — real estate vs equipment vs leasehold improvements) — required to select appropriate haircut
- Inventory type (from Inventory Footnote or Note 1 — raw materials vs WIP vs finished goods) — affects collectibility
- Intangible asset composition (from Intangibles Footnote — patents vs customer relationships vs trade names vs software) — required to apply non-zero haircut where appropriate

---

## Where it lives

**Formula 1 inputs — Balance Sheet (Phase 2):**

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Total Assets | Balance Sheet — bottom of asset section | "Total assets" — required GAAP subtotal | 10-K and 10-Q |
| Goodwill | Balance Sheet — Non-Current Assets | "Goodwill" — separate line item | 10-K and 10-Q |
| Intangible Assets (net) | Balance Sheet — Non-Current Assets | "Intangible assets, net" or "Other intangible assets, net" | 10-K and 10-Q |
| Deferred Tax Asset | Balance Sheet — Non-Current Assets | "Deferred tax assets" or "Deferred income taxes" | 10-K and 10-Q |
| Total Debt | See LEVERAGE.md → Section "Where it lives" → Formula 1 table — all debt line item locations identical | Balance Sheet — Current and Non-Current Liabilities | 10-K and 10-Q |

**Formula 2 inputs — Footnotes (Phase 3 LLM):**

| Input | Document | Section | Available In |
|---|---|---|---|
| PP&E composition by asset type | PP&E Footnote (Note 4–7) | Asset category table showing land, buildings, equipment, leasehold separately with gross and accumulated depreciation | 10-K primarily; abbreviated in 10-Q |
| Inventory type breakdown | Inventory Footnote or Note 1 | "Inventories consist of raw materials ($X), WIP ($X), finished goods ($X)" | 10-K primarily |
| Intangible asset composition | Intangibles Footnote (Note 5–8) | Table of finite-lived and indefinite-lived intangibles by type with carrying values | 10-K primarily |
| Secured debt collateral description | Debt Footnote (Note 5–9) | Description of assets pledged as collateral — "The term loan is secured by substantially all assets of the Company" or specific asset descriptions | 10-K and 10-Q |

**Secured debt collateral — most important Phase 3 location:**

The debt footnote's collateral description identifies which assets are encumbered by secured debt. This is essential for assessing unsecured bondholder recovery. LLM should extract: which assets are pledged, to which debt instruments, and whether the pledge is a first lien or second lien. "Substantially all assets" pledges — common in leveraged loans — effectively leave nothing for unsecured holders.

---

## Structured or Unstructured

| Input / Component | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|
| **Total Assets** | `us-gaap:Assets` | Structured — required GAAP subtotal; virtually always tagged | Most reliable balance sheet tag. Almost never absent. |
| **Goodwill** | `us-gaap:Goodwill` | Structured — reliably tagged | Consistently present for companies with acquisition history. If null: company has no goodwill — treat as zero; no flag needed. |
| **Intangible Assets (net)** | Primary: `us-gaap:IntangibleAssetsNetExcludingGoodwill` Fallback: sum of finite and indefinite-lived components | Structured — reliably tagged | Fallback required when company separates finite and indefinite-lived intangibles. Sum both components. |
| **Deferred Tax Asset** | `us-gaap:DeferredTaxAssetsLiabilitiesNet` | Structured — tagged; may be negative (net liability) | If negative: company has net deferred tax liability — set to zero for tangible asset calculation (liability side handled in total assets already). |
| **Total Debt** | See LEVERAGE.md → Section "Formula" → Formula 1 outputs — reuse stored value; no re-extraction needed. | Structured — already extracted | No re-extraction needed. |
| **Tangible Asset Coverage** (derived) | No tag | Structured inputs, derived result | = (Total Assets − Goodwill − Intangibles − DTA) / Total Debt. Null propagation: if Total Assets null → null; if Total Debt null → null; if any deduction null → compute without that deduction and flag. |
| **PP&E composition by type** | No standard tag at category level | **Semi-structured — XBRL dimensional; unreliable** | PP&E is tagged in total (`us-gaap:PropertyPlantAndEquipmentNet`) but category-level breakdown (land, buildings, equipment) uses dimensional tags that are inconsistently populated. LLM extraction from PP&E Footnote table is more reliable for Formula 2 haircut application. |
| **Inventory type breakdown** | `us-gaap:InventoryRawMaterials`, `us-gaap:InventoryWorkInProcess`, `us-gaap:InventoryFinishedGoods` | Semi-structured — component tags exist; not always used | When component tags present: use for haircut differentiation. When absent: use aggregate inventory with blended 50% haircut. |
| **Intangible asset composition by type** | No standard tag at type level | **Unstructured — LLM required** | Intangibles Footnote table lists types (patents, customer relationships, trade names, software) with carrying values. LLM extracts per-type values for differentiated haircut application. |
| **Secured debt collateral description** | No tag | **Unstructured — LLM required** | Debt Footnote prose. LLM extracts: pledged assets, instrument, lien priority. Critical for unsecured holder recovery assessment. |
| **Liquidation-Adjusted Coverage** (derived F2) | No tag | Unstructured inputs + deterministic haircut computation | LLM extracts asset composition; system applies haircut table deterministically; result is a computed range (low and high haircut scenarios). |

---

## Extraction Fallback Logic

**Total Assets, Goodwill, Intangible Assets — incremental inputs only:**

```
Total Assets:
Step 1: us-gaap:Assets — primary; virtually always present
Step 2: Derive = us-gaap:AssetsCurrent
               + us-gaap:AssetsNoncurrent
        Flag: "total assets derived from current
        and non-current subtotals"
Step 3: Null → flag extraction failure

Goodwill:
Step 1: us-gaap:Goodwill
Step 2: If null AND company has made acquisitions
        (visible from prior filings or news):
        Flag: "goodwill absent — verify whether
        company has any acquisition history;
        if yes, tag may be missing"
Step 3: If null AND no acquisition history:
        Set Goodwill = 0; no flag needed

Intangible Assets:
Step 1: us-gaap:IntangibleAssetsNetExcludingGoodwill
Step 2: Sum us-gaap:FiniteLivedIntangibleAssetsNet
          + us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill
        Flag: "intangibles summed from components"
Step 3: If all null AND company is technology,
        pharma, or consumer brands:
        Flag: "intangible assets not tagged —
        material for this issuer type; verify
        balance sheet presentation"
        Escalate to LLM for balance sheet reading
Step 4: If null AND industrial/commodity company:
        Set to 0; no flag needed

Deferred Tax Asset:
Step 1: us-gaap:DeferredTaxAssetsLiabilitiesNet
Step 2: us-gaap:DeferredTaxAssetsNet
Step 3: If null: set to 0 with flag
        "DTA not separately tagged — tangible
        asset coverage may be marginally overstated"
        DTA is typically small relative to total
        assets; zero assumption is acceptable
```

**Total Debt:** See LEVERAGE.md → Section "Extraction Fallback Logic" → Inputs 1 through 4 (Short-Term Borrowings, Current LT Debt, Long-Term Debt, Total Debt derived) — apply identical fallback chains including double-count check and finance lease contamination flag.

**Tangible Asset Coverage null propagation:**
```
If Total Assets null → both ratios null
If Total Debt null → both ratios null
If Goodwill null AND technology/pharma issuer:
   Compute total coverage only; flag tangible
   coverage as "incomplete — goodwill not
   extracted; tangible coverage may be overstated"
If Intangibles null AND intangible-heavy issuer:
   Same treatment as Goodwill above
```

---

## Stress Threshold

Asset coverage thresholds vary significantly by asset composition. The same ratio means different things for a real estate company (assets are land and buildings with high liquidation value) versus a software company (assets are primarily goodwill and intangibles with near-zero liquidation value).

---

**Dimension 1 — Total Asset Coverage (broad solvency screen)**

Source: General credit analysis convention. No single published rating agency table — these thresholds reflect the level at which book value assets fail to cover total debt, a basic insolvency signal.

| Total Assets / Total Debt | Interpretation | Alert Level |
|---|---|---|
| ≥ 2.0x | Ample asset base relative to debt | No alert |
| 1.5x – 2.0x | Adequate | Watch |
| 1.2x – 1.5x | Thin — limited buffer | Flag |
| 1.0x – 1.2x | Very thin — assets barely cover debt at book | Stress |
| < 1.0x | Book value insolvent — assets insufficient to cover debt | Critical |

---

**Dimension 2 — Tangible Asset Coverage (primary credit signal)**

Tangible asset coverage is more credit-analytically relevant because it removes goodwill and intangibles that typically have minimal recovery value in distress.

| Tangible Assets / Total Debt | Interpretation | Alert Level |
|---|---|---|
| ≥ 1.5x | Strong tangible backing | No alert |
| 1.0x – 1.5x | Adequate tangible coverage | Watch |
| 0.7x – 1.0x | Below parity — intangibles dominating balance sheet | Flag |
| 0.4x – 0.7x | Weak — limited tangible recovery for creditors | Stress |
| < 0.4x | Very weak — creditors primarily relying on earnings, not assets | Critical |

**Sector calibration:** For asset-light sectors (technology, software, professional services) tangible asset coverage below 0.4x is structurally normal — these companies have few tangible assets by design. Apply the following adjustments:

| Sector | Adjust Tangible Coverage Thresholds By |
|---|---|
| Technology / Software / SaaS | Increase Flag threshold to 0.3x; Stress to 0.15x; Critical to 0.05x |
| Pharma / Biotech | Increase Flag to 0.3x; patents may have meaningful value — use F2 |
| Consumer brands / Media | Flag at 0.35x — brand value partially captured in intangibles |
| Industrials / Manufacturing | Standard thresholds apply — tangible assets material |
| Utilities / Infrastructure | Standard thresholds apply; real estate and plant dominant |
| Retail | Standard thresholds; inventory quality matters — cross-reference inventory haircut |

---

**Dimension 3 — Liquidation-Adjusted Coverage (Formula 2, Phase 3)**

This is the most credit-analytically precise output but requires LLM-extracted asset composition.

```
Compute two scenarios:

Conservative scenario (lower haircuts):
   Apply lower bound of each haircut range
   Flag if Conservative_Coverage < 0.5x: Stress
   Flag if Conservative_Coverage < 0.3x: Critical

Base scenario (midpoint haircuts):
   Apply midpoint of each haircut range
   Flag if Base_Coverage < 0.7x: Flag
   Flag if Base_Coverage < 0.5x: Stress
   Flag if Base_Coverage < 0.3x: Critical

Report as range: "Liquidation coverage estimated
at [conservative]x to [base]x depending on
asset realisation assumptions"

Never report a single liquidation coverage figure
without noting the scenario assumptions — the
haircut selection is judgmental and the range
is the honest output.
```

---

**Dimension 4 — Secured vs Unsecured Coverage Split (Phase 3)**

| Condition | Alert Level |
|---|---|
| Secured debt > tangible assets pledged as collateral | Stress — secured creditors are undercollateralised; recovery risk for all creditors |
| "Substantially all assets" pledged to secured lenders AND unsecured debt > 20% of total debt | Flag — unsecured holders have minimal asset recovery prospect |
| Liquidation coverage < 1.0x for secured debt alone | Critical — secured creditors face losses; unsecured holders have no recovery |

---

**Dimension 5 — Trend (applies to all dimensions)**

| Trend Condition | Alert Level |
|---|---|
| Any coverage ratio declining for 3 consecutive quarters | Watch regardless of absolute level |
| Tangible coverage declining AND leverage rising simultaneously | Flag — equity eroding from both sides; See LEVERAGE.md → Section "Stress Threshold" → Step 3 (Alert Trigger Rules) — apply dual-metric escalation rule when Asset Coverage declining and Leverage rising in same period |
| Total coverage approaching 1.0x from above | Flag — trajectory toward technical insolvency |

---

## Signal Timing

**Lagging — balance sheet measure with limited early warning capability.**

Asset coverage is a stock measure computed from balance sheet values that change slowly. It is the most lagging of all metrics in this spec — typically confirming stress that has already been signalled by FCF compression, coverage deterioration, and leverage deterioration over multiple prior quarters. It rarely provides early warning.

The exception is rapid balance sheet deterioration from large impairment charges — when a company writes down goodwill or intangibles materially, tangible asset coverage improves while total coverage collapses. This pattern (falling total coverage with stable or improving tangible coverage) signals that the company has recognised that its intangible assets were overvalued — itself a credit stress signal. See LOSS_PROVISIONS.md → Section "Signal Timing" → Signal Mode 2 (Sudden Adverse Event) — impairment charges follow similar sudden-event detection pattern; 8-K Item 2.05 triggers immediate recomputation of asset coverage.

**Filing lag:** See LEVERAGE.md → Section "Signal Timing" → Three-Tier Timing Structure table — apply identical Tier 1 filing lag; balance sheet items update only at filing dates. No intra-quarter updates.

**Most useful analytical application:** Asset coverage is least useful as a standalone early warning signal and most useful as a distress severity assessment tool — when other metrics have already flagged stress, asset coverage tells you how much recovery creditors can expect in a default scenario. It is the answer to "how bad could it get?" rather than "is stress developing?"

---

## Frequency

Updates quarterly via 10-Q and annually via 10-K — same schedule as all balance sheet metrics. Formula 1 inputs (Total Assets, Goodwill, Intangibles, Total Debt) all update at each quarterly filing.

Formula 2 (liquidation-adjusted) updates annually at 10-K when PP&E footnote, Inventory footnote, and Intangibles footnote are fully disclosed. Between annual filings, the prior 10-K asset composition is retained with a flag: "liquidation haircut applied to prior 10-K asset composition — verify no material asset disposals or acquisitions since [date]."

**Event-driven updates:** See DEBT_MATURITY_WALL.md → Section "Frequency" → 8-K Item 1.01 processing — apply similar rolling schedule patch logic to asset coverage when material asset disposals are confirmed via 8-K; update Formula 1 balance sheet figures. Formula 2 cannot be updated intra-quarter without LLM re-extraction of the asset composition footnotes.

**Phase 2:** Compute Formula 1 (Total and Tangible Asset Coverage) from XBRL quarterly. Apply Dimensions 1 and 2 thresholds. No liquidation adjustment.

**Phase 3:** Add Formula 2 liquidation-adjusted coverage using LLM-extracted asset composition from PP&E, Inventory, and Intangibles footnotes annually. Add Dimension 3 and 4 thresholds. Add secured collateral analysis from Debt Footnote. Add impairment charge cross-referencing.

