# Repository Map

**Project**: Pravah (AI-Driven Energy Supply Chain Resilience)
**Architecture**: Monolithic Backend (FastAPI) + Serverless Frontend (Next.js)

## High-Level Architecture

Pravah was originally designed as a multi-agent system with separate modules (Risk Agent, Scenario Engine, Procurement Agent, SPR Agent, Coordinator). 
To optimize for deployment (like Vercel serverless limits), these agents have been merged into a **single-file monolith backend** (`api.py`).

```mermaid
graph TD
    Client[Next.js Frontend] --> |API Calls| Backend[api.py Monolith]
    
    subgraph Backend [api.py (FastAPI)]
        Coordinator[Coordinator /final-recommendation]
        Risk[Risk Engine /risk-score]
        Scenario[Scenario Engine /simulate]
        Procurement[Procurement Agent /recommend]
        SPR[SPR Optimizer /spr-schedule]
        
        Coordinator --> Risk
        Coordinator --> Scenario
        Coordinator --> Procurement
        Coordinator --> SPR
    end
    
    Backend --> |External APIs| EIA[EIA / GDELT / Exchangerate.host]
```

## Directory Structure

*   **`api.py`**: The entire backend. Contains data models, AI logic, pathfinding algorithms, risk heuristic scoring, and FastAPI endpoints.
*   **`frontend/`**: Next.js App Router application.
    *   **`app/`**: Contains all pages (dashboard, citizen-view, digital-twin, policy-maker, procurement, risk-intelligence, simulator, spr).
    *   **`app/lib/`**: `api.ts` (endpoint configs), `live-data.ts` (fetchers), `use-live-data.ts` (React Hooks), `export.ts` (PDF/CSV exports).
    *   **`app/components/`**: UI components like `data-freshness.tsx` and `reasoning-trail.tsx`.
*   **`api/`** (inside `frontend/`): `index.py` likely wraps `api.py` for Vercel serverless functions.
*   **Legacy Agent Folders**: `risk-agent/`, `scenario-engine/`, `procurement-agent/`, `spr-agent/`, `coordinator/`, `shared/`. These exist for historical reference or testing but the active code is in `api.py`.
