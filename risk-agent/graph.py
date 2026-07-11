"""The risk-scoring pipeline as a LangGraph StateGraph.

    ingest → classify → map_corridor → severity → score → store

Each node is a pure function of the shared state that returns the keys it
updates. The heavy lifting lives in the ingestion/ and scoring/ modules; this
file just wires them into the graph the README describes.
"""
from datetime import datetime, timezone
from typing import List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ingestion.sources import FixtureSource, GDELTSource
from scoring.classify import classify_event
from scoring.corridor_map import assign_corridor
from scoring.severity import classify_severity
from scoring.risk_model import compute_risk


class RiskState(TypedDict, total=False):
    corridor: str
    as_of: datetime
    use_live: bool
    persist: bool
    raw_events: List[dict]
    events: List[dict]
    data_sources: List[str]
    result: dict
    store_info: dict


def node_ingest(state: RiskState) -> dict:
    corridor, as_of = state["corridor"], state["as_of"]
    sources = [FixtureSource()]
    if state.get("use_live", True):
        sources.append(GDELTSource())

    raw: List[dict] = []
    used: List[str] = []
    for src in sources:
        try:
            events = src.fetch(corridor, as_of)
        except Exception:
            continue  # a flaky live source must never crash the pipeline
        if events:
            raw.extend(events)
            used.append(src.name)
    return {"raw_events": raw, "data_sources": used}


def node_classify(state: RiskState) -> dict:
    return {"raw_events": [classify_event(e) for e in state["raw_events"]]}


def node_map_corridor(state: RiskState) -> dict:
    requested = state["corridor"]
    out = []
    for e in state["raw_events"]:
        e = dict(e)
        e["corridor"] = assign_corridor(e) or requested
        out.append(e)
    return {"raw_events": out}


def node_severity(state: RiskState) -> dict:
    out = []
    for e in state["raw_events"]:
        e = dict(e)
        e["severity"] = classify_severity(e)
        out.append(e)
    return {"raw_events": out}


def node_score(state: RiskState) -> dict:
    corridor = state["corridor"]
    events = [e for e in state["raw_events"]
              if e.get("relevant") and e.get("corridor") == corridor]
    result = compute_risk(corridor, events, state["as_of"], state.get("data_sources", []))
    return {"events": events, "result": result}


def node_store(state: RiskState) -> dict:
    if not state.get("persist", True):
        return {"store_info": {"stored": False, "reason": "persist disabled"}}
    from store import store_risk
    info = store_risk(state["corridor"], state["result"], state["as_of"])
    return {"store_info": info}


def build_graph():
    g = StateGraph(RiskState)
    g.add_node("ingest", node_ingest)
    g.add_node("classify", node_classify)
    g.add_node("map_corridor", node_map_corridor)
    g.add_node("severity", node_severity)
    g.add_node("score", node_score)
    g.add_node("store", node_store)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "classify")
    g.add_edge("classify", "map_corridor")
    g.add_edge("map_corridor", "severity")
    g.add_edge("severity", "score")
    g.add_edge("score", "store")
    g.add_edge("store", END)
    return g.compile()


_COMPILED = None


def _coerce_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def run_pipeline(corridor: str, as_of: Optional[datetime] = None,
                 use_live: bool = True, persist: bool = True):
    """Run the pipeline once. Returns (result_dict, data_sources, store_info)."""
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_graph()
    as_of = _coerce_utc(as_of or datetime.now(timezone.utc))
    final = _COMPILED.invoke({
        "corridor": corridor, "as_of": as_of,
        "use_live": use_live, "persist": persist,
    })
    return final["result"], final.get("data_sources", []), final.get("store_info")
