"""
test_pipeline.py — Stage 4 tests for the full LangGraph pipeline.

Runs the compiled graph (ingest -> classify -> map_corridor -> severity ->
score -> store) offline: use_live=False (no GDELT) and persist=False (no DB), so
every run is deterministic and network-free.
"""
from datetime import datetime, timezone

import pytest

from graph import run_pipeline

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _run(corridor):
    return run_pipeline(corridor, AS_OF, use_live=False, persist=False)


@pytest.mark.parametrize("corridor", ["hormuz", "redsea", "cape", "domestic"])
def test_pipeline_produces_valid_result(corridor):
    result, sources, store_info = _run(corridor)
    assert 0.0 <= result["score"] <= 100.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["alert_level"] in ("low", "elevated", "high", "critical")
    assert isinstance(result["reasoning_trail"], list) and result["reasoning_trail"]
    for ev in result["key_events"]:
        assert ev["severity"] in ("low", "medium", "high", "critical")
        assert isinstance(ev["date"], datetime)
    assert "fixtures" in sources
    assert store_info["stored"] is False        # persistence disabled in tests


def test_pipeline_is_deterministic_offline():
    a, _, _ = _run("hormuz")
    b, _, _ = _run("hormuz")
    assert a["score"] == b["score"]
    assert a["alert_level"] == b["alert_level"]


def test_hormuz_riskier_than_cape():
    hormuz, _, _ = _run("hormuz")
    cape, _, _ = _run("cape")
    assert hormuz["score"] > cape["score"]


def test_naive_as_of_is_accepted():
    # a timezone-naive as_of must not crash the recency math
    naive = datetime(2026, 7, 11)
    result, _, _ = run_pipeline("hormuz", naive, use_live=False, persist=False)
    assert 0.0 <= result["score"] <= 100.0


def test_default_as_of_when_none():
    result, sources, _ = run_pipeline("redsea", None, use_live=False, persist=False)
    assert 0.0 <= result["score"] <= 100.0
    assert "fixtures" in sources
