"""
test_scenario_math.py — Scenario Engine mathematical validation.
Tests POST /simulate endpoint for monotonicity, bounds, and economic correctness.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scenario-engine"))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

BASE = {
    "risk_score": 50.0, "corridor": "hormuz", "shock_duration_days": 30,
    "num_simulations": 2000, "current_brent_usd": 85.0,
    "elasticity_assumptions": {"price_elasticity_of_demand": -0.05,
                                "pass_through_rate_to_pump": 0.6,
                                "gdp_sensitivity_per_10pct_oil_shock": -0.15},
}

def simulate(overrides={}):
    resp = client.post("/simulate", json={**BASE, **overrides})
    assert resp.status_code == 200, resp.text
    return resp.json()

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_simulate_returns_required_keys():
    data = simulate()
    for k in ["brent_price_distribution", "daily_price_path", "pump_price_impact",
               "gdp_impact_pct", "num_simulations_run", "calibration_note", "computed_at"]:
        assert k in data

def test_num_simulations_run_matches():
    assert simulate({"num_simulations": 3000})["num_simulations_run"] == 3000

def test_daily_path_length_matches_shock_duration():
    assert len(simulate({"shock_duration_days": 15})["daily_price_path"]) == 15

def test_distribution_percentile_ordering():
    dist = simulate()["brent_price_distribution"]
    assert dist["p10"] <= dist["p50"] <= dist["p90"]

def test_distribution_mean_within_bounds():
    dist = simulate()["brent_price_distribution"]
    assert dist["p10"] <= dist["mean"] <= dist["p90"]

def test_std_dev_positive():
    assert simulate()["brent_price_distribution"]["std_dev"] > 0

def test_higher_risk_higher_price():
    low = simulate({"risk_score": 10.0})["brent_price_distribution"]["p50"]
    high = simulate({"risk_score": 90.0})["brent_price_distribution"]["p50"]
    assert high > low

def test_higher_risk_wider_spread():
    def spread(r): 
        d = simulate({"risk_score": r})["brent_price_distribution"]
        return d["p90"] - d["p10"]
    assert spread(80.0) > spread(20.0)

def test_risk20_not_equal_to_risk80():
    low  = simulate({"risk_score": 20.0})["brent_price_distribution"]["p50"]
    high = simulate({"risk_score": 80.0})["brent_price_distribution"]["p50"]
    assert high > low * 1.02

def test_pump_price_p90_exceeds_p50():
    pump = simulate()["pump_price_impact"]
    assert pump["projected_p90_inr_per_litre"] >= pump["projected_p50_inr_per_litre"]

def test_pump_price_increases_with_high_risk():
    pump = simulate({"risk_score": 80.0})["pump_price_impact"]
    assert pump["projected_p50_inr_per_litre"] > pump["current_inr_per_litre"]

def test_gdp_impact_negative_at_high_risk():
    gdp = simulate({"risk_score": 80.0})["gdp_impact_pct"]
    assert gdp["p50"] < 0

def test_gdp_ordering():
    gdp = simulate()["gdp_impact_pct"]
    assert gdp["p10"] >= gdp["p50"] >= gdp["p90"]

def test_mock_endpoint():
    resp = client.get("/simulate/mock")
    assert resp.status_code == 200
    assert "brent_price_distribution" in resp.json()
