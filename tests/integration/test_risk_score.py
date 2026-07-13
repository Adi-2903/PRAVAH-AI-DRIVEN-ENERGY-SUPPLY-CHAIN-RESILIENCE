"""
test_risk_score.py — Risk score schema and bounds validation.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

import pytest
from datetime import datetime, timezone
from schemas.risk_score import RiskScoreResponse, KeyEvent

def make_response(**kwargs):
    now = datetime.now(timezone.utc)
    defaults = dict(corridor="hormuz", score=50.0, confidence=0.8,
                    alert_level="elevated", reasoning_trail=["r1"],
                    key_events=[], computed_at=now, data_sources=["gdelt"])
    return RiskScoreResponse(**{**defaults, **kwargs})

def test_score_lower_bound():
    r = make_response(score=0.0)
    assert r.score == 0.0

def test_score_upper_bound():
    r = make_response(score=100.0)
    assert r.score == 100.0

def test_score_below_zero_raises():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        make_response(score=-1.0)

def test_score_above_100_raises():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        make_response(score=100.1)

def test_confidence_lower_bound():
    r = make_response(confidence=0.0)
    assert r.confidence == 0.0

def test_confidence_upper_bound():
    r = make_response(confidence=1.0)
    assert r.confidence == 1.0

def test_confidence_above_one_raises():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        make_response(confidence=1.01)

def test_reasoning_trail_is_list():
    r = make_response(reasoning_trail=["AIS anomaly", "Sanctions hit"])
    assert isinstance(r.reasoning_trail, list)
    assert len(r.reasoning_trail) == 2

def test_data_sources_is_list():
    r = make_response(data_sources=["gdelt", "eia", "aisstream"])
    assert len(r.data_sources) == 3

def test_alert_level_values():
    from pydantic import ValidationError
    for level in ["low", "elevated", "high", "critical"]:
        r = make_response(alert_level=level)
        assert r.alert_level == level
    with pytest.raises(ValidationError):
        make_response(alert_level="extreme")

def test_key_event_structure():
    now = datetime.now(timezone.utc)
    event = KeyEvent(headline="Tanker seized", severity="high", date=now)
    assert event.headline == "Tanker seized"
    assert event.severity == "high"
