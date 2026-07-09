from pydantic import BaseModel, Field
from typing import List

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
