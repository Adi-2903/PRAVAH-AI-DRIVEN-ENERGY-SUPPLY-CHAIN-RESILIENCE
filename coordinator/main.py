import os
import sys
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from shared.contracts.coordinator import CoordinatorRequest, CoordinatorResponse
from shared.contracts.risk_score import RiskScoreRequest
from shared.contracts.simulate import SimulateRequest, ElasticityAssumptions
from shared.contracts.recommend import RecommendRequest
from shared.contracts.spr_schedule import SPRScheduleRequest

app = FastAPI(title="Pravah Coordinator Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ready"}

@app.post("/coordinate", response_model=CoordinatorResponse)
async def coordinate(req: CoordinatorRequest) -> CoordinatorResponse:
    as_of = datetime.now(timezone.utc)
    
    # We will call the agents sequentially for simplicity
    async with httpx.AsyncClient() as client:
        # 1. Risk
        risk_req = RiskScoreRequest(corridor=req.corridor, as_of=as_of)
        r = await client.post("http://127.0.0.1:8001/risk-score", json=risk_req.model_dump(mode="json"), timeout=15.0)
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=f"Risk agent failed: {r.text}")
        risk_res = r.json()
        
        # 2. Scenario
        scen_req = SimulateRequest(
            risk_score=risk_res["score"],
            corridor=req.corridor,
            shock_duration_days=30,
            num_simulations=1000,
            current_brent_usd=82.0,
            elasticity_assumptions=ElasticityAssumptions()
        )
        r = await client.post("http://127.0.0.1:8002/simulate", json=scen_req.model_dump(mode="json"), timeout=15.0)
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=f"Scenario agent failed: {r.text}")
        scen_res = r.json()
        
        # 3. Procurement
        proc_req = RecommendRequest(
            current_supplier="SAU_ARAMCO",
            current_corridor_risk_score=risk_res["score"],
            target_refinery=req.target_refinery,
            required_crude_grade="GRADE_MEDIUM_SOUR",
            cost_weight=0.5,
            risk_weight=0.3,
            transit_time_weight=0.2,
            max_alternatives=5
        )
        r = await client.post("http://127.0.0.1:8003/recommend", json=proc_req.model_dump(mode="json"), timeout=15.0)
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=f"Procurement agent failed: {r.text}")
        proc_res = r.json()
        
        # 4. SPR
        spr_req = SPRScheduleRequest(
            planning_horizon_days=30,
            current_reserve_days=9.5,
            min_safety_floor_days=5.0,
            daily_risk_scores=[risk_res["score"]] * 30,
            daily_price_forecast_usd_per_bbl=[p["p50"] for p in scen_res["daily_price_path"]],
            max_daily_drawdown_days=1.0
        )
        r = await client.post("http://127.0.0.1:8004/schedule", json=spr_req.model_dump(mode="json"), timeout=15.0)
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=f"SPR agent failed: {r.text}")
        spr_res = r.json()
        
    summary = (f"The {req.corridor} corridor is at {risk_res['alert_level'].upper()} risk ({risk_res['score']}/100). "
               f"In a 30-day disruption, Brent is projected to reach ${scen_res['brent_price_distribution']['p50']:.0f}/bbl (median). "
               f"Combined strategy: Re-route via top recommended supplier and draw down SPR to mitigate price shocks.")
        
    return CoordinatorResponse(
        summary=summary,
        risk=risk_res,
        scenario=scen_res,
        procurement=proc_res,
        spr=spr_res,
        as_of=as_of
    )
