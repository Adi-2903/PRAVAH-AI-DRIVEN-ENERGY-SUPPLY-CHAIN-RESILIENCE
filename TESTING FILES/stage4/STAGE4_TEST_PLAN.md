# Stage 4 (Risk Agent) — Audit & Test Plan

**Target:** `risk-agent/` — FastAPI microservice; scoring pipeline is a LangGraph
`StateGraph` (`ingest → classify → map_corridor → severity → score → store`).
**Endpoints:** `GET /health`, `POST /risk-score` (body `RiskScoreRequest`, returns
the frozen `RiskScoreResponse`).
**Branch:** `vraj`.

---

## 1. Objective

Prove the risk agent (a) always returns a response that satisfies the **frozen
`shared/schemas/risk_score.py` contract**, (b) rejects bad input, (c) scores
sensibly and deterministically, and (d) degrades gracefully when the live data
source or the database is unavailable — without ever writing test data to the
shared Supabase project.

## 2. Audit summary

Reviewed file-by-file (scoring math, pipeline state, ingestion, storage,
endpoint) plus an independent read-only audit pass. Findings below were each
verified against the code; the real ones were **fixed with regression tests**.

| # | Sev | Finding | Status |
|---|-----|---------|--------|
| H1 | High | `store.py` built the Supabase client *outside* the try/except, so a malformed `SUPABASE_URL` (or missing `supabase` pkg) would 500 every `/risk-score` even though scoring succeeded | **Fixed** — client construction moved inside `try`; `node_store` also guarded. Regression: `test_store_resilience.py` |
| H2 | High | No endpoint/integration tests existed; the HTTP layer, `KeyEvent` assembly and `response_model` validation were untested | **Fixed** — added `test_endpoint.py` (TestClient) + `smoke_test_risk_agent.py` |
| M1 | Med | `"suez"` (redsea) was matched before `cape`, so "take the Cape … to avoid Suez" headlines misrouted and were dropped from cape (score 16.7 vs correct 21.7) | **Fixed** — cape checked before redsea. Regression: `test_cape_route_avoid_suez_maps_to_cape` |
| M2 | Med | A mildly-cooperative Goldstein value suppressed explicit HIGH keywords (`sanctions`+goldstein `+0.5` → `low`) | **Fixed** — severity now takes the strongest of {critical-kw, high-kw, Goldstein}. Regression added |
| M3 | Med | Relevance filter dropped geopolitical events lacking an oil/shipping keyword; `"port"` missed the plural `"ports"` | **Fixed** — `ports?` + escalation terms (tension/escalat/conflict/blockade/closure/…). Regression added |
| L2 | Low | Naive/aware datetime subtraction in the recency math would crash on a future naive source | **Fixed** — `_aware()` coercion in `compute_risk`. Regression added |
| L3 | Low | An out-of-enum `severity` could reach `KeyEvent` and 500 | **Fixed** — `_norm_severity()` degrades to `low`. Regression added |
| L5 | Low | CORS `allow_origins=["*"]` with `allow_credentials=True` (invalid combo) | **Fixed** — `allow_credentials=False` |
| L1 | Low | GDELT country→corridor map is largely dead for live data (name/format mismatch); headline keywords dominate anyway | **Deferred** — low value; noted |
| L4 | Low | `/risk-score` calls GDELT synchronously (≤15 s) and, if Gemini is enabled, one call per event — unbounded latency | **Deferred** — add timeout/caching before prod |

**Verdict:** the contract holds on every corridor, input validation works, and
both the live source and the DB now fail safe. No High/Medium issues outstanding.

## 3. Test strategy — four layers

| Layer | File | Runs | Purpose |
|-------|------|------|---------|
| Unit | `test_unit_scoring.py` | offline | corridor map, severity, relevance classifier, risk-model bounds/clamp/recency/ordering |
| Pipeline | `test_pipeline.py` | offline | full LangGraph run per corridor; determinism; `hormuz > cape`; naive/`None` `as_of` |
| Endpoint | `test_endpoint.py` | in-process `TestClient` | routing, request parsing, response serialization, `422` validation, contract round-trip |
| Smoke | `smoke_test_risk_agent.py` | live HTTP | real server end-to-end; ✅/❌ + non-zero exit; demo/CI gate |

**Isolation:** unit/pipeline/endpoint are network-free and DB-free (`conftest.py`
patches the Supabase client to `None`; endpoint tests force `use_live=False,
persist=False`). The smoke script is the only layer that touches the network.

## 4. Test matrix (what's asserted)

**Contract / endpoint**
- `/health` → `200 {"status":"ok"}`.
- `/risk-score` → `200` and a valid `RiskScoreResponse` for `hormuz, redsea, cape, domestic`.
- Response round-trips through `RiskScoreResponse.model_validate(...)`.
- `422` for uppercase `HORMUZ`, unknown `suez`, missing `corridor`, missing `as_of`, empty body.

**Scoring**
- `score` ∈ [0,100], `confidence` ∈ [0,1], `alert_level` ∈ {low,elevated,high,critical} for all corridors.
- Baseline-only (no events) → corridor baseline; clamp at 100 under event flood.
- Recency decay boundaries (≤7d = 1.0, ≥30d = 0.2, mid-range interpolated).
- Alert thresholds inclusive at 30/55/75; top-5 key events, most-severe first.
- Word boundaries: `war`≠`warship`, `oil`≠`boil`, `port`≠`important`, `aden`≠`garden`.

**Resilience**
- Pipeline deterministic with `use_live=False`.
- GDELT down / rate-limited → falls back to fixtures, contract still valid (smoke).
- No test writes to Supabase (guarded).

## 5. How to run

```bash
pip install -r risk-agent/requirements.txt

# offline suite (CI-safe)
pytest "TESTING FILES/stage4" -v --tb=short

# live end-to-end
python "TESTING FILES/stage4/smoke_test_risk_agent.py" --start
```

## 6. Current result

- `pytest "TESTING FILES/stage4"` → **44 passed** (incl. 7 regression tests for the audit fixes).
- `risk-agent/tests` (author suite) → **19 passed**.
- `smoke_test_risk_agent.py --start` → **16/16 checks passed** (hormuz 100/critical,
  redsea ~89/critical, cape 21.7/low, domestic ~28/low; live GDELT contributed
  this run, falls back to fixtures when rate-limited).

## 7. Not covered yet (future work)

- Mocked **Gemini classifier** path (set `GEMINI_API_KEY`, stub the SDK).
- A **live GDELT** contract test (opt-in / network-gated; flaky by nature).
- A **real DB integration** test writing to a throwaway/test Supabase project.
- **Performance / latency** budget for `/risk-score` under live GDELT (audit L4).
- Wiring the real EIA/AIS/OFAC sources once `shared/clients/` exists.
