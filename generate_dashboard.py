"""
generate_dashboard.py — build a self-contained static dashboard (dashboard.html).

Reads credit_warning.db (issuer metric_values) and backtest_results.json (backtest
scorecard) and emits a single HTML file with all data embedded as JavaScript objects.
No backend, no server — opens in any browser. Charts via Chart.js (cdnjs).

Run:  python generate_dashboard.py   ->   dashboard.html
"""

from __future__ import annotations

import json
import sqlite3

DB_PATH = "credit_warning.db"
BACKTEST_JSON = "backtest_results.json"
OUT = "dashboard.html"

# Display order + human labels for the 19 metrics (matches cli.py DISPLAY_ROWS).
METRIC_ORDER = [
    ("leverage", "Leverage (Net Debt/EBITDA)"),
    ("interest_coverage", "Interest Coverage"),
    ("free_cash_flow", "Free Cash Flow"),
    ("fcf_margin", "FCF Margin"),
    ("moody_adjusted_fcf", "Moody Adjusted FCF"),
    ("rcf_net_debt", "RCF / Net Debt"),
    ("ocf_ebitda_conversion", "OCF / EBITDA Conversion"),
    ("current_ratio", "Current Ratio"),
    ("quick_ratio", "Quick Ratio"),
    ("ebitda_margin", "EBITDA Margin"),
    ("revenue_yoy_growth", "Revenue YoY Growth"),
    ("debt_to_equity", "Debt / Equity"),
    ("asset_coverage", "Asset Coverage"),
    ("tangible_asset_coverage", "Tangible Asset Coverage"),
    ("liquidation_asset_coverage", "Liquidation Asset Coverage"),
    ("maturity_coverage_near_term", "Maturity Coverage (near-term)"),
    ("covenant_headroom_leverage", "Covenant Headroom (leverage)"),
    ("covenant_headroom_coverage", "Covenant Headroom (coverage)"),
    ("loss_provisions_balance", "Loss Provisions Balance"),
]

# Sector map for the 30 distressed cases (accurate sector, not the backtest's grouping comment).
SECTOR_MAP = {
    "Rite Aid": "Retail — Pharmacy", "Bed Bath & Beyond": "Retail — Home",
    "JCPenney": "Retail — Department", "Sears Holdings": "Retail — Department",
    "Party City": "Retail — Specialty", "Pier 1 Imports": "Retail — Home",
    "Tailored Brands": "Retail — Apparel", "Tupperware": "Consumer Products",
    "Chesapeake Energy": "Energy — E&P", "Whiting Petroleum": "Energy — E&P",
    "Denbury Resources": "Energy — E&P", "Lilis Energy": "Energy — E&P",
    "Extraction Oil": "Energy — E&P", "Sanchez Energy": "Energy — E&P",
    "Briggs & Stratton": "Industrials", "iHeartMedia": "Media — Broadcasting",
    "Cumulus Media": "Media — Broadcasting", "Revlon": "Consumer Products",
    "Hertz": "Transport — Rental", "Yellow Corp": "Transport — Logistics",
    "Frontier Comms": "Telecom", "Mallinckrodt": "Pharma",
    "Lannett Company": "Pharma", "Akorn": "Pharma", "Windstream": "Telecom",
    "WeWork": "Real Estate / Services", "Garrett Motion": "Auto Parts",
    "Intelsat": "Telecom — Satellite", "Conduent": "Business Services",
    "Coty": "Consumer Products",
}

# Cohen's d — hardcoded from analyze_backtest.py Analysis 4 (current 33-control JSON).
# Ordinal-based, distressed-at-first-signal vs healthy-avg. fcf_margin & loss_provisions_balance
# never reached Stress+ in either group, so they have no separation (0.0).
COHENS_D = [
    ("leverage", 1.76), ("interest_coverage", 1.68), ("covenant_headroom_coverage", 1.34),
    ("moody_adjusted_fcf", 1.34), ("rcf_net_debt", 1.30), ("debt_to_equity", 1.06),
    ("covenant_headroom_leverage", 0.99), ("asset_coverage", 0.85), ("free_cash_flow", 0.80),
    ("ocf_ebitda_conversion", 0.66), ("liquidation_asset_coverage", 0.61),
    ("revenue_yoy_growth", 0.60), ("tangible_asset_coverage", 0.49), ("quick_ratio", 0.49),
    ("ebitda_margin", 0.15), ("maturity_coverage_near_term", 0.12), ("current_ratio", -0.05),
    ("fcf_margin", 0.0), ("loss_provisions_balance", 0.0),
]

# Section 4 — the 4 remaining unannotated false positives (from the final backtest run).
FP_ANALYSIS = [
    {"name": "General Mills", "qtrs": 10,
     "drivers": "liquidation_asset_coverage, maturity_coverage_near_term, quick_ratio, revenue_yoy_growth",
     "why": "Asset-light packaged-foods balance sheet (high goodwill, lean working capital) plus flat "
            "revenue trip multiple bands — investment-grade, no credit deterioration."},
    {"name": "Home Depot", "qtrs": 8,
     "drivers": "maturity_coverage_near_term, quick_ratio",
     "why": "Negative working capital by design (fast inventory turns, stretched payables) depresses the "
            "quick ratio; large near-term notes vs. a thin cash buffer. Healthy retailer."},
    {"name": "Amgen", "qtrs": 2,
     "drivers": "liquidation_asset_coverage, moody_adjusted_fcf, tangible_asset_coverage",
     "why": "Horizon-acquisition debt plus intangible-heavy biotech assets depress tangible/liquidation "
            "coverage; a one-quarter FCF dip. Investment-grade, comfortably serviced."},
    {"name": "Eli Lilly", "qtrs": 1,
     "drivers": "maturity_coverage_near_term, ocf_ebitda_conversion",
     "why": "Single-quarter working-capital swing and near-term debt vs. cash; record growth, no stress "
            "(fired in only one quarter)."},
]


def load_issuers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    issuers, units = {}, {}
    for r in conn.execute("SELECT cik,name,tickers,sector_group FROM issuers ORDER BY name"):
        tickers = json.loads(r["tickers"] or "[]")
        issuers[r["cik"]] = {"name": r["name"], "ticker": tickers[0] if tickers else "",
                             "sector": r["sector_group"], "periods": [], "data": {}}
    for cik in issuers:
        issuers[cik]["periods"] = [x[0] for x in conn.execute(
            "SELECT DISTINCT period_end_date FROM metric_values WHERE cik=? ORDER BY period_end_date",
            (cik,))]
    for r in conn.execute("SELECT cik,metric_name,period_end_date,value,value_unit,alert_level "
                          "FROM metric_values"):
        if r["cik"] not in issuers:
            continue
        d = issuers[r["cik"]]["data"].setdefault(r["metric_name"], {})
        d[r["period_end_date"]] = {"v": r["value"], "a": r["alert_level"]}
        if r["value_unit"]:
            units[r["metric_name"]] = r["value_unit"]
    conn.close()
    return issuers, units


def load_llm():
    """Per-issuer LLM footnote extraction (covenants / maturities / revolver / compliance),
    parsed from llm_extractions.raw_json (the full structured extraction). Returns {cik: dict}
    only for issuers that have at least one meaningful sub-section."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    out = {}
    try:
        ciks = [r[0] for r in conn.execute("SELECT DISTINCT cik FROM llm_extractions")]
    except sqlite3.OperationalError:
        conn.close()
        return out
    for cik in ciks:
        r = conn.execute("SELECT raw_json FROM llm_extractions WHERE cik=? "
                         "ORDER BY extracted_at DESC LIMIT 1", (cik,)).fetchone()
        if not r or not r["raw_json"]:
            continue
        try:
            d = json.loads(r["raw_json"])
        except Exception:
            continue
        covs = [{"type": cv.get("covenant_type") or cv.get("ratio_name"),
                 "threshold": cv.get("threshold_value"), "unit": cv.get("unit") or "",
                 "direction": cv.get("direction"), "frequency": cv.get("testing_frequency"),
                 "springing": bool(cv.get("is_springing"))}
                for cv in (d.get("covenants") or [])]
        mats = [{"year": m.get("year_label"), "amount": m.get("amount_millions")}
                for m in (d.get("maturity_schedule") or []) if m.get("amount_millions") is not None]
        rev = d.get("revolver") or {}
        revolver = None
        if rev.get("exists"):
            revolver = {"commitment": rev.get("total_commitment_millions"),
                        "drawn": rev.get("drawn_amount_millions"),
                        "undrawn": rev.get("undrawn_availability_millions"),
                        "maturity": rev.get("maturity_date")}
        cmp = d.get("compliance") or {}
        status = cmp.get("status")
        compliance = None
        if status and status != "not_disclosed":
            compliance = {"status": status, "going_concern": bool(cmp.get("going_concern_flag")),
                          "evidence": cmp.get("evidence") or cmp.get("description")}
        if covs or mats or revolver or compliance:
            out[cik] = {"compliance": compliance, "covenants": covs,
                        "maturities": mats, "revolver": revolver}
    conn.close()
    return out


def load_scorecard(bt):
    dist = bt["distressed"]
    caught = [c for c in dist if c["status"] == "caught"]
    scoreable = [c for c in dist if c["status"] in ("caught", "flagged_late", "missed")]
    leads = sorted(c["lead_days"] for c in caught if c.get("lead_days") is not None)
    median_lead_mo = round(leads[len(leads) // 2] / 30.44) if leads else 0
    resolved = [c for c in bt["healthy"] if c["status"] in ("clean", "annotated", "false_positive")]
    fps = [c for c in resolved if c["status"] == "false_positive"]
    annotated = [c for c in resolved if c["status"] == "annotated"]
    surv = bt["stressed_survivors"]
    surv_scoreable = [c for c in surv if c["status"] in ("detected_clean", "detected_noisy", "missed_stress")]
    detected = [c for c in surv_scoreable if c.get("stress_detected")]

    catch_rate = len(caught) / len(scoreable) if scoreable else 0.0
    fp_rate = len(fps) / len(resolved) if resolved else 0.0
    passed = catch_rate >= 0.80 and fp_rate <= 0.20 and median_lead_mo >= 6

    rows = []
    for c in dist:
        lead = round(c["lead_days"] / 30.44) if c.get("lead_days") is not None else None
        # Alert level on the first confirmed distress-signal date (not the timeline peak).
        first_signal_level = None
        if c.get("first_stress_date"):
            for sp in c.get("timeline", []):
                if sp["as_of"] == c["first_stress_date"]:
                    first_signal_level = sp["level"]
                    break
        rows.append({"name": c["name"], "sector": SECTOR_MAP.get(c["name"], "—"),
                     "event": c["event_date"], "first": c["first_stress_date"],
                     "lead": lead, "level": first_signal_level})
    rows.sort(key=lambda r: (-(r["lead"] or 0)))
    return {
        "caught": len(caught), "scoreable": len(scoreable),
        "fp_rate": round(fp_rate * 100), "fp_count": len(fps),
        "annotated": len(annotated), "resolved": len(resolved),
        "median_lead": median_lead_mo,
        "surv_detected": len(detected), "surv_total": len(surv_scoreable),
        "passed": passed, "rows": rows,
    }


def build():
    bt = json.load(open(BACKTEST_JSON, encoding="utf-8"))
    # Friendly-name overlay: map each CIK to its case-library display name (e.g. "Rite Aid",
    # "Bed Bath & Beyond") so the dropdown shows those rather than the raw EDGAR shell names
    # (e.g. "NEW RITE AID, LLC", "20230930-DK-Butterfly-1, Inc.").
    friendly = {}
    for grp in ("distressed", "healthy", "stressed_survivors"):
        for c in bt.get(grp, []):
            friendly[c["cik"]] = c["name"]

    issuers, units = load_issuers()
    for cik, info in issuers.items():
        if cik in friendly:
            info["name"] = friendly[cik]
    # LLM footnote extractions (only issuers that have any) -> attach per issuer.
    llm = load_llm()
    for cik, info in issuers.items():
        if cik in llm:
            info["llm"] = llm[cik]
    # Re-sort by the (possibly overlaid) display name so the dropdown is alphabetical.
    issuers = dict(sorted(issuers.items(), key=lambda kv: kv[1]["name"].lower()))

    scorecard = load_scorecard(bt)
    data_js = (
        "const ISSUERS = " + json.dumps(issuers) + ";\n"
        "const UNITS = " + json.dumps(units) + ";\n"
        "const METRIC_ORDER = " + json.dumps(METRIC_ORDER) + ";\n"
        "const SCORECARD = " + json.dumps(scorecard) + ";\n"
        "const COHENS_D = " + json.dumps(COHENS_D) + ";\n"
        "const FP_ANALYSIS = " + json.dumps(FP_ANALYSIS) + ";\n"
    )
    html = TEMPLATE.replace("/*__DATA__*/", data_js)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Wrote {OUT}  ({len(html):,} bytes)  ·  {len(issuers)} issuers · "
          f"{len(scorecard['rows'])} distressed cases")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Credit Warning System — Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0b1220; --header:#0d1b2a; --card:#ffffff; --ink:#1f2937; --muted:#6b7280;
    --line:#e5e7eb; --accent:#2563eb; --good:#16a34a; --warn:#d97706; --bad:#dc2626;
    --mono:'SF Mono','SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0;background:#f3f4f6;color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.45}
  header{background:linear-gradient(180deg,#0d1b2a,#10243a);color:#e5edf5;padding:22px 32px;
    border-bottom:3px solid var(--accent)}
  header h1{margin:0;font-size:21px;letter-spacing:.3px;font-weight:600}
  header .sub{color:#9fb3c8;font-size:12.5px;margin-top:4px;font-family:var(--mono)}
  main{max-width:1180px;margin:0 auto;padding:26px 24px 60px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;
    box-shadow:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(16,24,40,.04);padding:22px 24px;margin-bottom:24px}
  h2{font-size:15px;text-transform:uppercase;letter-spacing:.7px;color:#374151;margin:0 0 16px;
    padding-bottom:10px;border-bottom:1px solid var(--line)}
  h2 .tag{font-size:11px;color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400;margin-left:8px}
  .kpis{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:18px}
  .kpi{flex:1;min-width:150px;background:#0d1b2a;color:#fff;border-radius:9px;padding:16px 18px}
  .kpi .v{font-family:var(--mono);font-size:26px;font-weight:600;letter-spacing:.5px}
  .kpi .l{font-size:11.5px;color:#9fb3c8;text-transform:uppercase;letter-spacing:.6px;margin-top:3px}
  .kpi.pass .v{color:#34d399}
  .badge{display:inline-block;padding:3px 11px;border-radius:999px;font-weight:600;font-size:12px}
  .badge.pass{background:#dcfce7;color:#166534}.badge.fail{background:#fee2e2;color:#991b1b}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #f0f1f3}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;
    background:#fafbfc;position:sticky;top:0}
  td.num,th.num{text-align:right;font-family:var(--mono)}
  tr.crit{background:rgba(220,38,38,.07)} tr.crit td:first-child{box-shadow:inset 3px 0 0 var(--bad)}
  tr.stress{background:rgba(217,119,6,.08)} tr.stress td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
  .mono{font-family:var(--mono)}
  select{font-family:var(--sans);font-size:14px;padding:8px 12px;border:1px solid var(--line);
    border-radius:8px;background:#fff;min-width:280px}
  .scroll{overflow-x:auto}
  .mtable td.metric{white-space:nowrap;font-weight:500}
  .mtable td.val{font-family:var(--mono);text-align:right;white-space:nowrap}
  .ic{display:inline-block;width:1.1em;text-align:center}
  .spark-wrap{display:flex;gap:24px;flex-wrap:wrap;margin-top:20px}
  .spark{flex:1;min-width:300px;background:#fafbfc;border:1px solid var(--line);border-radius:9px;padding:14px 16px}
  .spark h3{margin:0 0 8px;font-size:12.5px;color:#374151;font-weight:600}
  .nodata{display:flex;align-items:center;justify-content:center;height:100%;text-align:center;
    color:var(--muted);font-size:12.5px;font-style:italic;padding:0 14px}
  .legend{font-size:12px;color:var(--muted);margin-top:10px}
  .legend span{margin-right:14px}
  .muted{color:var(--muted)}
  .why{color:#374151;font-size:12.5px}
  .llm-compliance{display:inline-block;padding:8px 14px;border-radius:8px;font-weight:600;font-size:13px}
  .llm-compliance.green{background:#dcfce7;color:#166534}
  .llm-compliance.orange{background:#ffedd5;color:#9a3412}
  .llm-compliance.red{background:#fee2e2;color:#991b1b}
  .llm-compliance.grey{background:#f3f4f6;color:#374151}
  blockquote.ev{margin:10px 0 0;padding:8px 14px;border-left:3px solid #d1d5db;color:#6b7280;
    font-style:italic;font-size:12.5px;line-height:1.5}
  .llm-sub{margin-top:18px}
  .llm-sub h4{margin:0 0 8px;font-size:11.5px;text-transform:uppercase;letter-spacing:.5px;color:#6b7280;font-weight:600}
  td.freq{font-size:11.5px;color:#6b7280;white-space:normal;max-width:420px}
  .drv{font-family:var(--mono);font-size:12px;color:#b45309}
  .note{font-size:12px;color:var(--muted);margin-top:12px;font-style:italic}
  footer{max-width:1180px;margin:0 auto;padding:0 24px 40px;color:var(--muted);font-size:11.5px;font-family:var(--mono)}
</style>
</head>
<body>
<header>
  <h1>Credit Warning System — Monitoring Dashboard</h1>
  <div class="sub">Point-in-time backtest · deterministic Formula-1 metrics · 30 distressed / 31 healthy / 12 survivors</div>
</header>
<main>

  <!-- Section 1 -->
  <section class="card">
    <h2>1 · Backtest Scorecard <span class="tag">point-in-time, no look-ahead</span></h2>
    <div class="kpis" id="kpis"></div>
    <div class="scroll">
      <table id="distTable">
        <thead><tr>
          <th>Company</th><th>Sector</th><th>Bankruptcy</th><th>First Signal</th>
          <th class="num">Lead (mo)</th><th>First Signal Level</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="legend"><span>🔴 Critical</span><span>🟠 Stress</span><span>🟡 Flag</span><span>🔵 Watch</span><span>✅ None</span></div>
  </section>

  <!-- Section 2 -->
  <section class="card">
    <h2>2 · Company Monitor <span class="tag">19 metrics × 8 quarters</span></h2>
    <label class="muted" for="issuerSel">Issuer:&nbsp;</label>
    <select id="issuerSel"></select>
    <div class="scroll" style="margin-top:16px"><table class="mtable" id="metricTable"></table></div>
    <div class="legend"><span>🔴 Critical</span><span>🟠 Stress</span><span>🟡 Flag</span><span>🔵 Watch</span><span>✅ None</span><span>· n/a or suppressed</span></div>
    <div class="spark-wrap">
      <div class="spark"><h3>Leverage (Net Debt / EBITDA)</h3>
        <div id="leverageBox" style="position:relative; height:300px;"><canvas id="sparkLev"></canvas></div>
      </div>
      <div class="spark"><h3>Interest Coverage</h3>
        <div id="coverageBox" style="position:relative; height:300px;"><canvas id="sparkCov"></canvas></div>
      </div>
    </div>
    <div id="llmSection" style="display:none; margin-top:24px;">
      <h3 onclick="toggleLLM()" style="font-size:13px; color:#374151; margin-bottom:12px; cursor:pointer; user-select:none;">
        <span id="llmCaret">▾</span> 📋 LLM Extracted Details
        <span style="font-size:11px; color:#9ca3af; font-weight:normal;">— from SEC filing footnotes</span>
      </h3>
      <div id="llmContent"></div>
    </div>
  </section>

  <!-- Section 3 -->
  <section class="card">
    <h2>3 · Statistical Analysis — Cohen's d Separation
      <span class="tag">EXPLORATORY — 30 distressed cases, Cohen (1988) benchmarks</span></h2>
    <div style="position:relative; height:520px;">
      <canvas id="cohenChart"></canvas>
    </div>
    <div class="legend"><span style="color:var(--good)">■ d &gt; 0.8 large</span>
      <span style="color:var(--warn)">■ d &gt; 0.5 medium</span>
      <span style="color:var(--bad)">■ d &lt; 0.5 small</span></div>
    <div class="note">Distressed alert level at first confirmed signal vs. healthy average over the scored window,
      on the [0,4] alert-level ordinal. Hypothesis-generating only — values in the 0.5–1.0 band have wide CIs.</div>
  </section>

  <!-- Section 4 -->
  <section class="card">
    <h2>4 · False Positive Analysis <span class="tag">4 remaining unannotated FPs</span></h2>
    <div class="scroll"><table id="fpTable">
      <thead><tr><th>Control</th><th class="num">Qtrs</th><th>Confirming metrics</th><th>Explanation</th></tr></thead>
      <tbody></tbody>
    </table></div>
    <div class="note">Annotated one-off events (Air Products, RTX) and reclassified cyclical names (Pfizer, Texas
      Instruments → stressed survivors) are excluded from the false-positive count.</div>
  </section>

</main>
<footer>Generated by generate_dashboard.py · static, self-contained · data embedded at build time.</footer>

<script>
/*__DATA__*/

// ---- helpers ----
const ICON = {Critical:"🔴",Stress:"🟠",Flag:"🟡",Watch:"🔵"};
function iconFor(v,a){ if(ICON[a]) return ICON[a]; return (v===null||v===undefined)?"·":"✅"; }
function fmtVal(v,unit){
  if(v===null||v===undefined) return "—";
  if(unit==="ratio") return v.toFixed(2)+"x";
  if(unit==="percent") return v.toFixed(1)+"%";
  if(unit==="millions_usd") return (v<0?"-$":"$")+Math.abs(v).toLocaleString(undefined,{maximumFractionDigits:0})+"M";
  return v.toFixed(2);
}
function qLabel(iso){ const d=new Date(iso+"T00:00:00"); return d.toLocaleString('en',{month:'short'})+" '"+String(d.getFullYear()).slice(2); }
const rowClass = p => p==="Critical" ? "crit" : (p==="Stress" ? "stress" : "");

// ---- Section 1 ----
function renderScorecard(){
  const s=SCORECARD;
  const kpis=[
    {v:s.caught+"/"+s.scoreable, l:"Distressed caught"},
    {v:s.fp_rate+"%", l:"False-positive rate"},
    {v:s.median_lead+"mo", l:"Median lead time"},
    {v:s.surv_detected+"/"+s.surv_total, l:"Survivors detected"},
    {v:(s.passed?"✅ PASS":"❌ FAIL"), l:"Gate", pass:s.passed},
  ];
  document.getElementById("kpis").innerHTML = kpis.map(k=>
    `<div class="kpi ${k.pass?'pass':''}"><div class="v">${k.v}</div><div class="l">${k.l}</div></div>`).join("");
  const tb=document.querySelector("#distTable tbody");
  tb.innerHTML = s.rows.map(r=>`<tr class="${rowClass(r.level)}">
    <td><strong>${r.name}</strong></td><td class="muted">${r.sector}</td>
    <td class="mono">${r.event||"—"}</td><td class="mono">${r.first||"—"}</td>
    <td class="num">${r.lead==null?"—":r.lead}</td>
    <td>${iconFor(1,r.level)} ${r.level||"None"}</td></tr>`).join("");
}

// ---- Section 2 ----
const SPARK_CHARTS = {};   // canvasId -> Chart instance
function drawSpark(boxId, canvasId, vals, labels, color){
  const box=document.getElementById(boxId);
  if(SPARK_CHARTS[canvasId]){ SPARK_CHARTS[canvasId].destroy(); SPARK_CHARTS[canvasId]=null; }
  const allNull = vals.every(v=>v===null||v===undefined);
  if(allNull){
    box.innerHTML='<div class="nodata">No data — metric null for all periods (EBITDA ≤ 0 or tag absent)</div>';
    return;
  }
  box.innerHTML='<canvas id="'+canvasId+'"></canvas>';
  SPARK_CHARTS[canvasId]=new Chart(document.getElementById(canvasId),{type:'line',
    data:{labels,datasets:[{data:vals,borderColor:color,backgroundColor:color+'1a',
      fill:true,tension:.25,spanGaps:true}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      elements:{point:{radius:2}},
      scales:{x:{grid:{display:false},ticks:{font:{size:10}}},
        y:{grid:{color:'#eef0f2'},ticks:{font:{size:10}}}}}});
}
function renderCompany(cik){
  const iss=ISSUERS[cik], periods=iss.periods;
  let head="<thead><tr><th>Metric</th>"+periods.map(p=>`<th class="num">${qLabel(p)}</th>`).join("")+"</tr></thead>";
  let body="<tbody>";
  for(const [m,label] of METRIC_ORDER){
    const series=iss.data[m]||{};
    body+=`<tr><td class="metric">${label}</td>`;
    for(const p of periods){
      const cell=series[p]||{v:null,a:null};
      body+=`<td class="val"><span class="ic">${iconFor(cell.v,cell.a)}</span> ${fmtVal(cell.v,UNITS[m])}</td>`;
    }
    body+="</tr>";
  }
  document.getElementById("metricTable").innerHTML=head+body+"</tbody>";

  const lev=periods.map(p=>(iss.data["leverage"]||{})[p]?.v ?? null);
  const cov=periods.map(p=>(iss.data["interest_coverage"]||{})[p]?.v ?? null);
  const labels=periods.map(qLabel);
  drawSpark("leverageBox","sparkLev",lev,labels,'#2563eb');
  drawSpark("coverageBox","sparkCov",cov,labels,'#16a34a');
  renderLLM(cik);
}

// ---- Section 2: LLM extracted details ----
const CMP_STYLE={in_compliance:["green","✅"],going_concern_doubt:["orange","🟠"],
  breach:["red","🔴"],chapter_11:["red","🔴"],default_event:["red","🔴"]};
function money(v){ return v==null ? "—" : "$"+Number(v).toLocaleString(undefined,{maximumFractionDigits:1})+"M"; }
function toggleLLM(){
  const c=document.getElementById("llmContent"), car=document.getElementById("llmCaret");
  const hidden=c.style.display==="none";
  c.style.display=hidden?"block":"none"; car.textContent=hidden?"▾":"▸";
}
function renderLLM(cik){
  const sec=document.getElementById("llmSection"), box=document.getElementById("llmContent");
  const llm=ISSUERS[cik].llm;
  if(!llm){ sec.style.display="none"; box.innerHTML=""; return; }
  let h="";
  // A — compliance
  if(llm.compliance){
    const st=llm.compliance.status, sty=CMP_STYLE[st]||["grey","ℹ️"];
    h+=`<div class="llm-sub"><div class="llm-compliance ${sty[0]}">${sty[1]} Compliance: ${st.replace(/_/g,' ')}`
      +`${llm.compliance.going_concern?' · going-concern doubt':''}</div>`;
    if(llm.compliance.evidence) h+=`<blockquote class="ev">${llm.compliance.evidence}</blockquote>`;
    h+="</div>";
  }
  // B — covenants
  if(llm.covenants && llm.covenants.length){
    h+=`<div class="llm-sub"><h4>Covenants</h4><table><thead><tr><th>Type</th>`
      +`<th class="num">Threshold</th><th>Direction</th><th>Frequency</th><th>Springing</th></tr></thead><tbody>`;
    for(const c of llm.covenants){
      const thr=c.threshold==null?"—":(c.threshold+(c.unit||""));
      h+=`<tr><td>${(c.type||"—").replace(/_/g,' ')}</td><td class="num">${thr}</td>`
        +`<td>${c.direction||"—"}</td><td class="freq">${c.frequency||"—"}</td>`
        +`<td>${c.springing?"Yes":"No"}</td></tr>`;
    }
    h+="</tbody></table></div>";
  }
  // C — maturities
  if(llm.maturities && llm.maturities.length){
    h+=`<div class="llm-sub"><h4>Debt Maturity Schedule</h4><table><thead><tr><th>Year</th>`
      +`<th class="num">Principal ($M)</th></tr></thead><tbody>`;
    for(const m of llm.maturities){
      h+=`<tr><td>${m.year||"—"}</td><td class="num">${money(m.amount)}</td></tr>`;
    }
    h+="</tbody></table></div>";
  }
  // D — revolver
  if(llm.revolver){
    const r=llm.revolver;
    h+=`<div class="llm-sub"><h4>Revolving Credit Facility</h4>`
      +`<div class="mono" style="font-size:13px">Commitment ${money(r.commitment)} · `
      +`Drawn ${money(r.drawn)} · Available ${money(r.undrawn)} · Matures ${r.maturity||"—"}</div></div>`;
  }
  box.innerHTML=h;
  box.style.display="block";
  document.getElementById("llmCaret").textContent="▾";
  sec.style.display="block";
}
function initIssuers(){
  const sel=document.getElementById("issuerSel");
  sel.innerHTML=Object.keys(ISSUERS).map(c=>`<option value="${c}">${ISSUERS[c].name}${ISSUERS[c].ticker?' ('+ISSUERS[c].ticker+')':''}</option>`).join("");
  sel.addEventListener("change",e=>renderCompany(e.target.value));
  renderCompany(sel.value);
}

// ---- Section 3 ----
function renderCohen(){
  const labels=COHENS_D.map(d=>d[0]), vals=COHENS_D.map(d=>d[1]);
  const colors=vals.map(d=> d>0.8 ? '#16a34a' : (d>0.5 ? '#d97706' : '#dc2626'));
  new Chart(document.getElementById("cohenChart"),{type:'bar',
    data:{labels,datasets:[{data:vals,backgroundColor:colors,borderRadius:3}]},
    options:{
      indexAxis:'y',
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{display:false},
        tooltip:{callbacks:{label:c=>"Cohen's d = "+c.parsed.x.toFixed(2)}}},
      scales:{
        x:{min:-0.5,max:2.5,grid:{color:'#eef0f2'},ticks:{font:{family:'monospace',size:11}},
           title:{display:true,text:"Cohen's d"}},
        y:{grid:{display:false},ticks:{font:{family:'monospace',size:11}}}
      }
    }});
}

// ---- Section 4 ----
function renderFP(){
  document.querySelector("#fpTable tbody").innerHTML=FP_ANALYSIS.map(f=>
    `<tr><td><strong>${f.name}</strong></td><td class="num">${f.qtrs}</td>
     <td class="drv">${f.drivers}</td><td class="why">${f.why}</td></tr>`).join("");
}

renderScorecard(); initIssuers(); renderCohen(); renderFP();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
