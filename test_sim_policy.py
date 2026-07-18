from api import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("\nTesting /simulate...")
req_sim = {
    "risk_score": 90,
    "corridor": "hormuz",
    "shock_duration_days": 14,
    "num_simulations": 1000,
    "current_brent_usd": 84.0,
    "elasticity_assumptions": {
        "price_elasticity_of_demand": -0.05,
        "pass_through_rate_to_pump": 0.6,
        "gdp_sensitivity_per_10pct_oil_shock": -0.15
    },
    "scenario_type": "hormuz_closure"
}
resp = client.post("/simulate", json=req_sim)
print("Simulate Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("P50 Price:", data["brent_price_distribution"]["p50"])

print("\nTesting /generate-policy...")
resp = client.post("/generate-policy")
print("Policy Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Policy summary:", data["summary"])
