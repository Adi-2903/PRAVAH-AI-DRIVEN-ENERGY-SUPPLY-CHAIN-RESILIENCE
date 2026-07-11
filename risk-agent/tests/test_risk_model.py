from datetime import datetime, timezone, timedelta

from scoring.risk_model import compute_risk, alert_level_for, recency_factor

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _ev(severity, days_ago=1, goldstein=None):
    return {
        "headline": f"{severity} event",
        "severity": severity,
        "event_date": AS_OF - timedelta(days=days_ago),
        "goldstein_scale": goldstein,
        "relevant": True,
    }


def test_alert_level_thresholds():
    assert alert_level_for(80) == "critical"
    assert alert_level_for(60) == "high"
    assert alert_level_for(40) == "elevated"
    assert alert_level_for(10) == "low"


def test_recency_decay():
    assert recency_factor(AS_OF - timedelta(days=1), AS_OF) == 1.0
    assert recency_factor(AS_OF - timedelta(days=40), AS_OF) == 0.2
    mid = recency_factor(AS_OF - timedelta(days=18), AS_OF)
    assert 0.2 < mid < 1.0


def test_no_events_returns_baseline():
    r = compute_risk("hormuz", [], AS_OF, data_sources=["fixtures"])
    assert r["score"] == 60.0            # hormuz baseline
    assert r["alert_level"] == "high"
    assert r["key_events"] == []
    assert 0.0 <= r["confidence"] <= 1.0


def test_events_raise_score_and_clamp():
    events = [_ev("critical", goldstein=-9) for _ in range(8)]
    r = compute_risk("hormuz", events, AS_OF, data_sources=["fixtures", "gdelt"])
    assert r["score"] > 60.0
    assert r["score"] <= 100.0           # clamped
    assert r["alert_level"] == "critical"
    assert len(r["key_events"]) == 5     # top-5 only


def test_key_events_sorted_by_severity():
    events = [_ev("low"), _ev("critical"), _ev("medium")]
    r = compute_risk("cape", events, AS_OF, data_sources=["fixtures"])
    assert r["key_events"][0]["severity"] == "critical"


def test_output_shape():
    r = compute_risk("redsea", [_ev("high")], AS_OF, data_sources=["fixtures"])
    for key in ("score", "confidence", "alert_level", "reasoning_trail", "key_events", "data_sources"):
        assert key in r
    assert isinstance(r["reasoning_trail"], list) and r["reasoning_trail"]
