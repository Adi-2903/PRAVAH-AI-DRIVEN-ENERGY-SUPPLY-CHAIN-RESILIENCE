"""
test_contracts.py — Schema freeze contract tests.

Every field, type, bound, and enum for all 4 frozen contracts.
These tests are the source of truth. Breaking them = breaking the contract.
"""
import pytest
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════════
# /risk-score  (shared/schemas/risk_score.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskScoreContract:

    def test_request_required_fields(self):
        """RiskScoreRequest requires corridor + as_of."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import RiskScoreRequest
        with pytest.raises(ValidationError):
            RiskScoreRequest()  # missing both fields

    def test_request_valid_corridors(self):
        """Only the four frozen corridors are accepted."""
        from shared.contracts.risk_score import RiskScoreRequest
        now = datetime.now(timezone.utc)
        for corridor in ["hormuz", "redsea", "cape", "domestic"]:
            req = RiskScoreRequest(corridor=corridor, as_of=now)
            assert req.corridor == corridor

    def test_request_rejects_invalid_corridor(self):
        """Unknown corridor must fail validation."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import RiskScoreRequest
        with pytest.raises(ValidationError):
            RiskScoreRequest(corridor="HORMUZ", as_of=datetime.now(timezone.utc))

    def test_response_score_bounds(self):
        """score field must be 0 ≤ score ≤ 100."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import RiskScoreResponse, KeyEvent
        now = datetime.now(timezone.utc)
        base = dict(corridor="hormuz", confidence=0.9, alert_level="high",
                    reasoning_trail=["r1"], key_events=[], computed_at=now,
                    data_sources=["gdelt"])
        # Score below 0
        with pytest.raises(ValidationError):
            RiskScoreResponse(score=-1.0, **base)
        # Score above 100
        with pytest.raises(ValidationError):
            RiskScoreResponse(score=101.0, **base)
        # Valid edge cases
        RiskScoreResponse(score=0.0, **base)
        RiskScoreResponse(score=100.0, **base)

    def test_response_confidence_bounds(self):
        """confidence must be 0 ≤ confidence ≤ 1."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import RiskScoreResponse
        now = datetime.now(timezone.utc)
        base = dict(corridor="hormuz", score=50.0, alert_level="elevated",
                    reasoning_trail=[], key_events=[], computed_at=now,
                    data_sources=[])
        with pytest.raises(ValidationError):
            RiskScoreResponse(confidence=-0.1, **base)
        with pytest.raises(ValidationError):
            RiskScoreResponse(confidence=1.1, **base)

    def test_response_alert_level_enum(self):
        """alert_level must be one of the four frozen values."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import RiskScoreResponse
        now = datetime.now(timezone.utc)
        base = dict(corridor="hormuz", score=50.0, confidence=0.8,
                    reasoning_trail=[], key_events=[], computed_at=now,
                    data_sources=[])
        with pytest.raises(ValidationError):
            RiskScoreResponse(alert_level="extreme", **base)  # not in enum

    def test_response_required_fields_present(self):
        """All required fields must produce a valid response object."""
        from shared.contracts.risk_score import RiskScoreResponse
        now = datetime.now(timezone.utc)
        r = RiskScoreResponse(
            corridor="hormuz", score=75.0, confidence=0.85,
            alert_level="high", reasoning_trail=["AIS anomaly detected"],
            key_events=[], computed_at=now, data_sources=["gdelt", "eia"]
        )
        assert r.score == 75.0
        assert r.corridor == "hormuz"

    def test_key_event_required_fields(self):
        """KeyEvent requires headline, severity, date."""
        from pydantic import ValidationError
        from shared.contracts.risk_score import KeyEvent
        with pytest.raises(ValidationError):
            KeyEvent(headline="something")  # missing severity + date
        event = KeyEvent(headline="Attack", severity="high",
                         date=datetime.now(timezone.utc))
        assert event.severity == "high"


# ══════════════════════════════════════════════════════════════════════════════
# /simulate  (shared/schemas/simulate.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestSimulateContract:

    def test_request_risk_score_bounds(self):
        """risk_score must be 0–100."""
        from pydantic import ValidationError
        from shared.contracts.simulate import SimulateRequest, ElasticityAssumptions
        ela = ElasticityAssumptions(price_elasticity_of_demand=-0.05,
                                    pass_through_rate_to_pump=0.6,
                                    gdp_sensitivity_per_10pct_oil_shock=-0.15)
        base = dict(corridor="hormuz", shock_duration_days=30,
                    num_simulations=1000, current_brent_usd=85.0,
                    elasticity_assumptions=ela)
        with pytest.raises(ValidationError):
            SimulateRequest(risk_score=-1.0, **base)
        with pytest.raises(ValidationError):
            SimulateRequest(risk_score=101.0, **base)

    def test_request_num_simulations_bounds(self):
        """num_simulations must be 1000–20000."""
        from pydantic import ValidationError
        from shared.contracts.simulate import SimulateRequest, ElasticityAssumptions
        ela = ElasticityAssumptions(price_elasticity_of_demand=-0.05,
                                    pass_through_rate_to_pump=0.6,
                                    gdp_sensitivity_per_10pct_oil_shock=-0.15)
        base = dict(risk_score=50.0, corridor="hormuz", shock_duration_days=30,
                    current_brent_usd=85.0, elasticity_assumptions=ela)
        with pytest.raises(ValidationError):
            SimulateRequest(num_simulations=500, **base)  # below 1000

    def test_request_shock_duration_bounds(self):
        """shock_duration_days must be 1–365."""
        from pydantic import ValidationError
        from shared.contracts.simulate import SimulateRequest, ElasticityAssumptions
        ela = ElasticityAssumptions(price_elasticity_of_demand=-0.05,
                                    pass_through_rate_to_pump=0.6,
                                    gdp_sensitivity_per_10pct_oil_shock=-0.15)
        base = dict(risk_score=50.0, corridor="hormuz", num_simulations=1000,
                    current_brent_usd=85.0, elasticity_assumptions=ela)
        with pytest.raises(ValidationError):
            SimulateRequest(shock_duration_days=0, **base)

    def test_request_pass_through_rate_bounds(self):
        """pass_through_rate_to_pump must be 0–1."""
        from pydantic import ValidationError
        from shared.contracts.simulate import ElasticityAssumptions
        with pytest.raises(ValidationError):
            ElasticityAssumptions(price_elasticity_of_demand=-0.05,
                                  pass_through_rate_to_pump=1.5,  # > 1
                                  gdp_sensitivity_per_10pct_oil_shock=-0.15)


# ══════════════════════════════════════════════════════════════════════════════
# /recommend  (shared/schemas/recommend.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendContract:

    def test_request_required_fields(self):
        """RecommendRequest requires blocked_corridors, required_volume_mbpd, max_transit_days."""
        from pydantic import ValidationError
        from shared.contracts.recommend import RecommendRequest
        with pytest.raises(ValidationError):
            RecommendRequest()

    def test_request_optional_scenario_id(self):
        """scenario_id is optional and defaults to None."""
        from shared.contracts.recommend import RecommendRequest
        req = RecommendRequest(blocked_corridors=["hormuz"],
                               required_volume_mbpd=2.5, max_transit_days=30)
        assert req.scenario_id is None

    def test_response_required_fields(self):
        """RecommendResponse must have all required fields."""
        from shared.contracts.recommend import RecommendResponse, SupplierRecommendation
        now = datetime.now(timezone.utc)
        rec = SupplierRecommendation(rank=1, supplier="Saudi Aramco", country="SAU",
                                     corridor="cape", grade="Arab Light",
                                     cost_index=1.05, transit_days=25,
                                     risk_score=30.0, rationale="Lowest risk")
        resp = RecommendResponse(recommendations=[rec], total_suppliers_evaluated=4,
                                 graph_paths_analyzed=12, computed_at=now)
        assert resp.total_suppliers_evaluated == 4
        assert len(resp.recommendations) == 1


# ══════════════════════════════════════════════════════════════════════════════
# /spr-schedule  (shared/schemas/spr_schedule.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestSprScheduleContract:

    def test_request_required_fields(self):
        """SprScheduleRequest requires shock_duration_days + supply_gap_mbpd."""
        from pydantic import ValidationError
        from shared.contracts.spr_schedule import SprScheduleRequest
        with pytest.raises(ValidationError):
            SprScheduleRequest()

    def test_request_default_cover_days(self):
        """current_cover_days defaults to 9.5."""
        from shared.contracts.spr_schedule import SprScheduleRequest
        req = SprScheduleRequest(shock_duration_days=30, supply_gap_mbpd=0.5)
        assert req.current_cover_days == 9.5

    def test_response_all_fields_present(self):
        """SprScheduleResponse has all 8 required fields."""
        from shared.contracts.spr_schedule import SprScheduleResponse
        from datetime import date
        now = datetime.now(timezone.utc)
        resp = SprScheduleResponse(
            recommended_release_mbpd=0.2,
            release_duration_days=14,
            start_date=date.today(),
            cover_days_before=9.5,
            cover_days_after=6.7,
            optimization_objective="minimize import bill",
            constraint_notes=["floor >= 3 days"],
            computed_at=now,
        )
        assert resp.recommended_release_mbpd == 0.2


# ══════════════════════════════════════════════════════════════════════════════
# Cross-contract: backward compatibility sentinel
# ══════════════════════════════════════════════════════════════════════════════

def test_all_schema_modules_importable():
    """All four schema modules must be importable without errors."""
    import schemas.risk_score
    import schemas.simulate
    import schemas.recommend
    import schemas.spr_schedule
    assert True
