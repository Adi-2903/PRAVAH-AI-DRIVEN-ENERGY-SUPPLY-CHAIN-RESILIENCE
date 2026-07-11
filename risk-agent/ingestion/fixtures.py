"""Bundled, deterministic test events per corridor.

These are the risk agent's "own test data" (README Stage 4): they let the whole
pipeline run and be tested with zero network access. Dates are generated
relative to the ``as_of`` passed in, so recency weighting is exercised
deterministically.
"""
from datetime import datetime, timedelta, timezone
from typing import List

# (days_before_as_of, headline, country_code, goldstein_scale)
_FIXTURES = {
    "hormuz": [
        (1, "Iran threatens to close the Strait of Hormuz amid rising tensions", "IRN", -6.5),
        (2, "Oil tanker seized near the Strait of Hormuz, crew detained", "IRN", -8.0),
        (4, "US Navy warship escorts crude tanker through Persian Gulf", "SAU", -2.0),
        (9, "OPEC signals steady crude exports through the Gulf", "SAU", 1.5),
    ],
    "redsea": [
        (1, "Houthi drone attack hits oil tanker in the Red Sea", "YEM", -7.5),
        (3, "Shipping firms reroute crude away from Bab-el-Mandeb", "EGY", -3.5),
        (8, "Naval coalition steps up patrols in the Gulf of Aden", "YEM", -1.0),
    ],
    "cape": [
        (2, "More tankers take the Cape of Good Hope route to avoid Suez", "ZAF", -1.0),
        (12, "Nigerian crude exports steady via the Cape route", "NGA", 2.0),
    ],
    "domestic": [
        (5, "Maintenance shutdown at an Indian refinery trims output", "IND", -1.5),
    ],
}


def fixture_events(corridor: str, as_of: datetime) -> List[dict]:
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    out: List[dict] = []
    for days_before, headline, country, goldstein in _FIXTURES.get(corridor, []):
        out.append({
            "source": "fixtures",
            "headline": headline,
            "country_code": country,
            "event_date": as_of - timedelta(days=days_before),
            "goldstein_scale": goldstein,
        })
    return out
