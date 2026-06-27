"""
core/audit.py  ·  Full audit orchestration
==========================================
Runs Feature A (out-of-market) and Feature B (setter/velocity)
and returns a fully annotated DataFrame plus summary stats.
"""

import pandas as pd
import numpy as np
from itertools import combinations

from core.geocoder import geocode_addresses, calculate_distance_miles
from core.normalizer import normalize_address, address_similarity, name_similarity
from core.whitelist import build_key, is_whitelisted

# ── Risk level constants ──────────────────────────────────────────────────────
RISK_CLEAN   = "Clean"
RISK_LOW     = "Low"
RISK_MEDIUM  = "Medium"
RISK_HIGH    = "High"
RISK_CRITICAL = "Critical"

RISK_ORDER = {RISK_CLEAN: 0, RISK_LOW: 1, RISK_MEDIUM: 2, RISK_HIGH: 3, RISK_CRITICAL: 4}


def _escalate(current: str, new: str) -> str:
    """Return whichever risk level is higher."""
    return current if RISK_ORDER[current] >= RISK_ORDER[new] else new


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_full_audit(
    raw_df: pd.DataFrame,
    column_map: dict[str, str],
    params: dict,
) -> dict:
    """
    Parameters
    ----------
    raw_df      : original uploaded DataFrame
    column_map  : {required_field: actual_column_name}
    params      : audit config from sidebar

    Returns
    -------
    dict with keys:
        df          : annotated DataFrame
        summary     : high-level stats dict
        rep_summary : per-rep aggregated DataFrame
    """

    # ── 1. Remap columns to canonical names ──────────────────────────────────
    rename = {v: k for k, v in column_map.items()}
    df = raw_df.rename(columns=rename).copy()

    # Coerce IDs to string
    df["Sales Rep ID"] = df["Sales Rep ID"].astype(str).str.strip()
    df["Sales Rep Name"] = df["Sales Rep Name"].astype(str).str.strip()
    df["Customer Address"] = df["Customer Address"].astype(str).str.strip()
    df["Office City"] = df["Office City"].astype(str).str.strip()
    df["Round"] = df["Round"].astype(str).str.strip()
    df["Customer Name"] = df["Customer Name"].astype(str).str.strip()
    # Optional fields — coerce only if present
    for opt in ["Pool", "State", "Event Name", "Event Date", "Location ID"]:
        if opt in df.columns:
            df[opt] = df[opt].astype(str).str.strip()

    # ── 2. Add result columns ─────────────────────────────────────────────────
    df["Norm Address"]        = df["Customer Address"].apply(normalize_address)
    df["Distance (miles)"]    = np.nan
    df["Out of Market"]       = "N"
    df["Geo Error"]           = False
    df["Setter Flag"]         = "N"
    df["Setter Reason"]       = ""
    df["Velocity Flag"]       = "N"
    df["Risk Level"]          = RISK_CLEAN
    df["Whitelist Key"]       = df.apply(
        lambda r: build_key(r["Sales Rep ID"], r["Norm Address"]), axis=1
    )
    df["Whitelisted"]         = df["Whitelist Key"].apply(is_whitelisted)
    df["Flag Count"]          = 0
    df["Flag Notes"]          = ""

    # ── 3. Feature A: Geocode and distance check ──────────────────────────────
    all_addresses = list(df["Customer Address"].unique())
    office_cities = list(df["Office City"].unique())
    all_to_geocode = all_addresses + office_cities

    coords = geocode_addresses(
        all_to_geocode,
        delay=params["geocode_delay"],
        progress_label="Geocoding addresses",
    )

    max_r  = params["max_radius"]
    med_r  = params["medium_risk_radius"]

    for idx, row in df.iterrows():
        if row["Whitelisted"]:
            df.at[idx, "Flag Notes"] = "Whitelisted"
            continue

        cust_coords   = coords.get(row["Customer Address"])
        office_coords = coords.get(row["Office City"])

        if cust_coords is None or office_coords is None:
            df.at[idx, "Geo Error"]     = True
            df.at[idx, "Out of Market"] = "Error"
            df.at[idx, "Risk Level"]    = RISK_CRITICAL
            df.at[idx, "Flag Count"]   += 1
            df.at[idx, "Flag Notes"]    = (
                df.at[idx, "Flag Notes"] + " | Geocode failed"
            ).lstrip(" | ")
            continue

        dist = calculate_distance_miles(cust_coords, office_coords)
        df.at[idx, "Distance (miles)"] = round(dist, 1) if dist is not None else np.nan

        if dist is not None:
            if dist > max_r:
                df.at[idx, "Out of Market"] = "Y"
                df.at[idx, "Risk Level"]    = _escalate(df.at[idx, "Risk Level"], RISK_HIGH)
                df.at[idx, "Flag Count"]   += 1
                df.at[idx, "Flag Notes"]    = (
                    df.at[idx, "Flag Notes"] + f" | OOM {dist:.0f}mi (>{max_r}mi)"
                ).lstrip(" | ")
            elif dist > med_r:
                df.at[idx, "Out of Market"] = "Y"
                df.at[idx, "Risk Level"]    = _escalate(df.at[idx, "Risk Level"], RISK_MEDIUM)
                df.at[idx, "Flag Count"]   += 1
                df.at[idx, "Flag Notes"]    = (
                    df.at[idx, "Flag Notes"] + f" | OOM {dist:.0f}mi (>{med_r}mi)"
                ).lstrip(" | ")

    # ── 4. Feature B: Setter / duplicate address detection ────────────────────
    threshold = params["fuzzy_threshold"]

    # Group by normalized address — exact duplicates first (fast path)
    addr_to_reps: dict[str, set[str]] = {}
    for idx, row in df.iterrows():
        norm = row["Norm Address"]
        rep  = row["Sales Rep ID"]
        addr_to_reps.setdefault(norm, set()).add(rep)

    # Mark rows where an exact-norm address was submitted by >1 rep
    for idx, row in df.iterrows():
        if row["Whitelisted"]:
            continue
        reps = addr_to_reps.get(row["Norm Address"], set())
        if len(reps) > 1:
            df.at[idx, "Setter Flag"]  = "Y"
            df.at[idx, "Setter Reason"] = f"Address shared by {len(reps)} reps"
            df.at[idx, "Risk Level"]   = _escalate(df.at[idx, "Risk Level"], RISK_HIGH)
            df.at[idx, "Flag Count"]  += 1
            df.at[idx, "Flag Notes"]   = (
                df.at[idx, "Flag Notes"] + " | Shared address"
            ).lstrip(" | ")

    # Fuzzy duplicate check across unique norm addresses (pairwise, capped for performance)
    unique_norms = df["Norm Address"].unique().tolist()
    # Only fuzzy-check if the dataset isn't massive (cap at 2000 pairwise for speed)
    if len(unique_norms) <= 200:
        for a, b in combinations(unique_norms, 2):
            sim = address_similarity(a, b)
            if sim >= threshold and sim < 100:  # exact already handled above
                reps_a = addr_to_reps.get(a, set())
                reps_b = addr_to_reps.get(b, set())
                if reps_a != reps_b:
                    mask = df["Norm Address"].isin([a, b])
                    for idx in df[mask].index:
                        if df.at[idx, "Whitelisted"]:
                            continue
                        if df.at[idx, "Setter Flag"] != "Y":
                            df.at[idx, "Setter Flag"]   = "Y"
                            df.at[idx, "Setter Reason"] = f"Fuzzy-similar address ({sim:.0f}% match) across reps"
                            df.at[idx, "Risk Level"]    = _escalate(df.at[idx, "Risk Level"], RISK_MEDIUM)
                            df.at[idx, "Flag Count"]   += 1
                            df.at[idx, "Flag Notes"]    = (
                                df.at[idx, "Flag Notes"] + f" | Fuzzy addr {sim:.0f}%"
                            ).lstrip(" | ")

    # Customer name duplicate across reps
    name_to_reps: dict[str, set[str]] = {}
    for idx, row in df.iterrows():
        norm_name = row["Customer Name"].lower().strip()
        name_to_reps.setdefault(norm_name, set()).add(row["Sales Rep ID"])

    for idx, row in df.iterrows():
        if row["Whitelisted"]:
            continue
        norm_name = row["Customer Name"].lower().strip()
        reps = name_to_reps.get(norm_name, set())
        if len(reps) > 1 and row["Setter Flag"] != "Y":
            df.at[idx, "Setter Flag"]   = "Y"
            df.at[idx, "Setter Reason"] = f"Customer name shared by {len(reps)} reps"
            df.at[idx, "Risk Level"]    = _escalate(df.at[idx, "Risk Level"], RISK_MEDIUM)
            df.at[idx, "Flag Count"]   += 1
            df.at[idx, "Flag Notes"]    = (
                df.at[idx, "Flag Notes"] + " | Shared customer name"
            ).lstrip(" | ")

    # ── 5. Feature B cont.: Velocity / spike detection ────────────────────────
    mult = params["velocity_multiplier"]

    round_counts = (
        df.groupby(["Sales Rep ID", "Round"])
        .size()
        .reset_index(name="round_count")
    )

    rep_baseline = (
        round_counts.groupby("Sales Rep ID")["round_count"]
        .mean()
        .reset_index()
        .rename(columns={"round_count": "baseline"})
    )

    round_counts = round_counts.merge(rep_baseline, on="Sales Rep ID")
    spike_mask   = round_counts["round_count"] > (round_counts["baseline"] * mult)
    spike_combos = set(
        zip(
            round_counts.loc[spike_mask, "Sales Rep ID"],
            round_counts.loc[spike_mask, "Round"],
        )
    )

    for idx, row in df.iterrows():
        if row["Whitelisted"]:
            continue
        key = (row["Sales Rep ID"], row["Round"])
        if key in spike_combos:
            df.at[idx, "Velocity Flag"] = "Y"
            df.at[idx, "Risk Level"]    = _escalate(df.at[idx, "Risk Level"], RISK_MEDIUM)
            df.at[idx, "Flag Count"]   += 1
            df.at[idx, "Flag Notes"]    = (
                df.at[idx, "Flag Notes"] + " | Velocity spike"
            ).lstrip(" | ")

    # ── 6. Summary stats ──────────────────────────────────────────────────────
    total          = len(df)
    total_flagged  = (df["Flag Count"] > 0).sum()
    oom_flags      = (df["Out of Market"] == "Y").sum()
    setter_flags   = (df["Setter Flag"] == "Y").sum()
    velocity_flags = (df["Velocity Flag"] == "Y").sum()
    geo_errors     = df["Geo Error"].sum()
    critical_flags = (df["Risk Level"] == RISK_CRITICAL).sum()
    whitelisted    = df["Whitelisted"].sum()

    summary = {
        "total":          total,
        "total_flagged":  int(total_flagged),
        "flag_rate":      round(total_flagged / max(total, 1) * 100, 1),
        "oom_flags":      int(oom_flags),
        "setter_flags":   int(setter_flags),
        "velocity_flags": int(velocity_flags),
        "geo_errors":     int(geo_errors),
        "critical_flags": int(critical_flags),
        "whitelisted":    int(whitelisted),
    }

    # ── 7. Rep-level leaderboard ──────────────────────────────────────────────
    rep_summary = (
        df.groupby(["Sales Rep ID", "Sales Rep Name"])
        .agg(
            total_accounts=("Flag Count", "count"),
            total_flags=("Flag Count", "sum"),
            oom=("Out of Market", lambda x: (x == "Y").sum()),
            setter=("Setter Flag", lambda x: (x == "Y").sum()),
            velocity=("Velocity Flag", lambda x: (x == "Y").sum()),
            critical=("Risk Level", lambda x: (x == RISK_CRITICAL).sum()),
        )
        .reset_index()
    )
    rep_summary["Flag Rate %"] = (
        rep_summary["total_flags"] / rep_summary["total_accounts"].clip(lower=1) * 100
    ).round(1)
    rep_summary = rep_summary.sort_values("total_flags", ascending=False).reset_index(drop=True)
    rep_summary.index += 1  # 1-based rank

    return {
        "df":          df,
        "summary":     summary,
        "rep_summary": rep_summary,
        "coords":      coords,
    }
