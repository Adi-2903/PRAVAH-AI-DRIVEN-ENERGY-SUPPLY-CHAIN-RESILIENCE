"""Pravah Risk Agent — FastAPI microservice.

Exposes ``POST /risk-score`` returning the frozen ``RiskScoreResponse`` contract
from shared/schemas. Runs the LangGraph pipeline (ingest → classify → corridor →
severity → score → store) and returns an explainable reasoning trail.
"""
import os
import sys
from datetime import datetime, timezone

# Make the repo-root `shared` package importable when run from inside this
# folder (uvicorn main:app) — this folder's name has a hyphen and can't be a
# package itself, so we add the repo root to sys.path explicitly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, ".env"))  # shared root .env (Supabase creds)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas.risk_score import RiskScoreRequest, RiskScoreResponse, KeyEvent
from graph import run_pipeline

app = FastAPI(title="Pravah Risk Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/risk-score", response_model=RiskScoreResponse)
def risk_score(req: RiskScoreRequest) -> RiskScoreResponse:
    result, data_sources, _store = run_pipeline(req.corridor, req.as_of)
    return RiskScoreResponse(
        corridor=req.corridor,
        score=result["score"],
        confidence=result["confidence"],
        alert_level=result["alert_level"],
        reasoning_trail=result["reasoning_trail"],
        key_events=[KeyEvent(**k) for k in result["key_events"]],
        computed_at=datetime.now(timezone.utc),
        data_sources=data_sources,
    )
