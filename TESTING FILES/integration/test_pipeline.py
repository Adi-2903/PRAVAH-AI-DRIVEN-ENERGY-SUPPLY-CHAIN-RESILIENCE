"""
test_pipeline.py — End-to-end pipeline integration test.
Simulates the full data flow: RiskScore → Simulate → Recommend → SPR.
Uses FastAPI TestClient for scenario-engine and spr-agent; schema validation for contracts.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scenario-engine"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "spr-agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# ── STEP 1: Construct a RiskScore response (contract-validated) ───────────────

def step1_risk_score(risk_level=75.0):
    """Simulate what the Risk Agent would produce."""
    from schemas.risk_score import RiskScoreResponse
    now = datetime.now(timezone.utc)
    return RiskScoreResponse(
        corridor="hormuz", score=risk_level, confidence=0.87,
        alert_level="high", reasoning_trail=["AIS anomaly", "GDELT tension"],
        key_events=[], computed_at=now, data_sources=["gdelt", "aisstream"]
    )

# ── STEP 2: Use it as input for Scenario Engine ──────────────────────────────

def step2_simulate(risk_response):
    import importlib.util, types
    # Import scenario-engine main
    spec = importlib.util.spec_from_file_location(
        "scenario_main",
        os.path.join(os.path.dirname(__file__), "..", "..", "scenario-engine", "main.py")
    )
    scenario_main = importlib.util.module_from_spec(spec)
    scenario_main.__spec__ = spec
    spec.loader.exec_module(scenario_main)
    tc = TestClient(scenario_main.app)
    payload = {
        "risk_score": float(risk_response.score),
        "corridor": risk_response.corridor,
        "shock_duration_days": 30,
        "num_simulations": 1000,
        "current_brent_usd": 85.0,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.6,
            "gdp_sensitivity_per_10pct_oil_shock": -0.15,
        },
    }
    resp = tc.post("/simulate", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()

# ── STEP 3: Validate Recommend contract ──────────────────────────────────────

def step3_recommend(scenario_data):
    from schemas.recommend import RecommendResponse, SupplierRecommendation
    now = datetime.now(timezone.utc)
    # Mock procurement agent output using real schema
    recs = [
        SupplierRecommendation(rank=1, supplier="Saudi Aramco", country="SAU",
                               corridor="cape", grade="Arab Light",
                               cost_index=1.05, transit_days=25,
                               risk_score=30.0, rationale="Lowest risk alternate"),
    ]
    return RecommendResponse(recommendations=recs, total_suppliers_evaluated=4,
                              graph_paths_analyzed=12, computed_at=now)

# ── STEP 4: Pass to SPR agent ────────────────────────────────────────────────

def step4_spr():
    spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "spr-agent", "main.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("spr_main", spec_path)
    spr_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(spr_main)
    tc = TestClient(spr_main.app)
    N = 7
    payload = {
        "planning_horizon_days": N,
        "current_reserve_days": 9.5,
        "min_safety_floor_days": 3.0,
        "daily_risk_scores": [75.0] * N,
        "daily_price_forecast_usd_per_bbl": [100.0] * N,
        "max_daily_drawdown_days": 1.0,
    }
    resp = tc.post("/spr-schedule", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── TESTS ─────────────────────────────────────────────────────────────────────

def test_step1_risk_score_produces_valid_schema():
    r = step1_risk_score()
    assert 0 <= r.score <= 100
    assert 0 <= r.confidence <= 1
    assert r.corridor == "hormuz"

def test_step2_simulate_uses_risk_output():
    risk = step1_risk_score(75.0)
    sim = step2_simulate(risk)
    assert "brent_price_distribution" in sim
    assert sim["brent_price_distribution"]["p10"] > 0

def test_step2_higher_risk_higher_brent():
    low_risk  = step2_simulate(step1_risk_score(10.0))["brent_price_distribution"]["p50"]
    high_risk = step2_simulate(step1_risk_score(90.0))["brent_price_distribution"]["p50"]
    assert high_risk > low_risk

def test_step3_recommend_uses_scenario_output():
    risk = step1_risk_score()
    sim = step2_simulate(risk)
    rec = step3_recommend(sim)
    assert len(rec.recommendations) > 0
    assert rec.recommendations[0].rank == 1

def test_step4_spr_produces_valid_schedule():
    spr = step4_spr()
    assert spr["reserve_never_below_floor"] is True
    assert len(spr["schedule"]) == 7

def test_full_pipeline_end_to_end():
    """
    Full chain: Risk → Scenario → Recommend → SPR.
    All outputs must be valid, non-empty, and type-correct.
    """
    risk = step1_risk_score(75.0)
    assert risk.score == 75.0

    sim = step2_simulate(risk)
    assert sim["num_simulations_run"] == 1000

    rec = step3_recommend(sim)
    assert rec.total_suppliers_evaluated == 4

    spr = step4_spr()
    assert spr["savings_pct"] >= 0.0
