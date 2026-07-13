# Stage 4 — Risk Agent tests

Tests for the `risk-agent/` microservice: the scoring layer, the LangGraph
pipeline, and the live `GET /health` + `POST /risk-score` endpoints.

## Files

| File | Layer | Network / DB |
|------|-------|--------------|
| `conftest.py` | path setup + a guard that blocks all DB writes | — |
| `test_unit_scoring.py` | pure functions: corridor map, severity, classifier, risk model | none |
| `test_pipeline.py` | full LangGraph pipeline, `use_live=False, persist=False` | none |
| `test_endpoint.py` | `main.app` via FastAPI `TestClient` (in-process) | none |
| `smoke_test_risk_agent.py` | **runnable script** hitting a real server over HTTP | live |

The pytest files are deterministic and offline — safe for CI. The smoke script
talks to a running server (and by default lets it fetch live GDELT), so it's the
demo-day / manual check.

## Prerequisites

```bash
pip install -r risk-agent/requirements.txt   # fastapi, uvicorn, langgraph, supabase, pydantic, requests, pytest, httpx
```

## Run the pytest suite (offline, no DB)

```bash
pytest "TESTING FILES/stage4" -v --tb=short
```

Nothing here writes to Supabase: `conftest.py` patches the Supabase client to
`None`, and the endpoint tests force the pipeline into `use_live=False,
persist=False`.

## Run the smoke script (live endpoints)

```bash
# auto-start the server, test it, shut it down
python "TESTING FILES/stage4/smoke_test_risk_agent.py" --start

# or against an already-running server
cd risk-agent && uvicorn main:app --port 8001    # (terminal 1)
python "TESTING FILES/stage4/smoke_test_risk_agent.py"   # (terminal 2)

# custom URL
python "TESTING FILES/stage4/smoke_test_risk_agent.py" --url http://localhost:8001
```

It prints ✅/❌ per check and exits non-zero if anything fails, so it works as a
CI gate too. It tolerates GDELT being rate-limited (the agent falls back to
bundled fixtures) — the contract must still validate either way.

## What is covered

- `/health` returns `{"status":"ok"}`.
- `/risk-score` returns a valid **frozen `RiskScoreResponse`** for all four
  corridors (score 0–100, confidence 0–1, valid `alert_level`, valid key-event
  severities).
- Validation: non-canonical / unknown corridor and missing fields → `422`.
- Scoring: baseline-only, clamping at 100, recency decay, alert thresholds,
  top-5 key-event ordering, word-boundary keyword matching.
- Pipeline determinism offline, `hormuz` > `cape`, naive/`None` `as_of` handling.
