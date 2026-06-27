"""
core/geocoder.py  ·  Geocoding with local disk cache
=====================================================
Uses Nominatim via geopy. Caches results in geocache.json
to avoid redundant network requests across runs.
"""

import json
import time
import pathlib
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

CACHE_FILE = pathlib.Path("geocache.json")


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass  # Non-fatal: cache write failure just means next run re-geocodes


def geocode_addresses(
    addresses: list[str],
    delay: float = 1.0,
    progress_label: str = "Geocoding…",
) -> dict[str, tuple[float, float] | None]:
    """
    Geocode a list of address strings.
    Returns {address: (lat, lon) or None if failed}.
    Uses disk cache to skip already-known addresses.
    """
    cache = _load_cache()
    geolocator = Nominatim(user_agent="sales_audit_portal_v1")
    results: dict[str, tuple[float, float] | None] = {}

    unique = list(dict.fromkeys(addresses))  # deduplicate, preserve order
    uncached = [a for a in unique if a not in cache]

    progress = st.progress(0, text=progress_label)
    total = len(unique)

    for i, addr in enumerate(unique):
        progress.progress((i + 1) / max(total, 1), text=f"{progress_label} ({i+1}/{total})")

        if addr in cache:
            val = cache[addr]
            results[addr] = tuple(val) if val is not None else None
            continue

        # Fresh geocode
        try:
            time.sleep(delay)
            loc = geolocator.geocode(addr, timeout=10)
            if loc:
                coords = (loc.latitude, loc.longitude)
                cache[addr] = list(coords)
                results[addr] = coords
            else:
                cache[addr] = None
                results[addr] = None
        except Exception:
            cache[addr] = None
            results[addr] = None

    _save_cache(cache)
    progress.empty()
    return results


def calculate_distance_miles(
    point_a: tuple[float, float] | None,
    point_b: tuple[float, float] | None,
) -> float | None:
    """Return geodesic distance in miles, or None if either point is invalid."""
    if point_a is None or point_b is None:
        return None
    try:
        return geodesic(point_a, point_b).miles
    except Exception:
        return None
