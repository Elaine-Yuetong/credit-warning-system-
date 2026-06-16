"""
app_data.py — pure data-access layer for the Streamlit app (no Streamlit imports).

Keeping the logic here (rather than inline in the pages) means it is unit-testable without a
running Streamlit server. The pages import these functions and wrap them in UI.
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import json
import re
import sqlite3
import urllib.parse
import urllib.request



DB_PATH = "credit_warning.db"
BACKTEST_JSON = "backtest_results.json"
UA = "CreditWarningSystem/1.0 (research project; contact: elaine.wei@xpef.org)"

# 19 metrics in display order with human labels (mirrors cli.py / generate_dashboard).
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

ALERT_ICON = {"Critical": "🔴", "Stress": "🟠", "Flag": "🟡", "Watch": "🔵", None: "✅"}

# Quartile -> (label, hex color) for the "vs Peers" column.
PEER_DISPLAY = {
    "top":          ("↑ Top quartile",    "#16a34a"),
    "upper_middle": ("↗ Above median",    "#86c98b"),
    "lower_middle": ("↘ Below median",    "#e6a3a3"),
    "bottom":       ("↓ Bottom quartile", "#dc2626"),
    "no_data":      ("— No peer data",    "#9ca3af"),
}


# --------------------------------------------------------------------------------------
# Issuer / classification
# --------------------------------------------------------------------------------------

def issuer_row(cik: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute(
        "SELECT cik,name,tickers,sector_group,size_category,sub_sector FROM issuers WHERE cik=?",
        (cik,)).fetchone()
    conn.close()
    if r is None:
        return None
    d = dict(r)
    try:
        d["ticker"] = (json.loads(d.get("tickers") or "[]") or [""])[0]
    except Exception:
        d["ticker"] = ""
    return d


def classification_badge(cik: str) -> tuple[str, str]:
    """(icon+label, category) from backtest_results.json; ('', 'unknown') if not a case."""
    try:
        bt = json.load(open(BACKTEST_JSON, encoding="utf-8"))
    except Exception:
        return "", "unknown"
    from extractor import pad_cik
    c = pad_cik(cik)
    for case in bt.get("distressed", []):
        if pad_cik(case["cik"]) == c:
            return "🔴 Distressed — bankruptcy case", "distressed"
    for case in bt.get("stressed_survivors", []):
        if pad_cik(case["cik"]) == c:
            return "🟠 Stressed survivor", "survivor"
    for case in bt.get("healthy", []):
        if pad_cik(case["cik"]) == c:
            return "✅ Healthy control", "healthy"
    return "", "unknown"


def recently_monitored() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT cik,name,sector_group,size_category FROM issuers ORDER BY name")]
    conn.close()
    return rows


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------

def company_in_db(cik: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    hit = conn.execute("SELECT 1 FROM metric_values WHERE cik=? LIMIT 1", (cik,)).fetchone()
    conn.close()
    return hit is not None


def ensure_company(cik: str) -> bool:
    """If the CIK has no metric_values yet, run the full pipeline and persist. Network-bound.
    Returns True if the company has data after the call."""
    if company_in_db(cik):
        return True
    from extractor import SecClient, extract
    from metrics import compute_metrics, _load_llm_loss_provisions
    from thresholds import classify, assign_alerts
    import db as _db
    result = extract(cik, client=SecClient())
    if result is None:
        return False
    cls = classify(result.metadata.sic_code)
    ms = compute_metrics(result, cls.institution_type)
    assign_alerts(ms, cls, _load_llm_loss_provisions(result.metadata.cik))
    conn = _db.connect()
    _db.upsert_issuer(conn, result.metadata, cls)
    _db.write_metrics(conn, result.metadata.cik, ms)
    conn.close()
    return True


def load_metric_table(cik: str) -> dict:
    """Return {periods: [8 most recent], data: {metric: {period: {'v','a','unit'}}}}."""
    conn = sqlite3.connect(DB_PATH)
    periods = [r[0] for r in conn.execute(
        "SELECT DISTINCT period_end_date FROM metric_values WHERE cik=? "
        "ORDER BY period_end_date DESC LIMIT 8", (cik,))]
    periods = sorted(periods)
    data: dict = {}
    for m, pe, val, unit, alert in conn.execute(
            "SELECT metric_name,period_end_date,value,value_unit,alert_level "
            "FROM metric_values WHERE cik=?", (cik,)):
        if pe in periods:
            data.setdefault(m, {})[pe] = {"v": val, "a": alert, "unit": unit}
    conn.close()
    return {"periods": periods, "data": data}


def latest_value(cik: str, metric: str):
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(
        "SELECT value FROM metric_values WHERE cik=? AND metric_name=? AND value IS NOT NULL "
        "ORDER BY period_end_date DESC LIMIT 1", (cik, metric)).fetchone()
    conn.close()
    return r[0] if r else None


def fmt_value(v, unit) -> str:
    if v is None:
        return "—"
    if unit == "ratio":
        return f"{v:.2f}x"
    if unit == "percent":
        return f"{v:.1f}%"
    if unit == "millions_usd":
        return f"{'-$' if v < 0 else '$'}{abs(v):,.0f}M"
    return f"{v:.2f}"


def peer_classification(cik: str, metric: str) -> dict:
    """vs-peers cell for a metric: {label, color, quartile, value, benchmark}."""
    from benchmarks import get_benchmark, classify_quartile
    value = latest_value(cik, metric)
    bm = get_benchmark(DB_PATH, cik, metric)
    if bm is None or value is None:
        q = "no_data"
    else:
        q = classify_quartile(value, bm["p25"], bm["p50"], bm["p75"], metric)
    label, color = PEER_DISPLAY.get(q, PEER_DISPLAY["no_data"])
    return {"label": label, "color": color, "quartile": q, "value": value, "benchmark": bm}


# --------------------------------------------------------------------------------------
# LLM footnote data (read existing rows; mirrors generate_dashboard.load_llm for one CIK)
# --------------------------------------------------------------------------------------

def load_llm(cik: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        r = conn.execute(
            "SELECT raw_json FROM llm_extractions WHERE cik=? ORDER BY extracted_at DESC LIMIT 1",
            (cik,)).fetchone()
    except sqlite3.OperationalError:
        conn.close()
        return None
    conn.close()
    if not r or not r[0]:
        return None
    try:
        d = json.loads(r[0])
    except Exception:
        return None
    covs = [{"type": cv.get("covenant_type") or cv.get("ratio_name"),
             "threshold": cv.get("threshold_value"), "unit": cv.get("unit") or "",
             "direction": cv.get("direction"), "frequency": cv.get("testing_frequency"),
             "springing": bool(cv.get("is_springing")), "evidence": cv.get("evidence") or ""}
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
    # Verbatim footnote text fed to the LLM, if the extraction stored it (current extractions
    # do not persist it, so this is typically None — the field is future-ready).
    footnote_text = d.get("footnote_text") or d.get("source_text") or d.get("debt_footnote_text")
    if covs or mats or revolver or compliance:
        return {"compliance": compliance, "covenants": covs, "maturities": mats,
                "revolver": revolver, "footnote_text": footnote_text}
    return None


def get_filing_url(cik: str) -> str | None:
    """SEC EDGAR URL for the filing used in the most recent LLM extraction.
    Prefers a URL stored in raw_json; otherwise constructs the EDGAR filing-index URL from the
    stored accession number (raw_json currently stores no URL, so the constructed path is used)."""
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(
        "SELECT accession, raw_json FROM llm_extractions WHERE cik=? ORDER BY extracted_at DESC LIMIT 1",
        (cik,)).fetchone()
    conn.close()
    if not r:
        return None
    accession, rj = r
    try:
        d = json.loads(rj) if rj else {}
        stored = d.get("source_url") or d.get("filing_url")
        if stored:
            return stored
    except Exception:
        pass
    if accession:
        cik_int = str(int(cik))                       # EDGAR data path drops leading zeros
        acc_nodash = accession.replace("-", "")
        return (f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
                f"{accession}-index.htm")
    return None


def run_llm_extraction(cik: str, form: str = "10-K") -> str:
    """Trigger LLM footnote extraction for the latest filing. Requires ANTHROPIC_API_KEY.
    Returns a status message. Persists into the llm_* tables (best-effort)."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "error: ANTHROPIC_API_KEY not set — cannot call the LLM."
    from extractor import SecClient
    from sec_fetcher import get_debt_footnote
    from llm_extractor import (extract_debt_terms, extract_loss_provisions,
                               extract_asset_composition, extract_capex_split)
    fn = get_debt_footnote(SecClient(), cik, form)
    if fn is None or not fn.found:
        return "error: could not locate a debt footnote to extract from."
    extract_debt_terms(fn)
    extract_loss_provisions(fn)
    extract_asset_composition(fn)
    extract_capex_split(fn)
    return "ok"


# --------------------------------------------------------------------------------------
# EDGAR full-text company search
# --------------------------------------------------------------------------------------

def _search_efts(query: str, max_results: int) -> list[dict]:
    """Primary: EDGAR full-text search. Raises on transport error (caller falls back)."""
    url = ("https://efts.sec.gov/LATEST/search?q="
           + urllib.parse.quote(f'"{query}"')
           + "&dateRange=custom&startdt=2020-01-01&forms=10-K"
           + "&hits.hits._source=ciks,display_names,sics")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    out, seen = [], set()
    for hit in data.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        for c in src.get("ciks", []):
            c10 = c.zfill(10)
            if c10 in seen:
                continue
            seen.add(c10)
            name = next((dn.split(" (CIK")[0] for dn in src.get("display_names", [])
                         if c.lstrip("0") in dn or f"CIK {c}" in dn),
                        (src.get("display_names") or ["?"])[0])
            sics = src.get("sics", [])
            out.append({"name": name, "cik": c10, "sic": sics[0] if sics else ""})
            if len(out) >= max_results:
                return out
    return out


def _search_browse_edgar(query: str, max_results: int) -> list[dict]:
    """Fallback: classic EDGAR company-name search (browse-edgar atom), reachable where the
    efts full-text host is blocked. The atom reliably exposes only <cik> (its per-company name
    attribute is a corrupt 'ARRAY(0x..)' in multi-match results), so we parse CIKs from the atom
    and resolve name + SIC from the data.sec.gov submissions API. Capped to bound search latency."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?company="
           + urllib.parse.quote(query)
           + "&CIK=&type=10-K&dateb=&owner=include&count=20&search_text=&action=getcompany&output=atom")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/xml"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", "replace")
    ciks, seen = [], set()
    for c in re.findall(r"<cik>(\d+)</cik>", body):
        c10 = c.zfill(10)
        if c10 not in seen:
            seen.add(c10)
            ciks.append(c10)
    from extractor import SecClient, fetch_issuer_metadata
    client = SecClient()
    out = []
    for c10 in ciks[:min(max_results, 12)]:   # cap submissions lookups
        name, sic = f"CIK {c10}", ""
        try:
            m = fetch_issuer_metadata(client, c10)
            if m:
                name, sic = (m.name or name), (m.sic_code or "")
        except Exception:
            pass
        out.append({"name": name, "cik": c10, "sic": sic})
    return out


def _is_likely_subsidiary(name: str) -> bool:
    """Heuristic: does the entity name look like a financing/subsidiary co-issuer shell rather
    than the primary operating company?"""
    signals = ["holdings llc", " llc", "finance corp", "capital corp",
               "us inc", "co-issuer", "funding corp", "escrow",
               "co-registrant"]
    lower = name.lower()
    return any(s in lower for s in signals)


def _enrich_flags(results: list[dict]) -> list[dict]:
    """Tag each result with in_database (already monitored) and likely_subsidiary."""
    conn = sqlite3.connect(DB_PATH)
    db_ciks = {r[0] for r in conn.execute("SELECT cik FROM issuers")}
    conn.close()
    for r in results:
        r["in_database"] = r["cik"] in db_ciks
        r["likely_subsidiary"] = _is_likely_subsidiary(r["name"])
    return results


def edgar_search(query: str, max_results: int = 25) -> tuple[list[dict], str]:
    """Search EDGAR for 10-K filers by company name. Returns (results, error_msg).
    Tries the full-text search API first; if that host is blocked/unavailable (or returns no
    hits), falls back to the classic browse-edgar company-name search. Each result is tagged
    with in_database / likely_subsidiary for disambiguation badges."""
    try:
        out = _search_efts(query, max_results)
        if out:
            return _enrich_flags(out), ""
    except Exception:
        pass  # efts blocked/unavailable -> fall back
    try:
        out = _search_browse_edgar(query, max_results)
        return _enrich_flags(out), ("" if out else "No matching 10-K filers found.")
    except Exception as e:
        return [], f"EDGAR search unavailable ({e}). Use Recently Monitored below."
