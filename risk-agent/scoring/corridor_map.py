"""Map an event to a shipping corridor.

Corridor names are the lowercase canonical strings used everywhere in Pravah
(``corridors.name`` in the DB, the knowledge-graph node IDs, and the frozen
``Corridor`` enum in shared/schemas): hormuz, redsea, cape, domestic.
"""
import re
from typing import Optional

CORRIDORS = ("hormuz", "redsea", "cape", "domestic")

# ISO-3166 alpha-3 country code -> the corridor its crude primarily reaches
# India through. Derived from the supply-chain knowledge graph.
COUNTRY_CORRIDOR = {
    "SAU": "hormuz", "IRQ": "hormuz", "ARE": "hormuz", "KWT": "hormuz",
    "QAT": "hormuz", "IRN": "hormuz", "BHR": "hormuz", "OMN": "hormuz",
    "RUS": "redsea", "YEM": "redsea", "EGY": "redsea", "SDN": "redsea",
    "NGA": "cape", "AGO": "cape", "ZAF": "cape",
    "IND": "domestic",
}

# Headline keyword hints -> corridor (word-boundary matched, first corridor with
# any hit wins). Order matters: hormuz is checked before redsea, etc.
KEYWORD_CORRIDOR = [
    (r"\b(strait of hormuz|hormuz|persian gulf|arabian gulf|musandam)\b", "hormuz"),
    (r"\b(red sea|bab-el-mandeb|bab el mandeb|houthi|suez|gulf of aden|aden)\b", "redsea"),
    (r"\b(cape of good hope|cape route|good hope)\b", "cape"),
    (r"\b(domestic pipeline|india refinery|indian refinery)\b", "domestic"),
]
_KEYWORD_CORRIDOR = [(re.compile(pat, re.IGNORECASE), corridor) for pat, corridor in KEYWORD_CORRIDOR]


def corridor_for_country(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return COUNTRY_CORRIDOR.get(code.strip().upper())


def corridor_for_text(text: Optional[str]) -> Optional[str]:
    t = text or ""
    for pattern, corridor in _KEYWORD_CORRIDOR:
        if pattern.search(t):
            return corridor
    return None


def assign_corridor(event: dict) -> Optional[str]:
    """Best-effort corridor for an event: headline keyword first, then country."""
    return corridor_for_text(event.get("headline")) or corridor_for_country(event.get("country_code"))
