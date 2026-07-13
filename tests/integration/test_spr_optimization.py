"""
test_spr_optimization.py — SPR Agent optimization validation.
Tests POST /spr-schedule for constraint satisfaction and economic correctness.
"""
import sys, os

# SPR dir must be FIRST so spr-agent/models.py shadows scenario-engine/models.py
SPR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "spr-agent"))
SCENARIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scenario-engine"))
# Remove scenario-engine from path if it's there — it has a conflicting models.py
if SCENARIO_DIR in sys.path:
    sys.path.remove(SCENARIO_DIR)
if SPR_DIR not in sys.path:
    sys.path.insert(0, SPR_DIR)

import pytest
from fastapi.testclient import TestClient
import importlib.util

_spec = importlib.util.spec_from_file_location("spr_main", os.path.join(SPR_DIR, "main.py"))
_spr_main = importlib.util.module_from_spec(_spec)
# Clear any cached 'models' module from scenario-engine before loading SPR
sys.modules.pop("models", None)
_spec.loader.exec_module(_spr_main)
app = _spr_main.app

client = TestClient(app)

N = 7
BASE = {
    "planning_horizon_days": N,
    "current_reserve_days": 9.5,
    "min_safety_floor_days": 3.0,
    "daily_risk_scores": [80.0] * N,
    "daily_price_forecast_usd_per_bbl": [100.0] * N,
    "max_daily_drawdown_days": 1.0,
}

def spr(overrides={}):
    resp = client.post("/spr-schedule", json={**BASE, **overrides})
    assert resp.status_code == 200, resp.text
    return resp.json()

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_spr_response_structure():
    data = spr()
    for k in ["schedule", "total_drawdown_days", "baseline_cost_usd",
               "optimized_cost_usd", "savings_usd", "savings_pct",
               "reserve_never_below_floor", "computed_at"]:
        assert k in data

def test_schedule_length_matches_horizon():
    data = spr()
    assert len(data["schedule"]) == N

def test_reserve_never_below_floor():
    """Optimizer must set reserve_never_below_floor=True."""
    data = spr()
    assert data["reserve_never_below_floor"] is True

def test_daily_drawdown_never_exceeds_max():
    """Each day's drawdown must not exceed max_daily_drawdown_days."""
    data = spr()
    for day in data["schedule"]:
        assert day["drawdown_days"] <= 1.0 + 1e-5

def test_daily_drawdown_never_negative():
    data = spr()
    for day in data["schedule"]:
        assert day["drawdown_days"] >= -1e-5, f"Negative drawdown on day {day['day']}"

def test_reserve_monotonically_decreasing_or_stable():
    """reserve_after_days must never increase day-over-day."""
    data = spr()
    schedule = data["schedule"]
    for i in range(1, len(schedule)):
        prev = schedule[i-1]["reserve_after_days"]
        curr = schedule[i]["reserve_after_days"]
        assert curr <= prev + 1e-5

def test_total_drawdown_sum_matches_schedule():
    data = spr()
    declared = data["total_drawdown_days"]
    calculated = sum(d["drawdown_days"] for d in data["schedule"])
    assert abs(declared - calculated) < 0.01

def test_optimized_cost_lte_baseline():
    data = spr()
    assert data["optimized_cost_usd"] <= data["baseline_cost_usd"] + 1.0

def test_savings_pct_non_negative():
    data = spr()
    assert data["savings_pct"] >= 0.0

def test_array_length_mismatch_returns_422():
    payload = {**BASE, "daily_risk_scores": [80.0] * 5}
    resp = client.post("/spr-schedule", json=payload)
    assert resp.status_code == 422

def test_reserve_below_floor_returns_400():
    payload = {**BASE, "current_reserve_days": 2.0, "min_safety_floor_days": 3.0}
    resp = client.post("/spr-schedule", json=payload)
    assert resp.status_code == 400

def test_zero_risk_produces_conservative_drawdown():
    low_risk  = spr({"daily_risk_scores": [5.0]  * N})["total_drawdown_days"]
    high_risk = spr({"daily_risk_scores": [95.0] * N})["total_drawdown_days"]
    assert high_risk >= low_risk

def test_mock_endpoint():
    resp = client.get("/spr-schedule/mock")
    assert resp.status_code == 200
    assert resp.json()["reserve_never_below_floor"] is True
