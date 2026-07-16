# Future Roadmap & Extension Points

The current Pravah architecture successfully validates the core concepts of AI-driven supply chain resilience. To transition from a monolithic prototype to a highly scalable production system, the following architectural extensions should be considered:

## 1. Database Integration
**Current State**: Stateless. Configuration and graph data are hardcoded.
**Future State**: Integrate PostgreSQL (via SQLAlchemy) to store:
*   Dynamic Supply Chain Graph nodes (Supplier costs, new ports).
*   Historical Risk Scores for time-series trend analysis.
*   User Session data and Audit Logs for Policy Decisions.

## 2. Decoupling the Monolith
**Current State**: Single file `api.py`.
**Future State**: As the deployment target moves away from Vercel Serverless (e.g., to AWS ECS, Kubernetes, or Google Cloud Run), the strict 250MB size limit will disappear. The codebase should be refactored back into independent microservices (`risk-agent`, `scenario-engine`, etc.). The frontend `NEXT_PUBLIC_*` environment variables are already structured to support this split routing.

## 3. Re-introducing Data Science Libraries
**Current State**: Manual numpy LP optimization and random walks.
**Future State**: Once freed from serverless constraints, re-introduce `scipy` for more complex, multi-constraint optimizations (e.g., balancing SPR drawdown across *multiple* storage caverns simultaneously) and `pandas` for advanced time-series forecasting models (ARIMA, Prophet) instead of standard Geometric Brownian Motion.

## 4. Live Tracking Integration
**Current State**: Network traversal assumes static transit times (e.g., Hormuz to Vadinar = 9 days).
**Future State**: Integrate live AIS (Automatic Identification System) vessel tracking APIs to dynamically adjust transit times based on weather, port congestion, and actual ship speeds.
