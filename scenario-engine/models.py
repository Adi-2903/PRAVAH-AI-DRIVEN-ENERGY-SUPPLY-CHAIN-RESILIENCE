from pydantic import BaseModel, Field
from typing import List

class ElasticityAssumptions(BaseModel):
    price_elasticity_of_demand: float = Field(..., description="Price elasticity of demand")
    pass_through_rate_to_pump: float = Field(..., description="Pass-through rate to Indian pump prices")
    gdp_sensitivity_per_10pct_oil_shock: float = Field(..., description="GDP sensitivity per 10% oil shock")

class SimulateRequest(BaseModel):
    risk_score: float = Field(..., ge=0, le=100, description="Supply-shock risk score (0-100)")
    corridor: str = Field(..., description="Corridor name, e.g. hormuz")
    shock_duration_days: int = Field(..., gt=0, le=365, description="Shock duration in days")
    num_simulations: int = Field(..., gt=0, le=20000, description="Number of Monte Carlo simulations")
    elasticity_assumptions: ElasticityAssumptions
    current_brent_usd: float = Field(..., gt=0, description="Current Brent crude oil price in USD")

class DistributionStats(BaseModel):
    p10: float
    p50: float
    p90: float
    mean: float
    std_dev: float

class DailyPriceStats(BaseModel):
    day: int
    p10: float
    p50: float
    p90: float

class PumpPriceImpact(BaseModel):
    current_inr_per_litre: float
    projected_p50_inr_per_litre: float
    projected_p90_inr_per_litre: float

class GDPImpactPct(BaseModel):
    p10: float
    p50: float
    p90: float

class SimulateResponse(BaseModel):
    brent_price_distribution: DistributionStats
    daily_price_path: List[DailyPriceStats]
    pump_price_impact: PumpPriceImpact
    gdp_impact_pct: GDPImpactPct
    calibration_note: str
    num_simulations_run: int
    computed_at: str
    data_source: str = Field(..., description="Source of Brent spot price history ('live_eia' or 'fallback_cache')")
    volatility_calibrated_from: str = Field(..., description="Date range used for volatility calibration")

