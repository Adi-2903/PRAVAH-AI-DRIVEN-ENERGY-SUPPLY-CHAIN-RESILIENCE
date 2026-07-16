# Architectural Decisions & Rationale

This document serves as an Architectural Decision Log (ADL) to explain *why* Pravah is built the way it is.

## 1. The Monolith Pivot
**Context**: Pravah was originally designed as a multi-agent system with separate folders for `risk-agent`, `scenario-engine`, etc.
**Decision**: We merged all agents into a single `api.py` file.
**Rationale**: Vercel Serverless Functions have a strict 250MB limit and struggle with complex relative imports (e.g., trying to import `shared.schemas` from a sibling directory in a serverless environment). A single-file monolith guarantees successful deployment while keeping the conceptual boundaries of the agents intact via distinct functions and endpoints.

## 2. Removal of SciPy and Pandas
**Context**: Financial and data-science algorithms typically rely heavily on `scipy` (for optimization) and `pandas` (for data manipulation).
**Decision**: We removed these dependencies, rewriting the logic using raw Python and `numpy`.
**Rationale**: `scipy` and `pandas` are massive compiled binaries. Including them in `requirements.txt` instantly blows past Vercel's 250MB serverless limit. The SPR Optimizer's knapsack algorithm was rewritten as a greedy LP in numpy.

## 3. Determinism Over LLMs
**Context**: The Risk Engine needed to classify news events and assign severity.
**Decision**: We prioritized regex keyword heuristics over LLM calls (though Gemini is supported as an option).
**Rationale**: LLMs introduce latency and unpredictability. For a system dictating national energy security, deterministic rules (e.g., if headline contains "missile", severity = critical) ensure stable, testable, and instantly responsive UI behavior.

## 4. The "Thick" Coordinator Response
**Context**: The frontend needed data from all 4 agents to render the dashboard.
**Decision**: The `/final-recommendation` endpoint aggregates the full payloads of every agent (Scenario, Risk, Procurement, SPR) into a single massive JSON response.
**Rationale**: This prevents the frontend from having to orchestrate 4 separate asynchronous fetch calls and manage complex waterfall loading states. The frontend hits one endpoint and hydrates 80% of its UI simultaneously.
