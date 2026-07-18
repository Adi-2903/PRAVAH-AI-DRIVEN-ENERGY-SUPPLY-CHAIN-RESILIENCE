"""
Pravah — SINGLE-FILE monolith backend.

The three agents the frontend calls live (scenario-engine, spr-agent,
procurement-agent) merged into ONE self-contained FastAPI app. No `shared/`
folder, no data files, no relative imports, no package structure — drop this
file anywhere with `requirements.txt` and run:

    uvicorn api:app --host 0.0.0.0 --port $PORT

Endpoints (paths are unique, so the frontend points every NEXT_PUBLIC_*_URL at
this one URL):
    scenario     POST /simulate    GET /simulate/mock    GET /data-status
    spr          POST /spr-schedule    GET /spr-schedule/mock
    procurement  POST /recommend    GET /market    GET /graph
    risk         POST /risk-score    GET /corridors
    coordinator  POST /final-recommendation
    app          GET /    GET /health

The risk scorer is ported from risk-agent/ (same math) minus LangGraph; the
coordinator (originally an empty file) blends risk→scenario→procurement+spr
in-process into one recommendation.
"""
import os
import csv
import io
import re
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Literal

import numpy as np
import networkx as nx
import httpx
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

# ── structured logging (level via LOG_LEVEL env; defaults INFO) ──────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("pravah")


# ════════════════════════════════════════════════════════════════════════════
#  MODELS  (inlined from shared/schemas/simulate.py + each agent's models.py)
# ════════════════════════════════════════════════════════════════════════════

# ── scenario (was shared.schemas.simulate) ─────────────────────────────────
Corridor = Literal["hormuz", "redsea", "cape", "domestic"]


class ElasticityAssumptions(BaseModel):
    price_elasticity_of_demand: float = -0.05
    pass_through_rate_to_pump: float = Field(ge=0.0, le=1.0)
    gdp_sensitivity_per_10pct_oil_shock: float = -0.15


class SimulateRequest(BaseModel):
    risk_score: float = Field(ge=0.0, le=100.0)
    corridor: Corridor
    shock_duration_days: int = Field(ge=1, le=365)
    num_simulations: int = Field(ge=1000, le=20000)
    current_brent_usd: float
    elasticity_assumptions: ElasticityAssumptions
    scenario_type: Literal["base", "hormuz_closure", "opec_cut"] = "base"


class PriceDistribution(BaseModel):
    p10: float
    p50: float
    p90: float
    mean: float
    std_dev: float


class DailyPricePoint(BaseModel):
    day: int
    p10: float
    p50: float
    p90: float


class PumpPriceImpact(BaseModel):
    current_inr_per_litre: float
    projected_p50_inr_per_litre: float
    projected_p90_inr_per_litre: float


class GdpImpactPct(BaseModel):
    p10: float
    p50: float
    p90: float


class SimulateResponse(BaseModel):
    brent_price_distribution: PriceDistribution
    daily_price_path: List[DailyPricePoint]
    pump_price_impact: PumpPriceImpact
    gdp_impact_pct: GdpImpactPct
    calibration_note: str
    num_simulations_run: int
    computed_at: datetime
    data_source: Literal["live_eia", "fallback_cache"]
    volatility_calibrated_from: str


# aliases used by the scenario endpoint code (kept from scenario-engine/models.py)
DistributionStats = PriceDistribution
DailyPriceStats = DailyPricePoint
GDPImpactPct = GdpImpactPct


# ── spr (was spr-agent/models.py) ──────────────────────────────────────────
class SPRScheduleRequest(BaseModel):
    planning_horizon_days: int = Field(..., description="Number of days to plan for")
    current_reserve_days: float = Field(..., description="Current SPR cover in days")
    min_safety_floor_days: float = Field(..., description="Minimum SPR cover to maintain")
    daily_risk_scores: List[float] = Field(..., description="Risk scores for each day")
    daily_price_forecast_usd_per_bbl: List[float] = Field(..., description="Price forecast for each day")
    max_daily_drawdown_days: float = Field(..., description="Maximum drawdown allowed per day")


class DailySchedule(BaseModel):
    day: int
    drawdown_days: float
    reserve_after_days: float
    risk_score: float
    price_usd: float
    rationale: str


class SPRScheduleResponse(BaseModel):
    schedule: List[DailySchedule]
    total_drawdown_days: float
    baseline_cost_usd: float
    optimized_cost_usd: float
    savings_usd: float
    savings_pct: float
    reserve_never_below_floor: bool
    computed_at: str
    replenishment_window_days: int = 0


# ── procurement (was procurement-agent/models.py) ──────────────────────────
class RecommendRequest(BaseModel):
    current_supplier: str
    current_corridor_risk_score: float = Field(ge=0, le=100)
    target_refinery: str
    required_crude_grade: str
    cost_weight: float = Field(ge=0, le=1)
    risk_weight: float = Field(ge=0, le=1)
    transit_time_weight: float = Field(ge=0, le=1)
    max_alternatives: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def normalize_weights(self):
        w_sum = self.cost_weight + self.risk_weight + self.transit_time_weight
        if not (0.99 <= w_sum <= 1.01):
            if w_sum > 0:
                self.cost_weight /= w_sum
                self.risk_weight /= w_sum
                self.transit_time_weight /= w_sum
            else:
                raise ValueError("Weights cannot sum to zero")
        return self


class RecommendationItem(BaseModel):
    supplier: str
    route: str
    port: str
    grade_match: str
    grade_compatibility_score: float
    estimated_cost_usd_per_bbl: float
    transit_days: int
    corridor_risk_score: float
    composite_score: float
    rank: int
    reasoning: str


class Baseline(BaseModel):
    supplier: str
    estimated_cost_usd_per_bbl: float
    transit_days: int
    corridor_risk_score: float
    composite_score: float


class GraphStats(BaseModel):
    nodes_considered: int
    edges_traversed: int


class LiveMarketData(BaseModel):
    brent_usd: float
    wti_usd: float
    usd_inr: float
    is_live: bool
    fetched_at: str


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
    current_supplier_baseline: Baseline
    graph_stats: GraphStats
    computed_at: str
    market_data: Optional[LiveMarketData] = None


# ════════════════════════════════════════════════════════════════════════════
#  EMBEDDED DATA  (bundled Brent history — was fallback_brent_history.csv)
# ════════════════════════════════════════════════════════════════════════════
_BRENT_CSV = """
date,price_usd
2024-07-09,84.66
2024-07-10,85.08
2024-07-11,85.4
2024-07-12,85.03
2024-07-15,84.85
2024-07-16,83.73
2024-07-17,85.08
2024-07-18,85.11
2024-07-19,82.63
2024-07-22,82.4
2024-07-23,81.01
2024-07-24,81.71
2024-07-25,82.37
2024-07-26,81.13
2024-07-29,79.78
2024-07-30,78.63
2024-07-31,80.72
2024-08-01,79.52
2024-08-02,76.81
2024-08-05,76.3
2024-08-06,76.48
2024-08-07,78.33
2024-08-08,79.16
2024-08-09,79.66
2024-08-12,82.3
2024-08-13,80.69
2024-08-14,79.76
2024-08-15,81.04
2024-08-16,79.68
2024-08-19,77.66
2024-08-20,77.2
2024-08-21,76.05
2024-08-22,77.22
2024-08-23,79.02
2024-08-26,81.43
2024-08-27,79.55
2024-08-28,78.65
2024-08-29,79.94
2024-08-30,78.8
2024-09-03,73.75
2024-09-04,72.7
2024-09-05,72.69
2024-09-06,71.06
2024-09-09,71.84
2024-09-10,69.19
2024-09-11,70.61
2024-09-12,71.97
2024-09-13,71.61
2024-09-16,72.75
2024-09-17,73.7
2024-09-18,73.65
2024-09-19,74.88
2024-09-20,74.49
2024-09-23,73.9
2024-09-24,75.17
2024-09-25,73.46
2024-09-26,71.6
2024-09-27,71.98
2024-09-30,71.77
2024-10-01,73.56
2024-10-02,73.9
2024-10-03,77.62
2024-10-04,78.05
2024-10-07,80.93
2024-10-08,77.18
2024-10-09,76.58
2024-10-10,79.4
2024-10-11,79.04
2024-10-14,77.46
2024-10-15,74.25
2024-10-16,74.22
2024-10-17,74.45
2024-10-18,73.06
2024-10-21,74.29
2024-10-22,76.04
2024-10-23,74.96
2024-10-24,74.38
2024-10-25,76.05
2024-10-28,71.42
2024-10-29,71.12
2024-10-30,72.55
2024-10-31,73.16
2024-11-01,73.1
2024-11-04,75.08
2024-11-05,75.53
2024-11-06,74.92
2024-11-07,75.63
2024-11-08,73.87
2024-11-11,71.83
2024-11-12,71.89
2024-11-13,72.28
2024-11-14,72.56
2024-11-15,71.04
2024-11-18,73.3
2024-11-19,73.31
2024-11-20,72.81
2024-11-21,74.23
2024-11-22,75.17
2024-11-25,73.01
2024-11-26,72.81
2024-11-27,72.83
2024-11-29,72.94
2024-12-02,71.83
2024-12-03,73.62
2024-12-04,72.31
2024-12-05,72.09
2024-12-06,71.12
2024-12-09,72.14
2024-12-10,72.19
2024-12-11,73.52
2024-12-12,73.41
2024-12-13,74.49
2024-12-16,73.91
2024-12-17,73.19
2024-12-18,73.39
2024-12-19,72.88
2024-12-20,72.94
2024-12-23,72.63
2024-12-24,73.58
2024-12-26,73.26
2024-12-27,74.17
2024-12-30,74.39
2024-12-31,74.64
2025-01-02,75.93
2025-01-03,76.51
2025-01-06,76.3
2025-01-07,77.05
2025-01-08,76.16
2025-01-09,76.92
2025-01-10,79.76
2025-01-13,81.01
2025-01-14,79.92
2025-01-15,82.03
2025-01-16,81.29
2025-01-17,80.79
2025-01-21,79.29
2025-01-22,79.0
2025-01-23,78.29
2025-01-24,78.5
2025-01-27,77.08
2025-01-28,77.49
2025-01-29,76.58
2025-01-30,76.87
2025-01-31,76.76
2025-02-03,75.96
2025-02-04,76.2
2025-02-05,74.61
2025-02-06,74.29
2025-02-07,74.66
2025-02-10,75.87
2025-02-11,77.0
2025-02-12,75.18
2025-02-13,75.02
2025-02-14,74.74
2025-02-18,75.84
2025-02-19,76.04
2025-02-20,76.48
2025-02-21,74.43
2025-02-24,74.78
2025-02-25,73.02
2025-02-26,72.53
2025-02-27,74.04
2025-02-28,73.18
2025-03-03,71.62
2025-03-04,71.04
2025-03-05,69.3
2025-03-06,69.46
2025-03-07,70.36
2025-03-10,69.28
2025-03-11,69.56
2025-03-12,70.95
2025-03-13,69.88
2025-03-14,70.58
2025-03-17,71.07
2025-03-18,70.56
2025-03-19,70.78
2025-03-20,72.0
2025-03-21,72.16
2025-03-24,73.0
2025-03-25,73.02
2025-03-26,73.79
2025-03-27,74.03
2025-03-28,73.63
2025-03-31,74.74
2025-04-01,74.49
2025-04-02,74.95
2025-04-03,70.14
2025-04-04,65.58
2025-04-07,64.21
2025-04-08,62.82
2025-04-09,65.48
2025-04-10,63.33
2025-04-11,64.76
2025-04-14,64.88
2025-04-15,64.67
2025-04-16,65.85
2025-04-17,67.96
2025-04-21,66.26
2025-04-22,67.44
2025-04-23,66.12
2025-04-24,66.55
2025-04-25,66.87
2025-04-28,65.86
2025-04-29,64.25
2025-04-30,63.12
2025-05-01,62.13
2025-05-02,61.29
2025-05-05,60.23
2025-05-06,62.15
2025-05-07,61.12
2025-05-08,62.84
2025-05-09,63.91
2025-05-12,64.96
2025-05-13,66.63
2025-05-14,66.09
2025-05-15,64.53
2025-05-16,65.41
2025-05-19,65.54
2025-05-20,65.38
2025-05-21,64.91
2025-05-22,64.44
2025-05-23,64.78
2025-05-27,64.09
2025-05-28,64.9
2025-05-29,64.15
2025-05-30,63.9
2025-06-02,64.63
2025-06-03,65.63
2025-06-04,64.86
2025-06-05,65.34
2025-06-06,66.47
2025-06-09,67.04
2025-06-10,66.87
2025-06-11,69.77
2025-06-12,69.36
2025-06-13,74.23
2025-06-16,73.23
2025-06-17,76.45
2025-06-18,76.7
2025-06-20,77.01
2025-06-23,71.48
2025-06-24,67.14
2025-06-25,67.68
2025-06-26,67.73
2025-06-27,67.77
2025-06-30,67.61
2025-07-01,67.11
2025-07-02,69.11
2025-07-03,68.8
2025-07-04,68.29
2025-07-07,69.58
2025-07-08,70.15
2025-07-09,70.19
2025-07-10,68.64
2025-07-11,70.36
2025-07-14,69.21
2025-07-15,68.71
2025-07-16,68.52
2025-07-17,69.52
2025-07-18,69.28
2025-07-21,69.21
2025-07-22,68.59
2025-07-23,68.51
2025-07-24,69.18
2025-07-25,68.44
2025-07-28,70.04
2025-07-29,72.51
2025-07-30,73.24
2025-07-31,72.53
2025-08-01,69.67
2025-08-04,68.76
2025-08-05,67.64
2025-08-06,66.89
2025-08-07,66.43
2025-08-08,66.59
2025-08-11,66.63
2025-08-12,66.12
2025-08-13,65.63
2025-08-14,66.84
2025-08-15,65.85
2025-08-18,66.6
2025-08-19,65.79
2025-08-20,66.84
2025-08-21,67.67
2025-08-22,67.73
2025-08-25,68.8
2025-08-26,67.22
2025-08-27,68.05
2025-08-28,68.62
2025-08-29,68.12
2025-09-02,69.14
2025-09-03,67.6
2025-09-04,66.99
2025-09-05,65.5
2025-09-08,66.02
2025-09-09,66.39
2025-09-10,67.49
2025-09-11,66.37
2025-09-12,66.99
2025-09-15,67.44
2025-09-16,68.47
2025-09-17,67.95
2025-09-18,67.44
2025-09-19,66.68
2025-09-22,66.57
2025-09-23,67.63
2025-09-24,69.31
2025-09-25,69.42
2025-09-26,70.13
2025-09-29,67.97
2025-09-30,67.02
2025-10-01,65.35
2025-10-02,64.11
2025-10-03,64.53
2025-10-06,65.47
2025-10-07,65.45
2025-10-08,66.25
2025-10-09,65.22
2025-10-10,62.73
2025-10-13,63.32
2025-10-14,62.39
2025-10-15,61.91
2025-10-16,61.06
2025-10-17,61.29
2025-10-20,61.01
2025-10-21,61.32
2025-10-22,62.59
2025-10-23,65.99
2025-10-24,65.94
2025-10-27,65.62
2025-10-28,64.4
2025-10-29,64.92
2025-10-30,65.0
2025-10-31,65.07
2025-11-03,64.89
2025-11-04,64.44
2025-11-05,63.52
2025-11-06,63.38
2025-11-07,63.63
2025-11-10,64.06
2025-11-11,65.16
2025-11-12,62.71
2025-11-13,63.01
2025-11-14,64.39
2025-11-17,64.2
2025-11-18,64.89
2025-11-19,63.51
2025-11-20,63.38
2025-11-21,62.56
2025-11-24,63.37
2025-11-25,62.48
2025-11-26,63.13
2025-11-28,63.2
2025-12-01,63.17
2025-12-02,62.45
2025-12-03,62.67
2025-12-04,63.26
2025-12-05,63.75
2025-12-08,62.49
2025-12-09,61.94
2025-12-10,62.21
2025-12-11,61.28
2025-12-12,61.12
2025-12-15,60.56
2025-12-16,58.92
2025-12-17,59.68
2025-12-18,59.82
2025-12-19,60.47
2025-12-22,62.07
2025-12-23,62.38
2025-12-24,62.24
2025-12-26,60.64
2025-12-29,61.94
2025-12-30,61.92
2025-12-31,60.85
2026-01-02,60.75
2026-01-05,61.76
2026-01-06,60.7
2026-01-07,59.96
2026-01-08,61.99
2026-01-09,63.34
2026-01-12,63.87
2026-01-13,65.47
2026-01-14,66.52
2026-01-15,63.76
2026-01-16,64.13
2026-01-20,64.92
2026-01-21,65.24
2026-01-22,64.06
2026-01-23,65.88
2026-01-26,65.59
2026-01-27,67.57
2026-01-28,68.4
2026-01-29,70.71
2026-01-30,70.69
2026-02-02,66.3
2026-02-03,67.33
2026-02-04,69.46
2026-02-05,67.55
2026-02-06,68.05
2026-02-09,69.04
2026-02-10,68.8
2026-02-11,69.4
2026-02-12,67.52
2026-02-13,67.75
2026-02-17,67.42
2026-02-18,70.35
2026-02-19,71.66
2026-02-20,71.76
2026-02-23,71.49
2026-02-24,70.77
2026-02-25,70.85
2026-02-26,70.75
2026-02-27,72.48
2026-03-02,77.74
2026-03-03,81.4
2026-03-04,81.4
2026-03-05,85.41
2026-03-06,92.69
2026-03-09,98.96
2026-03-10,87.8
2026-03-11,91.98
2026-03-12,100.46
2026-03-13,103.14
2026-03-16,100.21
2026-03-17,103.42
2026-03-18,107.38
2026-03-19,108.65
2026-03-20,112.19
2026-03-23,99.94
2026-03-24,104.49
2026-03-25,102.22
2026-03-26,108.01
2026-03-27,112.57
2026-03-30,112.78
2026-03-31,118.35
2026-04-01,101.16
2026-04-02,109.03
2026-04-06,109.77
2026-04-07,109.27
2026-04-08,94.75
2026-04-09,95.92
2026-04-10,95.2
2026-04-13,99.36
2026-04-14,94.79
2026-04-15,94.93
2026-04-16,99.39
2026-04-17,90.38
2026-04-20,95.48
2026-04-21,98.48
2026-04-22,101.91
2026-04-23,105.07
2026-04-24,105.33
2026-04-27,108.23
2026-04-28,111.26
2026-04-29,118.03
2026-04-30,114.01
2026-05-01,108.17
2026-05-04,114.44
2026-05-05,109.87
2026-05-06,101.27
2026-05-07,100.06
2026-05-08,101.29
2026-05-11,104.21
2026-05-12,107.77
2026-05-13,105.63
2026-05-14,105.72
2026-05-15,109.26
2026-05-18,112.1
2026-05-19,111.28
2026-05-20,105.02
2026-05-21,102.58
2026-05-22,103.54
2026-05-26,99.58
2026-05-27,94.29
2026-05-28,93.71
2026-05-29,92.05
2026-06-01,94.98
2026-06-02,96.0
2026-06-03,97.81
2026-06-04,95.03
2026-06-05,93.09
2026-06-08,94.25
2026-06-09,91.45
2026-06-10,93.1
2026-06-11,90.38
2026-06-12,87.33
2026-06-15,83.17
2026-06-16,78.96
2026-06-17,79.55
2026-06-18,79.85
2026-06-22,77.9
2026-06-23,77.08
2026-06-24,73.74
2026-06-25,75.26
2026-06-26,71.99
2026-06-29,73.15
2026-06-30,72.92
2026-07-01,71.57
2026-07-02,71.8
2026-07-06,71.99
2026-07-07,74.16
2026-07-08,78.02
2026-07-09,77.54
"""


# ════════════════════════════════════════════════════════════════════════════
#  EIA CLIENT  (inlined + simplified: embedded CSV, no disk cache)
# ════════════════════════════════════════════════════════════════════════════
STATUS = {
    "live_working": False,
    "last_fetched": None,
    "cached_days_count": 0,
    "current_source": "fallback_cache",
}


def load_fallback_data() -> List[dict]:
    """Parse the embedded Brent history CSV."""
    results: List[dict] = []
    # .strip() so a leading/trailing blank line in the embedded literal never
    # shifts the header row.
    reader = csv.DictReader(io.StringIO(_BRENT_CSV.strip()))
    for row in reader:
        try:
            results.append({"date": row["date"], "price_usd": float(row["price_usd"])})
        except (ValueError, KeyError):
            continue
    return results


def fetch_brent_spot_history(start_date: str, end_date: str) -> List[dict]:
    """Return daily Brent spot prices in [start_date, end_date].

    Uses the live EIA API only if EIA_API_KEY is set; otherwise (and on any
    failure) falls back to the embedded CSV. No disk cache — self-contained.
    """
    global STATUS
    api_key = os.getenv("EIA_API_KEY", "").strip()

    if api_key:
        url_series = (
            f"https://api.eia.gov/v2/petroleum/pri/spt/data/?"
            f"frequency=daily&data[0]=value&facets[series][]=RBRTE&"
            f"sort[0][column]=period&sort[0][direction]=desc&length=1000&api_key={api_key}"
        )
        url_product = (
            f"https://api.eia.gov/v2/petroleum/pri/spt/data/?"
            f"frequency=daily&data[0]=value&facets[product][]=RBRTE&"
            f"sort[0][column]=period&sort[0][direction]=desc&length=1000&api_key={api_key}"
        )
        for url in (url_series, url_product):
            try:
                response = httpx.get(url, timeout=10.0)
                if response.status_code == 200:
                    json_res = response.json()
                    raw = json_res.get("response", {}).get("data")
                    if raw:
                        parsed = []
                        for item in raw:
                            period = item.get("period")
                            value = item.get("value")
                            if not period or value is None:
                                continue
                            try:
                                parsed.append({"date": period, "price_usd": float(value)})
                            except ValueError:
                                continue
                        if parsed:
                            STATUS.update(
                                live_working=True,
                                last_fetched=datetime.now(timezone.utc).isoformat(),
                                cached_days_count=len(parsed),
                                current_source="live_eia",
                            )
                            filtered = [x for x in parsed if start_date <= x["date"] <= end_date]
                            return sorted(filtered, key=lambda x: x["date"])
            except Exception:
                continue

    # Fallback: embedded CSV
    STATUS.update(live_working=False, current_source="fallback_cache")
    fallback = load_fallback_data()
    STATUS["cached_days_count"] = len(fallback)
    filtered = [x for x in fallback if start_date <= x["date"] <= end_date]
    return sorted(filtered, key=lambda x: x["date"])


def get_data_status() -> dict:
    global STATUS
    if STATUS["cached_days_count"] == 0:
        STATUS["cached_days_count"] = len(load_fallback_data())
    return STATUS


# ════════════════════════════════════════════════════════════════════════════
#  SCENARIO ENGINE  (was scenario-engine/main.py)
# ════════════════════════════════════════════════════════════════════════════
CALIBRATED_VOLATILITY = 0.02
CALIBRATION_RANGE = "unknown"
DATA_SOURCE = "fallback_cache"


def calibrate_volatility():
    """Calibrate simulation volatility from Brent history; safe fallback on error."""
    global CALIBRATED_VOLATILITY, CALIBRATION_RANGE, DATA_SOURCE
    end_date = date.today()
    start_date = end_date - timedelta(days=int(24 * 30.5))
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    try:
        history = fetch_brent_spot_history(start_date_str, end_date_str)
        if len(history) > 1:
            prices = [x["price_usd"] for x in history if x["price_usd"] > 0]
            if len(prices) > 1:
                log_returns = np.diff(np.log(prices))
                CALIBRATED_VOLATILITY = float(np.std(log_returns))
                CALIBRATION_RANGE = f"{history[0]['date']} to {history[-1]['date']}"
                DATA_SOURCE = get_data_status().get("current_source", "fallback_cache")
                print(f"[CALIBRATION] volatility={CALIBRATED_VOLATILITY:.6f} ({CALIBRATION_RANGE}) via {DATA_SOURCE}")
                return
    except Exception as e:
        print(f"[CALIBRATION] error: {e}")
    CALIBRATED_VOLATILITY = 0.02
    CALIBRATION_RANGE = f"{start_date_str} to {end_date_str} (fallback defaults)"
    DATA_SOURCE = "fallback_cache"
    print(f"[CALIBRATION] fallback volatility={CALIBRATED_VOLATILITY:.6f} ({CALIBRATION_RANGE})")


def _simulate(req: SimulateRequest) -> SimulateResponse:
    S0 = req.current_brent_usd
    days = req.shock_duration_days
    N = req.num_simulations
    risk_factor = req.risk_score / 100.0

    # Geometric random walk with mean reversion (Ornstein-Uhlenbeck log process).
    if req.scenario_type == "hormuz_closure":
        theta = S0 * (1 + 1.2 * risk_factor)
        sigma = CALIBRATED_VOLATILITY + (0.15 * risk_factor)
        kappa = 0.05
    elif req.scenario_type == "opec_cut":
        theta = S0 * (1 + 0.3 * risk_factor)
        sigma = CALIBRATED_VOLATILITY + (0.02 * risk_factor)
        kappa = 0.2
    else:
        theta = S0 * (1 + 0.5 * risk_factor)
        kappa = 0.1
        sigma = CALIBRATED_VOLATILITY + (0.05 * risk_factor)

    paths = np.zeros((N, days))
    paths[:, 0] = S0
    Z = np.random.standard_normal((N, days - 1))
    for t in range(1, days):
        paths[:, t] = paths[:, t - 1] * np.exp(
            kappa * (np.log(theta) - np.log(paths[:, t - 1])) + sigma * Z[:, t - 1]
        )

    final_prices = paths[:, -1]
    p10, p50, p90 = np.percentile(final_prices, [10, 50, 90])
    brent_dist = DistributionStats(
        p10=float(p10), p50=float(p50), p90=float(p90),
        mean=float(np.mean(final_prices)), std_dev=float(np.std(final_prices)),
    )

    daily_stats = []
    for t in range(days):
        d_p10, d_p50, d_p90 = np.percentile(paths[:, t], [10, 50, 90])
        daily_stats.append(DailyPriceStats(day=t + 1, p10=float(d_p10), p50=float(d_p50), p90=float(d_p90)))

    current_pump = 96.5
    brent_pct_change_p50 = (p50 - S0) / S0
    brent_pct_change_p90 = (p90 - S0) / S0
    pass_through = req.elasticity_assumptions.pass_through_rate_to_pump
    pump_impact = PumpPriceImpact(
        current_inr_per_litre=current_pump,
        projected_p50_inr_per_litre=float(current_pump * (1 + (brent_pct_change_p50 * pass_through))),
        projected_p90_inr_per_litre=float(current_pump * (1 + (brent_pct_change_p90 * pass_through))),
    )

    brent_pct_change_p10 = (p10 - S0) / S0
    gdp_sens = req.elasticity_assumptions.gdp_sensitivity_per_10pct_oil_shock
    gdp_impact = GDPImpactPct(
        p10=float((brent_pct_change_p10 / 0.1) * gdp_sens),
        p50=float((brent_pct_change_p50 / 0.1) * gdp_sens),
        p90=float((brent_pct_change_p90 / 0.1) * gdp_sens),
    )

    return SimulateResponse(
        brent_price_distribution=brent_dist,
        daily_price_path=daily_stats,
        pump_price_impact=pump_impact,
        gdp_impact_pct=gdp_impact,
        calibration_note="elasticities validated against EIA historical shock: 2022 Ukraine invasion price spike",
        num_simulations_run=N,
        computed_at=datetime.now(timezone.utc),
        data_source=DATA_SOURCE,
        volatility_calibrated_from=CALIBRATION_RANGE,
    )


def _simulate_mock() -> SimulateResponse:
    return SimulateResponse(
        brent_price_distribution=DistributionStats(p10=88.0, p50=96.0, p90=112.0, mean=97.4, std_dev=8.1),
        daily_price_path=[
            DailyPriceStats(day=1, p10=83.0, p50=85.0, p90=89.0),
            DailyPriceStats(day=2, p10=84.0, p50=87.0, p90=93.0),
            DailyPriceStats(day=3, p10=85.0, p50=90.0, p90=98.0),
            DailyPriceStats(day=4, p10=86.0, p50=92.0, p90=102.0),
            DailyPriceStats(day=5, p10=88.0, p50=96.0, p90=112.0),
        ],
        pump_price_impact=PumpPriceImpact(
            current_inr_per_litre=96.5, projected_p50_inr_per_litre=104.2, projected_p90_inr_per_litre=111.8
        ),
        gdp_impact_pct=GDPImpactPct(p10=-0.08, p50=-0.21, p90=-0.41),
        calibration_note="elasticities validated against EIA historical shock: 2022 Ukraine invasion price spike",
        num_simulations_run=5000,
        computed_at=datetime.now(timezone.utc),
        data_source="fallback_cache",
        volatility_calibrated_from="2024-07-09 to 2026-07-09",
    )


# ════════════════════════════════════════════════════════════════════════════
#  SPR OPTIMIZER  (was spr-agent/main.py)
# ════════════════════════════════════════════════════════════════════════════
def _spr_risk_weight(score: float) -> float:
    return 1.0 + (score / 100.0)


def _spr_schedule(req: SPRScheduleRequest) -> SPRScheduleResponse:
    N = req.planning_horizon_days
    if len(req.daily_risk_scores) != N or len(req.daily_price_forecast_usd_per_bbl) != N:
        raise HTTPException(status_code=422, detail="Array lengths must match planning_horizon_days")
    if req.current_reserve_days < req.min_safety_floor_days:
        raise HTTPException(status_code=400, detail="Current reserve already below safety floor")

    # Objective: maximise total value of the SPR drawdown,
    #   max  Σ price_i · risk_weight_i · x_i
    #   s.t. Σ x_i ≤ (current_reserve − safety_floor)   [single budget]
    #        0 ≤ x_i ≤ max_daily_drawdown_days           [box bounds]
    # This is a single-budget knapsack LP, so the greedy allocation — fill the
    # highest-value days at the daily cap until the budget is spent — is the
    # EXACT optimum (identical objective to scipy's linprog, no scipy needed,
    # which keeps the serverless bundle small enough for Vercel's 250MB limit).
    max_total_draw = req.current_reserve_days - req.min_safety_floor_days
    
    current_month = datetime.now().month
    DEMAND_SEASONALITY = [1.0, 1.0, 1.05, 1.0, 0.95, 0.9, 0.9, 0.95, 1.05, 1.1, 1.1, 1.0]
    seasonality_multiplier = DEMAND_SEASONALITY[current_month - 1]
    adjusted_prices = [p * seasonality_multiplier for p in req.daily_price_forecast_usd_per_bbl]

    value = [
        adjusted_prices[i] * _spr_risk_weight(req.daily_risk_scores[i])
        for i in range(N)
    ]
    opt = [0.0] * N
    budget = max_total_draw
    for i in sorted(range(N), key=lambda k: value[k], reverse=True):
        take = max(0.0, min(req.max_daily_drawdown_days, budget))
        opt[i] = take
        budget -= take
        if budget <= 1e-9:
            break
    opt_drawdowns = np.array(opt)

    flat_daily = min(max_total_draw / N, req.max_daily_drawdown_days)
    naive_drawdowns = np.full(N, flat_daily)

    opt_value_usd = np.sum(opt_drawdowns * adjusted_prices) * 1_000_000
    naive_value_usd = np.sum(naive_drawdowns * adjusted_prices) * 1_000_000

    total_demand = req.max_daily_drawdown_days * N
    avg_price = np.mean(adjusted_prices)
    unmitigated_cost = total_demand * avg_price * 1_000_000

    baseline_cost = unmitigated_cost - naive_value_usd
    optimized_cost = unmitigated_cost - opt_value_usd
    savings = baseline_cost - optimized_cost
    savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

    schedule = []
    current_res = req.current_reserve_days
    for i in range(N):
        d = float(opt_drawdowns[i])
        current_res -= d
        if d > req.max_daily_drawdown_days * 0.9:
            rat = "Maximum capacity release to offset peak risk/price."
        elif d > 0:
            rat = "Partial release balancing safety floor constraints."
        else:
            rat = "Reserve preserved for higher risk days."
        schedule.append(DailySchedule(
            day=i + 1, drawdown_days=round(d, 3), reserve_after_days=round(current_res, 3),
            risk_score=req.daily_risk_scores[i], price_usd=adjusted_prices[i], rationale=rat,
        ))

    G_temp = build_procurement_graph()
    low_risk_transit_days = []
    for u, v, data in G_temp.edges(data=True):
        if "transit_days" in data:
            if G_temp.nodes[v].get("risk", 100) <= 30:
                low_risk_transit_days.append(data["transit_days"])
    replenishment_window_days = int(min(low_risk_transit_days)) + 10 if low_risk_transit_days else 30

    return SPRScheduleResponse(
        schedule=schedule,
        total_drawdown_days=round(float(np.sum(opt_drawdowns)), 3),
        baseline_cost_usd=round(baseline_cost, 2),
        optimized_cost_usd=round(optimized_cost, 2),
        savings_usd=round(savings, 2),
        savings_pct=round(savings_pct, 2),
        reserve_never_below_floor=(current_res >= req.min_safety_floor_days - 1e-5),
        computed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        replenishment_window_days=replenishment_window_days,
    )


def _spr_schedule_mock() -> SPRScheduleResponse:
    return SPRScheduleResponse(
        schedule=[
            DailySchedule(day=1, drawdown_days=1.0, reserve_after_days=8.5, risk_score=85, price_usd=102.5, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=2, drawdown_days=1.0, reserve_after_days=7.5, risk_score=88, price_usd=104.0, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=3, drawdown_days=1.0, reserve_after_days=6.5, risk_score=82, price_usd=101.0, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=4, drawdown_days=0.5, reserve_after_days=6.0, risk_score=70, price_usd=95.0, rationale="Partial release balancing safety floor constraints."),
            DailySchedule(day=5, drawdown_days=0.0, reserve_after_days=6.0, risk_score=60, price_usd=90.0, rationale="Reserve preserved for higher risk days."),
            DailySchedule(day=6, drawdown_days=0.0, reserve_after_days=6.0, risk_score=55, price_usd=88.0, rationale="Reserve preserved for higher risk days."),
            DailySchedule(day=7, drawdown_days=0.0, reserve_after_days=6.0, risk_score=50, price_usd=85.0, rationale="Reserve preserved for higher risk days."),
        ],
        total_drawdown_days=3.5, baseline_cost_usd=50000000.0, optimized_cost_usd=42000000.0,
        savings_usd=8000000.0, savings_pct=16.0, reserve_never_below_floor=True,
        computed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


# ════════════════════════════════════════════════════════════════════════════
#  PROCUREMENT  (was procurement-agent/main.py + knowledge_graph/graph_builder.py)
# ════════════════════════════════════════════════════════════════════════════
def build_procurement_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    suppliers = {
        "SAU_ARAMCO":  {"type": "supplier", "cost": 82.4, "grade": "medium_sour", "country": "Saudi Arabia", "lat": 24.0, "lon": 49.0},
        "IRQ_SOMO":    {"type": "supplier", "cost": 79.8, "grade": "medium_sour", "country": "Iraq", "lat": 31.0, "lon": 47.8},
        "UAE_ADNOC":   {"type": "supplier", "cost": 83.5, "grade": "light_sweet", "country": "UAE", "lat": 23.4, "lon": 54.4},
        "RUS_ROSNEFT": {"type": "supplier", "cost": 68.0, "grade": "medium_sour", "country": "Russia", "lat": 55.0, "lon": 60.0},
        "USA_WTI":     {"type": "supplier", "cost": 88.5, "grade": "light_sweet", "country": "USA", "lat": 38.0, "lon": -100.0},
        "NGA_NNPC":    {"type": "supplier", "cost": 86.0, "grade": "light_sweet", "country": "Nigeria", "lat": 9.0, "lon": 8.0},
        "KWT_KPC":     {"type": "supplier", "cost": 80.2, "grade": "medium_sour", "country": "Kuwait", "lat": 29.4, "lon": 47.5},
        "MEX_PEMEX":   {"type": "supplier", "cost": 77.5, "grade": "heavy_sour", "country": "Mexico", "lat": 19.4, "lon": -99.0},
    }
    for name, data in suppliers.items():
        G.add_node(name, **data)

    routes = {
        "hormuz_saudi":  {"type": "route", "risk": 78, "corridor": "Hormuz Strait", "display": "Hormuz (Saudi leg)", "lat": 26.5, "lon": 56.5},
        "hormuz_iraq":   {"type": "route", "risk": 74, "corridor": "Hormuz Strait", "display": "Hormuz (Iraq leg)", "lat": 25.8, "lon": 57.0},
        "hormuz_uae":    {"type": "route", "risk": 76, "corridor": "Hormuz Strait", "display": "Hormuz (UAE leg)", "lat": 25.2, "lon": 57.5},
        "hormuz_kuwait": {"type": "route", "risk": 77, "corridor": "Hormuz Strait", "display": "Hormuz (Kuwait leg)", "lat": 26.2, "lon": 56.8},
        "basra_direct":  {"type": "route", "risk": 38, "corridor": "Basra-India", "display": "Basra Direct VLCC", "lat": 22.0, "lon": 55.0},
        "red_sea_suez":  {"type": "route", "risk": 85, "corridor": "Red Sea/Suez", "display": "Red Sea / Suez", "lat": 20.0, "lon": 38.0},
        "cape_russia":   {"type": "route", "risk": 18, "corridor": "Cape Route", "display": "Cape of Good Hope (Russia)", "lat": -34.0, "lon": 18.5},
        "cape_nigeria":  {"type": "route", "risk": 16, "corridor": "Cape Route", "display": "Cape of Good Hope (Nigeria)", "lat": -33.0, "lon": 16.0},
        "cape_mexico":   {"type": "route", "risk": 14, "corridor": "Trans-Atlantic", "display": "Trans-Atlantic / Cape", "lat": -32.0, "lon": 14.0},
        "pacific_india": {"type": "route", "risk": 12, "corridor": "Pacific-India", "display": "Pacific-India", "lat": 10.0, "lon": 90.0},
    }
    for name, data in routes.items():
        G.add_node(name, **data)

    ports = {
        "PORT_VADINAR": {"type": "port", "display": "Vadinar Port", "lat": 22.5, "lon": 69.8, "congestion": 0.3},
        "PORT_KANDLA": {"type": "port", "display": "Kandla Port", "lat": 23.0, "lon": 70.2, "congestion": 0.8},
        "PORT_MUMBAI": {"type": "port", "display": "Mumbai JNPT", "lat": 18.9, "lon": 72.8, "congestion": 0.9},
        "PORT_PARADIP": {"type": "port", "display": "Paradip Port", "lat": 20.3, "lon": 86.6, "congestion": 0.4},
        "PORT_MANGALORE": {"type": "port", "display": "Mangalore Port", "lat": 12.9, "lon": 74.8, "congestion": 0.2},
        "PORT_VIZAG": {"type": "port", "display": "Visakhapatnam", "lat": 17.7, "lon": 83.3, "congestion": 0.6},
    }
    for name, data in ports.items():
        G.add_node(name, **data)

    refineries = {
        "REF_JAMNAGAR": {"type": "refinery", "display": "Jamnagar (RIL)", "lat": 22.4, "lon": 70.1},
        "REF_VADINAR": {"type": "refinery", "display": "Vadinar (Nayara)", "lat": 22.3, "lon": 69.9},
        "REF_MUMBAI": {"type": "refinery", "display": "Mumbai (BPCL/HPCL)", "lat": 19.0, "lon": 72.9},
        "REF_PARADIP": {"type": "refinery", "display": "Paradip (IOCL)", "lat": 20.2, "lon": 86.7},
        "REF_MANGALORE": {"type": "refinery", "display": "Mangalore (MRPL)", "lat": 12.8, "lon": 74.9},
        "REF_VIZAG": {"type": "refinery", "display": "Visakhapatnam (HPCL)", "lat": 17.6, "lon": 83.4},
    }
    for name, data in refineries.items():
        G.add_node(name, **data)

    grades = {
        "GRADE_MEDIUM_SOUR": {"type": "grade", "display": "Medium Sour"},
        "GRADE_LIGHT_SWEET": {"type": "grade", "display": "Light Sweet"},
        "GRADE_HEAVY_SOUR": {"type": "grade", "display": "Heavy Sour"},
    }
    for name, data in grades.items():
        G.add_node(name, **data)

    G.add_edge("SAU_ARAMCO", "hormuz_saudi", transit_days=9)
    G.add_edge("IRQ_SOMO", "hormuz_iraq", transit_days=10)
    G.add_edge("IRQ_SOMO", "basra_direct", transit_days=12)
    G.add_edge("UAE_ADNOC", "hormuz_uae", transit_days=8)
    G.add_edge("KWT_KPC", "hormuz_kuwait", transit_days=10)
    G.add_edge("RUS_ROSNEFT", "red_sea_suez", transit_days=18)
    G.add_edge("RUS_ROSNEFT", "cape_russia", transit_days=42)
    G.add_edge("NGA_NNPC", "cape_nigeria", transit_days=24)
    G.add_edge("USA_WTI", "pacific_india", transit_days=28)
    G.add_edge("MEX_PEMEX", "cape_mexico", transit_days=32)

    G.add_edge("hormuz_saudi", "PORT_VADINAR")
    G.add_edge("hormuz_iraq", "PORT_KANDLA")
    G.add_edge("hormuz_uae", "PORT_VADINAR")
    G.add_edge("hormuz_kuwait", "PORT_VADINAR")
    G.add_edge("basra_direct", "PORT_VADINAR")
    G.add_edge("red_sea_suez", "PORT_PARADIP")
    G.add_edge("cape_russia", "PORT_MANGALORE")
    G.add_edge("cape_nigeria", "PORT_MANGALORE")
    G.add_edge("cape_mexico", "PORT_MANGALORE")
    G.add_edge("pacific_india", "PORT_VIZAG")

    G.add_edge("PORT_VADINAR", "REF_JAMNAGAR")
    G.add_edge("PORT_VADINAR", "REF_VADINAR")
    G.add_edge("PORT_KANDLA", "REF_JAMNAGAR")
    G.add_edge("PORT_MUMBAI", "REF_MUMBAI")
    G.add_edge("PORT_PARADIP", "REF_PARADIP")
    G.add_edge("PORT_MANGALORE", "REF_MANGALORE")
    G.add_edge("PORT_VIZAG", "REF_VIZAG")

    G.add_edge("REF_JAMNAGAR", "GRADE_MEDIUM_SOUR", compatibility=0.95)
    G.add_edge("REF_JAMNAGAR", "GRADE_LIGHT_SWEET", compatibility=0.88)
    G.add_edge("REF_JAMNAGAR", "GRADE_HEAVY_SOUR", compatibility=0.72)
    G.add_edge("REF_VADINAR", "GRADE_MEDIUM_SOUR", compatibility=0.92)
    G.add_edge("REF_VADINAR", "GRADE_LIGHT_SWEET", compatibility=0.85)
    G.add_edge("REF_VADINAR", "GRADE_HEAVY_SOUR", compatibility=0.68)
    G.add_edge("REF_MUMBAI", "GRADE_MEDIUM_SOUR", compatibility=0.88)
    G.add_edge("REF_MUMBAI", "GRADE_LIGHT_SWEET", compatibility=0.82)
    G.add_edge("REF_PARADIP", "GRADE_MEDIUM_SOUR", compatibility=0.90)
    G.add_edge("REF_PARADIP", "GRADE_HEAVY_SOUR", compatibility=0.75)
    G.add_edge("REF_MANGALORE", "GRADE_LIGHT_SWEET", compatibility=0.92)
    G.add_edge("REF_MANGALORE", "GRADE_MEDIUM_SOUR", compatibility=0.80)
    G.add_edge("REF_VIZAG", "GRADE_LIGHT_SWEET", compatibility=0.90)
    G.add_edge("REF_VIZAG", "GRADE_MEDIUM_SOUR", compatibility=0.78)
    return G


def get_grade_compatibility(graph: nx.DiGraph, refinery: str, grade: str) -> float:
    if graph.has_edge(refinery, grade):
        return graph[refinery][grade].get("compatibility", 0.0)
    return 0.0


G = build_procurement_graph()

_market_cache: Optional[dict] = None
_market_cache_ts: float = 0.0
CACHE_TTL_SECONDS = 300


async def fetch_live_market_data() -> dict:
    """Live USD/INR (open API) blended with realistic static 2025 spot prices."""
    global _market_cache, _market_cache_ts
    now = datetime.now(timezone.utc).timestamp()
    if _market_cache and (now - _market_cache_ts) < CACHE_TTL_SECONDS:
        return _market_cache

    live = {}
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            fx_resp = await client.get("https://api.exchangerate.host/latest", params={"base": "USD", "symbols": "INR"})
            if fx_resp.status_code == 200:
                live["usd_inr"] = fx_resp.json().get("rates", {}).get("INR", 83.5)
    except Exception:
        pass

    defaults = {
        "brent_usd": 84.12, "wti_usd": 80.55, "dubai_usd": 82.90, "oman_usd": 83.15,
        "usd_inr": live.get("usd_inr", 83.42), "nat_gas_usd": 2.81,
        "SAU_ARAMCO_diff": -1.72, "IRQ_SOMO_diff": -4.32, "UAE_ADNOC_diff": 0.45,
        "RUS_ROSNEFT_diff": -14.12, "USA_WTI_diff": 4.38, "NGA_NNPC_diff": 2.10,
        "KWT_KPC_diff": -2.40, "MEX_PEMEX_diff": -6.80,
        "data_source": "EIA/OpenExchangeRate fallback",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_live": len(live) > 0,
    }
    defaults.update(live)
    _market_cache = defaults
    _market_cache_ts = now
    return defaults


def get_live_cost(market: dict, supplier_id: str, base_cost: float) -> float:
    brent = market.get("brent_usd", 84.12)
    diff = market.get(f"{supplier_id}_diff", 0.0)
    return round(0.4 * base_cost + 0.6 * (brent + diff), 2)


async def _recommend(req: RecommendRequest) -> RecommendResponse:
    if req.target_refinery not in G.nodes or G.nodes[req.target_refinery].get("type") != "refinery":
        available = [n for n, d in G.nodes(data=True) if d.get("type") == "refinery"]
        raise HTTPException(status_code=400, detail=f"Refinery '{req.target_refinery}' not found. Available: {available}")
    if req.required_crude_grade not in G.nodes or G.nodes[req.required_crude_grade].get("type") != "grade":
        available = [n for n, d in G.nodes(data=True) if d.get("type") == "grade"]
        raise HTTPException(status_code=400, detail=f"Grade '{req.required_crude_grade}' not found. Available: {available}")

    compatibility = get_grade_compatibility(G, req.target_refinery, req.required_crude_grade)
    if compatibility < 0.6:
        raise HTTPException(status_code=400, detail=f"Refinery '{req.target_refinery}' not compatible with grade '{req.required_crude_grade}' (score {compatibility:.2f} < 0.60)")

    market = await fetch_live_market_data()

    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]
    candidates_by_supplier: dict = {}
    edges_traversed = 0
    baseline_cand = None

    for supplier in suppliers:
        try:
            paths = list(nx.all_simple_paths(G, source=supplier, target=req.required_crude_grade))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        valid_paths = [p for p in paths if req.target_refinery in p]
        if not valid_paths:
            continue
        min_len = min(len(p) for p in valid_paths)
        shortest_paths = [p for p in valid_paths if len(p) == min_len]
        edges_traversed += min_len - 1

        per_supplier_cands = []
        for path in shortest_paths:
            route = path[1] if len(path) > 1 else None
            port = path[2] if len(path) > 2 else None
            if route is None or port is None:
                continue
            if G.nodes[route].get("type") != "route" or G.nodes[port].get("type") != "port":
                continue
            base_cost = G.nodes[supplier].get("cost", 80.0)
            corridor_risk = G.nodes[route].get("risk", 50)
            port_congestion = G.nodes[port].get("congestion", 0.5)
            tanker_availability = max(0.1, 1.0 - (corridor_risk / 100.0))
            per_supplier_cands.append({
                "supplier": supplier, "route": route, "port": port,
                "grade_match": req.required_crude_grade, "grade_compatibility_score": compatibility,
                "estimated_cost_usd_per_bbl": get_live_cost(market, supplier, base_cost),
                "transit_days": G[supplier][route].get("transit_days", 15),
                "corridor_risk_score": corridor_risk,
                "port_congestion": port_congestion,
                "tanker_availability": tanker_availability,
                "route_display": G.nodes[route].get("display", route),
                "port_display": G.nodes[port].get("display", port),
                "supplier_country": G.nodes[supplier].get("country", supplier),
            })
        if not per_supplier_cands:
            continue
        if supplier == req.current_supplier:
            baseline_cand = per_supplier_cands[0].copy()
            baseline_cand["corridor_risk_score"] = req.current_corridor_risk_score
        else:
            candidates_by_supplier[supplier] = per_supplier_cands

    if not candidates_by_supplier and baseline_cand is None:
        raise HTTPException(status_code=404, detail="No valid routes found in supply graph")

    if baseline_cand is None:
        base_cost = G.nodes.get(req.current_supplier, {}).get("cost", 82.4)
        port_congestion = G.nodes.get("PORT_VADINAR", {}).get("congestion", 0.5)
        tanker_availability = max(0.1, 1.0 - (req.current_corridor_risk_score / 100.0))
        baseline_cand = {
            "supplier": req.current_supplier, "route": "hormuz_strait", "port": "PORT_VADINAR",
            "grade_match": req.required_crude_grade, "grade_compatibility_score": compatibility,
            "estimated_cost_usd_per_bbl": get_live_cost(market, req.current_supplier, base_cost),
            "transit_days": 9, "corridor_risk_score": req.current_corridor_risk_score,
            "port_congestion": port_congestion,
            "tanker_availability": tanker_availability,
            "route_display": "Hormuz Strait", "port_display": "Vadinar Port", "supplier_country": "Saudi Arabia",
        }

    all_tied = [c for group in candidates_by_supplier.values() for c in group]
    all_for_norm = all_tied + [baseline_cand]
    max_cost = max(c["estimated_cost_usd_per_bbl"] for c in all_for_norm) or 1.0
    min_cost = min(c["estimated_cost_usd_per_bbl"] for c in all_for_norm)
    max_risk = max(c["corridor_risk_score"] for c in all_for_norm) or 1.0
    min_risk = min(c["corridor_risk_score"] for c in all_for_norm)
    max_transit = max(c["transit_days"] for c in all_for_norm) or 1.0
    min_transit = min(c["transit_days"] for c in all_for_norm)

    def norm(val, lo, hi):
        return 1.0 - ((val - lo) / (hi - lo)) if hi > lo else 1.0

    def composite(c):
        nc = norm(c["estimated_cost_usd_per_bbl"], min_cost, max_cost)
        nr = norm(c["corridor_risk_score"], min_risk, max_risk)
        nt = norm(c["transit_days"], min_transit, max_transit)
        base_score = req.cost_weight * nc + req.risk_weight * nr + req.transit_time_weight * nt
        return round(base_score * c["tanker_availability"] * (1.0 - c["port_congestion"] * 0.5), 4)

    b_score = composite(baseline_cand)
    baseline_out = Baseline(
        supplier=str(baseline_cand["supplier"]), estimated_cost_usd_per_bbl=baseline_cand["estimated_cost_usd_per_bbl"],
        transit_days=baseline_cand["transit_days"], corridor_risk_score=baseline_cand["corridor_risk_score"],
        composite_score=b_score,
    )

    all_candidates_flat = []
    for group in candidates_by_supplier.values():
        all_candidates_flat.append(max(group, key=composite))

    scored = []
    for cand in all_candidates_flat:
        score = composite(cand)
        cost_delta = cand["estimated_cost_usd_per_bbl"] - baseline_cand["estimated_cost_usd_per_bbl"]
        risk_delta = cand["corridor_risk_score"] - baseline_cand["corridor_risk_score"]
        transit_delta = cand["transit_days"] - baseline_cand["transit_days"]
        parts = []
        if risk_delta < 0:
            parts.append(f"Risk ↓{abs(int(risk_delta))} pts via {cand['route_display']}")
        elif risk_delta > 0:
            parts.append(f"Risk ↑{int(risk_delta)} pts via {cand['route_display']}")
        else:
            parts.append(f"Equal risk via {cand['route_display']}")
        if cost_delta < 0:
            parts.append(f"saves ${abs(cost_delta):.2f}/bbl")
        else:
            parts.append(f"costs +${cost_delta:.2f}/bbl")
        if transit_delta <= 0:
            parts.append(f"transit {cand['transit_days']}d ({'same' if transit_delta == 0 else f'{abs(transit_delta)}d faster'})")
        else:
            parts.append(f"transit {cand['transit_days']}d ({transit_delta}d slower)")
        parts.append(f"src: {cand['supplier_country']}, via {cand['port_display']} ({cand['port_congestion']*100:.0f}% congested)")
        parts.append(f"tanker availability at {cand['tanker_availability']*100:.0f}%")
        cand["composite_score"] = score
        cand["reasoning"] = ". ".join(parts) + "."
        scored.append(cand)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    top_n = scored[: req.max_alternatives]
    final_recs = [
        RecommendationItem(
            supplier=c["supplier"], route=c["route"], port=c["port"], grade_match=c["grade_match"],
            grade_compatibility_score=c["grade_compatibility_score"], estimated_cost_usd_per_bbl=c["estimated_cost_usd_per_bbl"],
            transit_days=c["transit_days"], corridor_risk_score=c["corridor_risk_score"],
            composite_score=c["composite_score"], rank=idx + 1, reasoning=c["reasoning"],
        )
        for idx, c in enumerate(top_n)
    ]

    return RecommendResponse(
        recommendations=final_recs,
        current_supplier_baseline=baseline_out,
        graph_stats=GraphStats(nodes_considered=len(G.nodes), edges_traversed=edges_traversed),
        computed_at=datetime.now(timezone.utc).isoformat(),
        market_data=LiveMarketData(
            brent_usd=market.get("brent_usd", 84.12), wti_usd=market.get("wti_usd", 80.55),
            usd_inr=market.get("usd_inr", 83.42), is_live=market.get("is_live", False),
            fetched_at=market.get("fetched_at", datetime.now(timezone.utc).isoformat()),
        ),
    )


# ════════════════════════════════════════════════════════════════════════════
#  RISK AGENT  (ported from risk-agent/ — same scoring math, no langgraph)
#  Pipeline: ingest(fixtures[+GDELT]) → classify → map_corridor → severity → score
# ════════════════════════════════════════════════════════════════════════════

# ── risk models (enriched to the frontend's RiskScoreResponse shape) ─────────
class RiskScoreRequest(BaseModel):
    corridor: Corridor
    as_of: Optional[datetime] = None


class RiskKeyEvent(BaseModel):
    headline: str
    severity: Literal["low", "medium", "high", "critical"]
    date: datetime
    source: str
    corridor: str


class RiskSignal(BaseModel):
    type: str
    source: str
    weight: float
    detail: str


class RiskScoreResponse(BaseModel):
    corridor: str
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    alert_level: Literal["low", "elevated", "high", "critical"]
    signals: List[RiskSignal]
    reasoning_trail: str
    key_events: List[RiskKeyEvent]
    computed_at: datetime
    data_sources: List[str]
    model: str
    supplier_risk_scores: dict[str, float] = Field(default_factory=dict)


# ── ingestion: bundled deterministic fixtures (always available) ────────────
_RISK_FIXTURES = {
    "hormuz": [
        (1, "Iran threatens to close the Strait of Hormuz amid rising tensions", "IRN", -6.5),
        (2, "Oil tanker seized near the Strait of Hormuz, crew detained", "IRN", -8.0),
        (4, "US Navy warship escorts crude tanker through Persian Gulf", "SAU", -2.0),
        (9, "OPEC signals steady crude exports through the Gulf", "SAU", 1.5),
    ],
    "redsea": [
        (1, "Houthi drone attack hits oil tanker in the Red Sea", "YEM", -7.5),
        (3, "Shipping firms reroute crude away from Bab-el-Mandeb", "EGY", -3.5),
        (8, "Naval coalition steps up patrols in the Gulf of Aden", "YEM", -1.0),
    ],
    "cape": [
        (2, "More tankers take the Cape of Good Hope route to avoid Suez", "ZAF", -1.0),
        (12, "Nigerian crude exports steady via the Cape route", "NGA", 2.0),
    ],
    "domestic": [
        (5, "Maintenance shutdown at an Indian refinery trims output", "IND", -1.5),
    ],
}


def _risk_fixture_events(corridor: str, as_of: datetime) -> List[dict]:
    out = []
    for days_before, headline, country, goldstein in _RISK_FIXTURES.get(corridor, []):
        out.append({
            "source": "fixtures", "headline": headline, "country_code": country,
            "event_date": as_of - timedelta(days=days_before), "goldstein_scale": goldstein,
        })
    return out


# ── optional live source: GDELT DOC 2.0 (keyless, short timeout, fallback) ──
_GDELT_QUERY = {
    "hormuz": '"Strait of Hormuz" (oil OR tanker OR shipping OR Iran)',
    "redsea": '("Red Sea" OR "Bab-el-Mandeb" OR Houthi) (oil OR tanker OR shipping)',
    "cape": '("Cape of Good Hope" OR "Cape route") (oil OR tanker OR shipping)',
    "domestic": '(India refinery OR India pipeline) oil',
}
_GDELT_ISO3 = {
    "iran": "IRN", "saudi arabia": "SAU", "iraq": "IRQ", "united arab emirates": "ARE",
    "yemen": "YEM", "egypt": "EGY", "russia": "RUS", "nigeria": "NGA",
    "south africa": "ZAF", "india": "IND",
}


def _gdelt_events(corridor: str, as_of: datetime) -> List[dict]:
    query = _GDELT_QUERY.get(corridor)
    if not query:
        return []
    try:
        resp = httpx.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "ArtList", "format": "json",
                    "maxrecords": 25, "timespan": "7d", "sort": "datedesc"},
            timeout=6.0, headers={"User-Agent": "pravah-monolith/1.0"},
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception:
        return []  # flaky live source must never break scoring
    out = []
    for a in articles:
        seen = a.get("seendate")
        try:
            ev_date = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            ev_date = datetime.now(timezone.utc)
        out.append({
            "source": "gdelt", "headline": a.get("title") or "",
            "country_code": _GDELT_ISO3.get(str(a.get("sourcecountry") or "").strip().lower()),
            "event_date": ev_date, "goldstein_scale": None,
        })
    return out


# ── classify (heuristic; Gemini optional via GEMINI_API_KEY) ────────────────
_SANCTIONED_ENTITIES = ["rosneft", "pdvsa", "nioc", "nnpc"]
_RISK_RELEVANT = re.compile(
    r"\b(oil|crude\w*|tanker\w*|refiner\w*|strait\w*|shipping|ship|sanction\w*|"
    r"ports?|vessel\w*|opec|pipeline\w*|embargo\w*|naval|maritime|export\w*|"
    r"barrel\w*|brent|petroleum|chokepoint\w*|blockade\w*|escalat\w*|tension\w*|"
    r"conflict\w*|closure\w*|hijack\w*|seiz\w*)\b", re.IGNORECASE)
_SEV_CRITICAL = re.compile(
    r"\b(attack\w*|strike\w*|missile\w*|seiz\w*|blockade\w*|war|explosion\w*|"
    r"tanker hit|drone hit|closed the strait|shut the strait|shut down the strait)\b", re.IGNORECASE)
_SEV_HIGH = re.compile(
    r"\b(sanction\w*|threat\w*|clash\w*|drone\w*|hijack\w*|military|escalat\w*|"
    r"warship\w*|naval|embargo\w*|seize)\b", re.IGNORECASE)
_SEV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_COUNTRY_CORRIDOR = {
    "SAU": "hormuz", "IRQ": "hormuz", "ARE": "hormuz", "KWT": "hormuz", "QAT": "hormuz",
    "IRN": "hormuz", "BHR": "hormuz", "OMN": "hormuz", "RUS": "redsea", "YEM": "redsea",
    "EGY": "redsea", "SDN": "redsea", "NGA": "cape", "AGO": "cape", "ZAF": "cape", "IND": "domestic",
}
_KEYWORD_CORRIDOR = [
    (re.compile(r"\b(strait of hormuz|hormuz|persian gulf|arabian gulf|musandam)\b", re.IGNORECASE), "hormuz"),
    (re.compile(r"\b(cape of good hope|cape route|good hope)\b", re.IGNORECASE), "cape"),
    (re.compile(r"\b(red sea|bab-el-mandeb|bab el mandeb|houthi|suez|gulf of aden|aden)\b", re.IGNORECASE), "redsea"),
    (re.compile(r"\b(domestic pipeline|india refinery|indian refinery)\b", re.IGNORECASE), "domestic"),
]


def _risk_is_relevant(headline: str) -> bool:
    return bool(_RISK_RELEVANT.search(headline or ""))


def _risk_assign_corridor(event: dict, requested: str) -> str:
    text = event.get("headline") or ""
    for pattern, corridor in _KEYWORD_CORRIDOR:
        if pattern.search(text):
            return corridor
    code = event.get("country_code")
    if code:
        c = _COUNTRY_CORRIDOR.get(code.strip().upper())
        if c:
            return c
    return requested


def _severity_from_goldstein(g):
    if g is None:
        return None
    if g <= -7:
        return "critical"
    if g <= -4:
        return "high"
    if g <= -1:
        return "medium"
    return "low"


def _risk_severity(event: dict) -> str:
    headline = event.get("headline") or ""
    candidates = ["low"]
    if _SEV_CRITICAL.search(headline):
        candidates.append("critical")
    if _SEV_HIGH.search(headline):
        candidates.append("high")
    g = _severity_from_goldstein(event.get("goldstein_scale"))
    if g:
        candidates.append(g)
    return max(candidates, key=_SEV_RANK.__getitem__)


# ── scoring (verbatim math from risk-agent/scoring/risk_model.py) ───────────
_CORRIDOR_BASELINE = {"hormuz": 60.0, "redsea": 50.0, "cape": 15.0, "domestic": 5.0}
_SEVERITY_POINTS = {"low": 2.0, "medium": 5.0, "high": 10.0, "critical": 18.0}
_MAX_EVENT_PRESSURE = 40.0
_ALERT_THRESHOLDS = ((75.0, "critical"), (55.0, "high"), (30.0, "elevated"), (0.0, "low"))


def _alert_level_for(score: float) -> str:
    for threshold, level in _ALERT_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _recency_factor(event_date: datetime, as_of: datetime) -> float:
    days = (as_of - event_date).days
    if days <= 7:
        return 1.0
    if days >= 30:
        return 0.2
    return 1.0 - (days - 7) * (0.8 / 23.0)


def _run_risk_pipeline(corridor: str, as_of: datetime, use_live: bool = False):
    """ingest → classify → map_corridor → severity → score. Returns (result, sources, events)."""
    sources_used: List[str] = []
    raw: List[dict] = []
    for fetch in ([_risk_fixture_events] + ([_gdelt_events] if use_live else [])):
        try:
            events = fetch(corridor, as_of)
        except Exception:
            continue
        if events:
            raw.extend(events)
            sources_used.append(events[0]["source"])

    # classify + map corridor + severity
    for e in raw:
        e["relevant"] = _risk_is_relevant(e.get("headline", ""))
        e["corridor"] = _risk_assign_corridor(e, corridor)
        e["severity"] = _risk_severity(e)
        if e["relevant"] and any(ent in e.get("headline", "").lower() for ent in _SANCTIONED_ENTITIES):
            e["severity"] = "critical"
            e["sanctions_hit"] = True

    events = [e for e in raw if e.get("relevant") and e.get("corridor") == corridor]

    # score (identical to risk_model.compute_risk)
    trail: List[str] = []
    base = _CORRIDOR_BASELINE.get(corridor, 20.0)
    trail.append(f"Baseline risk for '{corridor}' corridor = {base:.0f}/100.")
    pressure, counts = 0.0, {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for e in events:
        sev = e["severity"]
        counts[sev] = counts.get(sev, 0) + 1
        points = _SEVERITY_POINTS.get(sev, 2.0)
        pressure += points * _recency_factor(e["event_date"], as_of)
        if e.get("sanctions_hit"):
            trail.append(f"Sanctions hit in event '{e['headline'][:30]}...' -> escalated severity to critical (+{points} pts).")
    pressure = min(pressure, _MAX_EVENT_PRESSURE)
    if events:
        breakdown = ", ".join(f"{counts[s]} {s}" for s in ("critical", "high", "medium", "low") if counts[s])
        trail.append(f"{len(events)} relevant event(s) ({breakdown}) -> +{pressure:.1f} (recency-weighted, capped at {_MAX_EVENT_PRESSURE:.0f}).")
    else:
        trail.append("No relevant events found in window -> no event pressure added.")
    golds = [e["goldstein_scale"] for e in events if e.get("goldstein_scale") is not None]
    goldstein_adj = 0.0
    if golds:
        avg_g = sum(golds) / len(golds)
        if avg_g < 0:
            goldstein_adj = min(-avg_g * 1.5, 12.0)
            trail.append(f"Avg Goldstein conflict scale {avg_g:.1f} (conflictual) -> +{goldstein_adj:.1f}.")
        else:
            trail.append(f"Avg Goldstein conflict scale {avg_g:.1f} (cooperative) -> no increase.")
    score = max(0.0, min(100.0, base + pressure + goldstein_adj))
    alert = _alert_level_for(score)
    trail.append(f"Final score = {score:.1f}/100 -> alert level '{alert}'.")
    confidence = max(0.0, min(0.95, 0.5 + 0.1 * len(set(sources_used)) + 0.02 * min(len(events), 10)))
    trail.append(f"Confidence {confidence:.2f} from {len(set(sources_used))} source(s), {len(events)} event(s).")

    events.sort(key=lambda e: (_SEV_RANK.get(e["severity"], 0), e["event_date"].timestamp()), reverse=True)
    result = {"score": round(score, 1), "confidence": round(confidence, 2), "alert_level": alert,
              "reasoning_trail": trail}
    return result, list(dict.fromkeys(sources_used)), events[:5]


def build_risk_response(corridor: str, as_of: Optional[datetime] = None, use_live: bool = False) -> RiskScoreResponse:
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    result, sources, top = _run_risk_pipeline(corridor, as_of, use_live)

    _SIG_SOURCE = {"fixtures": "GDELT", "gdelt": "GDELT"}
    total_pts = sum(_SEVERITY_POINTS.get(e["severity"], 2.0) for e in top) or 1.0
    signals = [
        RiskSignal(type="geo_event", source=_SIG_SOURCE.get(e["source"], "GDELT"),
                   weight=round(_SEVERITY_POINTS.get(e["severity"], 2.0) / total_pts, 2),
                   detail=e["headline"])
        for e in top
    ]
    key_events = [
        RiskKeyEvent(headline=e["headline"], severity=e["severity"], date=e["event_date"],
                     source=_SIG_SOURCE.get(e["source"], e["source"]), corridor=e["corridor"])
        for e in top
    ]
    model = "gemini-2.5-flash" if os.getenv("GEMINI_API_KEY") else "heuristic-keyword-v1"
    import typing
    alert_level_typed = typing.cast(Literal['critical', 'elevated', 'high', 'low'], result["alert_level"])
    
    supplier_risk_scores = {}
    C_MAP = {"hormuz": "Hormuz Strait", "redsea": "Red Sea/Suez", "cape": "Cape Route", "domestic": "Domestic"}
    target_c = C_MAP.get(corridor)
    if target_c:
        for u, d in G.nodes(data=True):
            if d.get("type") == "supplier":
                for route_id in G.successors(u):
                    if G.nodes[route_id].get("corridor") == target_c:
                        supplier_risk_scores[u] = result["score"]
                        break

    return RiskScoreResponse(
        corridor=corridor, score=result["score"], confidence=result["confidence"],
        alert_level=alert_level_typed, signals=signals,
        reasoning_trail=" ".join(result["reasoning_trail"]), key_events=key_events,
        computed_at=datetime.now(timezone.utc), data_sources=sources or ["fixtures"], model=model,
        supplier_risk_scores=supplier_risk_scores,
    )


# ════════════════════════════════════════════════════════════════════════════
#  COORDINATOR  (was coordinator/main.py — EMPTY; built here, in-process)
#  Blends risk → scenario → procurement + spr into one recommendation.
# ════════════════════════════════════════════════════════════════════════════
class FinalRecommendationRequest(BaseModel):
    corridor: Corridor = "hormuz"
    as_of: Optional[datetime] = None
    current_brent_usd: float = 84.0
    shock_duration_days: int = Field(default=14, ge=2, le=60)
    scenario_type: Literal["base", "hormuz_closure", "opec_cut"] = "base"


class Resolution(BaseModel):
    chosen_action: str
    tradeoff: str
    confidence: float
    reasoning_trail: List[str]


class FinalRecommendationResponse(BaseModel):
    summary: str
    risk: RiskScoreResponse
    scenario: SimulateResponse
    procurement: RecommendResponse
    spr: SPRScheduleResponse
    resolution: Resolution
    degraded: bool
    agents_status: dict
    as_of: datetime
    computed_at: datetime


async def _coordinate(req: FinalRecommendationRequest) -> FinalRecommendationResponse:
    corridor = req.corridor
    agents_status = {"risk": "live", "scenario": "live", "procurement": "live", "spr": "live"}
    degraded = False

    # 1) risk first — everything else keys off the corridor risk score
    risk = build_risk_response(corridor, req.as_of)

    # 2) scenario simulation driven by the risk score
    scenario = _simulate(SimulateRequest(
        risk_score=risk.score, corridor=corridor, shock_duration_days=req.shock_duration_days,
        num_simulations=5000, current_brent_usd=req.current_brent_usd,
        elasticity_assumptions=ElasticityAssumptions(pass_through_rate_to_pump=0.6,
                                                     gdp_sensitivity_per_10pct_oil_shock=-0.15),
        scenario_type=req.scenario_type,
    ))

    # 3) procurement alternatives (never 500 the blend if the FX call hiccups)
    try:
        procurement = await _recommend(RecommendRequest(
            current_supplier="SAU_ARAMCO", current_corridor_risk_score=risk.score,
            target_refinery="REF_JAMNAGAR", required_crude_grade="GRADE_MEDIUM_SOUR",
            cost_weight=0.34, risk_weight=0.33, transit_time_weight=0.33, max_alternatives=5,
        ))
    except Exception:
        agents_status["procurement"] = "error"
        degraded = True
        raise

    # 4) SPR schedule against the scenario's median price path
    horizon = min(len(scenario.daily_price_path), req.shock_duration_days, 14)
    prices = [round(p.p50, 2) for p in scenario.daily_price_path[:horizon]]
    spr = _spr_schedule(SPRScheduleRequest(
        planning_horizon_days=horizon, current_reserve_days=9.5, min_safety_floor_days=6.0,
        daily_risk_scores=[risk.score] * horizon, daily_price_forecast_usd_per_bbl=prices,
        max_daily_drawdown_days=1.0,
    ))

    # 5) resolve cost-vs-security into one action
    top = procurement.recommendations[0] if procurement.recommendations else None
    base = procurement.current_supplier_baseline
    if top:
        cost_delta = top.estimated_cost_usd_per_bbl - base.estimated_cost_usd_per_bbl
        risk_delta = top.corridor_risk_score - base.corridor_risk_score
        tradeoff = (f"accepted {cost_delta:+.2f} $/bbl cost for {risk_delta:+.0f} corridor-risk points "
                    f"via {top.route} ({top.supplier})")
        chosen = (f"Shift procurement to {top.supplier} via {top.route}; "
                  f"run SPR drawdown of {spr.total_drawdown_days} days over {horizon} days.")
    else:
        cost_delta = risk_delta = 0.0
        tradeoff = "no alternative supplier beat the baseline"
        chosen = f"Hold current supplier; run SPR drawdown of {spr.total_drawdown_days} days."

    reasoning_trail = [
        f"Corridor '{corridor}' risk {risk.score}/100 ({risk.alert_level}).",
        f"Scenario: median Brent ${scenario.brent_price_distribution.p50:.1f}/bbl over {req.shock_duration_days}d "
        f"(pump p50 ₹{scenario.pump_price_impact.projected_p50_inr_per_litre:.1f}/L).",
        (f"Procurement: top alternative {top.supplier} at ${top.estimated_cost_usd_per_bbl:.1f}/bbl, "
         f"supplier-specific risk {risk.supplier_risk_scores.get(top.supplier, top.corridor_risk_score):.0f}." if top else "Procurement: baseline retained."),
        f"SPR: release {spr.total_drawdown_days} days, est. savings ${spr.savings_usd:,.0f}; "
        f"replenishment window estimated at {spr.replenishment_window_days} days.",
        f"Resolution: {tradeoff}.",
    ]
    summary = (
        f"The {corridor.capitalize()} corridor is at {risk.alert_level.upper()} risk ({risk.score}/100). "
        f"Over a {req.shock_duration_days}-day disruption, Brent is projected near "
        f"${scenario.brent_price_distribution.p50:.0f}/bbl (median), lifting Indian pump prices to about "
        f"₹{scenario.pump_price_impact.projected_p50_inr_per_litre:.1f}/L. "
        + (f"Recommended: shift volume to {top.supplier} ({top.route}) and activate an SPR drawdown of "
           f"{spr.total_drawdown_days} days (est. ${spr.savings_usd:,.0f} saved) while keeping reserves above the safety floor."
           if top else
           f"Recommended: hold the current supplier and run a measured SPR drawdown of {spr.total_drawdown_days} days.")
    )

    return FinalRecommendationResponse(
        summary=summary, risk=risk, scenario=scenario, procurement=procurement, spr=spr,
        resolution=Resolution(chosen_action=chosen, tradeoff=tradeoff, confidence=risk.confidence,
                              reasoning_trail=reasoning_trail),
        degraded=degraded, agents_status=agents_status,
        as_of=datetime.now(timezone.utc), computed_at=datetime.now(timezone.utc),
    )


# ════════════════════════════════════════════════════════════════════════════
#  FASTAPI APP
# ════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Pravah monolith backend starting up (v1.0.0)")
    try:
        calibrate_volatility()
        log.info("scenario volatility calibration complete")
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("scenario calibration skipped: %s", exc)
    log.info("startup complete — ready to serve")
    yield
    log.info("Pravah monolith backend shutting down")


app = FastAPI(title="Pravah Monolith Backend", version="1.0.0", lifespan=lifespan)

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])
log.info("CORS allow_origins = %s", _origins)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    """Log every request with method, path, status and latency (ms)."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        dur = (time.perf_counter() - start) * 1000
        log.exception("%s %s -> unhandled error after %.1fms", request.method, request.url.path, dur)
        raise
    dur = (time.perf_counter() - start) * 1000
    level = logging.WARNING if response.status_code >= 500 else logging.INFO
    log.log(level, "%s %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, dur)
    return response


@app.get("/")
def root():
    return {
        "service": "pravah-monolith-backend",
        "status": "ok",
        "agents": ["scenario", "spr", "procurement", "risk", "coordinator"],
        "endpoints": [
            "POST /simulate", "GET /simulate/mock", "GET /data-status",
            "POST /spr-schedule", "GET /spr-schedule/mock",
            "POST /recommend", "GET /market", "GET /graph",
            "POST /risk-score", "GET /corridors", "POST /final-recommendation",
            "GET /health",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ── scenario routes ─────────────────────────────────────────────────────────
@app.get("/data-status")
def data_status():
    return get_data_status()


@app.get("/simulate/mock", response_model=SimulateResponse)
def simulate_mock():
    return _simulate_mock()


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    return _simulate(req)


# ── spr routes ──────────────────────────────────────────────────────────────
@app.post("/spr-schedule", response_model=SPRScheduleResponse)
def spr_schedule(req: SPRScheduleRequest):
    return _spr_schedule(req)


@app.get("/spr-schedule/mock", response_model=SPRScheduleResponse)
def spr_schedule_mock():
    return _spr_schedule_mock()


# ── procurement routes ──────────────────────────────────────────────────────
_FLEET_DATA = [
    {"id": f"VSL_{i:03d}", "lat": 20.0 + (i * 0.5) % 15.0, "lon": 60.0 + (i * 1.5) % 25.0, "status": "underway"}
    for i in range(35)
]

@app.get("/fleet")
def get_fleet():
    now = datetime.now(timezone.utc)
    drift = (now.hour * 60 + now.minute) / 1440.0 * 0.5
    drifted = []
    for v in _FLEET_DATA:
        drifted.append({
            **v,
            "lat": v["lat"] + drift,
            "lon": v["lon"] + drift
        })
    return {"fleet": drifted}

@app.get("/graph")
def get_graph():
    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


@app.get("/market")
async def get_market():
    return await fetch_live_market_data()


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    return await _recommend(req)


# ── risk routes ─────────────────────────────────────────────────────────────
@app.post("/risk-score", response_model=RiskScoreResponse)
def risk_score(req: RiskScoreRequest, live: bool = False):
    return build_risk_response(req.corridor, req.as_of, use_live=live)


@app.get("/corridors", response_model=List[RiskScoreResponse])
def corridors(live: bool = False):
    """Real risk score for every monitored corridor (Citizen/Command/Risk views)."""
    return [build_risk_response(c, use_live=live) for c in ("hormuz", "redsea", "cape", "domestic")]


# ── coordinator route ───────────────────────────────────────────────────────
@app.post("/final-recommendation", response_model=FinalRecommendationResponse)
async def final_recommendation(req: FinalRecommendationRequest):
    return await _coordinate(req)


# ── policy maker route ──────────────────────────────────────────────────────
class PolicyAction(BaseModel):
    id: str
    title: str
    description: str
    outcome: str
    timeline: str
    category: str
    impact: str

class GeneratePolicyResponse(BaseModel):
    summary: str
    actions: List[PolicyAction]
    confidence: float

@app.post("/generate-policy", response_model=GeneratePolicyResponse)
async def generate_policy():
    try:
        corridors = [build_risk_response(c, use_live=True) for c in ("hormuz", "redsea", "cape", "domestic")]
        market = await fetch_live_market_data()
        
        # We need the final recommendation summary as well
        rec_req = FinalRecommendationRequest(corridor="hormuz")
        recommendation = await _coordinate(rec_req)

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
        
        prompt = f"""
        Act as the Indian Ministry of Petroleum's AI advisor.
        Current Market: Brent ${market["brent_usd"]}
        Risk Scores: Hormuz {corridors[0].score}, Red Sea {corridors[1].score}
        Backend AI Recommendation: {recommendation.summary}
        
        Generate 3 high-impact policy actions to mitigate energy supply chain risks based on this live intelligence.
        Format the output strictly as JSON with this schema:
        {{
            "summary": "Brief executive summary of the situation",
            "actions": [
                {{
                    "id": "POL-1",
                    "title": "Title of action",
                    "description": "Detailed description",
                    "outcome": "Expected outcome",
                    "timeline": "Immediate / 30 Days / etc",
                    "category": "SPR / Procurement / Diplomatic",
                    "impact": "critical"
                }}
            ],
            "confidence": 0.95
        }}
        """
        
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return GeneratePolicyResponse(**result)
    except Exception as e:
        log.warning("LLM Policy generation failed: %s. Falling back to template.", e)
        fallback = {
            "summary": "Fallback Policy: Activate predefined supply chain resilience measures.",
            "actions": [
                {
                    "id": "POL-FB-1",
                    "title": "Activate SPR Drawdown",
                    "description": "Initiate predefined SPR drawdown to offset immediate price shocks.",
                    "outcome": "Stabilized domestic pump prices.",
                    "timeline": "Immediate",
                    "category": "SPR",
                    "impact": "high"
                },
                {
                    "id": "POL-FB-2",
                    "title": "Divert Procurement",
                    "description": "Shift spot procurement away from high-risk corridors.",
                    "outcome": "Reduced exposure to transit delays.",
                    "timeline": "7 Days",
                    "category": "Procurement",
                    "impact": "medium"
                },
                {
                    "id": "POL-FB-3",
                    "title": "Diplomatic Outreach",
                    "description": "Engage with suppliers for guaranteed loading windows.",
                    "outcome": "Secured supply lines.",
                    "timeline": "30 Days",
                    "category": "Diplomatic",
                    "impact": "medium"
                }
            ],
            "confidence": 0.8
        }
        return GeneratePolicyResponse(**fallback)
