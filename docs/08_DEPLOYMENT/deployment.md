# Deployment Guide

## Platform
Pravah is designed to be hosted entirely on **Vercel** as a single project.

## Architecture Mapping on Vercel
*   **Frontend**: Handled by Vercel's standard Next.js build pipeline.
*   **Backend (Python)**: Handled via Vercel Serverless Functions. The `api/index.py` file inside the `frontend/` directory is the entry point that Vercel uses to boot up the FastAPI app defined in `api.py`.

## Environment Variables
The following environment variables must be configured in the Vercel project dashboard:

| Variable | Type | Purpose |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_RISK_URL` | URL | Target URL for the Risk Engine. |
| `NEXT_PUBLIC_SCENARIO_URL` | URL | Target URL for the Scenario Engine. |
| `NEXT_PUBLIC_PROCUREMENT_URL` | URL | Target URL for the Procurement Agent. |
| `NEXT_PUBLIC_SPR_URL` | URL | Target URL for the SPR Optimizer. |
| `NEXT_PUBLIC_COORDINATOR_URL` | URL | Target URL for the Coordinator. |
| `NEXT_PUBLIC_SHARED_URL` | URL | Target URL for shared endpoints (health/market). |
| `EIA_API_KEY` | Secret | (Optional) Enables live Brent crude history fetching. |
| `GEMINI_API_KEY` | Secret | (Optional) Enables NLP classification in the Risk Engine. |
| `LOG_LEVEL` | String | e.g., `INFO` or `DEBUG` (Defaults to `INFO`). |

*(Note: In the monolithic deployment, all `NEXT_PUBLIC_*` URLs should point to the exact same Vercel production domain, e.g., `https://pravah.vercel.app/api`).*

## Vercel Constraints & Pitfalls
1.  **Bundle Size (250MB)**: Vercel limits serverless function sizes. If you add heavy libraries like `pandas`, `scipy`, or `tensorflow` to `requirements.txt`, the build will fail during deployment. This is why complex algorithms were re-written using vanilla Python and lightweight `numpy`.
2.  **Relative Imports**: Vercel Python serverless functions notoriously struggle with complex folder hierarchies and relative imports outside the root `/api` folder. Keep the Python backend as flat as possible (hence `api.py`).
3.  **Build Warnings**: Next.js builds on Vercel will fail on ESLint errors. Specifically, `react-hooks/exhaustive-deps` rules are sometimes suppressed in `eslint.config.mjs` to ensure the prototype code deploys cleanly.
