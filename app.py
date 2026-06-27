"""
Sales Competition Audit Portal
================================
Main entry point. Run with: streamlit run app.py
"""

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Audit Portal · Sales Competition",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject custom CSS ─────────────────────────────────────────────────────────
from ui.styles import inject_styles
inject_styles()

# ── Import page modules ───────────────────────────────────────────────────────
from ui.sidebar import render_sidebar
from ui.upload import render_upload
from ui.dashboard import render_dashboard

# ── Session state defaults ────────────────────────────────────────────────────
if "audit_results" not in st.session_state:
    st.session_state.audit_results = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "column_map" not in st.session_state:
    st.session_state.column_map = {}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="portal-header">
        <span class="portal-eyebrow">COMPETITION INTEGRITY</span>
        <h1 class="portal-title">Sales Audit Portal</h1>
        <p class="portal-sub">Upload · Map · Flag · Export</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar config (returns audit params) ─────────────────────────────────────
params = render_sidebar()

# ── Main content ──────────────────────────────────────────────────────────────
if st.session_state.audit_results is None:
    render_upload(params)
else:
    render_dashboard(params)
