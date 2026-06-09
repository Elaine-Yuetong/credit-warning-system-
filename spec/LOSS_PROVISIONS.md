# Loss Provisions / Litigation Contingencies

---

## What it is

Loss provisions and litigation contingencies measure the financial obligations a company has recognised — or is required to disclose but has not yet recognised — arising from legal disputes, regulatory actions, environmental liabilities, product liability claims, and other contingent events. They answer two related questions: *"how much has this company already set aside for known losses?"* and *"what additional losses might it face that have not yet been quantified on the balance sheet?"*

The metric covers two distinct but related disclosures that appear in the same section of the financial statements:

**Loss provisions** are amounts the company has already recorded on the balance sheet as liabilities because a loss is probable and the amount is reasonably estimable under ASC 450 (the US GAAP standard governing loss contingencies). They represent confirmed financial obligations that will require cash outflow — the timing and exact amount may be uncertain, but the liability is real and has already reduced equity through a charge to the income statement.

**Litigation contingencies** are potential losses the company has disclosed but not recorded because either the loss is not yet probable, or the amount cannot be reasonably estimated, or both. Under ASC 450, companies must disclose material contingencies even when they cannot record them. These disclosed-but-unrecorded contingencies represent financial risks that are invisible on the balance sheet but visible in the footnotes — and can be substantially larger than the recorded provisions.

The distinction matters enormously for credit analysis. A $500M recorded provision reduces equity and appears in financial ratios. A $500M unrecorded contingency described as "reasonably possible" does not appear in any ratio — it exists only in the footnote text and requires the LLM layer to detect and flag. This is the central extraction challenge of this metric and the primary reason it is classified as Phase 3 LLM-heavy.

This metric differs from all prior metrics in one fundamental way: it is not a ratio that crosses a threshold. There is no formula that produces a number comparable across companies. The signal is the existence, size, direction, and language of provisions and contingencies — whether they are growing, whether the company is describing them with increasing hedging language, whether large unquantified contingencies are being disclosed for the first time, and whether provision coverage ratios suggest the recorded amounts are inadequate for the underlying exposure.

---

## Why it signals stress

**Mechanism 1 — The cash drain (direct financial impact).**
When a provision is recognised, it reduces current period earnings immediately. When it is paid — typically in a subsequent period when litigation settles or a regulatory penalty is assessed — it drains cash from operations. Large provisions flowing through the income statement reduce EBITDA, which deteriorates coverage and leverage ratios in the same quarter. A company with a $300M litigation provision in a quarter where EBITDA would otherwise have been $400M suddenly shows $100M EBITDA — coverage collapses and leverage appears to spike. This is not a business deterioration in the operational sense but it is a real financial event that your system will detect in the leverage and coverage metrics before it identifies the cause. The loss provisions metric provides the explanatory layer — it identifies whether a ratio deterioration is driven by a litigation charge versus an operational decline.

**Mechanism 2 — The unrecorded contingency cliff (most dangerous signal).**
Large litigation contingencies that are disclosed but not recorded represent potential sudden balance sheet events. A company disclosing "a reasonably possible loss of up to $2 billion" in its contingencies footnote is telling investors that its equity and liquidity could be materially impaired by a single adverse court decision — but this $2 billion appears nowhere in the leverage ratio, nowhere in the coverage ratio, and nowhere in the liquidity ratios. Your system's other metrics are blind to it. The litigation contingency footnote is the only place this risk is visible, and only the LLM layer can extract it. When a large unrecorded contingency resolves adversely, the company must record the provision immediately — producing a sudden, large, one-quarter hit to EBITDA, equity, and potentially liquidity.

**Mechanism 3 — The hedging language escalation signal.**
Companies are required by ASC 450 to use specific language to classify contingencies: "probable" triggers recording; "reasonably possible" triggers disclosure only; "remote" requires no disclosure. When a company's contingency language shifts from "remote" to "reasonably possible" or from "reasonably possible" to "probable" across consecutive filings, it is signalling that the underlying exposure is crystallising. This language progression is one of the most reliable early warning signals in unstructured filing data — it precedes the actual recording of a provision by 1–4 quarters. Only the LLM layer can detect and track this language shift.

**Mechanism 4 — The provision coverage ratio deterioration.**
When a company's recorded provisions grow faster than its resolution of prior provisions — meaning it is adding to the litigation reserve faster than it is settling cases — it signals an escalating legal exposure. Conversely, when provisions are being released (reversed because cases were resolved more favourably than expected), it suggests the litigation environment is improving. Tracking provision balances over time reveals whether the company's legal situation is escalating or resolving.

**Mechanism 5 — Regulatory and environmental provisions — systemic risk signals.**
Regulatory fines and environmental remediation provisions carry particular systemic weight. A company facing a large regulatory action may also face changes to its business model, consent decree restrictions on operations, or reputational damage that impairs future revenue. These second-order effects are not captured in any other metric but are often foreshadowed in the contingencies footnote where the company must describe the nature of the regulatory action.

---

## Formula

Loss provisions and litigation contingencies do not produce a single ratio. The metric produces a set of extracted values and a qualitative assessment. There are three quantitative outputs and two qualitative outputs.

---

**Quantitative Output 1 — Total Recorded Provisions Balance**

```
Total_Provisions =
    Sum of all loss contingency liabilities
    recorded on the balance sheet

This includes:
   Legal / litigation reserves
   Environmental remediation reserves
   Regulatory penalty reserves
   Product liability reserves
   Warranty reserves (if material to credit
   analysis — typically excluded for most
   non-manufacturing issuers)

Source: Balance sheet (current and non-current
        contingent liabilities) + Loss Contingency
        Footnote
XBRL tag (partial): us-gaap:LossContingencyAccrualAtCarryingValue
                 OR us-gaap:LiabilityForUncertainTaxPositions
                    (for tax contingencies — separate from
                    litigation; flag if included)

Units: millions USD
Trend: track quarter-over-quarter change
       Rising provisions: stress signal
       Falling provisions: resolution signal
       (may also mean adverse settlements consuming reserves)
```

---

**Quantitative Output 2 — Provision Income Statement Impact**

```
Provision_Charge_Current_Period =
    New provisions added in current period
    (distinguished from prior period balance)

Source: Loss Contingency Footnote roll-forward table
        OR income statement line item
XBRL tag: us-gaap:LossContingencyAccrualProvision
          (if tagged — often not)

This output answers: how much did litigation
charges affect this quarter's EBITDA?
Provides the explanatory link between a
sudden EBITDA decline and a legal event.
```

---

**Quantitative Output 3 — Maximum Unrecorded Contingency Exposure**

```
Max_Contingency_Exposure =
    Largest disclosed "reasonably possible"
    loss amount that has NOT been recorded
    as a provision

Source: Contingencies Footnote — unstructured prose
        Requires LLM extraction
        No XBRL tag exists

Typical disclosure language:
"The Company believes it is reasonably possible
that losses could range from $X million to
$Y million in excess of the amounts accrued."
OR
"While it is not possible to estimate the
range of potential loss, the Company believes
the outcome could have a material adverse
effect on its financial condition."

LLM extracts:
   (a) Quantified maximum exposure if stated
   (b) Whether described as "material" without
       quantification — flag separately
   (c) Number of unquantified material contingencies
```

---

**Qualitative Output 1 — Language Classification**

```
For each material contingency disclosed:
LLM classifies the company's own language:

Tier 1 — Remote: no financial impact expected
Tier 2 — Reasonably possible, quantified range
Tier 3 — Reasonably possible, no range given,
          described as potentially material
Tier 4 — Probable, amount not yet estimable
Tier 5 — Probable, amount estimable — provision recorded

Language shift tracking:
   Compare classification for each named
   contingency across consecutive filings.
   Downgrade (Tier 1 → Tier 2 → Tier 3):
   escalating risk — early warning signal
   Upgrade (Tier 3 → Tier 1):
   risk resolving — positive signal

This is the most valuable output of this
metric and the primary use case for Phase 3
LLM extraction.
```

---

**Qualitative Output 2 — New Material Contingency Detection**

```
For each filing, LLM identifies:
   Are any material contingencies being
   disclosed for the first time that were
   not present in the prior filing?

New material contingency in current filing
that was absent from prior filing:
   Flag immediately regardless of tier
   "New material contingency disclosed —
   [description]; not present in prior filing;
   monitor for tier escalation"

This requires comparing current filing
extraction to stored prior filing extraction —
a cross-period comparison capability that
is unique to this metric.
```

---

**No stress threshold ratio.** Unlike all prior metrics, there is no universal threshold (e.g. provisions > X% of EBITDA = Flag) that generalises across companies. The thresholds are covered in the Stress Threshold section and are primarily relative — provisions growing faster than earnings, unrecorded contingencies exceeding available liquidity, language shifting toward higher tiers.

---

## Where it lives

---

**Document hierarchy for loss provisions and contingency information**

Contingency information is distributed across more locations than any other metric in this spec. Unlike debt covenants (primarily in one footnote) or financial ratios (on the face of financial statements), loss provisions appear in up to six locations with varying levels of detail and accessibility.

| Document | What It Contains | Accessibility | Phase |
|---|---|---|---|
| Balance Sheet | Recorded provision balances (current and non-current) | Highest — face of financial statements | Phase 2 (partial XBRL) |
| Loss Contingency / Legal Proceedings Footnote | Roll-forward of provision balances; descriptions of individual legal matters; language classifications | High — standardised footnote location | Phase 3 LLM |
| Commitments and Contingencies Footnote | Sometimes combined with Loss Contingency; unrecorded contingencies disclosed here | High | Phase 3 LLM |
| MD&A — Legal Proceedings / Risk Factors | Management narrative on material legal matters; sometimes more current than footnote | Medium — narrative prose | Phase 3 LLM |
| Item 3 — Legal Proceedings (10-K only) | Required disclosure of material legal proceedings; brief descriptions | Medium — standardised location | Phase 3 LLM |
| 8-K Item 8.01 / Item 1.01 | New material legal developments disclosed between quarterly filings | Low — event-driven; variable format | Phase 3 LLM |

---

**Location 1 — Balance Sheet (Phase 2)**

| Input | Financial Statement | Exact Line Item | Available In |
|---|---|---|---|
| Current litigation / contingency reserves | Balance Sheet — Current Liabilities | "Accrued litigation," "Legal reserves," "Contingent liabilities — current," or bundled into "Accrued liabilities and other" | 10-K and 10-Q |
| Non-current litigation / contingency reserves | Balance Sheet — Non-Current Liabilities | "Litigation reserves," "Environmental remediation obligations," "Contingent liabilities — non-current" | 10-K and 10-Q |
| Total recorded provisions | Balance Sheet | Sum of current and non-current contingency lines | 10-K and 10-Q |

**Critical limitation of balance sheet extraction:** Many companies bundle litigation reserves into aggregated line items — "Accrued liabilities and other current liabilities" — without separately disclosing the litigation component on the face of the balance sheet. When this occurs the balance sheet provides no usable signal and the entire extraction depends on the Loss Contingency Footnote. This is the most common Phase 2 failure mode for this metric.

---

**Location 2 — Loss Contingency / Legal Proceedings Footnote (Phase 3 primary)**

| Field | Detail |
|---|---|
| Where it lives | Notes to Financial Statements — typically Note 10–16 in 10-K, Note 7–12 in 10-Q. Titled "Commitments and Contingencies," "Legal Proceedings," "Loss Contingencies," or "Contingencies and Litigation" |
| Available in | 10-K (comprehensive); 10-Q (abbreviated — usually updated for material developments only) |
| Exact location within footnote | The footnote typically contains: (1) a general statement of accounting policy for loss contingencies referencing ASC 450; (2) descriptions of individual material legal matters by name or category; (3) provision balance and roll-forward if material; (4) the language classification (probable/reasonably possible/remote) for each matter; (5) quantified or unquantified exposure range if disclosable |
| What LLM should extract | For each named legal matter: (a) name or description of the matter, (b) language classification per ASC 450, (c) recorded provision amount if any, (d) disclosed exposure range if stated, (e) whether described as potentially material without quantification, (f) case status (pending, settled, appealed), (g) whether new in this filing vs previously disclosed |
| Roll-forward table location | If a provision roll-forward table is present (beginning balance + additions + payments + reversals = ending balance), it is typically at the beginning of the footnote before the individual matter descriptions. LLM should extract the roll-forward separately from individual matter descriptions |

---

**Location 3 — Item 3: Legal Proceedings (10-K only)**

| Field | Detail |
|---|---|
| Where it lives | Part I, Item 3 of the 10-K — a separate required section titled "Legal Proceedings" distinct from the financial statement footnotes |
| Available in | 10-K only — not in 10-Q (10-Q uses Part II, Item 1 "Legal Proceedings" for updates, but typically refers back to the 10-K for full descriptions) |
| Exact location | Immediately before the financial statements in the 10-K document structure. May cross-reference the footnote: "The information required by this item is incorporated by reference to Note [X] to the Consolidated Financial Statements." If incorporated by reference: no incremental information beyond the footnote. If separately described: may contain additional detail not in the footnote, particularly for regulatory matters |
| What LLM should extract | Any matter described in Item 3 that is absent from the footnote (unusual but possible). Any additional detail on quantification or case status not present in the footnote |

---

**Location 4 — MD&A (Phase 3 supplementary)**

| Field | Detail |
|---|---|
| Where it lives | MD&A — "Legal Proceedings," "Commitments and Contingencies," or "Liquidity and Capital Resources" subsections. Some companies address major litigation in their discussion of financial results when a charge has been taken |
| Available in | 10-K and 10-Q |
| Exact location | Variable — scan MD&A for litigation-related language. In 10-Q, the "Recent Developments" or "Subsequent Events" discussion may describe new legal matters that have not yet been formally disclosed in the footnote |
| What LLM should extract | Any litigation development described in MD&A that is more current or more detailed than the footnote disclosure. Particularly watch for: management commentary on the likelihood of settlement, characterisation of the company's legal strategy, and any mention of insurance coverage offsetting exposure |

---

**Location 5 — 8-K Filings (Phase 3 real-time)**

Material legal developments between quarterly filings may be disclosed via 8-K. These are the most time-sensitive disclosures and the primary source of intra-quarter loss provision signals.

| 8-K Item | When Used | Content |
|---|---|---|
| Item 8.01 (Other Events) | Most common for litigation updates | Adverse court decisions, large settlements, new regulatory investigations, EPA enforcement actions |
| Item 1.01 (Material Agreement) | Settlement agreements | Settlement terms, payment amounts, consent decree conditions |
| Item 2.05 (Material Impairment) | When provision triggers impairment | Provision amount, affected assets |
| Item 2.06 (Material Impairment) | Goodwill impairment triggered by litigation | Impairment amount |

**Keyword filter for 8-K monitoring:**
```
Always process:
   "litigation," "lawsuit," "settlement,"
   "judgment," "verdict," "regulatory,"
   "investigation," "enforcement," "penalty,"
   "fine," "consent decree," "indictment,"
   "class action," "environmental," "remediation"

Process if issuer already flagged:
   "legal proceedings," "contingency,"
   "accrual," "reserve," "material adverse"
```

---

**Location 6 — Subsequent Events Footnote**

| Field | Detail |
|---|---|
| Where it lives | Last footnote in the financial statements — typically "Subsequent Events" or "Events After the Reporting Period" |
| Available in | 10-K primarily; 10-Q for material post-period events |
| What LLM should extract | Any litigation settlement, adverse judgment, or new regulatory action that occurred after the balance sheet date but before the filing date. These are particularly important because they represent confirmed financial impacts that are not yet in any ratio but will appear in the next period's financials |

---

## Structured or Unstructured

This metric has the lowest proportion of structured XBRL content and the highest proportion of LLM-dependent extraction of any metric in the spec. Phase 2 can extract only aggregate balance sheet provision balances — and even those are frequently bundled into non-specific line items. The entire analytical content of this metric — individual matter descriptions, language classifications, unrecorded contingency amounts, provision roll-forwards — is unstructured and Phase 3 only.

| Input / Component | XBRL Tag | Structured or Unstructured | Notes |
|---|---|---|---|
| **Current contingency / litigation reserves** | Primary: `us-gaap:LossContingencyAccrualAtCarryingValue` Fallback: `us-gaap:AccruedLiabilitiesCurrent` (bundled — unreliable) | **Semi-structured — tag exists but population inconsistent; often bundled** | Tag exists in taxonomy but many companies do not tag separately — bundle into accrued liabilities. If primary tag null AND no separate balance sheet line item: extraction fails for Phase 2; entire metric deferred to Phase 3 LLM. |
| **Non-current contingency reserves** | `us-gaap:LossContingencyAccrualNoncurrent` | **Semi-structured — same population issues as current** | Same bundling problem. Flag if absent but accrued liabilities line is material: "non-current contingency reserves may be bundled — Phase 3 LLM extraction required for disaggregation." |
| **Provision charge (current period)** | `us-gaap:LossContingencyAccrualProvision` | **Semi-structured — rarely tagged** | Populated by fewer filers than the balance sheet tags. When absent: LLM must extract from roll-forward table in footnote. |
| **Provision payments (current period)** | `us-gaap:LossContingencyAccrualPaymentsMade` | **Semi-structured — rarely tagged** | Same as provision charge — LLM fallback required. Used to compute net change in provision balance. |
| **Provision roll-forward (complete)** | No standard tag for full roll-forward | **Unstructured — LLM required** | The beginning balance, additions, payments, reversals, ending balance table lives in the Loss Contingency Footnote as an HTML table. LLM extracts all five line items. Available in 10-K; sometimes abbreviated in 10-Q. |
| **Individual legal matter descriptions** | No tag | **Unstructured — LLM required** | Prose descriptions in Loss Contingency Footnote. LLM extracts: matter name, status, language classification, exposure range. Core analytical content of this metric. |
| **Language classification (probable / reasonably possible / remote)** | No tag | **Unstructured — LLM required** | LLM identifies ASC 450 language from footnote text. Most valuable extraction — enables tier escalation tracking across filings. |
| **Unrecorded contingency maximum exposure** | No tag | **Unstructured — LLM required** | Dollar amount (if disclosed) extracted from contingency footnote prose. Frequently stated as a range; sometimes described as "material" without quantification. |
| **New contingency detection (vs prior filing)** | No tag | **Unstructured — LLM required + cross-period comparison** | Requires comparing current filing LLM extraction to stored prior filing extraction. Unique to this metric — no other metric requires cross-period comparison for signal generation. |
| **Settlement agreements** | No tag | **Unstructured — LLM required** | From 8-K Item 1.01 or subsequent events footnote. LLM extracts settlement amount, payment schedule, and any operational restrictions from consent decrees. |
| **Insurance coverage offset** | No tag | **Unstructured — LLM required** | MD&A or contingency footnote may describe insurance recoveries expected to offset recorded provisions. LLM extracts offset amount and certainty of recovery. Reduces net exposure. |
| **Regulatory investigation disclosures** | No tag | **Unstructured — LLM required** | 8-K Item 8.01 or Item 3 / Note disclosures. LLM extracts: regulator name, investigation subject, estimated penalty range if disclosed. |
| **Environmental remediation reserves** | `us-gaap:AccrualForEnvironmentalLossContingencies` | **Semi-structured — tagged for industrial, energy, chemical issuers; absent for others** | Standard tag exists. Reliable for heavy industry issuers where environmental liability is material. For service, technology, and financial issuers: assume zero if tag absent. |

---

**Quick Reference — Structured vs Unstructured Summary**

| Category | Items | Method | Phase |
|---|---|---|---|
| **Semi-structured (XBRL, inconsistent population)** | Current and non-current provision balance, provision charge, provision payments, environmental reserves | XBRL — attempt first; LLM fallback when bundled or absent | Phase 2 (attempt) / Phase 3 (complete) |
| **Fully unstructured (LLM required)** | Provision roll-forward, individual matter descriptions, language classification, unrecorded exposure, new matter detection, settlement terms, insurance offset, regulatory disclosures | LLM — Loss Contingency Footnote, MD&A, Item 3, 8-K | Phase 3 |
| **Cross-period comparison (unique to this metric)** | New matter detection vs prior filing | LLM + stored prior extraction | Phase 3 |

---


## Extraction Fallback Logic — Loss Provisions / Litigation Contingencies

---

**Design Principles**

Three additional rules beyond the universal four apply specifically to this metric:

**Rule 5 — Absence of extraction is not absence of risk.** A null result from all XBRL tags does not mean the company has no litigation exposure. It means the balance sheet presentation bundles provisions into aggregated line items. For any issuer where the Loss Contingency Footnote exists (confirmed by LLM), the metric is not null — it is Phase 3 pending. Flag clearly: "provision balance not extractable from XBRL — Phase 3 LLM extraction required; do not interpret as zero exposure."

**Rule 6 — Language classification takes priority over quantification.** A company disclosing an unquantified "reasonably possible material loss" is signalling more credit risk than a company with a small quantified provision. When dollar amounts are unavailable, the language tier classification is the primary signal. Never suppress a language-based alert because a dollar amount could not be extracted.

**Rule 7 — Cross-period comparison is required for new matter detection.** This is the only metric where the extraction logic explicitly requires comparing the current filing's LLM output to the stored prior filing's output. The system must maintain a per-issuer matter registry — a structured record of all previously disclosed contingencies — and check each new filing against it to detect new disclosures.

---

**Input 1 — Recorded Provision Balance (Phase 2 attempt)**

```
Step 1 — Try XBRL primary tag:
   us-gaap:LossContingencyAccrualAtCarryingValue
   If non-null: use as current recorded provision
   Log: "provision balance from XBRL primary tag"

Step 2 — If null, try environmental sub-tag
   (for industrial, energy, chemical issuers):
   us-gaap:AccrualForEnvironmentalLossContingencies
   If non-null: store separately as environmental
   reserve; flag: "only environmental component
   extracted — other litigation provisions
   may be bundled; Phase 3 required for complete
   picture"

Step 3 — If both null:
   Scan balance sheet current liabilities for
   any line item containing keywords:
   "litigation," "legal," "contingent,"
   "reserve," "accrued legal"
   via XBRL label search (not value search)
   If found: extract associated value
   Flag: "provision balance from labelled
   balance sheet line — verify not bundled
   with other accruals"

Step 4 — If all structured attempts fail:
   Set Provision_Balance = null (Phase 2)
   Flag: "provision balance not extractable
   from XBRL — balance sheet bundles
   contingencies into accrued liabilities;
   Phase 3 LLM required"
   Do NOT set to zero
   Do NOT suppress metric — Phase 3 will
   complete extraction from footnote

Step 5 — Non-current component:
   Try: us-gaap:LossContingencyAccrualNoncurrent
   If found: add to current component for total
   If null: total = current component only
   Flag if non-current absent: "non-current
   provision component not separately tagged —
   total may be understated"
```

---

**Input 2 — Provision Roll-Forward (Phase 3 LLM)**

```
Step 1 — LLM reads Loss Contingency Footnote.
   Locate roll-forward table with structure:
   Beginning balance: $X
   Additions (new provisions): $X
   Payments / settlements: ($X)
   Reversals: ($X)
   Ending balance: $X

Step 2 — Extract all five line items.
   Verify: Beginning + Additions − Payments
           − Reversals = Ending
   If does not balance: flag discrepancy
   "Roll-forward does not balance — verify
   LLM extraction accuracy"

Step 3 — If no roll-forward table present:
   LLM derives from two period balance sheet
   values:
   Net_Change = Ending Balance − Beginning Balance
   Flag: "roll-forward not disclosed — net
   change only; additions and payments not
   separately identifiable"

Step 4 — If 10-Q shows abbreviated disclosure
   ("no material changes since [10-K date]"):
   Use prior 10-K roll-forward as baseline
   Flag: "10-Q provides no roll-forward update —
   using 10-K baseline; material changes
   may have occurred"
```

---

**Input 3 — Individual Matter Language Classification (Phase 3 LLM)**

```
Step 1 — LLM reads entire Loss Contingency
   Footnote and Item 3 Legal Proceedings.
   For each named or described legal matter:

   Extract structured record:
   {
     "matter_id": "auto-generated hash or
                   first 50 chars of description",
     "matter_name": "company's label if given",
     "description": "brief LLM summary (2-3 sentences)",
     "language_tier": 1-5 (per tier classification
                     in Formula section),
     "language_quote": "verbatim sentence or phrase
                        that determines tier",
     "recorded_provision": X or null,
     "exposure_range_low": X or null,
     "exposure_range_high": X or null,
     "exposure_unquantified_material": true/false,
     "case_status": "pending/settled/appealed/other",
     "first_disclosed": "YYYY-QX" (filing when
                        first appeared),
     "filing_date": "YYYY-MM-DD"
   }

Step 2 — If footnote is vague or uses boilerplate
   language without individual matter descriptions:
   Flag: "Loss Contingency Footnote is generic —
   no individual matters identified; company
   may have no material contingencies or may
   be providing minimum required disclosure"
   Store generic compliance statement if present:
   "We are subject to legal proceedings in
   the ordinary course of business" type language
   → Tier 1 classification; no alert
```

---

**Input 4 — Cross-Period Comparison (Phase 3 LLM)**

```
Step 1 — Load prior filing matter registry
   from stored extraction.
   Prior registry contains all matters from
   last 10-K plus any 10-Q updates.

Step 2 — For each matter in current extraction:
   Match to prior registry by matter_id or
   description similarity.
   LLM assists with fuzzy matching when
   descriptions use different phrasing
   across filings.

Step 3 — Classify each current matter:
   Existing — unchanged:
      Same matter, same tier, similar amount
      → No incremental alert
   Existing — escalated:
      Same matter, higher tier
      → Escalation alert: "matter [X]
      escalated from Tier [N] to Tier [M]"
   Existing — resolved:
      Matter present in prior, absent in current
      → Resolution signal: "matter [X] no
      longer disclosed — assumed resolved
      or settled"
   New — material:
      Present in current, absent in prior
      → New matter alert: "new material
      contingency disclosed for first time:
      [description]"
   New — immaterial:
      New generic disclosure, non-specific
      → Log only; no alert

Step 4 — Update matter registry with current
   filing extraction for use in next comparison.
```

---

**Input 5 — 8-K Intra-Quarter Detection (Phase 3)**

```
For any 8-K containing litigation keywords
(per keyword filter in Where it lives):

LLM reads full 8-K text and extracts:
   Event type: adverse judgment / settlement /
               new investigation / penalty /
               consent decree / other
   Amount: dollar value if disclosed
   Counter-party: plaintiff / regulator name
   Impact characterisation: company's own
      language on financial impact
   Whether previously disclosed in periodic
      filing or new development

System action:
   New adverse judgment / penalty > $50M:
      Immediate Flag alert regardless of
      prior provision balance
   New regulatory investigation disclosed:
      Watch alert; flag for Phase 3
      LLM extraction at next 10-Q
   Settlement confirmed:
      Update matter registry; resolve
      prior contingency flag if applicable
```

---

## Stress Threshold — Loss Provisions / Litigation Contingencies

---

**Threshold Framework**

Unlike all prior metrics, there is no universal graduated ratio threshold. The alert framework combines four signal types: magnitude relative to financial capacity, trend direction, language tier escalation, and new matter detection.

---

**Dimension 1 — Provision Balance as % of EBITDA**

This is the closest equivalent to a ratio threshold for this metric. It measures whether the recorded provision stock is material relative to earnings capacity. EBITDA denominator: See LEVERAGE.md → Section "Extraction Fallback Logic" → derived EBITDA value — use stored annual EBITDA (TTM preferred) as denominator; no re-extraction required.

| Provision Balance / Annual EBITDA | Interpretation | Alert Level |
|---|---|---|
| < 5% | Immaterial relative to earnings | No alert |
| 5% – 15% | Moderate — monitor trend | Watch |
| 15% – 30% | Material — earnings impact if provisions increase | Flag |
| 30% – 50% | High — multi-year earnings impact | Stress |
| > 50% | Severe — provisions threaten solvency | Critical |
| Provision balance rising for 3 consecutive quarters | Escalating litigation environment | Watch regardless of absolute level |

---

**Dimension 2 — Maximum Unrecorded Contingency Exposure vs Available Liquidity**

This is the most operationally critical threshold — it measures whether an adverse resolution of unrecorded contingencies could produce a liquidity crisis.

| Max Unrecorded Contingency / Available Liquidity | Interpretation | Alert Level |
|---|---|---|
| < 25% | Contingency manageable within liquidity | No alert |
| 25% – 50% | Meaningful — adverse resolution would strain liquidity | Watch |
| 50% – 100% | Significant — adverse resolution would severely stress liquidity | Flag |
| > 100% | Contingency exceeds available liquidity — potential solvency event | Critical |
| Unquantified "material" contingency with liquidity < $500M | Cannot size but could be existential | Stress — flag for manual review |

---

**Dimension 3 — Language Tier Escalation**

| Language Tier Change | Alert Level |
|---|---|
| Tier 1 → Tier 2 (remote → reasonably possible) | Flag — exposure crystallising |
| Tier 2 → Tier 3 (quantified → unquantified material) | Stress — uncertainty increasing |
| Tier 2 → Tier 4 (reasonably possible → probable, unestimable) | Stress — provision recording imminent |
| Tier 4 → Tier 5 (provision recorded) | Watch to Flag — confirms prior signal; now visible in ratios |
| Any tier → settlement / resolution | Positive — close monitoring |
| New Tier 3 matter (first disclosure, unquantified material) | Flag — unknown exposure introduced |
| New Tier 4 matter (first disclosure, probable unestimable) | Stress — provision recording imminent |

---

**Dimension 4 — Current Period Provision Charge vs EBITDA**

Large single-quarter provisions distort EBITDA and all EBITDA-dependent ratios. EBITDA denominator: See LEVERAGE.md → Section "Extraction Fallback Logic" → derived EBITDA value — use stored quarterly EBITDA; See INTEREST_COVERAGE.md → Section "Formula" → Formula 1 (EBIT) — flag when provision causes ratio deterioration in those metrics.

| Provision Charge / Quarterly EBITDA | Interpretation | Alert Level |
|---|---|---|
| < 5% | Immaterial to quarterly earnings | No alert |
| 5% – 20% | Moderate impact — EBITDA reduced but manageable | Watch |
| 20% – 50% | Material — leverage and coverage ratios distorted | Flag — See LEVERAGE.md → Section "Stress Threshold" → Step 3 (Alert Trigger Rules) and INTEREST_COVERAGE.md → Section "Stress Threshold" → Step 3 — append cause note to those metric alerts: "ratio deterioration litigation-driven — see LOSS_PROVISIONS.md alert for [period]" |
| > 50% | Severe — EBITDA dominated by provision charge | Stress — alert with note: "ratio deterioration litigation-driven; verify operational EBITDA separately" |
| Provision charge causes EBITDA negative | Automatic escalation | Critical |

**System rule for ratio distortion:** When a large provision charge causes deterioration in the Leverage or Coverage metrics: See LEVERAGE.md → Section "Stress Threshold" → Step 3 (Alert Trigger Rules) and INTEREST_COVERAGE.md → Section "Stress Threshold" → Step 3 — append to those metric alerts: "Ratio deterioration partially or wholly driven by litigation provision charge of $X million — operational EBITDA was $Y million excluding provision." This prevents the system from conflating a legal event with operational deterioration.

---

**Dimension 5 — Binary Critical Flags**

These conditions trigger Critical alerts regardless of dimensions 1–4:

| Condition | Alert |
|---|---|
| Regulatory investigation by DOJ, SEC, CFTC, or equivalent disclosed for first time | Critical — regulatory enforcement risk |
| Consent decree or deferred prosecution agreement entered | Critical — operational restrictions likely |
| Class action certified as class (not just filed) | Critical — exposure scope confirmed |
| Bankruptcy-related claim against the company disclosed | Critical |
| Environmental liability described as potentially requiring "substantial expenditure" without quantification | Stress — escalate to Critical if liquidity < $200M |

---

## Signal Timing — Loss Provisions / Litigation Contingencies

---

**Classification: Irregular and event-driven — the least predictable signal timing in the spec.**

Unlike all prior metrics whose signal timing is governed by the quarterly filing schedule, loss provisions and litigation contingencies generate signals at irregular intervals determined by external legal and regulatory events rather than accounting cycles. A company can have stable provisions for eight consecutive quarters and then face a sudden new regulatory investigation or adverse court decision that materially changes its risk profile within days. This makes this metric the most challenging to monitor systematically and the most dependent on 8-K real-time monitoring.

**Three distinct signal modes:**

**Mode 1 — Gradual escalation (quarterly filing driven):**
Language tier escalation and provision balance growth are detectable through quarterly filing analysis. The lead time in this mode is typically 2–6 quarters — a contingency progresses through tiers before a provision is recorded and before the provision is large enough to materially affect financial ratios. This is the most valuable early warning mode and is where the Phase 3 language tracking delivers its primary benefit.

**Mode 2 — Sudden adverse event (8-K driven):**
An adverse court verdict, a DOJ indictment, or a large regulatory fine arrives with no warning in the quarterly filing cycle. The signal appears in an 8-K within days of the event. The quarterly filing then confirms the financial impact 40–90 days later. In this mode the system has no lead time — it is detecting a concurrent event. The 8-K monitoring is the detection mechanism; the quarterly filing is the financial confirmation.

**Mode 3 — Silent accumulation (detected only at filing):**
Some litigation matters accumulate unreported between quarterly filings — a company may negotiate a settlement in month 2 of the quarter without filing an 8-K if it judges the matter immaterial. The settlement then appears in the next quarterly filing as a provision charge. In this mode the system has no intra-quarter visibility. This is the primary undetectable risk of the metric.

**Filing lag:** 40 days after quarter-end for 10-Q; 60 days for 10-K. Same as all periodic filing metrics. 8-K disclosures available within 4 business days of event. The gap between Mode 2 event occurrence and 8-K filing (up to 4 business days) is the minimum detection lag for real-time events.

**Interaction with EBITDA Margin Trend and Leverage:** When a large provision charge appears, it simultaneously triggers alerts in Loss Provisions, EBITDA Margin Trend, and Leverage/Coverage — See LEVERAGE.md → Section "Signal Timing", INTEREST_COVERAGE.md → Section "Signal Timing", and EBITDA_MARGIN_TREND.md → Section "Signal Timing" — cross-reference those metric alerts when provision charge is identified as cause; add correlation note to all affected metric outputs. The system should correlate these alerts and identify the common cause: "Leverage ratio deterioration in [period] attributed to $X million litigation provision charge — operational metrics unaffected." This cross-metric correlation is a Phase 3 capability requiring the LLM layer to identify the provision charge as a specific income statement item.

---

## Frequency — Loss Provisions / Litigation Contingencies

---

**Overview**

This metric has the most irregular update pattern of any metric in the spec — combining scheduled quarterly updates with unpredictable event-driven updates.

**Scheduled updates:**

| Filing | Update Type | Phase |
|---|---|---|
| 10-K (annual) | Full LLM extraction: complete matter registry refresh, roll-forward, language classification for all matters, cross-period comparison vs prior 10-K | Phase 3 |
| 10-Q (quarterly) | Partial LLM extraction: update for material developments since prior filing; abbreviated footnote; cross-period comparison vs prior quarter | Phase 3 |
| 10-Q abbreviated disclosure | If company states "no material changes" in contingencies footnote: confirm statement; no alert change; log confirmation | Phase 3 |

**Event-driven updates:**

| Event | Channel | Phase | Action |
|---|---|---|---|
| Adverse court judgment | 8-K Item 8.01 | Phase 3 (Phase 2 keyword monitor for flagged issuers) | Immediate LLM extraction; amount and matter identification; escalate alert |
| Settlement agreement | 8-K Item 1.01 | Phase 3 | Extract settlement terms; resolve prior matter in registry; flag cash payment timing |
| New regulatory investigation | 8-K Item 8.01 | Phase 3 | Immediate Critical flag; add to matter registry as new Tier 2–3 matter |
| Consent decree / DPA | 8-K Item 1.01 or 8.01 | Phase 3 | Critical flag; extract operational restrictions if any |
| Class action certification | 8-K Item 8.01 | Phase 3 | Escalate from filing-level to class-level; exposure scope confirmed |

**Phase 2 monitoring (prior to Phase 3 LLM):**

In Phase 2, this metric is limited to:
- XBRL balance sheet provision tag extraction (semi-structured, often null)
- 8-K keyword monitoring for litigation-related filings for issuers already flagged on other metrics
- Going concern keyword detection — See LIQUIDITY.md → Section "Frequency" → going concern monitoring and COVENANT_HEADROOM.md → Section "Frequency" → keyword scan — going concern detection is already active system-wide; Loss Provisions uses the same keyword scan without modification

Phase 2 cannot deliver the core analytical value of this metric — language tier classification, cross-period matter tracking, and unrecorded contingency detection all require Phase 3 LLM. Phase 2 contribution is a rough binary flag: provision balance exists and is growing vs stable, confirmed by XBRL where available.

**Matter registry maintenance:**

The cross-period comparison requirement creates a unique data maintenance obligation. The system must maintain a per-issuer matter registry that persists across filings. At each quarterly and annual extraction:

```
1. Load prior registry
2. Run current extraction
3. Match current matters to prior registry
4. Update registry:
   - Resolve settled/dismissed matters
   - Escalate matters with tier changes
   - Add new matters
   - Update exposure ranges
5. Store updated registry for next comparison
6. Generate alerts from changes
```

This registry is the most complex persistent data structure in the system — more complex than the rolling maturity schedule in DEBT_MATURITY_WALL.md because it requires semantic matching of legal matter descriptions across filings where the language may differ. Phase 3 LLM implementation of this registry is the highest-complexity extraction task in the entire spec.

