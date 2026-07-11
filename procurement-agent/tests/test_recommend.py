import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


def test_normal_recommendation():
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
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
    """Requesting a grade node that does not exist in the graph should 400."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_UNKNOWN",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 400


def test_refinery_not_found():
    """Requesting a refinery that does not exist in the graph should 400."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_NONEXISTENT",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 400


def test_weight_sum_zero_invalid():
    """All-zero weights should be rejected (sums to zero → ValueError → 422)."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.0,
        "risk_weight": 0.0,
        "transit_time_weight": 0.0,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_weight_shift_changes_ranking():
    """Composite scores must change when weights change — the ranked list is weight-sensitive."""
    payload_cost = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 1.0,
        "risk_weight": 0.0,
        "transit_time_weight": 0.0,
        "max_alternatives": 5
    }
    response_cost = client.post("/recommend", json=payload_cost)
    assert response_cost.status_code == 200

    payload_transit = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.0,
        "risk_weight": 0.0,
        "transit_time_weight": 1.0,
        "max_alternatives": 5
    }
    response_transit = client.post("/recommend", json=payload_transit)
    assert response_transit.status_code == 200

    # Cost-only favours cheapest supplier; transit-only favours fastest route.
    # The top-ranked supplier must differ between the two extremes.
    top_cost    = response_cost.json()["recommendations"][0]["supplier"]
    top_transit = response_transit.json()["recommendations"][0]["supplier"]
    assert top_cost != top_transit, (
        f"Expected different top suppliers for cost-only vs transit-only weights, "
        f"but both returned '{top_cost}'. Check graph data."
    )


def test_composite_scores_in_descending_order():
    """Recommendations must be sorted highest composite_score first."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.4,
        "risk_weight": 0.4,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    scores = [r["composite_score"] for r in response.json()["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_rank_field_sequential():
    """rank field must be 1, 2, 3… with no gaps."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    ranks = [r["rank"] for r in response.json()["recommendations"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_market_data_present_in_response():
    """Response must include a market_data block."""
    payload = {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 78,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "market_data" in data
    md = data["market_data"]
    assert "brent_usd" in md
    assert "usd_inr" in md
    assert isinstance(md["is_live"], bool)


def test_health_endpoint():
    """Health check must return status ok and graph metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["graph_nodes"] > 0
    assert data["graph_edges"] > 0
