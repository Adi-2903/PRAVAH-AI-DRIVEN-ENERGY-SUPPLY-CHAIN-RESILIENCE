from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

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
    daily_price_path: list[DailyPricePoint]
    pump_price_impact: PumpPriceImpact
    gdp_impact_pct: GdpImpactPct
    calibration_note: str
    num_simulations_run: int
    computed_at: datetime
    data_source: Literal["live_eia", "fallback_cache"]
    volatility_calibrated_from: str
