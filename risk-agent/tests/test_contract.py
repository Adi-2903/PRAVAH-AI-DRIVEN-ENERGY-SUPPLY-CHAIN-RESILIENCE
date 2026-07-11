"""The pipeline output MUST satisfy the frozen shared/schemas contract."""
from datetime import datetime, timezone

from graph import run_pipeline
from shared.schemas.risk_score import RiskScoreResponse, KeyEvent

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def test_output_validates_against_frozen_schema():
    result, sources, _ = run_pipeline("hormuz", AS_OF, use_live=False, persist=False)
    resp = RiskScoreResponse(
        corridor="hormuz",
        score=result["score"],
        confidence=result["confidence"],
        alert_level=result["alert_level"],
        reasoning_trail=result["reasoning_trail"],
        key_events=[KeyEvent(**k) for k in result["key_events"]],
        computed_at=datetime.now(timezone.utc),
        data_sources=sources,
    )
    assert resp.corridor == "hormuz"
    assert 0.0 <= resp.score <= 100.0
    # round-trips through JSON like the API will serialize it
    assert RiskScoreResponse.model_validate_json(resp.model_dump_json()).score == resp.score
