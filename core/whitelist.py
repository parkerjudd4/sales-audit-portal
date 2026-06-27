"""
core/whitelist.py  ·  Persistent whitelist / exception memory
=============================================================
Stores approved exceptions in whitelist.csv so they survive
between portal sessions. A whitelisted account key is built
from (Sales Rep ID, Customer Address norm) so it's specific
enough to not accidentally clear real flags.
"""

import pathlib
import pandas as pd

WHITELIST_FILE = pathlib.Path("whitelist.csv")


def _load() -> set[str]:
    if not WHITELIST_FILE.exists():
        return set()
    try:
        df = pd.read_csv(WHITELIST_FILE, dtype=str)
        return set(df["key"].dropna().tolist())
    except Exception:
        return set()


def _save(keys: set[str]):
    df = pd.DataFrame({"key": sorted(keys)})
    df.to_csv(WHITELIST_FILE, index=False)


def build_key(rep_id: str, norm_address: str) -> str:
    return f"{str(rep_id).strip()}||{str(norm_address).strip()}"


def is_whitelisted(key: str) -> bool:
    return key in _load()


def add_to_whitelist(keys: list[str]):
    existing = _load()
    existing.update(keys)
    _save(existing)


def remove_from_whitelist(keys: list[str]):
    existing = _load()
    for k in keys:
        existing.discard(k)
    _save(existing)


def get_all() -> list[str]:
    return sorted(_load())
