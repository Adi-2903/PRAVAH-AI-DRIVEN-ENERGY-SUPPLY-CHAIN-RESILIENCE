# Stage 9 — Coordinator + Real Integration — Implementation Plan

**Goal (README):** *Build `coordinator/` to call all four agents and resolve conflicts into one final recommendation. Swap frontend mocks for real URLs. First day everything talks to everything.*

**Reality check (verified in code):** Stage 9 is **not** "just wire URLs." The frozen contracts drifted, so there is real reconciliation and hardening to do before things can talk to each other reliably. This plan makes that explicit and sequences it for a **production-ready** result, not a demo-only one.

---

## 0. The one thing to internalize first: the contracts already drifted

The Stage-3 promise was "freeze `shared/schemas/`, then integration is trivial." That did **not** hold. Verified state:

| Contract | `shared/schemas/*` (the "frozen" one) | What the agent **actually** imports/returns | Frontend type | Verdict |
|---|---|---|---|---|
| **risk-score** | `risk_score.py` — `reasoning_trail: list[str]`, `key_events{headline,severity,date}`, **no** `signals`, **no** `model` | `risk-agent` **uses `shared/schemas`** ✅ | mock has `reasoning_trail: string` + `signals[]` + `model` | ⚠️ frontend expects **more than the API returns** → adapter or enrich API |
| **simulate** | `simulate.py` | `scenario-engine` uses its **own `models.py`** (shape matches) | matches | ✅ aligned (but duplicated definition) |
| **recommend** | `recommend.py` — `blocked_corridors`, `cost_index`, `risk_score` | `procurement-agent` uses **own `models.py`** — `target_refinery`, `estimated_cost_usd_per_bbl`, `baseline`, `market_data` | matches the agent's model | ⚠️ **`shared/schemas/recommend.py` is stale/superseded** |
| **spr-schedule** | `spr_schedule.py` — `recommended_release_mbpd`, `start_date` | `spr-agent` uses **own `models.py`** — `DailySchedule[]`, savings | matches the agent's model | ⚠️ **`shared/schemas/spr_schedule.py` is stale/superseded** |

**Takeaway:** `shared/schemas/` is used by **only 1 of 4 agents**. The real contract for the other three lives in each agent's local `models.py`, and the frontend already matches those. Each contract exists in **2–3 copies** that have diverged. Fixing this is Phase 0 and everything else depends on it.

Other verified integration facts:
- `coordinator/main.py` is **empty** — the coordinator must be built from scratch.
- Every agent already has permissive CORS (`allow_origins=["*"]`) — fine for dev, **must be restricted for prod**.
- `docker-compose.yml` only enables `procurement-agent` (host `8003`); the rest are commented out. Ports there: risk `8001`, scenario `8002`, procurement `8003`, spr `8004`, coordinator `8005`.
- Frontend now reads service URLs from `NEXT_PUBLIC_*` (see `frontend/app/lib/api.ts`, added in Stage-8 hardening) with defaults matching those compose ports.

---

## 1. Target architecture

```
                 Browser (Next.js frontend)
        ┌──────────────┬─────────────────────────┐
        │ Citizen /    │ Analyst modules         │
        │ Command view │ (risk, sim, proc, spr)  │
        ▼              ▼                          ▼
  POST /final-recommendation        POST /risk-score, /simulate, …
        │              (drill-down calls straight to each agent)
        ▼
   ┌─────────────┐   fan-out (async, timeouts, retries, fallback)
   │ COORDINATOR │──┬─────────┬───────────┬─────────┐
   │  :8005      │  ▼         ▼           ▼         ▼
   └─────────────┘ risk    scenario   procurement  spr
                   :8001    :8002       :8003      :8004
        ▲                                   │
        └────────── shared contracts (one source of truth) ──────────┘
```

**Decision — who calls what:**
- **Citizen view + Command Center** call **`coordinator /final-recommendation`** → the blended headline (score + summary + top recommendation). One call, one story.
- **Analyst modules** (Risk Intelligence, Simulator, Procurement, SPR) call **their agent directly** for interactivity (sliders re-run one agent). They already do this — Stage 8 just fixed the URLs.
- **Every** browser call falls back to `mock-data.ts` on failure (never a blank screen).

**Two-tier URL config (critical, easy to get wrong):**
- **Server-side** (coordinator → agents, inside Docker): use service DNS, e.g. `http://risk-agent:8000`.
- **Browser-side** (frontend → coordinator/agents): must use **host-published ports or public URLs** (`http://127.0.0.1:8001`, or the deployed URL). A browser cannot resolve Docker service names.
- Both come from env, never hardcoded.

---

## 2. Restructure first (proper SWE codebase) — before any wiring

> Rationale: integrating on top of 3 diverged copies of each contract will reproduce the exact bugs found in Stage 8. Consolidate, then integrate.

**R1 — Single source of truth for contracts (highest priority).**
- Create `shared/contracts/` (Python package) holding the **canonical** pydantic models for all four endpoints + the new coordinator response. Seed them from each agent's **current local `models.py`** (those are what actually runs), not from the stale `shared/schemas/`.
- Every agent imports its request/response models from `shared.contracts` and deletes its local duplicate. `risk-agent` already imports from shared — migrate it too.
- Delete or rewrite the stale `shared/schemas/recommend.py` & `spr_schedule.py`.
- Generate **TypeScript types for the frontend** from the same source, so drift becomes impossible:
  - Emit OpenAPI from each FastAPI app (`app.openapi()`), then `openapi-typescript` → `frontend/app/lib/contracts.ts`.
  - Add a `make contracts` target + a CI check that fails if generated types are stale.
- **Definition of done:** exactly one definition per contract; frontend types are generated, not hand-written.

**R2 — Config via environment, per service.**
- Add `pydantic-settings` `Settings` to each service (ports, upstream URLs, API keys, `DEMO_MODE`, `ALLOWED_ORIGINS`). No literals in code.
- `.env.example` per service (root `.env` already holds shared/Supabase/EIA keys); document server-side vs browser-side URLs.

**R3 — Repo hygiene.**
- Fix the **dual lockfile** (`hormuz/package-lock.json` + `frontend/package-lock.json`) — remove the stray root one or make the frontend a real workspace member. (Frontend already sets `outputFileTracingRoot` as a stopgap.)
- Standardize a `GET /health` (liveness) + `GET /ready` (readiness — deps reachable) on every service.
- Structured JSON logging + a request-id middleware, shared via `shared/`.
- A root `Makefile` / `docker compose` target to build+run the whole system with one command.

**R4 — Frontend contract module.** Route every fetch through `app/lib/api.ts` (done) + the generated `contracts.ts`; add adapters only where the API genuinely returns a different shape (risk — see §4).

---

## 3. Build the Coordinator (core deliverable)

**Folder layout**
```
coordinator/
├── main.py                 # FastAPI app: POST /final-recommendation, /health, /ready, /final-recommendation/mock
├── config.py               # pydantic-settings: agent URLs, timeouts, DEMO_MODE, ALLOWED_ORIGINS
├── clients.py              # typed async httpx client per agent (call + timeout + retry + fallback)
├── resolver.py             # conflict-resolution logic (cost vs security → one recommendation)
├── models.py               # imports from shared.contracts; defines FinalRecommendationResponse
├── snapshots/golden.json   # cached full response for offline/demo mode
├── requirements.txt
├── Dockerfile
└── tests/
    ├── test_resolver.py    # unit: conflict resolution policies
    └── test_orchestration.py  # httpx-mocked agents: happy path + partial failure
```

**Endpoint:** `POST /final-recommendation`
- **Request:** `{ corridor, as_of, scenario_knobs? }` (scenario_knobs optional: shock_duration_days, current_brent_usd, elasticity overrides).
- **Response (`FinalRecommendationResponse`):**
  ```
  {
    summary: str,                     # plain-English headline (the Citizen line)
    headline_risk: RiskScoreResponse, # from risk agent
    scenario: SimulateResponse,       # from scenario agent
    procurement: RecommendResponse,   # from procurement agent
    spr: SprScheduleResponse,         # from spr agent
    resolution: {                     # the coordinator's own reasoning
       chosen_action: str,
       tradeoff: str,                 # e.g. "accepted +$10/bbl cost for -58% corridor exposure"
       confidence: float,
       reasoning_trail: list[str],
    },
    degraded: bool,                   # true if any agent fell back
    agents_status: {risk: "live|fallback|error", ...},
    computed_at: datetime,
  }
  ```

**Orchestration flow (async, with a real dependency graph):**
```python
# pseudo — coordinator/main.py
risk = await clients.risk_score(corridor, as_of)            # 1. risk first (others depend on it)
scenario_req = build_scenario_req(risk, knobs)
scenario, procurement, spr = await asyncio.gather(         # 2. fan out the independent calls
    clients.simulate(scenario_req),
    clients.recommend(blocked_corridors=[corridor], ...),
    clients.spr_schedule(supply_gap_from(scenario_req)),
    return_exceptions=True,                                 # partial failure never 500s the whole thing
)
resolution = resolver.resolve(risk, scenario, procurement, spr)  # 3. cost-vs-security policy
return assemble(risk, scenario, procurement, spr, resolution)
```

**Resilience (production requirements, not optional):**
- Per-agent **timeout** (e.g. 8 s) via httpx; **retry** once on connect error; **circuit-break** after N consecutive failures (skip + mark degraded).
- `asyncio.gather(..., return_exceptions=True)` so one dead agent yields a partial result with `degraded=true` and `agents_status`, not a full failure.
- Each client falls back to that agent's `/mock` (or `snapshots/golden.json`) when unreachable, so the coordinator always returns something coherent.

**Conflict resolution (`resolver.py`) — make the policy explicit:**
- Inputs: corridor risk (security), scenario price path (economic), procurement options (cost/transit/risk), SPR schedule (buffer).
- Policy (documented + tunable weights): pick the procurement option and SPR posture that **minimize blended exposure** = `w_security·risk + w_cost·price + w_continuity·transit`, subject to keeping SPR above its safety floor. Emit the tradeoff in plain English + a reasoning trail (this is the product's whole selling point — "advisory layer, not a black box").

---

## 4. Frontend: swap mocks → real (with fallback)

- **Plumbing is done** (`api.ts`, env URLs, fixed ports, procurement fallback). Remaining work is per-view wiring:
- **Simulator / SPR / Procurement:** already call real endpoints via `api.ts`; verify against the running agents (correct ports) and keep the mock fallback.
- **Risk adapter (the one real shape gap):** the real `/risk-score` returns `reasoning_trail: list[str]` and **no** `signals`/`model`. Two clean options — **pick one, don't fabricate**:
  - **(A, recommended) enrich `risk-agent`** to also return `signals[]` + `model` (it already computes signal weights internally for the LangGraph pipeline) → frontend consumes directly.
  - **(B) trim the frontend** to render only what the API provides: join `reasoning_trail` for the text, derive the signal chips from `key_events`, drop the fake `model` line.
- **Citizen view + Command Center:** call `coordinator /final-recommendation`; use `summary` + `headline_risk.score` for the hero, `resolution` for the "what we recommend" line. Fall back to `MOCK_COORDINATOR`.
- **Risk Intelligence multi-corridor view:** needs a **new** endpoint — there is no "all corridors" API today. Add `coordinator /corridors` (or `risk /corridors`) that returns `RiskScoreResponse[]`; until then loop `/risk-score` per corridor or keep the mock. **Do not ship this as real if the endpoint doesn't exist — label it.**
- Wire `data-freshness` to the **real** `computed_at`, not the mock timestamp.
- Delete/relabel the remaining fabricated literals (ticker, alert-level chrome, SPR offline "savings") so nothing static masquerades as live.

---

## 5. Production hardening (the "not just a demo" checklist)

- **CORS:** replace `allow_origins=["*"]` with an env-driven allow-list (`ALLOWED_ORIGINS`) on every service + coordinator.
- **Timeouts / retries / circuit-breaking** on all cross-service calls (see §3).
- **Uniform error contract:** return `{error, detail, request_id}` (RFC-7807-ish) so the frontend shows meaningful messages instead of "Backend error".
- **Health/readiness** on every service + Docker `healthcheck` + compose `depends_on: condition: service_healthy`.
- **Observability:** structured logs, request-id propagation coordinator→agents, basic latency metrics (optionally OpenTelemetry).
- **Secrets/config:** never commit `.env`; validate required env on boot (fail fast).
- **Auth:** `shared/main.py` already exposes `/auth/signup` + `/auth/login` (Supabase). Wire real login for Analyst/Policy tiers (frontend auth is currently stubbed); gate the coordinator/analyst endpoints if required.
- **Demo mode / golden snapshot (Stage 12 prep):** a `DEMO_MODE` env + `/mock` on every service + `coordinator/snapshots/golden.json`, so the whole system runs from a frozen snapshot with visible "as of" timestamps if the venue internet dies.

---

## 6. docker-compose / deploy

- Uncomment **all** services; add `coordinator` (`8005:8000`); align every port with `api.ts` defaults; add `healthcheck` + `depends_on`.
- Coordinator env uses **service-DNS** URLs (`http://risk-agent:8000`); frontend env uses **published/public** URLs.
- One-command bring-up: `docker compose up --build`.
- Deploy split (per README): frontend → Vercel (env = public service URLs), services → Railway/containers, DB → Supabase.

---

## 7. Testing & verification

- **Contract tests:** for each agent, assert its live response validates against `shared.contracts` (pytest); optionally `schemathesis` against the OpenAPI.
- **Coordinator unit tests:** `resolver.py` policies (cost-vs-security edge cases); `test_orchestration.py` with **httpx-mocked** agents covering happy path, one-agent-down (degraded), all-down (full fallback).
- **E2E:** `docker compose up`; POST a scenario to `/final-recommendation`; assert a coherent blended result; kill one agent and re-assert `degraded=true`.
- **Frontend:** keep the `next build` gate; add render-smoke tests that every view mounts both backend-up and backend-down.
- **Latency/chaos:** measure coordinator fan-out latency; verify timeouts trip correctly when an agent is slow.

---

## 8. Phased execution (ordered; each phase independently shippable)

| Phase | Work | Owner(s) | Done when |
|---|---|---|---|
| **0 — Contract freeze** (½ day) | Audit all 4 contracts; create `shared/contracts/`; generate `frontend/app/lib/contracts.ts`; team re-agrees the shapes | whole team, led by shared owner (Vraj) | one definition per contract; TS generated in CI |
| **1 — Restructure** (1 day) | Agents import from `shared.contracts`; per-service config; health/ready; logging; compose fixed | each agent owner | all agents build on shared contracts; `docker compose up` starts everything healthy |
| **2 — Coordinator** (1½ days) | `clients.py`, `resolver.py`, `/final-recommendation`, resilience, tests, golden snapshot | coordinator owner (Vraj / Member with bandwidth) | orchestration + partial-failure tests green |
| **3 — Frontend integration** (1 day) | Verify agent wiring; risk adapter (§4); Citizen/Command → coordinator; fallback; real `computed_at` | Member 4 (Jenil) | every view runs live with mock fallback; no fabricated "live" values |
| **4 — Hardening** (½ day) | CORS allow-list, error contract, timeouts, secrets, auth wiring | whole team | prod checklist (§9) passes |
| **5 — E2E + demo** (½ day) | Full-scenario E2E; golden-snapshot offline rehearsal | whole team | works end-to-end **and** fully offline |

Maps onto the README team split: Member 1 risk, Member 2 scenario, Member 3 procurement/spr, Member 4 frontend, shared/coordinator to whoever owns `shared/` (Vraj).

---

## 9. Definition of Done (production-ready)

- [ ] Exactly one definition per contract (`shared/contracts`), frontend TS types generated from it, CI fails on drift.
- [ ] `coordinator /final-recommendation` returns a blended result with an explicit reasoning trail and degrades gracefully (partial results + `agents_status`).
- [ ] Every service: env-driven config, restricted CORS, health+ready, structured errors, timeouts on outbound calls.
- [ ] Frontend runs against live services **and** falls back to mock on failure; no static value is presented as "live"; freshness reflects real `computed_at`.
- [ ] `docker compose up` brings up all 6 services healthy; a scenario flows end-to-end; killing one agent still yields a coherent answer.
- [ ] Golden-snapshot demo mode works with the internet off.
- [ ] Tests: contract + coordinator unit + one E2E, all green in CI.

---

## 10. Top risks & mitigations

| Risk | Mitigation |
|---|---|
| Contract drift recurs (the Stage-8/9 root cause) | Single `shared/contracts` + generated TS + CI drift check |
| Coordinator latency (4 agents serially) | Dependency-aware fan-out (`asyncio.gather`) + timeouts + cache |
| Browser can't reach Docker service names | Documented two-tier URL config (server-DNS vs published) |
| One agent down kills the demo | `return_exceptions=True` + per-agent `/mock` fallback + `degraded` flag |
| Risk API returns less than the UI shows | Decide **enrich vs trim** in Phase 0, not at integration time |
| Internet dies at the venue | `DEMO_MODE` + golden snapshot on every service |

---
*Prepared for Stage 9 kickoff. Companion to `frontend/STAGE8_REVIEW.md`. Contract findings verified against the current agent source on branch `fix/stage8-frontend-integration`.*
