# `shared/` — DB + Backend Foundation (Pravah Stage 2 & 3)

Owner: **Vraj**. This is the foundation every agent talks to: the database schema,
a minimal auth backend, the supply-chain knowledge graph, and the **frozen** JSON
contracts (Pydantic models) that all agents send/receive.

## Layout

```text
shared/
├── main.py                  # Stage 2b — minimal FastAPI shell (health + auth)
├── requirements.txt
├── db/
│   ├── schema.sql           # Stage 2a — all CREATE TABLE / index / RLS statements
│   ├── seed.py              # Stage 2a — seed countries, corridors, data_sources
│   ├── knowledge_graph.py   # Stage 3 — supply-chain graph (networkx)
│   └── migrations/          # future migrations
├── schemas/                 # Stage 3 — FROZEN Pydantic contracts (see "Schema Freeze")
│   ├── risk_score.py
│   ├── simulate.py
│   ├── recommend.py
│   └── spr_schedule.py
└── clients/                 # Stage 1 person's Live Data Spine (not owned here)
```

## Setup

```bash
pip install -r shared/requirements.txt
```

Add to `.env` at the repo root (see `.env.example` for the template):

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here
```

## Run each piece

| What | Command | Needs |
|------|---------|-------|
| Create tables | paste `db/schema.sql` into Supabase → SQL Editor | Supabase project |
| Seed lookups | `python shared/db/seed.py` | `.env` + tables created |
| Backend shell | `uvicorn shared.main:app --reload --port 8000` | `.env` |
| Health check | `GET http://localhost:8000/health` → `{"status":"ok"}` | shell running |
| Knowledge graph | `python shared/db/knowledge_graph.py` | `networkx` only |
| Schema import | `python -c "from shared.schemas.risk_score import RiskScoreResponse"` | `pydantic` (run from repo root) |

> Run `uvicorn` and the `shared.schemas` import **from the repo root** so the
> `shared` package resolves.

## Corridor naming — read before touching anything

`corridor.name` is **always lowercase**: `hormuz`, `redsea`, `cape`, `domestic`.
The exact same strings are used in three places and must never diverge:
- `corridors.name` in `db/schema.sql` / `db/seed.py`
- corridor node IDs in `db/knowledge_graph.py`
- the `Corridor` `Literal[...]` enum in `schemas/risk_score.py` and `schemas/simulate.py`

A case mismatch between the DB and the graph is a silent join failure.

## ⚠️ Schema Freeze

`shared/schemas/` is the contract every agent depends on:

| Schema | Produced by | Consumed by |
|--------|-------------|-------------|
| `risk_score.py`   | risk-agent        | coordinator, frontend |
| `simulate.py`     | scenario-engine   | coordinator, frontend |
| `recommend.py`    | procurement-agent | coordinator, frontend |
| `spr_schedule.py` | spr-agent         | coordinator, frontend |

Agents import these directly (`from shared.schemas.simulate import SimulateResponse`)
instead of retyping the spec. **Once frozen, do not change any field, type, or range
without team agreement** — a change here silently breaks every agent at once.

## Verification status

Live Supabase project **`pravah`** (`runewqeuvmcqqvfnqhzj`, region ap-south-1) is provisioned:

- ✅ All 12 tables created (via `schema.sql`), plus both indexes, `pgcrypto`, and the
  `user_views` RLS policies. RLS is **on** only for `user_views`; the public tables are
  readable by the anon key (Citizen view).
- ✅ Seed data loaded: 6 countries, 4 corridors (`cape, domestic, hormuz, redsea`),
  4 data_sources.
- ✅ Anon-key REST read of `corridors` returns 200.
- ✅ Supabase Auth signup + password login both return 200 (login yields an
  `access_token`). `mailer_autoconfirm` is enabled so new users can log in
  immediately — re-enable email confirmation before production.
- ✅ All `shared/**/*.py` byte-compile; `python shared/db/knowledge_graph.py` →
  `18 nodes, 29 edges`, `24` paths through Hormuz.
- ⏳ Importing `shared/schemas/*` and running `uvicorn shared.main:app` locally still
  need `pip install -r shared/requirements.txt`. On this machine the system Python's
  `ctypes`/`pip` are broken, so install deps in a fresh Python before running those two.
