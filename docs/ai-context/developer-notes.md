# Developer Notes & Memory

## Why `api.py` exists (The Monolith Pivot)
Pravah was originally built with separate Python packages (`risk-agent/`, `scenario-engine/`, etc.). This caused massive deployment headaches on Vercel regarding relative imports, dynamic module loading (`postgrest.constants`), and the 250MB serverless limit. 
The solution was to merge all agent logic into a single file (`api.py`) and strip out heavy dependencies (like `scipy`, `pandas`, and `langgraph`). 
**Critical**: Do NOT refactor `api.py` back into separate folders if deploying to Vercel Serverless.

## Assumptions & Limitations
*   **Database**: There is no database. All state is maintained in-memory or passed via the frontend requests.
*   **Data Consistency**: The `_BRENT_CSV` string embedded in `api.py` serves as the ultimate fallback. It must not be removed.
*   **Routing**: The Next.js frontend points 6 different API `NEXT_PUBLIC_*` URLs to the backend. While currently they all point to the monolithic `api.py`, the architecture intentionally supports pointing them to microservices in the future.

## What will break if changed
*   **`_spr_schedule()`**: The SPR Optimizer uses a greedy knapsack algorithm manually written in numpy. Do not replace this with `scipy.optimize.linprog`, or the deployment bundle will exceed 250MB.
*   **Frontend Data Fetching**: The `useLiveData` hook heavily relies on the backend returning specific nested JSON structures matching the Pydantic models in `api.py`. Modifying the Pydantic schemas will silently break frontend data rendering.

## Future Context for AI Agents
If you are an AI reading this in the future:
1.  **Do not invent database schemas** - Pravah is stateless.
2.  **Do not try to find `shared/schemas`** - The schemas are inlined at the top of `api.py`.
3.  **Do not alter the `NEXT_PUBLIC_` env var structure** - The frontend relies on these to know where the endpoints live.
