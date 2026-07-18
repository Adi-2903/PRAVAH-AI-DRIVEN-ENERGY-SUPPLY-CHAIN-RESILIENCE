from api import app
from fastapi.testclient import TestClient
import json

client = TestClient(app)

print("Testing /graph...")
resp = client.get("/graph")
print("Graph Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Nodes:", len(data["nodes"]), "Edges:", len(data["edges"]))
    # check for lat/lon in a node
    print("Sample node coords:", {n["id"]: (n.get("lat"), n.get("lon")) for n in data["nodes"][:2]})

print("\nTesting /fleet...")
resp = client.get("/fleet")
print("Fleet Status:", resp.status_code)
if resp.status_code == 200:
    print("Fleet Count:", len(resp.json()["fleet"]))

print("\nTesting /risk-score (Hormuz)...")
resp = client.post("/risk-score", json={"corridor": "hormuz"})
print("Risk Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Score:", data["score"], "Alert:", data["alert_level"])
    print("Supplier Scores:", data.get("supplier_risk_scores"))
    print("Trail:", data.get("reasoning_trail")[:100], "...")
else:
    print(resp.text)
