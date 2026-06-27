"""
ui/dashboard.py  ·  Results dashboard
======================================
Rendered after a successful audit run. Contains:
  - Metric cards (overview)
  - Filtered interactive table (with highlight styling)
  - Rep Risk Leaderboard
  - Historical trend chart
  - Whitelist management
  - Export button
"""

import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from core.whitelist import add_to_whitelist, remove_from_whitelist, get_all
from core.audit import RISK_CLEAN, RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL

# ── Colour constants (matching CSS vars) ─────────────────────────────────────
_AMBER   = "#f5a623"
_RED     = "#e03b3b"
_GREEN   = "#2ec27e"
_SURFACE = "#161a22"
_BORDER  = "#2a3040"
_TEXT    = "#e8ecf2"
_MUTED   = "#7a8499"

_RISK_COLOR = {
    RISK_CLEAN:    _GREEN,
    RISK_LOW:      "#7ecdf0",
    RISK_MEDIUM:   _AMBER,
    RISK_HIGH:     "#f07850",
    RISK_CRITICAL: _RED,
}

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color=_TEXT, size=11),
    margin=dict(l=10, r=10, t=30, b=10),
)


# ─────────────────────────────────────────────────────────────────────────────
# Metric card helper
# ─────────────────────────────────────────────────────────────────────────────

def _card(label: str, value, accent: str = "") -> str:
    cls = f"metric-value {accent}".strip()
    return (
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="{cls}">{value}</div>'
        f"</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Risk badge cell renderer
# ─────────────────────────────────────────────────────────────────────────────

def _style_risk(val: str) -> str:
    colour = _RISK_COLOR.get(val, _TEXT)
    return f"color: {colour}; font-weight: 600;"


def _style_flag(val: str) -> str:
    if val == "Y":
        return f"color: {_RED}; font-weight:600;"
    return ""


def _style_row(row: pd.Series) -> list[str]:
    """Background tint based on risk level for whole-row styling."""
    risk = row.get("Risk Level", RISK_CLEAN)
    tints = {
        RISK_CRITICAL: "background-color: rgba(224,59,59,.10);",
        RISK_HIGH:     "background-color: rgba(240,120,80,.07);",
        RISK_MEDIUM:   "background-color: rgba(245,166,35,.06);",
    }
    base = tints.get(risk, "")
    return [base] * len(row)


# ─────────────────────────────────────────────────────────────────────────────
# Export helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Audit Results")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Main dashboard render
# ─────────────────────────────────────────────────────────────────────────────

def render_dashboard(params: dict):
    results     = st.session_state.audit_results
    df          = results["df"].copy()
    summary     = results["summary"]
    rep_summary = results["rep_summary"].copy()

    # ── 1. Overview metric cards ──────────────────────────────────────────────
    st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.markdown(_card("Total Accounts", f"{summary['total']:,}"), unsafe_allow_html=True)
    with c2: st.markdown(_card("Flagged", f"{summary['total_flagged']:,}", "amber"), unsafe_allow_html=True)
    with c3: st.markdown(_card("Flag Rate", f"{summary['flag_rate']}%", "amber"), unsafe_allow_html=True)
    with c4: st.markdown(_card("Out-of-Market", f"{summary['oom_flags']:,}", "red"), unsafe_allow_html=True)
    with c5: st.markdown(_card("Setter Flags", f"{summary['setter_flags']:,}", "red"), unsafe_allow_html=True)
    with c6: st.markdown(_card("Geo Errors", f"{summary['geo_errors']:,}", "red" if summary['geo_errors'] > 0 else ""), unsafe_allow_html=True)

    # ── 2. Tabs ───────────────────────────────────────────────────────────────
    tab_data, tab_leaderboard, tab_trends, tab_whitelist = st.tabs([
        "📋  Account Data",
        "🏴  Rep Leaderboard",
        "📈  Trend Chart",
        "✅  Whitelist",
    ])

    # ── TAB 1: Account Data ───────────────────────────────────────────────────
    with tab_data:
        st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            rounds = ["All"] + sorted(df["Round"].unique().tolist())
            sel_round = st.selectbox("Round", rounds)
        with f2:
            cities = ["All"] + sorted(df["Office City"].unique().tolist())
            sel_city = st.selectbox("Office City", cities)
        with f3:
            reps = ["All"] + sorted(df["Sales Rep Name"].unique().tolist())
            sel_rep = st.selectbox("Rep Name", reps)
        with f4:
            flag_options = ["All", "Flagged Only", "Clean Only", "Critical Only"]
            sel_flag = st.selectbox("Flag Status", flag_options)

        # Apply filters
        view = df.copy()
        if sel_round != "All":
            view = view[view["Round"] == sel_round]
        if sel_city != "All":
            view = view[view["Office City"] == sel_city]
        if sel_rep != "All":
            view = view[view["Sales Rep Name"] == sel_rep]
        if sel_flag == "Flagged Only":
            view = view[view["Flag Count"] > 0]
        elif sel_flag == "Clean Only":
            view = view[view["Flag Count"] == 0]
        elif sel_flag == "Critical Only":
            view = view[view["Risk Level"] == RISK_CRITICAL]

        # Display columns (hide internal helpers)
        display_cols = [
            "Sales Rep Name", "Sales Rep ID", "Customer Name", "Customer Address",
            "Office City", "Round",
            "Distance (miles)", "Out of Market", "Setter Flag", "Velocity Flag",
            "Risk Level", "Flag Notes", "Whitelisted",
        ]
        view_display = view[[c for c in display_cols if c in view.columns]]

        st.markdown(
            f'<p style="font-family:\'IBM Plex Mono\',monospace;font-size:.75rem;color:{_MUTED};">'
            f"Showing {len(view_display):,} of {len(df):,} accounts</p>",
            unsafe_allow_html=True,
        )

        styled = (
            view_display.style
            .apply(_style_row, axis=1)
            .applymap(_style_risk, subset=["Risk Level"])
            .applymap(_style_flag, subset=["Out of Market", "Setter Flag", "Velocity Flag"])
        )
        st.dataframe(styled, use_container_width=True, height=500)

        # Export
        st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
        xlsx_bytes = _to_excel(view)
        st.download_button(
            label="⬇ Download Filtered Results (.xlsx)",
            data=xlsx_bytes,
            file_name="audit_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── TAB 2: Rep Leaderboard ────────────────────────────────────────────────
    with tab_leaderboard:
        st.markdown('<div class="section-label">Leaderboard of Shame · Ranked by Total Flags</div>', unsafe_allow_html=True)

        top_n = st.slider("Show top N reps", 5, min(50, len(rep_summary)), min(20, len(rep_summary)))
        board = rep_summary.head(top_n).copy()

        board_display = board.rename(columns={
            "Sales Rep ID":    "Rep ID",
            "Sales Rep Name":  "Rep Name",
            "total_accounts":  "Accounts",
            "total_flags":     "Total Flags",
            "oom":             "OOM",
            "setter":          "Setter",
            "velocity":        "Velocity",
            "critical":        "Critical",
            "Flag Rate %":     "Flag Rate %",
        })

        def _color_flags(val):
            if isinstance(val, (int, float)) and val > 0:
                return f"color:{_AMBER};font-weight:600;"
            return ""

        def _color_rate(val):
            if isinstance(val, float):
                if val >= 50:
                    return f"color:{_RED};font-weight:600;"
                elif val >= 20:
                    return f"color:{_AMBER};"
            return ""

        styled_board = (
            board_display.style
            .applymap(_color_flags, subset=["Total Flags", "OOM", "Setter", "Velocity", "Critical"])
            .applymap(_color_rate, subset=["Flag Rate %"])
        )
        st.dataframe(styled_board, use_container_width=True, height=500)

        # Bar chart
        if len(board) > 0:
            fig = go.Figure(go.Bar(
                y=board["Sales Rep Name"],
                x=board["total_flags"],
                orientation="h",
                marker_color=_AMBER,
                hovertemplate="%{y}: %{x} flags<extra></extra>",
            ))
            fig.update_layout(
                **_PLOTLY_LAYOUT,
                title="Total Flags per Rep",
                xaxis_title="Flags",
                yaxis=dict(autorange="reversed", gridcolor=_BORDER),
                xaxis=dict(gridcolor=_BORDER),
                height=max(300, top_n * 28),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: Historical Trend ───────────────────────────────────────────────
    with tab_trends:
        st.markdown('<div class="section-label">Flag Volume by Round</div>', unsafe_allow_html=True)

        trend = (
            df[df["Flag Count"] > 0]
            .groupby("Round")
            .agg(
                total_flags=("Flag Count", "sum"),
                oom=("Out of Market", lambda x: (x == "Y").sum()),
                setter=("Setter Flag", lambda x: (x == "Y").sum()),
                velocity=("Velocity Flag", lambda x: (x == "Y").sum()),
            )
            .reset_index()
            .sort_values("Round")
        )

        if len(trend) == 0:
            st.info("No flagged accounts to chart.")
        else:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="Out of Market",
                x=trend["Round"],
                y=trend["oom"],
                marker_color=_RED,
            ))
            fig2.add_trace(go.Bar(
                name="Setter",
                x=trend["Round"],
                y=trend["setter"],
                marker_color=_AMBER,
            ))
            fig2.add_trace(go.Bar(
                name="Velocity Spike",
                x=trend["Round"],
                y=trend["velocity"],
                marker_color="#7ecdf0",
            ))
            fig2.add_trace(go.Scatter(
                name="Total Flags",
                x=trend["Round"],
                y=trend["total_flags"],
                mode="lines+markers",
                line=dict(color=_TEXT, width=2, dash="dot"),
            ))
            fig2.update_layout(
                **_PLOTLY_LAYOUT,
                barmode="stack",
                xaxis=dict(title="Round", gridcolor=_BORDER),
                yaxis=dict(title="Flag Count", gridcolor=_BORDER),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=380,
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Clean accounts per round too
            clean_trend = (
                df.groupby("Round")
                .agg(
                    total=("Flag Count", "count"),
                    flagged=("Flag Count", lambda x: (x > 0).sum()),
                )
                .reset_index()
                .sort_values("Round")
            )
            clean_trend["clean"] = clean_trend["total"] - clean_trend["flagged"]
            clean_trend["flag_rate"] = (clean_trend["flagged"] / clean_trend["total"].clip(1) * 100).round(1)

            fig3 = go.Figure(go.Scatter(
                x=clean_trend["Round"],
                y=clean_trend["flag_rate"],
                mode="lines+markers",
                line=dict(color=_AMBER, width=3),
                fill="tozeroy",
                fillcolor="rgba(245,166,35,.08)",
                hovertemplate="Round %{x}<br>Flag rate: %{y}%<extra></extra>",
            ))
            fig3.update_layout(
                **_PLOTLY_LAYOUT,
                title="Flag Rate % per Round",
                xaxis=dict(gridcolor=_BORDER),
                yaxis=dict(title="Flag Rate %", gridcolor=_BORDER),
                height=280,
            )
            st.plotly_chart(fig3, use_container_width=True)

    # ── TAB 4: Whitelist ──────────────────────────────────────────────────────
    with tab_whitelist:
        st.markdown('<div class="section-label">Approve Exceptions</div>', unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-family:\'IBM Plex Mono\',monospace;font-size:.78rem;color:{_MUTED};">'
            "Whitelisted accounts are excluded from flag counts in future runs. "
            "Keys are stored in <code>whitelist.csv</code>.</p>",
            unsafe_allow_html=True,
        )

        flagged_df = df[df["Flag Count"] > 0].copy()

        if len(flagged_df) == 0:
            st.success("No flagged accounts — nothing to whitelist.")
        else:
            flagged_df["Select"] = False
            editable = flagged_df[[
                "Sales Rep Name", "Customer Address", "Risk Level",
                "Flag Notes", "Whitelist Key", "Whitelisted",
            ]].copy()

            st.markdown("**Select rows to whitelist:**")
            selection = st.data_editor(
                editable.assign(Approve=False),
                column_config={
                    "Approve": st.column_config.CheckboxColumn("Approve", default=False),
                    "Whitelist Key": st.column_config.TextColumn(disabled=True),
                    "Whitelisted": st.column_config.CheckboxColumn("Already WL?", disabled=True),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                height=360,
            )

            keys_to_add = selection.loc[selection["Approve"], "Whitelist Key"].tolist()

            col_add, col_clear = st.columns(2)
            with col_add:
                if st.button("✓ Add Selected to Whitelist", disabled=len(keys_to_add) == 0):
                    add_to_whitelist(keys_to_add)
                    st.success(f"Added {len(keys_to_add)} key(s) to whitelist.")

            with col_clear:
                all_keys = get_all()
                if len(all_keys) > 0:
                    if st.button(f"✕ Clear Entire Whitelist ({len(all_keys)} entries)"):
                        remove_from_whitelist(all_keys)
                        st.warning("Whitelist cleared.")

        # Show current whitelist contents
        current = get_all()
        if current:
            with st.expander(f"Current whitelist — {len(current)} entries"):
                st.code("\n".join(current), language=None)
