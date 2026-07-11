"""Persist risk output to Supabase (the tables the shared/ foundation created).

Writes the scored ``key_events`` into ``risk_events`` and the aggregate into
``risk_scores``. If no Supabase credentials are present (e.g. during standalone
tests) it no-ops cleanly instead of failing — persistence is a side effect, not
part of the contract.
"""
import os
from datetime import datetime
from typing import Optional


def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and key):
        return None
    from supabase import create_client
    return create_client(url, key)


def _iso(dt):
    return dt.isoformat() if isinstance(dt, datetime) else dt


def store_risk(corridor: str, result: dict, as_of: datetime) -> dict:
    sb = _client()
    if sb is None:
        return {"stored": False, "reason": "no Supabase credentials"}

    try:
        found = sb.table("corridors").select("id").eq("name", corridor).limit(1).execute()
        corridor_id: Optional[int] = found.data[0]["id"] if found.data else None

        for ev in result.get("key_events", []):
            sb.table("risk_events").insert({
                "source": "risk-agent",
                "headline": ev.get("headline"),
                "corridor_id": corridor_id,
                "event_date": _iso(ev.get("date")) or _iso(as_of),
                "severity": ev.get("severity"),
                "raw_payload": {"origin": "risk-agent key_event"},
            }).execute()

        inserted = sb.table("risk_scores").insert({
            "corridor_id": corridor_id,
            "score": result["score"],
            "confidence": result["confidence"],
            "reasoning_trail": result["reasoning_trail"],
            "data_sources": result.get("data_sources", []),
        }).execute()

        risk_score_id = inserted.data[0]["id"] if inserted.data else None
        return {"stored": True, "corridor_id": corridor_id, "risk_score_id": risk_score_id}
    except Exception as e:  # never let a storage hiccup break the API response
        return {"stored": False, "reason": f"{type(e).__name__}: {e}"}
