# Deployment Context

**Platform**: Vercel (Frontend & Backend)

## Architecture Overview
The project is deployed as a single Vercel project utilizing:
1.  **Frontend**: Next.js App Router (static/SSR hybrid).
2.  **Backend**: FastAPI running as a Vercel Serverless Function via `api/index.py`.

## Environment Variables
The `.env` file must contain the following keys (or be set in Vercel):
*   `NEXT_PUBLIC_RISK_URL`, `NEXT_PUBLIC_SCENARIO_URL`, `NEXT_PUBLIC_PROCUREMENT_URL`, `NEXT_PUBLIC_SPR_URL`, `NEXT_PUBLIC_COORDINATOR_URL`, `NEXT_PUBLIC_SHARED_URL`
    *   In production, these all point to the same base URL (e.g., `https://pravah.vercel.app/api`).
*   `EIA_API_KEY` (Optional): For live Brent crude prices. Without it, the backend gracefully falls back to the embedded CSV.
*   `GEMINI_API_KEY` (Optional): If set, the risk engine uses Gemini for NLP classification. If not, it uses a regex heuristic.

## Build Constraints
*   **Vercel Serverless Limit (250MB)**: The backend avoids heavy libraries like `scipy` or `pandas` to ensure the Serverless function bundle size remains under Vercel's strict 250MB limit. This is why `api.py` uses standard Python math, numpy, and networkx, and implements its own greedy LP algorithm.
*   **Monolithic API**: The transition from multi-agent to `api.py` was specifically done to solve Vercel deployment issues with dynamic libraries and relative imports across folders. Do not re-introduce complex folder hierarchies for the Python backend if it remains on Vercel serverless.
*   **ESLint**: Strict ESLint rules (like exhaustive deps) are often suppressed in the Vercel build to prevent UI prototypes from failing deployment.
