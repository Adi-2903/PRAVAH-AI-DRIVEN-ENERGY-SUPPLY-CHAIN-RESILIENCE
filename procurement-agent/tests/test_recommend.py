import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_normal_recommendation():
    payload = {
        "current_supplier": "saudi_arabia",
        "current_corridor_risk_score": 78,
        "target_refinery": "jamnagar",
        "required_crude_grade": "medium_sour",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

def test_grade_incompatible():
    payload = {
        "current_supplier": "saudi_arabia",
        "current_corridor_risk_score": 78,
        "target_refinery": "jamnagar",
        "required_crude_grade": "unknown_grade",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 400

def test_weight_sum_invalid():
    payload = {
        "current_supplier": "saudi_arabia",
        "current_corridor_risk_score": 78,
        "target_refinery": "jamnagar",
        "required_crude_grade": "medium_sour",
        "cost_weight": 0.0,
        "risk_weight": 0.0,
        "transit_time_weight": 0.0,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 422 # validation error from pydantic

def test_weight_shift_changes_ranking():
    payload_cost = {
        "current_supplier": "saudi_arabia",
        "current_corridor_risk_score": 78,
        "target_refinery": "jamnagar",
        "required_crude_grade": "medium_sour",
        "cost_weight": 1.0,
        "risk_weight": 0.0,
        "transit_time_weight": 0.0,
        "max_alternatives": 5
    }
    response_cost = client.post("/recommend", json=payload_cost)
    assert response_cost.status_code == 200
    
    payload_risk = {
        "current_supplier": "saudi_arabia",
        "current_corridor_risk_score": 78,
        "target_refinery": "jamnagar",
        "required_crude_grade": "medium_sour",
        "cost_weight": 0.0,
        "risk_weight": 1.0,
        "transit_time_weight": 0.0,
        "max_alternatives": 5
    }
    response_risk = client.post("/recommend", json=payload_risk)
    assert response_risk.status_code == 200
    
    rank_cost = response_cost.json()["recommendations"][0]["supplier"]
    rank_risk = response_risk.json()["recommendations"][0]["supplier"]
    
    assert rank_cost != rank_risk
