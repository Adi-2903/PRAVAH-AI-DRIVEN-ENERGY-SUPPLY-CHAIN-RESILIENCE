from api import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("\nTesting /spr-schedule...")
req_spr = {
    "planning_horizon_days": 14,
    "current_reserve_days": 9.5,
    "min_safety_floor_days": 6.0,
    "daily_risk_scores": [60]*14,
    "daily_price_forecast_usd_per_bbl": [84.0]*14,
    "max_daily_drawdown_days": 1.0
}
resp = client.post("/spr-schedule", json=req_spr)
print("SPR Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Total drawdown:", data["total_drawdown_days"])
    print("Replenishment window:", data["replenishment_window_days"])

print("\nTesting /coordinate...")
req_coord = {
    "corridor": "hormuz",
    "shock_duration_days": 14,
    "current_brent_usd": 84.0
}
resp = client.post("/final-recommendation", json=req_coord)
print("Coord Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Coord reasoning:", data["resolution"]["reasoning_trail"])
    print("Coord summary:", data["summary"])
