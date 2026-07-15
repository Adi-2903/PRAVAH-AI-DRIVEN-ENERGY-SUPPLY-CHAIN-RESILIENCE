# Pravah — Production Readiness Report

_Status as verified end-to-end. Every claim below is backed by an executable check
(pytest, `next build`, or a headless-browser drive of the running app)._

Pravah is an **anticipatory intelligence dashboard for India's crude-oil supply
chain**: a stateless FastAPI analytics backend (`api.py`) + a Next.js 15 frontend.
It is an **illustrative prototype** (labelled as such throughout the UI) — the risk
scoring runs real math over bundled deterministic fixtures (with an optional live
GDELT source), and the scenario / SPR / procurement engines are genuine Monte-Carlo,
linear-programming and graph-optimisation computations.

---

## 1. What changed in this pass (frontend truthfulness + full wiring)

The backend already computed real data for every view, but several frontend screens
rendered **hardcoded mock values that never called the backend**. Those are now wired
to live endpoints, and fabricated telemetry with no backing source was removed.

| Screen | Before | After |
|---|---|---|
| **Command Center** | 100% static mock: hardcoded KPIs (`74/100`, `+12 pts vs 7-day avg`), a fabricated "Strategic Reserves Status" panel (VLCC 92%, refinery slack 85%, pipeline 71%…), a static "Live Signals" feed with invented IMO numbers/OFAC names, a 5th/6th corridor the backend never scores | Live `GET /corridors` + `GET /market`; composite index throughput-weighted from real scores; feed built from the **real scoring events**; fabricated readiness panel replaced by a **derived** Composite Risk Breakdown; KPIs labelled `LIVE` vs `REF` |
| **Risk Intelligence** | 100% static mock (5 corridors incl. Suez/Malacca; hand-authored "live" feed) | Live `GET /corridors`; cards, reasoning trails, signal weights and the event feed all from the backend; fabricated trend arrows removed (no historical baseline exists) |
| **App shell** (ticker, sidebar index, alert bar) | Hardcoded ticker with fake `%` deltas; `74/100`; `ALERT LEVEL 3` | Ticker from `GET /market` (no invented deltas); composite index + alert level derived live from `GET /corridors` |
| **Citizen View** | Gauge/summary live, but a hardcoded KPI row (`$84.12 +6.1% 24h`, `88%`, `$137B`) and a mock-fed map | Gauge = live national composite; map driven by live corridor scores; Brent from `GET /market`; reference figures labelled `REF` with sources (PPAC/ISPRL) |
| **Strategic Reserves** | Real LP solver but fed **synthetic** `Math.sin` risk/price inputs | Real risk from `GET /corridors` + real median price path from `POST /simulate`, then `POST /spr-schedule`; corridor selector added |
| **Scenario Modeller** | Already live (`/simulate`, `/data-status`) | Unchanged |
| **Procurement** | Already live (`/recommend`, `/market`) | Unchanged |

**Truthfulness standard applied:** every number shown is either (a) computed live by
the backend, (b) a clearly-labelled published reference figure with its source, or
(c) a user input/assumption. No fabricated live feeds, trend arrows, confidence
scores, or operational counters remain. The offline fallback (bundled sample data) is
always badged **"Offline (sample)"** so it is never mistaken for live data.

---

## 2. Architectural determinations (auth / database / containers)

Some generic "production" checklist items do not map onto this product's actual
architecture. Rather than bolt on fake features, the honest scope is documented here.

### Authentication & Authorization — **not a feature of this product**
Pravah is a **read-only public intelligence dashboard** (Ministry of Petroleum &
Natural Gas context). Evidence:
- The frontend has **no** login/signup UI, **no** session handling, and **no**
  protected routes — it loads straight into the dashboard.
- The Citizen/Analyst/Policy "tier switcher" is a **view preference**, not access
  control; the UI states plainly: _"Auth is stubbed for prototype demo. No real
  login required."_ (honest, not misleading).
- `api.py` has no auth middleware, user model, or credentials.

There is nothing to secure and nothing that claims to be secured, so "auth end-to-end"
is **N/A by design**. (An earlier architecture in `shared/` had a Supabase auth shell;
the deployable monolith deliberately does not use it — see `DEPLOY.md`.)

### Database persistence — **not applicable (stateless service)**
`api.py` is **pure compute**: every endpoint is a deterministic function of its
request (risk scoring, Monte-Carlo simulation, LP schedule, graph optimisation). There
is no user data, no mutable state, and nothing to persist between requests. Restarting
the service loses nothing. "DB persistence" is therefore **N/A by design**.

### Docker / containers — **not part of the architecture (removed)**
The production architecture is **native**: the backend deploys to **Render** as a
Python web service (`render.yaml`: `runtime: python`, `pip install`, `uvicorn api:app`)
and the frontend to **Vercel** (`next build`). CI (`.github/workflows/ci.yml`) is native
(`setup-python`/`setup-node`). Nothing in the deploy, run, or test path uses containers.

All Docker/Compose files were therefore **removed** (they were an optional add-on and
legacy microservice cruft, not required by any deployment or test). "Docker deployment"
is **N/A by design** — there is no container in this architecture to verify.

---

## 3. Evidence (all commands runnable from repo root)

**Backend contract tests — 17/17 pass** (`.venv/Scripts/python.exe -m pytest test_api.py`):
covers `/simulate`, `/spr-schedule`, `/recommend`, `/market`, `/graph`, `/risk-score`,
`/corridors`, `/final-recommendation`, each re-validated against an independent schema
oracle, plus real-math assertions (Hormuz scores critical, domestic low).

**Placeholder scan — clean:** no `TODO`/`FIXME`/`NotImplemented`/`placeholder` in
`api.py`; the only "mock" references are the intentional `/simulate/mock` &
`/spr-schedule/mock` fallback endpoints.

**Frontend `npm run build` — passes** with lint + type-check now enabled on every
build (`ignoreDuringBuilds: false`). The one opinionated perf rule
(`react-hooks/set-state-in-effect`, which flags idiomatic mount-time fetches) is a
warning; all correctness rules remain build-breaking.

**Headless-browser end-to-end drive — 31/31 assertions pass** (real Chrome renders
the app against the live backend). Confirmed:
- The browser issues live calls to **all seven** endpoints: `/corridors`, `/market`,
  `/final-recommendation`, `/simulate`, `/spr-schedule`, `/recommend`, `/data-status`.
- Live values render on every screen (composite `84/100`; corridors `100.0 / 88.7 /
  21.7 / 12.2`; real scoring events; live Brent from `/market`).
- Specific fabrications are **gone**: no `+12 pts vs 7-day avg`, no `VLCC Tanker
  Availability`, no invented IMO `9834521`, no invented OFAC entity names, no Malacca
  corridor, no `+6.1% 24h` Brent delta.

**User workflow executed:** Citizen View → "Go deeper" → Analyst tier → every module
tab (Command Center, Risk, Scenario, SPR, Procurement) → live data + Refresh — all
succeed; stopping the backend degrades to badged "Offline (sample)", never a blank.

---

## 4. Remaining blockers (external dependencies only)

1. **Live external data sources are optional and best-effort by design:** GDELT
   (`?live=true` on risk) and the FX rate feed have short timeouts and fall back to
   bundled data if unreachable. This is intentional resilience, not a defect.

No blockers remain that are resolvable from within this repository.
