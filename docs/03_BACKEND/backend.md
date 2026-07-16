# Backend Architecture & Implementation

## Overview
The Pravah backend is implemented as a single, self-contained Python file (`api.py`) using the **FastAPI** framework. It acts as a monolith, encapsulating the logic of five distinct theoretical agents: Risk, Scenario, Procurement, Strategic Petroleum Reserve (SPR), and Coordinator.

## The `api.py` Monolith
Historically, the project was split into separate modules (`risk-agent`, `scenario-engine`, etc.). To bypass Vercel's serverless deployment limitations (specifically the 250MB bundle limit and issues with relative imports in Python Serverless Functions), the codebase was refactored. 

All algorithms, data models (Pydantic), and embedded fallback data are contained within the ~1800 lines of `api.py`. There are no external database dependencies.

## Core Components

### 1. Embedded Data & Fallbacks
The backend guarantees 100% uptime through embedded data.
*   **`_BRENT_CSV`**: A multi-year historical dataset of Brent crude spot prices is hardcoded as a multiline string.
*   **`fetch_brent_spot_history()`**: Attempts to fetch live data from the EIA API using `EIA_API_KEY`. If the key is missing or the API fails, it seamlessly parses and returns data from `_BRENT_CSV`.

### 2. The Risk Engine (`_run_risk_pipeline`)
Calculates a risk score (0-100) for a given maritime corridor.
*   **Data Ingestion**: Pulls deterministic fixtures (`_RISK_FIXTURES`) and optionally fetches live news via the GDELT API (`_gdelt_events`).
*   **Classification**: Uses regex heuristics (`_RISK_RELEVANT`, `_SEV_CRITICAL`, `_SEV_HIGH`) to filter relevant oil/shipping news and assign severity. (Supports an optional Gemini integration via `GEMINI_API_KEY`).
*   **Scoring**: Applies a recency-weighted decay algorithm. Base corridor risk + pressure from recent critical events = Final Score.

### 3. The Scenario Engine (`_simulate`)
Forecasts crude oil price trajectories over a specific shock duration.
*   **Math Model**: Implements an Ornstein-Uhlenbeck geometric random walk with mean reversion.
*   **Risk Integration**: The baseline volatility (`sigma`) and mean reversion target (`theta`) are dynamically scaled upward based on the Risk Engine's score.
*   **Outputs**: Calculates P10, P50, and P90 confidence intervals for Brent prices, and translates those into localized pump prices (INR/L) and GDP impact percentages.

### 4. The Procurement Agent (`_recommend`)
Finds alternative supply routes when a primary corridor is compromised.
*   **Graph Model**: Builds an in-memory `NetworkX.DiGraph` representing global crude suppliers, shipping routes (with associated risks and transit times), ports, and domestic refineries.
*   **Traversal**: Uses `nx.all_simple_paths` to find viable supply chains from any supplier to the target refinery that match the required crude grade.
*   **Scoring**: Normalizes cost, transit time, and corridor risk across all alternatives, applying user-defined weights to generate a composite score and rank alternatives.

### 5. The SPR Optimizer (`_spr_schedule`)
Calculates an optimal drawdown schedule for the Strategic Petroleum Reserve.
*   **Algorithm**: Implements a Greedy Knapsack LP (Linear Programming) approach manually in numpy (to avoid the heavy `scipy` dependency). 
*   **Logic**: It allocates the available SPR budget (Current Reserve - Safety Floor) to the days with the highest forecasted price and highest risk weight, capping at the maximum daily drawdown limit.

### 6. The Coordinator (`_coordinate`)
The master orchestration function.
*   When `POST /final-recommendation` is hit, this function sequentially executes the Risk, Scenario, Procurement, and SPR pipelines.
*   It aggregates the results, compares the best alternative procurement route against a "do nothing" baseline, and generates a final deterministic `reasoning_trail` explaining the tradeoff.

## FastAPI Setup
*   **CORS**: Configured via `ALLOWED_ORIGINS` to accept requests from the frontend.
*   **Middleware**: Custom `_log_requests` middleware logs latency and status codes for every request.
*   **Lifespan**: The `lifespan` context manager runs `calibrate_volatility()` on startup to baseline the Scenario Engine against the most recent 2-year history of Brent crude.

---
*Related Documents:*
*   [API Reference](../06_API/api_reference.md)
*   [Data Flow](../05_DATA_FLOW/data_flow.md)
