# Backend Context

**Primary File**: `api.py`
**Framework**: FastAPI
**Paradigm**: Monolithic, single-file serverless backend.

## Overview
The entire Pravah backend is concentrated in `api.py`. It does not rely on a database. It utilizes in-memory logic, embedded datasets (like a hardcoded `_BRENT_CSV`), and lightweight external API calls (EIA, GDELT, Exchangerate.host). 

## Endpoints & Logic
*   **`GET /` & `GET /health`**: Standard health checks.
*   **`POST /risk-score`**: Calculates a risk score (0-100) based on embedded fixtures and live GDELT data. Uses a keyword/regex severity heuristic (`_run_risk_pipeline`).
*   **`GET /corridors`**: Returns risk scores for all four tracked corridors (`hormuz`, `redsea`, `cape`, `domestic`).
*   **`POST /simulate`**: Scenario engine. Runs a Monte Carlo simulation (Geometric random walk with mean reversion) over N iterations to forecast Brent crude prices over `shock_duration_days`.
*   **`POST /recommend`**: Procurement agent. Traverses a hardcoded NetworkX Directed Graph (`build_procurement_graph()`) to find alternative crude supply routes based on cost, risk, and transit weights.
*   **`POST /spr-schedule`**: Strategic Petroleum Reserve agent. Implements a greedy allocation (single-budget knapsack LP) to decide daily drawdown limits against forecasted price risks.
*   **`POST /final-recommendation`**: The Coordinator. An orchestration endpoint that sequentially calls: Risk -> Scenario -> Procurement -> SPR and aggregates them into one `FinalRecommendationResponse`.

## Important Architectural Notes
*   **No DB, No Dependencies**: The backend runs completely isolated. Data persistence is not required.
*   **Greedy LP for SPR**: scipy is avoided to keep the deployment bundle size under Vercel limits. The SPR logic uses greedy allocation.
*   **Error Handling**: If external APIs fail (like EIA), `api.py` seamlessly falls back to embedded CSV fixtures to ensure 100% uptime.
*   **Do Not Break**: The `api.py` file must remain standalone. Do not add `import shared...` because relative imports will break the serverless deployment setup.
