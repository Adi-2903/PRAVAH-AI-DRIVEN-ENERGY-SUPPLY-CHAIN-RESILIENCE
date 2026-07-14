import pytest
import httpx
from fastapi.testclient import TestClient
from shared.main import app

client = TestClient(app)

LIVE_SERVICES = {
    "risk": "http://localhost:8001",
    "scenario": "http://localhost:8002",
    "procurement": "http://localhost:8003",
    "spr": "http://localhost:8004",
}

GATED_ENDPOINTS = [
    ("scenario", "/simulate", {
        "current_brent_usd": 80.0,
        "shock_duration_days": 10,
        "num_simulations": 100,
        "risk_score": 50,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.5,
            "gdp_sensitivity_per_10pct_oil_shock": -0.1
        }
    }),
    ("procurement", "/recommend", {
        "current_supplier": "SAU_ARAMCO",
        "current_corridor_risk_score": 50,
        "target_refinery": "REF_JAMNAGAR",
        "required_crude_grade": "GRADE_MEDIUM_SOUR",
        "cost_weight": 0.5,
        "risk_weight": 0.3,
        "transit_time_weight": 0.2,
        "max_alternatives": 5
    }),
    ("spr", "/spr-schedule", {
        "planning_horizon_days": 7,
        "current_reserve_days": 10.0,
        "min_safety_floor_days": 3.0,
        "daily_risk_scores": [50] * 7,
        "daily_price_forecast_usd_per_bbl": [80] * 7,
        "max_daily_drawdown_days": 1.0
    }),
]

def test_unauthorized_access():
    """Verify gated endpoints block requests without auth headers on live services."""
    for service, path, payload in GATED_ENDPOINTS:
        url = f"{LIVE_SERVICES[service]}{path}"
        try:
            response = httpx.post(url, json=payload, timeout=5.0)
            assert response.status_code == 401, f"Expected 401 Unauthorized for {url}, got {response.status_code}"
        except httpx.RequestError as e:
            pytest.skip(f"Service {service} is not running: {e}")

def test_jwt_missing():
    """Verify requests with malformed/missing JWT are rejected."""
    for service, path, payload in GATED_ENDPOINTS:
        url = f"{LIVE_SERVICES[service]}{path}"
        try:
            # Need to provide some characters for the token to prevent header validation error
            response = httpx.post(url, json=payload, headers={"Authorization": "Bearer BAD"}, timeout=5.0)
            assert response.status_code == 401
        except httpx.RequestError as e:
            pytest.skip(f"Service {service} is not running: {e}")

def test_invalid_token():
    """Verify expired or improperly signed tokens are rejected."""
    for service, path, payload in GATED_ENDPOINTS:
        url = f"{LIVE_SERVICES[service]}{path}"
        try:
            response = httpx.post(url, json=payload, headers={"Authorization": "Bearer INVALID_TOKEN_HERE"}, timeout=5.0)
            assert response.status_code == 401
        except httpx.RequestError as e:
            pytest.skip(f"Service {service} is not running: {e}")


def test_health_endpoints_open():
    """Verify /health endpoints remain open to anonymous requests."""
    for service_name, base_url in LIVE_SERVICES.items():
        url = f"{base_url}/health"
        try:
            response = httpx.get(url, timeout=5.0)
            assert response.status_code == 200
        except httpx.RequestError as e:
            pytest.skip(f"Service {service_name} is not running: {e}")

@pytest.mark.skip(reason="not yet implemented")
def test_sql_injection_prevention():
    """Verify inputs are sanitized to prevent SQL injection."""
    pass

def test_malformed_payload():
    """Verify endpoints gracefully reject malformed JSON bodies."""
    # Sending raw invalid JSON text
    response = client.post(
        "/auth/login",
        content="this is not valid json",
        headers={"Content-Type": "application/json"}
    )
    # FastAPI typically returns 422 for malformed JSON, sometimes 400
    assert response.status_code in [400, 422]
    
    # Sending valid JSON but missing required fields according to Pydantic model
    response_missing = client.post(
        "/auth/login",
        json={"email": "incomplete@example.com"}
    )
    assert response_missing.status_code == 422

@pytest.mark.skip(reason="not yet implemented")
def test_large_payload_rejection():
    """Verify endpoints reject excessively large payloads."""
    pass

@pytest.mark.skip(reason="not yet implemented")
def test_rate_limiting():
    """Verify abusive IPs/tokens trigger rate limiting (429 Too Many Requests)."""
    pass
