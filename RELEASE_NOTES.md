# Release Notes: Pravah v1.0.0

**Pravah v1.0.0** is the first stable production release. It provides an AI-driven energy supply chain resilience platform, utilizing multi-agent orchestration to assess geopolitical risks, simulate price shocks, and optimize national strategic petroleum reserves.

## Features
- **Multi-Agent Orchestration:** Four dedicated AI agents (Risk, Scenario, Procurement, SPR) coordinated seamlessly into a single holistic advisory output.
- **Digital Twin Dashboard:** A comprehensive Next.js frontend with unified *Citizen*, *Analyst*, and *Policy* views.
- **Live Data Ingestion:** Automated data pipelines ingesting GDELT (news), EIA (prices), AIS (shipping), and OFAC (sanctions).
- **Graceful Offline Mode:** Ships with built-in mock endpoints ensuring the dashboard functions seamlessly even if upstream data APIs are unavailable.
- **Verifiable Reasoning Trails:** Every agent recommendation is backed by a transparent audit trail of calculations and LLM reasoning.

## Architecture
Pravah v1.0.0 utilizes a **Stateless Serverless Monolith** architecture:
- Instead of independent microservices, all four agents and the coordinator are unified into a single `api.py` FastAPI monolith.
- This design vastly simplifies deployment complexity and reduces cold-start latency, easily fitting within standard serverless limits (70MB total bundle size).
- All inter-agent communication happens via heavily enforced Pydantic schemas housed in `shared/contracts/`.

## Deployment
- **Target Platform:** Vercel (Frontend & Backend unified project).
- **Backend Routing:** Next.js rewrites `/api/*` to the Python serverless function `frontend/api/index.py`.
- **Zero-Config Origin:** Since both run on the exact same domain, there are no CORS requirements and no environment variables needed to wire the frontend to the backend.

## Technologies
- **Frontend:** Next.js 15, React, TypeScript, TailwindCSS, shadcn/ui, Mapbox, Recharts.
- **Backend:** Python 3.12, FastAPI, Pydantic.
- **AI/ML:** LangGraph, Google Gemini 2.5 Flash, SciPy (for SPR linear optimization), NetworkX (knowledge graph).

## Known Limitations
- The Vercel Hobby tier imposes a strict 60-second timeout. Extremely complex LLM reasoning queries (e.g. chaining multiple live GDELT pulls) can occasionally approach this limit.
- Real-time AIS tracking relies on the free tier of `aisstream.io`, which does not guarantee 100% global coverage.
- The UI relies heavily on Mapbox GL; without a valid Mapbox token, the map layer will revert to a blank canvas placeholder.

## Future Roadmap (v1.1.0 and beyond)
- **Database Integration:** Re-introduce Supabase for long-term telemetry, user authentication, and saving simulation scenarios.
- **Websockets / Streaming:** Transition agent outputs to Server-Sent Events (SSE) so users can watch reasoning trails generate token-by-token.
- **Custom Knowledge Graphs:** Allow users to define their own custom supply corridors and refinery nodes via the frontend.
- **Multi-Cloud Support:** Provide a standalone Docker image and Kubernetes Helm chart for enterprise/on-prem deployments.
