from api import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("\nTesting /recommend...")
req = {
    "current_supplier": "SAU_ARAMCO", 
    "current_corridor_risk_score": 60, 
    "target_refinery": "REF_JAMNAGAR", 
    "required_crude_grade": "GRADE_MEDIUM_SOUR", 
    "cost_weight": 0.6, 
    "risk_weight": 0.2, 
    "transit_time_weight": 0.2
}
resp = client.post("/recommend", json=req)
print("Recommend Status:", resp.status_code)
if resp.status_code == 200:
    for rec in resp.json()["recommendations"][:2]:
        print(rec["supplier"], rec["reasoning"])
