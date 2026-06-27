"""
ui/sidebar.py  ·  Sidebar configuration panel
==============================================
Returns a dict of audit parameters used throughout the app.
"""

import streamlit as st


def render_sidebar() -> dict:
    """Render the sidebar and return a params dict."""
    with st.sidebar:
        st.markdown(
            '<p style="font-family:\'IBM Plex Mono\',monospace;font-size:.65rem;'
            'letter-spacing:.14em;text-transform:uppercase;color:#f5a623;">'
            "⚙ Audit Config</p>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Out-of-Market settings ─────────────────────────────────────────
        st.markdown("**Geographic Limits**")
        max_radius = st.slider(
            "Max Allowed Radius (miles)",
            min_value=10,
            max_value=300,
            value=75,
            step=5,
            help="Accounts with customer addresses beyond this distance from the rep's office city will be flagged.",
        )

        medium_risk_radius = st.slider(
            "Medium-Risk Threshold (miles)",
            min_value=5,
            max_value=max_radius,
            value=min(50, max_radius - 5),
            step=5,
            help="Accounts beyond this but within the max radius get a medium-risk tag.",
        )

        st.markdown("---")

        # ── Setter / velocity settings ─────────────────────────────────────
        st.markdown("**Setter Detection**")
        fuzzy_threshold = st.slider(
            "Address Similarity Threshold (%)",
            min_value=70,
            max_value=100,
            value=88,
            step=1,
            help="How similar two addresses must be to count as a duplicate. 100 = exact match only.",
        )

        velocity_multiplier = st.slider(
            "Velocity Spike Multiplier",
            min_value=1.5,
            max_value=5.0,
            value=2.5,
            step=0.5,
            help="A rep whose round volume exceeds their baseline by this multiplier gets flagged.",
        )

        st.markdown("---")

        # ── Geocoding settings ─────────────────────────────────────────────
        st.markdown("**Geocoding**")
        geocode_delay = st.number_input(
            "Delay between requests (sec)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.5,
            help="Nominatim requires ≥1 second between requests. Increase if you hit rate limits.",
        )

        st.markdown("---")

        # ── Reset button ───────────────────────────────────────────────────
        if st.button("↩ New Upload / Reset"):
            for key in ["audit_results", "raw_df", "column_map"]:
                st.session_state[key] = None
            st.rerun()

        st.markdown(
            '<p style="font-family:\'IBM Plex Mono\',monospace;font-size:.6rem;'
            'color:#7a8499;margin-top:2rem;">Audit Portal v1.0</p>',
            unsafe_allow_html=True,
        )

    return {
        "max_radius": max_radius,
        "medium_risk_radius": medium_risk_radius,
        "fuzzy_threshold": fuzzy_threshold,
        "velocity_multiplier": velocity_multiplier,
        "geocode_delay": geocode_delay,
    }
