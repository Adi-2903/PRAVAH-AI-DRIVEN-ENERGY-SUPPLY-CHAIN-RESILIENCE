# API Reference

This document details the exact endpoints exposed by the Pravah backend (`api.py`).

## Core Endpoints

### `POST /final-recommendation`
The primary orchestration endpoint used by the main dashboard.
*   **Request (`FinalRecommendationRequest`)**:
    *   `corridor` (str): e.g., "hormuz", "redsea".
    *   `shock_duration_days` (int): Duration of the disruption to model.
    *   `current_brent_usd` (float): Baseline price.
*   **Response (`FinalRecommendationResponse`)**: Returns the aggregated JSON blob containing `risk`, `scenario`, `procurement`, `spr`, and the unified `resolution`.
*   **Business Logic**: Runs the internal `_coordinate()` function (Risk -> Scenario -> Procurement -> SPR pipeline).

### `POST /simulate`
*   **Request (`SimulateRequest`)**: Requires `risk_score`, `corridor`, `shock_duration_days`, `num_simulations`, `current_brent_usd`, and `elasticity_assumptions`.
*   **Response (`SimulateResponse`)**: Returns `brent_price_distribution`, `daily_price_path`, `pump_price_impact`, and `gdp_impact_pct`.
*   **Business Logic**: Executes the Monte Carlo random walk.

### `POST /spr-schedule`
*   **Request (`SPRScheduleRequest`)**: Requires `planning_horizon_days`, `current_reserve_days`, `min_safety_floor_days`, array of `daily_risk_scores`, array of `daily_price_forecast_usd_per_bbl`, and `max_daily_drawdown_days`.
*   **Response (`SPRScheduleResponse`)**: Returns a `schedule` array of daily actions, `total_drawdown_days`, and calculated `savings_usd`.
*   **Business Logic**: Executes the Greedy Knapsack LP optimization.

### `POST /recommend`
*   **Request (`RecommendRequest`)**: Requires `current_supplier`, `current_corridor_risk_score`, `target_refinery`, `required_crude_grade`, and weighting parameters (`cost_weight`, `risk_weight`, `transit_time_weight`).
*   **Response (`RecommendResponse`)**: Returns a sorted array of `RecommendationItem` objects, the `current_supplier_baseline`, and `graph_stats`.
*   **Business Logic**: Traverses the NetworkX DiGraph to rank alternative supply routes.

### `POST /risk-score`
*   **Request (`RiskScoreRequest`)**: Requires `corridor`. Query Param: `?live=true` (optional).
*   **Response (`RiskScoreResponse`)**: Returns `score`, `alert_level`, `signals`, and `reasoning_trail`.
*   **Business Logic**: Executes heuristic severity keyword matching against GDELT news or embedded fixtures.

## Utility Endpoints

*   **`GET /` & `GET /health`**: Returns basic service status.
*   **`GET /data-status`**: Returns metadata about the internal EIA cache state (`live_working`, `current_source`).
*   **`GET /graph`**: Dumps the raw internal NetworkX DiGraph nodes and edges for frontend visualization.
*   **`GET /market`**: Returns live USD/INR Forex data and static crude diffs.
*   **`GET /corridors`**: Returns an array of `RiskScoreResponse` objects for all 4 known corridors.
*   **`GET /simulate/mock` & `GET /spr-schedule/mock`**: Hardcoded deterministic responses used when the frontend is in `NEXT_PUBLIC_USE_MOCK=true` mode.
