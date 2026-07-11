"""Event sources behind one interface.

- ``FixtureSource``  — bundled deterministic test data (always available).
- ``GDELTSource``    — live, keyless GDELT DOC 2.0 API (real recent headlines).
- ``EIASource`` / ``AISSource`` / ``OFACSource`` — stubs that return nothing yet;
  they will be backed by the Stage-1 clients in ``shared/clients/`` once those
  exist. Keeping them here means the pipeline's source list is already complete.

Every source returns a list of event dicts shaped like:
    {"source", "headline", "country_code", "event_date" (datetime), "goldstein_scale"}
"""
from datetime import datetime, timezone
from typing import List

import requests

from .fixtures import fixture_events


class EventSource:
    name = "base"

    def fetch(self, corridor: str, as_of: datetime) -> List[dict]:
        raise NotImplementedError


class FixtureSource(EventSource):
    name = "fixtures"

    def fetch(self, corridor: str, as_of: datetime) -> List[dict]:
        return fixture_events(corridor, as_of)


class GDELTSource(EventSource):
    """Live headlines from the GDELT DOC 2.0 API (no API key required)."""

    name = "gdelt"
    ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

    CORRIDOR_QUERY = {
        "hormuz": '"Strait of Hormuz" (oil OR tanker OR shipping OR Iran)',
        "redsea": '("Red Sea" OR "Bab-el-Mandeb" OR Houthi) (oil OR tanker OR shipping)',
        "cape": '("Cape of Good Hope" OR "Cape route") (oil OR tanker OR shipping)',
        "domestic": '(India refinery OR India pipeline) oil',
    }

    def fetch(self, corridor: str, as_of: datetime, timeout: float = 15.0) -> List[dict]:
        query = self.CORRIDOR_QUERY.get(corridor)
        if not query:
            return []
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 25,
            "timespan": "7d",
            "sort": "datedesc",
        }
        resp = requests.get(self.ENDPOINT, params=params, timeout=timeout,
                            headers={"User-Agent": "pravah-risk-agent/1.0"})
        resp.raise_for_status()
        try:
            articles = resp.json().get("articles", [])
        except ValueError:
            return []  # GDELT occasionally returns non-JSON when throttled

        out: List[dict] = []
        for a in articles:
            out.append({
                "source": "gdelt",
                "headline": a.get("title") or "",
                "country_code": _iso2_to_iso3(a.get("sourcecountry")),
                "event_date": _parse_seendate(a.get("seendate")),
                "goldstein_scale": None,  # DOC API has no Goldstein; severity falls back to keywords
                "url": a.get("url"),
            })
        return out


class _NotYetWired(EventSource):
    """Placeholder for a Stage-1 client that isn't built yet."""

    def fetch(self, corridor: str, as_of: datetime) -> List[dict]:
        return []


class EIASource(_NotYetWired):
    name = "eia"


class AISSource(_NotYetWired):
    name = "aisstream"


class OFACSource(_NotYetWired):
    name = "ofac"


def _parse_seendate(s) -> datetime:
    # GDELT seendate looks like "20260711T143000Z"
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


# GDELT reports source country as a name/FIPS; we only need a rough ISO-3 hint
# for corridor mapping, and headline keywords usually dominate anyway.
_COUNTRY_NAME_ISO3 = {
    "iran": "IRN", "saudi arabia": "SAU", "iraq": "IRQ", "united arab emirates": "ARE",
    "yemen": "YEM", "egypt": "EGY", "russia": "RUS", "nigeria": "NGA",
    "south africa": "ZAF", "india": "IND",
}


def _iso2_to_iso3(name) -> str:
    if not name:
        return None
    return _COUNTRY_NAME_ISO3.get(str(name).strip().lower())
