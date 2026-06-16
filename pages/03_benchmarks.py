"""Page 3 — Sector Benchmarks (read-only view of the sector_benchmarks table)."""
import pandas as pd
import streamlit as st

import app_data as a
from benchmarks import HIGHER_IS_BETTER, LOWER_IS_BETTER

st.set_page_config(page_title="Benchmarks — Credit Warning System", layout="wide")

# ── Section A — filters ──────────────────────────────────────────────────────────────
st.title("📊 Sector Benchmarks")
st.caption("Peer metric distributions by sector and size — computed from healthy companies only.")

col1, col2 = st.columns(2)
with col1:
    sectors = ["All sectors"] + a.available_sectors()
    selected_sector = st.selectbox("Sector", sectors)
with col2:
    selected_size = st.selectbox("Size tier", ["All sizes", "Large", "Mid", "Small"])


def _arrow(metric: str) -> str:
    if metric in HIGHER_IS_BETTER:
        return "↑"
    if metric in LOWER_IS_BETTER:
        return "↓"
    return ""


# ── Section B — benchmark table ──────────────────────────────────────────────────────
rows = a.load_sector_benchmarks(
    sector_group=None if selected_sector == "All sectors" else selected_sector,
    size_category=None if selected_size == "All sizes" else selected_size,
)

if not rows:
    counts = a.sector_company_counts()
    n = counts.get(selected_sector, 0)
    if selected_sector == "All sectors":
        st.info("No benchmark data for this selection — try removing the size filter.")
    elif n == 0:
        st.warning(f"**{selected_sector}** — no companies in database yet. "
                   f"Use the Search page to add companies from this sector.")
    elif n < 3:
        st.warning(f"**{selected_sector}** — only {n} healthy "
                   f"{'company' if n == 1 else 'companies'} in database. "
                   f"Minimum 3 required for benchmark computation. "
                   f"Add more {selected_sector} companies to enable benchmarks.")
    else:
        st.info("No benchmark data for this selection — try removing the size filter.")
else:
    df = pd.DataFrame(rows)
    df["Metric"] = df["metric_name"].apply(lambda m: f"{_arrow(m)} {m}")
    # When viewing across sectors/sizes, show those columns so rows are distinguishable.
    multi_sector = selected_sector == "All sectors"
    multi_size = selected_size == "All sizes"
    df["p25"] = df["p25"].apply(lambda x: f"{x:.2f}" if x is not None else "—")
    df["Median (p50)"] = df["p50"].apply(lambda x: f"{x:.2f}" if x is not None else "—")
    df["p75"] = df["p75"].apply(lambda x: f"{x:.2f}" if x is not None else "—")
    df["Peers"] = df.apply(
        lambda r: f"{r['company_count']} healthy ({r['distressed_count']} distressed excl.)", axis=1)
    df["Precision"] = df["fallback_level"].map(
        {"full": "✅ full", "no_subsector": "sector+size", "sector_only": "⚠️ sector only"})

    cols = []
    if multi_sector:
        cols.append("sector_group")
    if multi_size:
        df["Size"] = df["size_category"]
        cols.append("Size")
    cols += ["Metric", "p25", "Median (p50)", "p75", "Peers", "Precision"]
    disp = df.rename(columns={"sector_group": "Sector"})
    cols = ["Sector" if c == "sector_group" else c for c in cols]

    # Median column shaded green for higher-is-better metrics (strength indicators).
    higher = df["metric_name"].isin(HIGHER_IS_BETTER).tolist()

    def _shade_median(col):
        return ["background-color: #dcfce7" if higher[i] else "" for i in range(len(col))]

    styler = disp[cols].style.apply(_shade_median, subset=["Median (p50)"])
    st.dataframe(styler, use_container_width=True, hide_index=True)

# ── Section C — sector overview cards (only on the full unfiltered view) ─────────────
if selected_sector == "All sectors" and selected_size == "All sizes":
    st.divider()
    st.subheader("Sector Coverage Overview")
    st.caption("Shows all defined sectors. Grey cards have insufficient healthy peers for "
               "benchmark computation.")

    counts = a.sector_company_counts()
    all_rows = a.load_sector_benchmarks()

    sectors_summary: dict = {}
    for r in all_rows:
        if r["fallback_level"] == "sector_only":
            s = r["sector_group"]
            sectors_summary.setdefault(s, {"companies": r["company_count"],
                                           "distressed_excl": r["distressed_count"]})
            if r["metric_name"] == "leverage":
                sectors_summary[s]["leverage_p50"] = r["p50"]
            if r["metric_name"] == "interest_coverage":
                sectors_summary[s]["coverage_p50"] = r["p50"]

    cards = st.columns(3)
    for i, sector in enumerate(a.ALL_SECTORS):
        with cards[i % 3]:
            if sector in sectors_summary:
                data = sectors_summary[sector]
                lev = f"{data['leverage_p50']:.1f}x" if data.get("leverage_p50") is not None else "—"
                cov = f"{data['coverage_p50']:.1f}x" if data.get("coverage_p50") is not None else "—"
                st.metric(label=sector, value=f"Leverage {lev}", delta=f"Coverage {cov}",
                          delta_color="off")
                st.caption(f"{data['companies']} healthy companies · "
                           f"{data['distressed_excl']} distressed excluded")
            else:
                n = counts.get(sector, 0)
                st.metric(label=sector, value="—", delta=None)
                if n == 0:
                    st.caption(":white_large_square: No companies in database")
                else:
                    st.caption(f":warning: {n} healthy {'company' if n == 1 else 'companies'} "
                               f"— need ≥3 for benchmarks")
