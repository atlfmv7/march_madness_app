# util/name_map.py
# Purpose: normalize team names from providers to our DB naming.

import re

# Known variations you want to normalize to your DB's "canonical" names.
# LEFT: provider/raw; RIGHT: your DB name.
CANONICAL_MAP = {
    # Connecticut variations
    "connecticut": "UConn",
    "uconn": "UConn",
    "u conn": "UConn",
    "uc onnecticut": "UConn",
    
    # TCU variations
    "texas christian": "TCU",
    "tcu": "TCU",
    
    # Saint Mary's variations
    "st marys": "Saint Mary's",
    "st mary's": "Saint Mary's",
    "saint marys": "Saint Mary's",
    
    # North Carolina variations
    "unc": "North Carolina",
    "north carolina": "North Carolina",
    "n carolina": "North Carolina",
    
    # Mississippi variations
    "ole miss": "Mississippi",
    "mississippi": "Mississippi",
    
    # LSU
    "lsu": "LSU",
    "louisiana state": "LSU",
    
    # Duke
    "duke": "Duke",
    
    # Kentucky
    "kentucky": "Kentucky",
    
    # Kansas
    "kansas": "Kansas",
    
    # Gonzaga
    "gonzaga": "Gonzaga",
    
    # Arizona
    "arizona": "Arizona",
    
    # Baylor
    "baylor": "Baylor",
    
    # Add more as you discover mismatches during testing…
}

def normalize_key(s: str) -> str:
    """Lowercase, collapse spaces/punct, strip suffixes like ' (NCAAB)'."""
    s = s or ""
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)  # drop trailing parentheses info
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_canonical(raw_name: str) -> str:
    """Convert a raw team name to canonical form."""
    if not raw_name:
        return raw_name
    key = normalize_key(raw_name)
    canonical = CANONICAL_MAP.get(key)
    if canonical:
        return canonical
    # If no mapping found, return the raw name with basic cleanup
    # (title case, remove extra whitespace)
    return ' '.join(raw_name.split()).title()
