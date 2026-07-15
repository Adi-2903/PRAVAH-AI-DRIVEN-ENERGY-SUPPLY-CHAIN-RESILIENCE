# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-15

### Added
- **Core Architecture:** Unified Python Monolith API deployed via Vercel Serverless Functions.
- **Frontend App:** Next.js 15 application with App Router, Shadcn/UI, and interactive Mapbox visualizer.
- **Risk Agent:** Integrates live GDELT data to classify and score geopolitical risks affecting shipping corridors.
- **Scenario Engine:** Monte Carlo simulation for crude oil price forecasting based on EIA historical benchmarks.
- **Procurement Agent:** Dynamic routing algorithm to determine optimal refiner supply adjustments using NetworkX.
- **SPR Agent:** Strategic Petroleum Reserve linear optimization scheduler to offset supply shocks.
- **Coordinator:** Master orchestration layer to synthesize agent outputs into a unified `Citizen View` and `Analyst View`.
- **Data Spines:** Robust API wrappers for EIA, GDELT, AIS, and OFAC.
- **Offline Mode:** Graceful mock-data fallbacks for seamless demonstrations without live API keys.

### Changed
- Refactored independent microservices into a single stateless `api.py` monolith to fit Vercel hobby-tier constraints.
- Upgraded UI from prototype to production-ready design system.
- Standardized `shared/contracts/` to enforce strict agent-to-agent communication via Pydantic schemas.

### Removed
- Deprecated Docker / `docker-compose.yml` orchestrations to favor simplified serverless deployment.
- Removed legacy Render Blueprint deployments (`render.yaml`, `runtime.txt`).
- Purged all superseded `STAGE_*` architectural planning documents.
