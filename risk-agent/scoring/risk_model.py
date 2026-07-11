"""Aggregate classified events into an explainable corridor risk score.

Pure and deterministic: given a corridor, a list of relevant events (already
classified, severity-labelled and corridor-assigned) and an ``as_of`` time, it
produces the numbers that fill the frozen ``RiskScoreResponse`` — plus a
human-readable ``reasoning_trail`` explaining every adjustment.
"""
from datetime import datetime
from typing import List, Optional

# Corridor baseline risk (0-100). Mirrors risk_baseline in the knowledge graph;
# 'domestic' is added here (not a chokepoint) with a low baseline.
CORRIDOR_BASELINE = {"hormuz": 60.0, "redsea": 50.0, "cape": 15.0, "domestic": 5.0}

# Points a single event adds, before recency weighting.
SEVERITY_POINTS = {"low": 2.0, "medium": 5.0, "high": 10.0, "critical": 18.0}
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# Total event pressure is capped so a flood of low events can't dominate.
MAX_EVENT_PRESSURE = 40.0

# alert_level thresholds (checked high-to-low). Values match the frozen enum.
ALERT_THRESHOLDS = ((75.0, "critical"), (55.0, "high"), (30.0, "elevated"), (0.0, "low"))


def alert_level_for(score: float) -> str:
    for threshold, level in ALERT_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def recency_factor(event_date: datetime, as_of: datetime) -> float:
    """1.0 within 7 days, decaying linearly to 0.2 by 30 days, floor 0.2."""
    days = (as_of - event_date).days
    if days <= 7:
        return 1.0
    if days >= 30:
        return 0.2
    return 1.0 - (days - 7) * (0.8 / 23.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def compute_risk(corridor: str, events: List[dict], as_of: datetime,
                 data_sources: Optional[List[str]] = None) -> dict:
    data_sources = data_sources or []
    trail: List[str] = []

    base = CORRIDOR_BASELINE.get(corridor, 20.0)
    trail.append(f"Baseline risk for '{corridor}' corridor = {base:.0f}/100.")

    # --- event pressure ---
    pressure = 0.0
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for e in events:
        sev = e.get("severity", "low")
        counts[sev] = counts.get(sev, 0) + 1
        date = e.get("event_date")
        rf = recency_factor(date, as_of) if isinstance(date, datetime) else 1.0
        pressure += SEVERITY_POINTS.get(sev, 2.0) * rf
    pressure = min(pressure, MAX_EVENT_PRESSURE)

    if events:
        breakdown = ", ".join(f"{counts[s]} {s}" for s in ("critical", "high", "medium", "low") if counts[s])
        trail.append(f"{len(events)} relevant event(s) ({breakdown}) -> +{pressure:.1f} (recency-weighted, capped at {MAX_EVENT_PRESSURE:.0f}).")
    else:
        trail.append("No relevant events found in window -> no event pressure added.")

    # --- Goldstein conflict adjustment ---
    goldsteins = [e["goldstein_scale"] for e in events if e.get("goldstein_scale") is not None]
    goldstein_adj = 0.0
    if goldsteins:
        avg_g = sum(goldsteins) / len(goldsteins)
        if avg_g < 0:
            goldstein_adj = min(-avg_g * 1.5, 12.0)
            trail.append(f"Avg Goldstein conflict scale {avg_g:.1f} (conflictual) -> +{goldstein_adj:.1f}.")
        else:
            trail.append(f"Avg Goldstein conflict scale {avg_g:.1f} (cooperative) -> no increase.")

    score = _clamp(base + pressure + goldstein_adj, 0.0, 100.0)
    alert = alert_level_for(score)
    trail.append(f"Final score = {score:.1f}/100 -> alert level '{alert}'.")

    # --- confidence: more sources + more corroborating events = higher ---
    confidence = _clamp(0.5 + 0.1 * len(set(data_sources)) + 0.02 * min(len(events), 10), 0.0, 0.95)
    trail.append(f"Confidence {confidence:.2f} from {len(set(data_sources))} source(s), {len(events)} event(s).")

    # --- key events: most severe first, then most recent, top 5 ---
    def _key(e):
        d = e.get("event_date")
        ts = d.timestamp() if isinstance(d, datetime) else 0.0
        return (SEVERITY_RANK.get(e.get("severity", "low"), 0), ts)

    top = sorted(events, key=_key, reverse=True)[:5]
    key_events = [
        {"headline": e.get("headline", ""), "severity": e.get("severity", "low"), "date": e.get("event_date")}
        for e in top
    ]

    return {
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "alert_level": alert,
        "reasoning_trail": trail,
        "key_events": key_events,
        "data_sources": list(dict.fromkeys(data_sources)),
    }
