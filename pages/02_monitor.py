"""Page 2 — Company Monitor."""
import pandas as pd
import streamlit as st

import app_data as a

st.set_page_config(page_title="Monitor — Credit Warning System", layout="wide")

cik = st.session_state.get("selected_cik")
if not cik:
    st.title("Company Monitor")
    st.warning("No company selected — use the **Search** page.")
    st.stop()


def _qlabel(iso: str) -> str:
    import datetime as _dt
    try:
        d = _dt.date.fromisoformat(iso[:10])
        return d.strftime("%b %y")
    except Exception:
        return iso[:7]


@st.cache_data(ttl=3600, show_spinner=False)
def load_company(cik: str) -> dict:
    """Ensure the company is in the DB (run pipeline if new), then load its metric table.
    Cached so a page refresh does not re-fetch from EDGAR."""
    ok = a.ensure_company(cik)
    if not ok:
        return {"ok": False}
    table = a.load_metric_table(cik)
    return {"ok": True, "table": table}


with st.spinner("Loading company metrics…"):
    loaded = load_company(cik)
issuer = a.issuer_row(cik)
if not loaded.get("ok") or issuer is None:
    st.error(f"Extraction failed for CIK {cik} — could not validate or fetch companyfacts.")
    st.stop()

# ── Component 1 — header ──────────────────────────────────────────────────────────────
badge, _cat = a.classification_badge(cik)
ticker = f" ({issuer['ticker']})" if issuer.get("ticker") else ""
st.title(f"{issuer['name']}{ticker}")
hdr = (f"**CIK** {cik}  ·  **Sector** {issuer['sector_group'] or '—'}  ·  "
       f"**Size** {issuer['size_category'] or '—'}")
if issuer.get("sub_sector"):
    hdr += f"  ·  **Sub-sector** {issuer['sub_sector']}"
if badge:
    hdr += f"  ·  {badge}"
st.markdown(hdr)
st.divider()

# ── Component 2 — metric table with peer comparison ────────────────────────────────────
st.subheader("Metrics × 8 quarters · alert · vs peers")
table = loaded["table"]
periods, data = table["periods"], table["data"]
rows, index = [], []
for key, label in a.METRIC_ORDER:
    series = data.get(key, {})
    row = {}
    for p in periods:
        cell = series.get(p)
        row[_qlabel(p)] = a.fmt_value(cell["v"], cell["unit"]) if (cell and cell["v"] is not None) else "·"
    latest = series.get(periods[-1]) if periods else None
    if latest and latest["v"] is not None:
        row["Alert"] = f"{a.ALERT_ICON.get(latest['a'], '✅')} {latest['a'] or 'None'}"
    else:
        row["Alert"] = "·"
    row["vs Peers"] = a.peer_classification(cik, key)["label"]
    rows.append(row)
    index.append(label)
df = pd.DataFrame(rows, index=index)

_color_map = {label: color for label, color in a.PEER_DISPLAY.values()}
def _style_peers(val):
    return f"color: {_color_map.get(val, '#9ca3af')}; font-weight: 600"
st.dataframe(df.style.map(_style_peers, subset=["vs Peers"]), use_container_width=True)
st.caption("🔴 Critical · 🟠 Stress · 🟡 Flag · 🔵 Watch · ✅ None · · suppressed / no data")

# Benchmark context (below metric table)
with st.expander("Peer benchmark details"):
    shown_desc = None
    brows = []
    for key, label in a.METRIC_ORDER:
        pc = a.peer_classification(cik, key)
        bm = pc["benchmark"]
        if not bm:
            continue
        shown_desc = shown_desc or bm["cell_description"]
        brows.append({"Metric": label, "p25": round(bm["p25"], 3), "p50": round(bm["p50"], 3),
                      "p75": round(bm["p75"], 3), "level": bm["fallback_level"],
                      "distressed excluded": bm["distressed_count"]})
    if shown_desc:
        st.markdown(f"**Benchmarking against:** {shown_desc}")
        st.dataframe(pd.DataFrame(brows), use_container_width=True, hide_index=True)
        if brows and brows[0]["level"] != "full":
            st.caption("Sector/size-level benchmark — sub-sector cell had insufficient population.")
    else:
        st.info("No peer benchmark available for this company's cells (insufficient healthy peers).")

# ── Component 3 — sparklines ────────────────────────────────────────────────────────────
st.subheader("Trend")
col1, col2 = st.columns(2)
def _spark(col, metric, title):
    with col:
        st.markdown(f"**{title}**")
        series = data.get(metric, {})
        vals = [(_qlabel(p), series.get(p, {}).get("v")) for p in periods]
        if all(v is None for _l, v in vals):
            st.info("No data — EBITDA ≤ 0 or tag absent")
        else:
            st.line_chart(pd.DataFrame({title: [v for _l, v in vals]},
                                       index=[l for l, _v in vals]))
_spark(col1, "leverage", "Leverage")
_spark(col2, "interest_coverage", "Interest Coverage")

# ── Component 4 — LLM extraction panel ──────────────────────────────────────────────────
st.divider()
st.subheader("📋 LLM Extracted Details")
_filing_url = a.get_filing_url(cik)
if _filing_url:
    st.markdown(f"[📄 View original SEC filing]({_filing_url})", unsafe_allow_html=False)

_CMP = {"in_compliance": ("✅", "#166534"), "going_concern_doubt": ("🟠", "#9a3412"),
        "breach": ("🔴", "#991b1b"), "chapter_11": ("🔴", "#991b1b")}

def render_llm(cik: str):
    llm = a.load_llm(cik)
    if not llm:
        st.caption("No LLM-extracted footnote data for this company yet.")
        return
    if llm["compliance"]:
        st_ = llm["compliance"]["status"]
        icon, color = _CMP.get(st_, ("ℹ️", "#374151"))
        gc = " · going-concern doubt" if llm["compliance"]["going_concern"] else ""
        st.markdown(f"<span style='color:{color};font-weight:600'>{icon} Compliance: "
                    f"{st_.replace('_', ' ')}{gc}</span>", unsafe_allow_html=True)
        if llm["compliance"]["evidence"]:
            st.caption(f"“{llm['compliance']['evidence']}”")
    if llm["covenants"]:
        st.markdown("**Covenants**")
        cov_df = pd.DataFrame([{
            "Type": (c["type"] or "—").replace("_", " "),
            "Threshold": "—" if c["threshold"] is None else f"{c['threshold']}{c['unit']}",
            "Direction": c["direction"] or "—", "Springing": "Yes" if c["springing"] else "No",
            "Frequency": (c["frequency"] or "—"),
        } for c in llm["covenants"]])
        st.dataframe(cov_df, use_container_width=True, hide_index=True)
        for c in llm["covenants"]:
            if c["evidence"]:
                with st.expander(f"Filing evidence — {(c['type'] or 'covenant').replace('_',' ')}"):
                    st.caption(f"“{c['evidence']}”")
    if llm["maturities"]:
        st.markdown("**Debt Maturity Schedule**")
        st.dataframe(pd.DataFrame([{"Year": m["year"], "Principal ($M)": m["amount"]}
                                   for m in llm["maturities"]]),
                     use_container_width=True, hide_index=True)
    if llm["revolver"]:
        r = llm["revolver"]
        money = lambda v: "—" if v is None else f"${v:,.1f}M"
        # st.text (not st.markdown): bare '$' pairs in markdown render as LaTeX math, which
        # was italicising/garbling the revolver line.
        st.markdown("**Revolver**")
        st.text(f"Commitment {money(r['commitment'])} · Drawn {money(r['drawn'])} · "
                f"Available {money(r['undrawn'])} · Matures {r['maturity'] or '—'}")
    if llm.get("footnote_text"):
        with st.expander("📋 View raw footnote text fed to LLM"):
            st.text(llm["footnote_text"])

render_llm(cik)

if st.button("▶ Run LLM Extraction"):
    with st.spinner("Extracting footnotes from SEC filing…"):
        status = a.run_llm_extraction(cik)
    if status == "ok":
        st.success("Extraction complete")
        st.rerun()   # load_llm is uncached, so the panel re-renders with the new rows
    else:
        st.error(status)
