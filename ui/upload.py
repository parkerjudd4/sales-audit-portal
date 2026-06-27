"""
ui/upload.py  ·  File upload + dynamic column mapping + Run Audit
=================================================================
Handles:
  - xlsx / csv upload
  - smart auto-mapping of column names
  - fallback UI dropdowns when auto-map fails
  - triggers core audit on button press
"""

import io
import streamlit as st
import pandas as pd

from core.audit import run_full_audit

# ── The canonical field names the system needs ────────────────────────────────
# Required for audit logic
REQUIRED_FIELDS = [
    "Sales Rep Name",
    "Sales Rep ID",
    "Customer Name",
    "Customer Address",
    "Office City",
    "Round",
]

# Optional but passed through for filtering / display
OPTIONAL_FIELDS = [
    "Pool",
    "State",
    "Event Name",
    "Event Date",
    "Location ID",
]

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Common aliases for smart auto-mapping (lower-cased keys)
_ALIASES: dict[str, list[str]] = {
    "Sales Rep Name":  ["sales_rep_name", "rep name", "salesperson", "sales rep", "rep", "agent name", "seller"],
    "Sales Rep ID":    ["sales_rep_id", "rep id", "employee id", "rep #", "salesperson id", "agent id", "user id"],
    "Customer Name":   ["customer_name", "customer", "client name", "account name", "homeowner", "lead name"],
    "Customer Address":["address", "customer address", "install address", "site address", "home address"],
    "Office City":     ["office", "city", "home office", "branch", "office location", "market", "territory"],
    "Round":           ["round", "competition round", "contest round", "week", "period", "round of the competition"],
    # Optional
    "Pool":            ["pool", "competition pool", "group"],
    "State":           ["state", "st", "rep state"],
    "Event Name":      ["event_name", "event name", "event"],
    "Event Date":      ["event_date", "event date", "date"],
    "Location ID":     ["location_id", "location id", "loc id", "site id"],
}


def _auto_map(columns: list[str]) -> dict[str, str | None]:
    """
    Try to auto-map sheet columns to required + optional fields.
    Returns {canonical_field: matched_column or None}.
    """
    col_lower = {c.lower().strip().replace("_", " "): c for c in columns}
    mapping: dict[str, str | None] = {}

    for field in ALL_FIELDS:
        matched = None
        # 1. Exact match (normalised)
        if field.lower() in col_lower:
            matched = col_lower[field.lower()]
        else:
            # 2. Alias match
            for alias in _ALIASES.get(field, []):
                if alias in col_lower:
                    matched = col_lower[alias]
                    break
        mapping[field] = matched

    return mapping


def _load_file(uploaded) -> pd.DataFrame | None:
    """Read an uploaded xlsx or csv into a DataFrame."""
    try:
        if uploaded.name.endswith(".csv"):
            return pd.read_csv(uploaded)
        else:
            return pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return None


def render_upload(params: dict):
    """Main upload + mapping UI. Triggers audit on button press."""

    # ── Upload widget ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label">01 · Upload Account Sheet</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop an Excel (.xlsx) or CSV (.csv) file",
        type=["xlsx", "csv"],
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.markdown(
            """
            <div style="text-align:center;padding:2rem;color:#7a8499;
                        font-family:'IBM Plex Mono',monospace;font-size:.8rem;">
                No file uploaded yet.<br>
                Supported formats: <strong>.xlsx</strong> and <strong>.csv</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Load & preview ─────────────────────────────────────────────────────
    df = _load_file(uploaded)
    if df is None:
        return

    st.session_state.raw_df = df

    with st.expander(f"Preview — {len(df):,} rows × {len(df.columns)} columns", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    # ── Column mapping ─────────────────────────────────────────────────────
    st.markdown('<div class="section-label">02 · Map Columns</div>', unsafe_allow_html=True)

    auto_map = _auto_map(list(df.columns))
    req_missing = [f for f in REQUIRED_FIELDS if auto_map.get(f) is None]

    if not req_missing:
        st.success(
            "✓ All required columns were automatically detected. "
            "Review the mapping below or adjust as needed."
        )
    else:
        st.warning(
            f"⚠ {len(req_missing)} required column(s) could not be auto-matched. "
            "Please assign them using the dropdowns below."
        )

    col_options = [None] + list(df.columns)
    mapping: dict[str, str] = {}

    # ── Required fields (shown prominently) ────────────────────────────────
    st.markdown("**Required Fields**")
    cols_left, cols_right = st.columns(2)
    for i, field in enumerate(REQUIRED_FIELDS):
        target_col = cols_left if i % 2 == 0 else cols_right
        with target_col:
            current = auto_map.get(field)
            idx = col_options.index(current) if current in col_options else 0
            chosen = st.selectbox(
                f"**{field}** ✱",
                options=col_options,
                index=idx,
                key=f"map_{field}",
                format_func=lambda x: "— select —" if x is None else x,
            )
            mapping[field] = chosen

    # ── Optional fields (shown in expander) ────────────────────────────────
    with st.expander("Optional Fields (Pool, State, Event Name, Event Date, Location ID)"):
        opt_left, opt_right = st.columns(2)
        for i, field in enumerate(OPTIONAL_FIELDS):
            target_col = opt_left if i % 2 == 0 else opt_right
            with target_col:
                current = auto_map.get(field)
                idx = col_options.index(current) if current in col_options else 0
                chosen = st.selectbox(
                    field,
                    options=col_options,
                    index=idx,
                    key=f"map_{field}",
                    format_func=lambda x: "— not mapped —" if x is None else x,
                )
                mapping[field] = chosen

    st.session_state.column_map = mapping

    # ── Validation (required only) ──────────────────────────────────────────
    unmapped = [f for f in REQUIRED_FIELDS if mapping.get(f) is None]
    if unmapped:
        st.error(f"Still unmapped (required): {', '.join(unmapped)}")
        st.stop()

    # ── Run Audit button ───────────────────────────────────────────────────
    st.markdown('<div class="section-label">03 · Run Audit</div>', unsafe_allow_html=True)

    total = len(df)
    pool_col = mapping.get("Pool")
    pool_info = f" · {df[pool_col].nunique()} pool(s)" if pool_col else ""
    st.markdown(
        f'<p style="font-family:\'IBM Plex Mono\',monospace;font-size:.8rem;color:#7a8499;">'
        f"{total:,} accounts queued for audit across "
        f"{df[mapping['Round']].nunique()} round(s)"
        f"{pool_info} · "
        f"{df[mapping['Sales Rep ID']].nunique()} unique rep IDs</p>",
        unsafe_allow_html=True,
    )

    if st.button("▶ Run Audit", use_container_width=True):
        with st.spinner("Geocoding addresses and running audit checks…"):
            results = run_full_audit(df, mapping, params)
        st.session_state.audit_results = results
        st.rerun()
