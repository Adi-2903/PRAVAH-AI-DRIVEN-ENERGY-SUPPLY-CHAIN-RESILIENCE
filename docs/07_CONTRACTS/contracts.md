# Data Contracts

This document outlines the strict data structures (Pydantic models) used for serialization and validation across the Pravah system. Because the backend is a monolith, there is no `shared/schemas/` directory; these contracts are defined inline in `api.py` (Lines 52-212).

## Global Types
*   **`Corridor`**: `Literal["hormuz", "redsea", "cape", "domestic"]`

## Scenario Engine Contracts

### `SimulateRequest`
```python
class SimulateRequest(BaseModel):
    risk_score: float = Field(ge=0.0, le=100.0)
    corridor: Corridor
    shock_duration_days: int = Field(ge=1, le=365)
    num_simulations: int = Field(ge=1000, le=20000)
    current_brent_usd: float
    elasticity_assumptions: ElasticityAssumptions
```

### `SimulateResponse`
Contains nested objects for statistical distributions.
*   `brent_price_distribution`: `{ p10, p50, p90, mean, std_dev }`
*   `daily_price_path`: Array of `{ day, p10, p50, p90 }`
*   `pump_price_impact`: `{ current_inr_per_litre, projected_p50_inr_per_litre, projected_p90_inr_per_litre }`
*   `gdp_impact_pct`: `{ p10, p50, p90 }`

## SPR Optimizer Contracts

### `SPRScheduleRequest`
*   `planning_horizon_days`: Length of arrays must match this.
*   `current_reserve_days` & `min_safety_floor_days`: Define the available budget.
*   `daily_risk_scores` & `daily_price_forecast_usd_per_bbl`: Arrays of floats used by the knapsack algorithm.

### `SPRScheduleResponse`
*   `schedule`: Array of `DailySchedule` (day, drawdown_days, reserve_after_days, rationale).
*   `total_drawdown_days`: Total capacity allocated.
*   `baseline_cost_usd` & `optimized_cost_usd` & `savings_usd`.

## Procurement Agent Contracts

### `RecommendRequest`
*   Requires standard weights: `cost_weight`, `risk_weight`, `transit_time_weight`.
*   A `model_validator` ensures that these three weights exactly sum to 1.0 (with a +/- 0.01 tolerance for floating point math), otherwise it throws a `ValueError`.

### `RecommendResponse`
*   `recommendations`: Sorted array of `RecommendationItem` (supplier, route, port, composite_score, reasoning).
*   `current_supplier_baseline`: Used by the Coordinator to calculate the delta (Cost penalty vs Risk reduction).

## Risk Engine Contracts

### `RiskScoreResponse`
*   `score` (0-100 float) and `alert_level` (low, elevated, high, critical).
*   `signals`: Array of weighted signals contributing to the score.
*   `key_events`: Raw news events (date, severity, headline) ingested from fixtures/GDELT.
*   `reasoning_trail`: A strictly formatted English string explaining the mathematical additions to the baseline score.
