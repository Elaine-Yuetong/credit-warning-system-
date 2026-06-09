# Credit Warning System — 1-Week Intern Plan

## Project Scope

Build a system that watches the issuers in a corporate-bond portfolio (~30 names) and flags credit stress before it becomes a problem — automating the work a credit analyst does by hand.

The system:

- **Ingests** SEC filings (10-K annual, 10-Q quarterly, 8-K event-driven), and later earnings-call transcripts and sell-side reports.
- **Extracts structured numbers deterministically** — leverage, coverage, free cash flow, liquidity, debt maturities. (A parser does the math, not an LLM — see note below.)
- **Uses an LLM for the subjective stuff** — tone, hedging language, covenant/litigation footnotes, concerns raised on calls. The LLM returns findings with evidence, never numbers or scores.
- **Combines both into a stress score** per issuer, tracked over time, with alerts and an explainable breakdown.

## For Your Reference

I had been working on the same project myself with Claude these few days at <https://github.com/Khootz/Credit_Warning>. Feel free to clone this repo and explore, but I encourage you to try and build it yourself

## Suggested outcome this week

| Phase | Days | Outcome |
| --- | --- | --- |
| 1 — Understand the credit-analyst workflow | Days 1–2 | A written spec of what to extract and why |
| 2 — MVP: extract figures + track an issuer | Days 3–5 | Add a company by name, see its key ratios over time |
| 3 — Backtest: measure if it actually works | Days 6–7 | Rewind real distressed names; report catch rate + lead time |

## Phase 1 (Days 1–2) — Understand What Matters in SEC Filings

**Goal:** Before writing code, I want you guys to learn the manual process a credit analyst follows, feel free to ask Steven for any questions.

Some examples:

1. **Balance-sheet overview & solvency ratios.** Assets vs. liabilities; debt-to-equity, quick ratio, other solvency ratios. Flag any large increase in debt period-over-period.
2. **Cash-flow / FCF compression.** Is operating cash flow shrinking? Is free cash flow (OCF − capex) turning negative or trending down? This is an early stress signal.
3. **Debt footnote (the most important read).**
   - **Maturity wall** — when is debt maturing? Flag if too much matures at the same time (refinancing risk).
   - **Rising rates** — are they paying higher interest (rate environment, or stress premium)?
   - **Maintenance covenants** — max leverage, min coverage, min net worth. Flag when the company sits close to a covenant limit.
4. **Loss provisions in footnotes** — provisions for future losses, especially litigation provisions and contingencies.

> **Crucial point to learn:** which data can be extracted structurally (e.g. tagged XML) and which ones cant.

## Phase 2 (Days 3–5) — MVP: Extract Figures & Track an Issuer

**Goal:** A working tool where you manually enter a company, it pulls the filings, computes the key credit ratios, and lets you track those over time.

**Build:**

1. **Ingestion** — given a company (name/ticker → its SEC identifier), fetch its recent 10-K, 10-Q, 8-K filings and its structured financial facts. Respect SEC rate limits; cache responses.
2. **Extraction (deterministic)** — pull the raw line items and compute the key ratios per period:
   - Leverage = net debt / EBITDA
   - Interest coverage = EBITDA / interest expense
   - Free cash flow = operating cash flow − capex (and FCF margin)
   - Liquidity = cash vs. near-term obligations
   - Near-term debt maturities / refinancing risk
   - Covenant signals (stretch — from footnote text)

   Each computed value records its inputs so it's auditable (no black-box numbers).
3. **Track over time** — store results per period so an issuer's ratios form a trend; show whether leverage is climbing, coverage falling, FCF compressing.
4. **Manual entry UX** — a simple "add a company to track" flow; it ingests and displays the latest ratios + trend.

**Handle the messy reality (intern learning):** companies tag the same concept differently — extraction needs prioritized fallbacks for each number, and EBITDA usually has to be derived (operating income + D&A) because it isn't a standard tag. Missing a number should not silently produce a wrong ratio.

**Done when:** you can type a real company, and within seconds see its leverage / coverage / FCF / liquidity for the last several periods, each traceable to the source filing.

## Phase 3 (Days 6–7) — Backtest: Does It Actually Catch Stress?

**Goal:** A backtest harness that measures accuracy as the system evolves. It doesn't need to be 100% accurate — it needs to be **measurable**, so every future change can be checked for improvement or regression.

**Build:**

1. **Case library** — a handful of known distressed issuers (companies that defaulted / went bankrupt, with the date) and healthy controls.
2. **Point-in-time scoring (no cheating)** — for each historical date, score using only data that was available then (no look-ahead from later restatements). This is the single most important correctness rule in backtesting.
3. **Measure two things:**
   - **Catch rate / lead time** — did distressed names reach a "stress" level before their event, and how many months early?
   - **False positives** — did healthy controls stay calm?
4. **Report** — a simple pass/fail summary you can re-run anytime (and wire into CI later).

**Done when:** running the backtest prints, per case, whether it was flagged early and by how long — a number that improves as you tune the model.
