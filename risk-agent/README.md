# risk-agent — Pravah Stage 4

Scores geopolitical & logistics risk for a shipping corridor and returns an
explainable reasoning trail. FastAPI microservice; the scoring pipeline is a
LangGraph `StateGraph`.

```
ingest → classify → map_corridor → severity → score → store
```

## Contract

`POST /risk-score` — body is the frozen `RiskScoreRequest`, response is the
frozen `RiskScoreResponse` (both from `shared/schemas/risk_score.py`).

```jsonc
// request
{ "corridor": "hormuz", "as_of": "2026-07-11T00:00:00Z" }

// response (shape)
{
  "corridor": "hormuz",
  "score": 88.0,                 // 0–100
  "confidence": 0.72,            // 0–1
  "alert_level": "critical",     // low | elevated | high | critical
  "reasoning_trail": ["Baseline risk for 'hormuz' corridor = 60/100.", "..."],
  "key_events": [{ "headline": "...", "severity": "critical", "date": "..." }],
  "computed_at": "...",
  "data_sources": ["fixtures", "gdelt"]
}
```

`GET /health` → `{"status": "ok"}`.

## Run

```bash
pip install -r risk-agent/requirements.txt
cd risk-agent
uvicorn main:app --reload --port 8001
# POST http://localhost:8001/risk-score  with a RiskScoreRequest body
```

## How it works

| Stage | Module | Notes |
|-------|--------|-------|
| ingest | `ingestion/sources.py` | bundled fixtures **+** live keyless GDELT DOC API; EIA/AIS/OFAC stubbed until `shared/clients/` lands |
| classify | `scoring/classify.py` | heuristic; auto-uses **Gemini 2.5 Flash** if `GEMINI_API_KEY` is set |
| map_corridor | `scoring/corridor_map.py` | headline keywords + country → hormuz / redsea / cape / domestic |
| severity | `scoring/severity.py` | Goldstein scale, else keywords → low / medium / high / critical |
| score | `scoring/risk_model.py` | baseline + recency-weighted event pressure + conflict adjustment, clamped 0–100 |
| store | `store.py` | writes `risk_events` + `risk_scores` in Supabase (no-ops without creds) |

## Test (standalone, no network)

```bash
cd risk-agent
pytest -q
```

Tests run fixtures-only (`use_live=False`, `persist=False`) and assert the
output validates against the frozen `RiskScoreResponse`.

## Notes

- **Corridors are always lowercase** — `hormuz`, `redsea`, `cape`, `domestic`.
- The Gemini classifier is optional: `pip install google-generativeai` and set
  `GEMINI_API_KEY`. Without it the heuristic classifier is used.
- Persistence uses `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` from the repo-root
  `.env`; it is a side effect and never blocks the API response.
