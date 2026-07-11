from datetime import datetime, timezone

from graph import run_pipeline

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def test_pipeline_runs_offline_for_each_corridor():
    for corridor in ("hormuz", "redsea", "cape", "domestic"):
        result, sources, store_info = run_pipeline(
            corridor, AS_OF, use_live=False, persist=False
        )
        assert 0.0 <= result["score"] <= 100.0
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["alert_level"] in ("low", "elevated", "high", "critical")
        assert "fixtures" in sources
        assert store_info["stored"] is False   # persist disabled in tests


def test_hormuz_is_higher_risk_than_cape():
    hormuz, _, _ = run_pipeline("hormuz", AS_OF, use_live=False, persist=False)
    cape, _, _ = run_pipeline("cape", AS_OF, use_live=False, persist=False)
    assert hormuz["score"] > cape["score"]
