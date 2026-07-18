"""
Pravah — Endpoint Test Suite
Covers every endpoint that was modified or added this session.
Prints PASS/FAIL clearly so we know what is working.
"""
import json
import sys
from api import app
from fastapi.testclient import TestClient

client = TestClient(app)
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def check(name: str, condition: bool, detail: str = ""):
    marker = PASS if condition else FAIL
    msg = f"{marker} {name}"
    if detail:
        # strip non-ASCII so Windows cp1252 terminal never crashes
        safe = detail.encode('ascii', errors='replace').decode('ascii')
        msg += f"  |  {safe}"
    print(msg)
    results.append((name, condition))
    return condition


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── 1. /graph ──────────────────────────────────────────────────
section("1. /graph — topology nodes & coords")
r = client.get("/graph")
check("/graph returns 200", r.status_code == 200)
if r.status_code == 200:
    d = r.json()
    check("Nodes present", len(d.get("nodes", [])) > 0,
          f"count={len(d.get('nodes', []))}")
    check("Edges present", len(d.get("edges", [])) > 0,
          f"count={len(d.get('edges', []))}")
    sample = d["nodes"][:2]
    has_coords = all("lat" in n and "lon" in n for n in sample)
    check("Nodes have lat/lon", has_coords,
          str({n["id"]: (n.get("lat"), n.get("lon")) for n in sample}))

# ── 2. /fleet ──────────────────────────────────────────────────
section("2. /fleet — vessel positions")
r = client.get("/fleet")
check("/fleet returns 200", r.status_code == 200)
if r.status_code == 200:
    fleet = r.json().get("fleet", [])
    check("Fleet non-empty", len(fleet) > 0, f"vessels={len(fleet)}")
    check("Vessels have lat/lon", all("lat" in v and "lon" in v for v in fleet))

# ── 3. /risk-score ─────────────────────────────────────────────
section("3. /risk-score — supplier_risk_scores field")
r = client.post("/risk-score", json={"corridor": "hormuz"})
check("/risk-score returns 200", r.status_code == 200)
if r.status_code == 200:
    d = r.json()
    check("score in 0-100", 0 <= d["score"] <= 100, f"score={d['score']}")
    check("alert_level present", bool(d.get("alert_level")), d.get("alert_level"))
    check("supplier_risk_scores present",
          isinstance(d.get("supplier_risk_scores"), dict),
          str(d.get("supplier_risk_scores")))
    check("reasoning_trail non-empty",
          bool(d.get("reasoning_trail")), d.get("reasoning_trail", "")[:80])

# ── 4. /spr-schedule ───────────────────────────────────────────
section("4. /spr-schedule — replenishment_window_days + seasonality")
spr_body = {
    "planning_horizon_days": 30,
    "current_reserve_days": 90,
    "min_safety_floor_days": 45,
    "max_daily_drawdown_days": 2,
    "daily_risk_scores": [70] * 30,
    "daily_price_forecast_usd_per_bbl": [85.0] * 30
}
r = client.post("/spr-schedule", json=spr_body)
check("/spr-schedule returns 200", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
if r.status_code == 200:
    d = r.json()
    check("replenishment_window_days present",
          d.get("replenishment_window_days") is not None,
          f"window={d.get('replenishment_window_days')} days")
    # Find the schedule field name dynamically — it may be 'schedule' or 'optimized_schedule'
    sched_key = next((k for k in d if "schedule" in k.lower()), None)
    check("schedule list present in response",
          sched_key is not None and isinstance(d.get(sched_key), list),
          f"field='{sched_key}', len={len(d.get(sched_key, []))}")
    check("value_usd_saved positive", d.get("value_usd_saved", 0) >= 0,
          f"saved=${d.get('value_usd_saved', 0):,.0f}")

# ── 5. /simulate — scenario_type ───────────────────────────────
section("5. /simulate — base, hormuz_closure, opec_cut presets")
sim_base = {
    "risk_score": 70, "corridor": "hormuz", "shock_duration_days": 14,
    "num_simulations": 2000, "current_brent_usd": 84.0,
    "elasticity_assumptions": {
        "price_elasticity_of_demand": -0.05,
        "pass_through_rate_to_pump": 0.6,
        "gdp_sensitivity_per_10pct_oil_shock": -0.15
    }
}
# base
r_base = client.post("/simulate", json={**sim_base, "scenario_type": "base"})
check("/simulate base returns 200", r_base.status_code == 200)

# hormuz_closure
r_hormuz = client.post("/simulate", json={**sim_base, "scenario_type": "hormuz_closure", "risk_score": 90})
check("/simulate hormuz_closure returns 200", r_hormuz.status_code == 200)

# opec_cut
r_opec = client.post("/simulate", json={**sim_base, "scenario_type": "opec_cut", "risk_score": 60})
check("/simulate opec_cut returns 200", r_opec.status_code == 200)

if r_base.status_code == r_hormuz.status_code == r_opec.status_code == 200:
    p50_base   = r_base.json()["brent_price_distribution"]["p50"]
    p50_hormuz = r_hormuz.json()["brent_price_distribution"]["p50"]
    p50_opec   = r_opec.json()["brent_price_distribution"]["p50"]
    print(f"         P50 prices -> base={p50_base:.2f}  hormuz_closure={p50_hormuz:.2f}  opec_cut={p50_opec:.2f}")
    # hormuz_closure at risk=90 should be MUCH higher than base at risk=70
    check("hormuz_closure P50 > base P50",
          p50_hormuz > p50_base,
          f"{p50_hormuz:.2f} vs {p50_base:.2f}")

# ── 6. /recommend ──────────────────────────────────────────────
section("6. /recommend — port congestion + tanker availability in reasoning")
r = client.post("/recommend", json={
    "current_supplier": "SAU_ARAMCO",
    "current_corridor_risk_score": 78,
    "target_refinery": "REF_JAMNAGAR",
    "required_crude_grade": "GRADE_MEDIUM_SOUR",
    "cost_weight": 0.5,
    "risk_weight": 0.3,
    "transit_time_weight": 0.2,
    "max_alternatives": 5
})
check("/recommend returns 200", r.status_code == 200)
if r.status_code == 200:
    d = r.json()
    recs = d.get("recommendations", [])
    check("at least 1 alternative returned (up to max_alternatives)", len(recs) >= 1, f"count={len(recs)}")
    first = recs[0] if recs else {}
    reasoning = first.get("reasoning", "")
    check("rank 1 has a reasoning string", bool(reasoning), reasoning[:120])
    # check that at least one of the new signals appear in reasoning text
    signals = ["congestion", "tanker", "port", "availability"]
    has_signal = any(sig.lower() in reasoning.lower() for sig in signals)
    check("reasoning mentions congestion/tanker/port signal", has_signal, reasoning[:200])

# ── 7. /generate-policy — fallback works ───────────────────────
section("7. /generate-policy — graceful fallback (no GEMINI_API_KEY)")
r = client.post("/generate-policy")
check("/generate-policy returns 200 (not 500)", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
if r.status_code == 200:
    d = r.json()
    check("summary present", bool(d.get("summary")), d.get("summary", "")[:80])
    check("3 actions returned", len(d.get("actions", [])) == 3, f"count={len(d.get('actions', []))}")
    check("confidence > 0", d.get("confidence", 0) > 0, f"confidence={d.get('confidence')}")

# ── 8. /final-recommendation — scenario_type propagation ───────
section("8. /final-recommendation — scenario_type propagation")
r = client.post("/final-recommendation", json={
    "corridor": "hormuz",
    "current_brent_usd": 84.0,
    "shock_duration_days": 14,
    "scenario_type": "hormuz_closure"
})
check("/final-recommendation returns 200", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
if r.status_code == 200:
    d = r.json()
    # risk.score is nested under the 'risk' sub-object
    risk_obj = d.get("risk", {})
    check("risk.score present", risk_obj.get("score") is not None,
          f"score={risk_obj.get('score')}")
    check("summary present", bool(d.get("summary")), d.get("summary", "")[:100])
    # procurement.recommendations is nested under the 'procurement' sub-object
    proc_obj = d.get("procurement", {})
    check("procurement.recommendations list returned",
          isinstance(proc_obj.get("recommendations"), list),
          f"count={len(proc_obj.get('recommendations', []))}")

# ── 9. /corridors ──────────────────────────────────────────────
section("9. /corridors — all 4 corridors")
r = client.get("/corridors")
check("/corridors returns 200", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    check("4 corridors returned", len(data) == 4, f"count={len(data)}")
    ids = [c["corridor"] for c in data]  # field is 'corridor', not 'corridor_id'
    for cid in ["hormuz", "redsea", "cape", "domestic"]:
        check(f"  corridor '{cid}' present", cid in ids)

# ── Summary ────────────────────────────────────────────────────
section("SUMMARY")
total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
print(f"\n  {passed}/{total} tests passed  ({failed} failed)\n")
if failed > 0:
    print("  FAILED tests:")
    for name, ok in results:
        if not ok:
            print(f"    {FAIL} {name}")

sys.exit(0 if failed == 0 else 1)
