"""
streamlit_app.py — interactive UI for the Credit Warning System.

Wraps the existing extraction / metric / benchmark layers. Search and Company Monitor pages
only (backtest and benchmarks pages are not built here). Run: streamlit run streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="Credit Warning System", layout="wide")
st.title("Credit Warning System")
st.markdown(
    "Search for any SEC-registered company to monitor credit stress metrics, peer-relative "
    "quartiles, and LLM-extracted footnote terms.\n\n"
    "Use the **Search** page (left sidebar) to find a company or pick one already monitored, "
    "then view it on the **Company Monitor** page."
)
st.info("👈 Open **Search** in the sidebar to begin.")
