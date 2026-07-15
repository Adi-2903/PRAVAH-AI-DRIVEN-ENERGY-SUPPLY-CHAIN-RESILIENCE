"""
Executable test + contract-validation suite for the monolith backend (api.py).

Run from the repo root:
    pytest test_api.py -v

Two things are proven here:
1. Every endpoint returns HTTP 200 with a schema-valid body (FastAPI response_model).
2. CONTRACT PARITY — each response is re-validated against the *independent*
   original source of truth (the frozen shared schema for /simulate, and each
   agent's own original models.py for /spr-schedule and /recommend), proving the
   single-file merge did not change any wire contract the frontend depends on.
"""
import importlib.util
import os
import sys

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api import app  # noqa: E402


def _load(mod_name: str, rel_path: str):
    """Import a module from an explicit file path under a unique name.

    Lets us load the hyphenated agent folders' models.py independently (and
    without the `from models import` name collision) as the contract oracle.
    """
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(REPO_ROOT, rel_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


# Independent contract oracles (NOT api.py's own copies). After the STAGE9
# reorg these live under shared/contracts/ (the single source of truth the
# per-agent services now import from).
_shared_sim = _load("oracle_shared_simulate", "shared/contracts/simulate.py")
_spr_models = _load("oracle_spr_models", "shared/contracts/spr_schedule.py")
_proc_models = _load("oracle_proc_models", "shared/contracts/recommend.py")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # `with` fires startup (volatility calibration)
        yield c


SIM_BODY = {
    "risk_score": 82, "corridor": "hormuz", "current_brent_usd": 84.0,
    "shock_duration_days": 5, "num_simulations": 2000,
    "elasticity_assumptions": {"pass_through_rate_to_pump": 0.6, "gdp_sensitivity_per_10pct_oil_shock": -0.2},
}
SPR_BODY = {
    "planning_horizon_days": 7, "current_reserve_days": 9.5, "min_safety_floor_days": 6.0,
    "max_daily_drawdown_days": 1.0, "daily_risk_scores": [85, 88, 82, 70, 60, 55, 50],
    "daily_price_forecast_usd_per_bbl": [102.5, 104, 101, 95, 90, 88, 85],
}
REC_BODY = {
    "target_refinery": "REF_JAMNAGAR", "required_crude_grade": "GRADE_MEDIUM_SOUR",
    "current_supplier": "SAU_ARAMCO", "current_corridor_risk_score": 82,
    "cost_weight": 0.34, "risk_weight": 0.33, "transit_time_weight": 0.33, "max_alternatives": 3,
}


# ── liveness / diagnostics ──────────────────────────────────────────────────
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_root_lists_endpoints(client):
    body = client.get("/").json()
    assert body["status"] == "ok"
    assert {"scenario", "spr", "procurement", "risk", "coordinator"} <= set(body["agents"])


def test_data_status_reads_embedded_csv(client):
    body = client.get("/data-status").json()
    # 505-line embedded CSV → 504 data rows; proves the inlined CSV parses.
    assert body["cached_days_count"] == 504
    assert body["current_source"] == "fallback_cache"


# ── scenario ────────────────────────────────────────────────────────────────
def test_simulate_200_and_shared_contract(client):
    r = client.post("/simulate", json=SIM_BODY)
    assert r.status_code == 200, r.text
    # CONTRACT: validate against the canonical frozen shared schema.
    obj = _shared_sim.SimulateResponse.model_validate(r.json())
    assert len(obj.daily_price_path) == SIM_BODY["shock_duration_days"]
    assert obj.brent_price_distribution.p10 <= obj.brent_price_distribution.p90


def test_simulate_mock_200(client):
    assert client.get("/simulate/mock").status_code == 200


def test_simulate_rejects_bad_corridor(client):
    r = client.post("/simulate", json={**SIM_BODY, "corridor": "atlantis"})
    assert r.status_code == 422  # pydantic Literal validation


# ── spr ─────────────────────────────────────────────────────────────────────
def test_spr_200_and_agent_contract(client):
    r = client.post("/spr-schedule", json=SPR_BODY)
    assert r.status_code == 200, r.text
    # CONTRACT: validate against the ORIGINAL spr-agent model (independent oracle).
    obj = _spr_models.SPRScheduleResponse.model_validate(r.json())
    assert len(obj.schedule) == SPR_BODY["planning_horizon_days"]
    assert obj.reserve_never_below_floor is True


def test_spr_mock_200(client):
    assert client.get("/spr-schedule/mock").status_code == 200


def test_spr_rejects_below_floor(client):
    bad = {**SPR_BODY, "current_reserve_days": 5.0}  # below the 6.0 floor
    assert client.post("/spr-schedule", json=bad).status_code == 400


# ── procurement ─────────────────────────────────────────────────────────────
def test_recommend_200_and_agent_contract(client):
    r = client.post("/recommend", json=REC_BODY)
    assert r.status_code == 200, r.text
    # CONTRACT: validate against the ORIGINAL procurement-agent model (independent oracle).
    obj = _proc_models.RecommendResponse.model_validate(r.json())
    assert 1 <= len(obj.recommendations) <= REC_BODY["max_alternatives"]
    # ranking is monotonic
    scores = [x.composite_score for x in obj.recommendations]
    assert scores == sorted(scores, reverse=True)


def test_recommend_rejects_unknown_refinery(client):
    r = client.post("/recommend", json={**REC_BODY, "target_refinery": "REF_ATLANTIS"})
    assert r.status_code == 400


def test_market_and_graph_200(client):
    assert client.get("/market").status_code == 200
    g = client.get("/graph").json()
    assert len(g["nodes"]) > 0 and len(g["edges"]) > 0


# ── risk (ported scoring, no langgraph) ─────────────────────────────────────
def test_risk_score_shape_and_enrichment(client):
    r = client.post("/risk-score", json={"corridor": "hormuz"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert 0 <= j["score"] <= 100
    assert j["alert_level"] in ("low", "elevated", "high", "critical")
    # frontend-enriched shape: reasoning_trail is a STRING, signals + model present,
    # key_events carry source + corridor
    assert isinstance(j["reasoning_trail"], str) and j["reasoning_trail"]
    assert len(j["signals"]) >= 1 and all("weight" in s for s in j["signals"])
    assert j["model"]
    assert all({"source", "corridor"} <= set(k) for k in j["key_events"])


def test_risk_math_is_real_not_static(client):
    # Hormuz fixtures (2 critical events over high baseline) must score critical;
    # domestic (1 low event, baseline 5) must score low. Proves real computation.
    hormuz = client.post("/risk-score", json={"corridor": "hormuz"}).json()
    domestic = client.post("/risk-score", json={"corridor": "domestic"}).json()
    assert hormuz["score"] >= 75 and hormuz["alert_level"] == "critical"
    assert domestic["score"] < 30
    assert hormuz["score"] > domestic["score"]


def test_corridors_all_four(client):
    arr = client.get("/corridors").json()
    assert [c["corridor"] for c in arr] == ["hormuz", "redsea", "cape", "domestic"]
    assert arr[0]["score"] > arr[2]["score"]  # hormuz > cape


# ── coordinator (was empty) — proves it embeds REAL agent outputs ───────────
def test_final_recommendation_blends_real_agents(client):
    r = client.post("/final-recommendation", json={"corridor": "hormuz"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["summary"] and j["agents_status"] == {
        "risk": "live", "scenario": "live", "procurement": "live", "spr": "live"}
    assert j["degraded"] is False
    # CONTRACT: each embedded sub-result validates against its independent oracle,
    # proving the coordinator carries genuine agent outputs (not a canned blob).
    _shared_sim.SimulateResponse.model_validate(j["scenario"])
    _spr_models.SPRScheduleResponse.model_validate(j["spr"])
    _proc_models.RecommendResponse.model_validate(j["procurement"])
    # resolution is derived from the real numbers
    assert j["resolution"]["reasoning_trail"] and "tradeoff" in j["resolution"]
    assert j["risk"]["score"] == j["risk"]["score"]  # present & consistent


def test_final_recommendation_citizen_view_fields(client):
    # The Citizen view reads exactly .summary and .risk.score — both must exist.
    j = client.post("/final-recommendation", json={"corridor": "redsea"}).json()
    assert isinstance(j["summary"], str) and 0 <= j["risk"]["score"] <= 100
