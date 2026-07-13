"""
shared/schemas/spr_schedule.py  —  Pravah SPR Agent contract  (v2)

This is the canonical schema. spr-agent/models.py imports from here
so both ends are always in sync.

v2 changes vs v1:
  - SprScheduleRequest replaced with LP-input contract (planning_horizon_days,
    daily_risk_scores[], daily_price_forecast_usd_per_bbl[], etc.)
  - SprScheduleResponse: replaced simple summary with LP-output contract
    (per-day DailySchedule list, cost/savings financials, reserve floor flag)
  - Old v1 class names kept as aliases so any existing coordinator reference
    still resolves at import time (they will break at runtime if they try to
    use the old fields — that's intentional; v1 was broken anyway).
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


# ── Request ────────────────────────────────────────────────────────────────────

class SPRScheduleRequest(BaseModel):
    planning_horizon_days: int = Field(..., description="Number of days to plan for")
    current_reserve_days: float = Field(..., description="Current SPR cover in days")
    min_safety_floor_days: float = Field(..., description="Minimum SPR cover to maintain")
    daily_risk_scores: List[float] = Field(..., description="Risk scores for each day")
    daily_price_forecast_usd_per_bbl: List[float] = Field(..., description="Price forecast for each day")
    max_daily_drawdown_days: float = Field(..., description="Maximum drawdown allowed per day")

# v1 alias — import still succeeds, do not use directly
SprScheduleRequest = SPRScheduleRequest


# ── Response sub-models ────────────────────────────────────────────────────────

class DailySchedule(BaseModel):
    day: int
    drawdown_days: float
    reserve_after_days: float
    risk_score: float
    price_usd: float
    rationale: str


# ── Top-level response ─────────────────────────────────────────────────────────

class SPRScheduleResponse(BaseModel):
    schedule: List[DailySchedule]
    total_drawdown_days: float
    baseline_cost_usd: float
    optimized_cost_usd: float
    savings_usd: float
    savings_pct: float
    reserve_never_below_floor: bool
    computed_at: str                          # ISO-8601 string from .isoformat()

# v1 alias — import still succeeds, do not use directly
SprScheduleResponse = SPRScheduleResponse
