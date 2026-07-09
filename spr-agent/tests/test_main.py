from fastapi.testclient import TestClient
import sys
import os

# Ensure we can import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_normal_case():
    payload = {
        "planning_horizon_days": 3,
        "current_reserve_days": 9.5,
        "min_safety_floor_days": 8.0,
        "daily_risk_scores": [90, 80, 50],
        "daily_price_forecast_usd_per_bbl": [100, 95, 80],
        "max_daily_drawdown_days": 1.0
    }
    response = client.post("/spr-schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["schedule"]) == 3
    assert data["total_drawdown_days"] <= 1.5
    assert data["reserve_never_below_floor"] is True

def test_floor_constraint_binding():
    # Only 0.5 days available to draw
    payload = {
        "planning_horizon_days": 3,
        "current_reserve_days": 3.5,
        "min_safety_floor_days": 3.0,
        "daily_risk_scores": [100, 100, 100],
        "daily_price_forecast_usd_per_bbl": [120, 120, 120],
        "max_daily_drawdown_days": 1.0
    }
    response = client.post("/spr-schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Should only draw 0.5 total
    assert round(data["total_drawdown_days"], 2) == 0.5
    assert data["reserve_never_below_floor"] is True
    # The last day's reserve should be exactly the floor
    assert data["schedule"][-1]["reserve_after_days"] >= 3.0

def test_invalid_input_length():
    payload = {
        "planning_horizon_days": 5, # Mismatch
        "current_reserve_days": 9.5,
        "min_safety_floor_days": 3.0,
        "daily_risk_scores": [90, 80, 50],
        "daily_price_forecast_usd_per_bbl": [100, 95, 80],
        "max_daily_drawdown_days": 1.0
    }
    response = client.post("/spr-schedule", json=payload)
    assert response.status_code == 422
