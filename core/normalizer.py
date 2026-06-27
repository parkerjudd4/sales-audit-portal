"""
core/normalizer.py  ·  Address normalization + fuzzy matching
============================================================
Normalizes addresses for reliable duplicate detection, and
provides a similarity scorer used in setter detection.
"""

import re
import unicodedata
from rapidfuzz import fuzz


# Abbreviation map for street suffix normalization
_STREET_SUFFIXES = {
    r"\bstreet\b": "st",
    r"\bavenue\b": "ave",
    r"\bboulevard\b": "blvd",
    r"\bdrive\b": "dr",
    r"\broad\b": "rd",
    r"\bcourt\b": "ct",
    r"\bcircle\b": "cir",
    r"\blane\b": "ln",
    r"\bplace\b": "pl",
    r"\bterrace\b": "ter",
    r"\bway\b": "way",
    r"\bparkway\b": "pkwy",
    r"\bhighway\b": "hwy",
    r"\bsuite\b": "ste",
    r"\bapartment\b": "apt",
    r"\bunit\b": "unit",
    r"\bnorth\b": "n",
    r"\bsouth\b": "s",
    r"\beast\b": "e",
    r"\bwest\b": "w",
    r"\bnortheast\b": "ne",
    r"\bnorthwest\b": "nw",
    r"\bsoutheast\b": "se",
    r"\bsouthwest\b": "sw",
}


def normalize_address(raw: str) -> str:
    """
    Normalize an address string for comparison:
      1. Unicode → ASCII
      2. Lowercase
      3. Strip punctuation (keep alphanumerics + spaces)
      4. Expand/collapse suffix abbreviations
      5. Collapse whitespace
    """
    if not isinstance(raw, str):
        return ""
    # Unicode normalization
    text = unicodedata.normalize("NFKD", raw)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    # Remove punctuation except spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Apply suffix map
    for pattern, replacement in _STREET_SUFFIXES.items():
        text = re.sub(pattern, replacement, text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def address_similarity(a: str, b: str) -> float:
    """
    Return a 0–100 similarity score between two (raw) addresses.
    Uses token_sort_ratio so word-order differences don't penalise.
    """
    na = normalize_address(a)
    nb = normalize_address(b)
    if not na or not nb:
        return 0.0
    return fuzz.token_sort_ratio(na, nb)


def name_similarity(a: str, b: str) -> float:
    """
    Return a 0–100 similarity score between two customer names.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return 0.0
    na = re.sub(r"[^a-z0-9\s]", " ", a.lower()).strip()
    nb = re.sub(r"[^a-z0-9\s]", " ", b.lower()).strip()
    return fuzz.token_sort_ratio(na, nb)
