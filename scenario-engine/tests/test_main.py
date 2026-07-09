from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_simulate_mock():
    response = client.get("/simulate/mock")
    assert response.status_code == 200
    data = response.json()
    assert data["num_simulations_run"] == 5000

def test_simulate_normal():
    payload = {
        "risk_score": 78,
        "corridor": "hormuz",
        "shock_duration_days": 14,
        "num_simulations": 1000,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.7,
            "gdp_sensitivity_per_10pct_oil_shock": -0.15
        },
        "current_brent_usd": 82.0
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["num_simulations_run"] == 1000
    assert len(data["daily_price_path"]) == 14
    assert data["calibration_note"].startswith("elasticities validated")

def test_simulate_edge_case_zero_risk():
    payload = {
        "risk_score": 0,
        "corridor": "hormuz",
        "shock_duration_days": 5,
        "num_simulations": 1000,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.7,
            "gdp_sensitivity_per_10pct_oil_shock": -0.15
        },
        "current_brent_usd": 82.0
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    dist = data["brent_price_distribution"]
    
    # with 0 risk, spread (p90-p10) should be relatively small
    spread = dist["p90"] - dist["p10"]
    assert spread < 30.0 # Just a sanity check for small spread

def test_simulate_invalid_input():
    payload = {
        "risk_score": 150, # Out of range (0-100)
        "corridor": "hormuz",
        "shock_duration_days": 14,
        "num_simulations": 5000,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.7,
            "gdp_sensitivity_per_10pct_oil_shock": -0.15
        },
        "current_brent_usd": 82.0
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 422
