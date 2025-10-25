# util/name_map.py
# Purpose: normalize team names from providers to our DB naming.

import re

# Known variations you want to normalize to your DB's "canonical" names.
# LEFT: provider/raw; RIGHT: your DB name.
CANONICAL_MAP = {
    "connecticut": "UConn",
    "uc onnecticut": "UConn",   # sometimes weird spacing from sources
    "texas christian": "TCU",
    "st. mary's": "Saint Mary's",
    "saint marys": "Saint Mary's",
    "unc": "North Carolina",
    "ole miss": "Mississippi",
    "lsu": "LSU",  # example of mapped-to-same
    # add as you discover mismatches…
}

def normalize_key(s: str) -> str:
    """Lowercase, collapse spaces/punct, strip suffixes like ' (NCAAB)'."""
    s = s or ""
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)  # drop trailing parentheses info
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_canonical(raw_name: str) -> str:
    key = normalize_key(raw_name)
    return CANONICAL_MAP.get(key, raw_name)
