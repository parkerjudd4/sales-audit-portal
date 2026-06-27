"""
ui/styles.py  ·  Visual identity for the Audit Portal
=====================================================
Design direction: forensic command-center aesthetic.
Palette: near-black base, cold white type, amber alert accents,
         electric red for high-risk, muted slate for neutral.
Typography: monospace utility face for data; clean sans for prose.
Signature element: amber "evidence tape" stripe that runs across
                   flagged rows.
"""

import streamlit as st


def inject_styles():
    st.markdown(
        """
        <style>
        /* ── Fonts ─────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

        /* ── Root tokens ───────────────────────────── */
        :root {
            --bg:          #0d0f14;
            --surface:     #161a22;
            --surface-2:   #1e2330;
            --border:      #2a3040;
            --text:        #e8ecf2;
            --text-muted:  #7a8499;
            --amber:       #f5a623;
            --amber-dim:   rgba(245,166,35,.15);
            --red:         #e03b3b;
            --red-dim:     rgba(224,59,59,.12);
            --green:       #2ec27e;
            --mono:        'IBM Plex Mono', monospace;
            --sans:        'Inter', sans-serif;
        }

        /* ── Global reset ──────────────────────────── */
        html, body, [class*="css"] {
            font-family: var(--sans);
            background-color: var(--bg) !important;
            color: var(--text) !important;
        }
        .stApp { background-color: var(--bg) !important; }
        .block-container { padding-top: 1rem !important; max-width: 1400px; }

        /* ── Sidebar ───────────────────────────────── */
        [data-testid="stSidebar"] {
            background: var(--surface) !important;
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] * { color: var(--text) !important; }

        /* ── Portal header ─────────────────────────── */
        .portal-header {
            border-left: 4px solid var(--amber);
            padding: .6rem 0 .6rem 1.2rem;
            margin-bottom: 1.6rem;
        }
        .portal-eyebrow {
            font-family: var(--mono);
            font-size: .65rem;
            letter-spacing: .18em;
            color: var(--amber) !important;
            text-transform: uppercase;
        }
        .portal-title {
            font-size: 1.9rem !important;
            font-weight: 700;
            margin: .1rem 0 !important;
            line-height: 1.1;
        }
        .portal-sub {
            font-family: var(--mono);
            font-size: .75rem;
            color: var(--text-muted) !important;
            margin: 0 !important;
            letter-spacing: .06em;
        }

        /* ── Metric cards ──────────────────────────── */
        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem 1.2rem;
            font-family: var(--mono);
        }
        .metric-label {
            font-size: .65rem;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: .3rem;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 600;
            color: var(--text);
            line-height: 1;
        }
        .metric-value.amber  { color: var(--amber); }
        .metric-value.red    { color: var(--red); }
        .metric-value.green  { color: var(--green); }

        /* ── Section labels ────────────────────────── */
        .section-label {
            font-family: var(--mono);
            font-size: .65rem;
            letter-spacing: .14em;
            text-transform: uppercase;
            color: var(--amber);
            border-bottom: 1px solid var(--border);
            padding-bottom: .4rem;
            margin: 1.6rem 0 .8rem;
        }

        /* ── Upload zone ───────────────────────────── */
        [data-testid="stFileUploader"] {
            border: 1px dashed var(--border) !important;
            border-radius: 6px !important;
            background: var(--surface) !important;
        }

        /* ── Buttons ───────────────────────────────── */
        .stButton > button {
            background: var(--amber) !important;
            color: #000 !important;
            font-family: var(--mono) !important;
            font-weight: 600 !important;
            font-size: .8rem !important;
            letter-spacing: .05em !important;
            border: none !important;
            border-radius: 4px !important;
            padding: .5rem 1.4rem !important;
        }
        .stButton > button:hover {
            background: #ffb830 !important;
        }
        .stDownloadButton > button {
            background: var(--surface-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            font-family: var(--mono) !important;
            font-size: .75rem !important;
            border-radius: 4px !important;
        }

        /* ── Inputs / selects ──────────────────────── */
        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            background: var(--surface-2) !important;
            border-color: var(--border) !important;
            color: var(--text) !important;
        }
        .stSlider > div { color: var(--text) !important; }

        /* ── Tables ────────────────────────────────── */
        .stDataFrame {
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            overflow: hidden !important;
        }

        /* ── Expander ──────────────────────────────── */
        .streamlit-expanderHeader {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 4px !important;
            font-family: var(--mono) !important;
            font-size: .8rem !important;
            color: var(--text) !important;
        }

        /* ── Alert boxes ───────────────────────────── */
        .stAlert { border-radius: 4px !important; }

        /* ── Tabs ──────────────────────────────────── */
        .stTabs [role="tablist"] {
            border-bottom: 1px solid var(--border) !important;
            gap: .2rem;
        }
        .stTabs [role="tab"] {
            font-family: var(--mono) !important;
            font-size: .75rem !important;
            letter-spacing: .05em !important;
            color: var(--text-muted) !important;
            border-radius: 4px 4px 0 0 !important;
            padding: .4rem .9rem !important;
        }
        .stTabs [aria-selected="true"] {
            color: var(--amber) !important;
            border-bottom: 2px solid var(--amber) !important;
        }

        /* ── Plotly chart backgrounds ──────────────── */
        .js-plotly-plot .plotly { background: transparent !important; }

        /* ── Scrollbar ─────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
