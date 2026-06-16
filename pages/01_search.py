"""Page 1 — Company Search."""
import streamlit as st

import app_data as a

st.set_page_config(page_title="Search — Credit Warning System", layout="wide")
st.title("🔍 Company Search")


def _go_to_monitor(cik: str):
    st.session_state["selected_cik"] = cik
    st.switch_page("pages/02_monitor.py")


# ---- EDGAR full-text search ----
query = st.text_input("Search SEC-registered companies (10-K filers)", placeholder="e.g. Apple")
if query:
    with st.spinner("Searching EDGAR…"):
        results, err = a.edgar_search(query)
    if err:
        st.warning(err)
    elif not results:
        st.info("No matching 10-K filers found.")
    else:
        st.caption(f"{len(results)} matches — click **Monitor** to open.")
        for r in results:
            c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
            c1.write(f"**{r['name']}**")
            c2.write(f"CIK {r['cik']}")
            c3.write(f"SIC {r['sic'] or '—'}")
            if c4.button("Monitor", key=f"s_{r['cik']}"):
                _go_to_monitor(r["cik"])

# ---- Recently monitored (companies already in the database) ----
st.divider()
st.subheader("Recently Monitored")
st.caption("Companies already in credit_warning.db — click to open the monitor.")
rows = a.recently_monitored()
if not rows:
    st.info("No companies in the database yet.")
else:
    for r in rows:
        c1, c2, c3, c4 = st.columns([4, 3, 2, 1])
        c1.write(f"**{r['name']}**")
        c2.write(r["sector_group"] or "—")
        c3.write(r["size_category"] or "—")
        if c4.button("Monitor", key=f"db_{r['cik']}"):
            _go_to_monitor(r["cik"])
