================================================================================
PRAVAH: AI-DRIVEN ENERGY SUPPLY CHAIN RESILIENCE
BUILD PLAN
================================================================================
Theme: Supply Chain Intelligence / Energy Security / Geopolitical Risk

Think of this as an operating system for India's energy supply chain — not
a single chatbot, but a set of independent AI agents coordinated by one
Coordinator Agent, sitting on top of real, live data feeds, wrapped in a
product that a non-technical person can actually use.

Everyone shares Stages 1-3. From Stage 4 onward, the codebase splits into
separate folders / microservices, one per person, each with its own
dependencies, its own tests, and a fixed JSON contract for talking to
everyone else. Nobody edits another person's folder. Integration is just
wiring HTTP calls together, not merging code.

================================================================================
1. LIVE DATA SOURCES
================================================================================

A. GLOBAL OIL PRICES & SUPPLY DATA
   Source: EIA (U.S. Energy Information Administration) Open Data API v2
   URL:    https://api.eia.gov  (free API key at eia.gov/opendata)
   Gives:  Brent/WTI spot prices, crude imports by country, petroleum
           product prices, refinery utilization. Free, RESTful JSON.

B. GEOPOLITICAL NEWS / EVENT SIGNALS
   Source: GDELT Project (news + event database, updated every 15 min)
   URL:    https://www.gdeltproject.org/
   Gives:  Global news stream, event codes, tone/sentiment, geo-tagging.

C. SHIP / TANKER TRACKING (AIS) — Hormuz, Bab-el-Mandeb, Red Sea
   Primary: aisstream.io — free real-time AIS over WebSocket, no card
            required, filterable by bounding box.
   Backup:  AISHub — free secondary feed.

D. SANCTIONS DATA
   Source: OFAC SDN list — https://sanctionslist.ofac.treas.gov
   Public CSV/XML, free, no scraping needed.

E. INDIA-SPECIFIC DATA (imports, refineries, SPR levels)
   Source: PPAC (Petroleum Planning & Analysis Cell) and Ministry of
           Petroleum & Natural Gas — published as PDFs/HTML, not a clean
           API. One narrow scheduled scraper (weekly), never called live
           during a demo, with a manual CSV last-known-good fallback.

F. RELIABILITY RULE
   Every live external call has a cached fallback with a visible
   "data as of [timestamp]" label. Connectivity loss degrades to last
   synced state, never a blank screen.

================================================================================
2. REPOSITORY / FOLDER STRUCTURE
================================================================================

pravah/
├── README.md
├── docker-compose.yml                 (spins up all services together)
│
├── shared/                            (owned by whoever does Stage 1-3,
│                                        frozen once Stage 4 begins)
│   ├── schemas/                       JSON/pydantic contracts — the
│   │                                  "API menu" every agent must follow
│   ├── db/                            Supabase schema + migrations
│   └── clients/                       ready-made wrappers for EIA, GDELT,
│                                      aisstream.io, OFAC, PPAC-cache
│
├── risk-agent/                        MEMBER 1 — own folder, own repo life
│   ├── ingestion/
│   ├── scoring/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py                        FastAPI service -> exposes
│                                       POST /risk-score
│
├── scenario-engine/                   MEMBER 2
│   ├── models/
│   ├── simulations/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py                        exposes POST /simulate
│
├── procurement-agent/                 MEMBER 3
│   ├── ranking/
│   ├── knowledge_graph/               (NetworkX graph lives here)
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py                        exposes POST /recommend
│
├── spr-agent/                         MEMBER 3 or 4 (pick based on load)
│   ├── optimization/                  SciPy linear programming
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py                        exposes POST /spr-schedule
│
├── coordinator/                       built LAST, Stage 9 — nobody
│   │                                  touches this until other agents
│   │                                  are already returning real output
│   ├── resolver/
│   └── main.py                        calls all four agents above,
│                                       exposes POST /final-recommendation
│
├── ppac-scraper/                      independent cron job, no
│   ├── scraper.py                     dependency on any agent
│   └── fallback_snapshot.csv
│
└── frontend/                          MEMBER 4
    ├── app/(citizen)/
    ├── app/(analyst)/
    ├── app/(policy)/
    ├── components/
    └── lib/api/                       thin client calling every
                                        microservice above by its
                                        contract, not its internals

Why this shape works:
   - Every agent is its own FastAPI microservice with its own
     requirements.txt and Dockerfile — one person's broken dependency
     never blocks anyone else.
   - The "shared/schemas" folder is the one place that needs agreement
     up front (Stage 4). Once it's frozen, every folder can be built,
     tested, and demoed completely in isolation, using mock data that
     matches the schema, before the real upstream agent even exists.
   - Integration (Stage 9) is genuinely just pointing the coordinator
     and frontend at real URLs instead of mocks — not a merge exercise.

================================================================================
3. PRODUCT DESIGN — USABLE BY ANYBODY
================================================================================

Three views on one shared backend:

  1. Citizen / general view (no login)
     One headline risk score, one line of plain-English explanation, a
     map. Nothing else.

  2. Procurement analyst view (login)
     Ranked alternative suppliers, cost/transit/risk tradeoffs, a
     "why this recommendation" reasoning trace, exportable PDF/CSV.

  3. Policy / SPR planner view (login)
     Scenario simulator with adjustable assumptions, SPR drawdown
     schedule, GDP/fuel-price impact chart, saved/compared scenarios.

Supporting details:
   - 3-step onboarding chooser routes a new user into one of the views.
   - Every AI-generated number carries a reasoning trail (source
     articles, confidence score, model used).
   - Explainability panel expands "why is Hormuz risk 82 today" into the
     underlying signals.
   - Fully usable at mobile width.
   - One-page exportable PDF brief.

================================================================================
4. ARCHITECTURE
================================================================================

                       Live External Sources
      -------------------------------------------------------
      | EIA API | GDELT | aisstream.io | OFAC SDN | PPAC/MoP |
      -------------------------------------------------------
                            |
                  Data Ingestion + Cache Layer
              (scheduled jobs, snapshot-on-write,
               "last synced at" timestamp on every field)
                            |
                   Risk Intelligence Layer
                            |
              -----------------------------
              |                           |
      Knowledge Graph                Vector DB (RAG)
              |                           |
              -----------------------------
                            |
                     Scenario Engine
                            |
         ---------------------------------------
         |                |                    |
 Procurement Agent   SPR Optimizer Agent   Digital Twin
         |                |                    |
         ---------------------------------------
                            |
                  Coordinator Agent
        (resolves conflicts, e.g. cost vs. security,
         produces one final recommendation)
                            |
              -----------------------------------
              | Citizen View | Analyst View | Policy View |
              -----------------------------------------

================================================================================
5. BUILD PLAN — 12 STAGES
================================================================================

STAGE 1 — Research + Live Data Spine (Day 1, everyone)
   Register API keys (EIA, aisstream.io). Pull one real record from EIA,
   GDELT, aisstream.io, and OFAC and store it in the database. Prove the
   live pipeline end to end before any agent is written.

STAGE 2 — Database & Backend Foundation (Day 1-2, one person)
   Tables: countries, suppliers, corridors, refineries, ships,
   risk_events, risk_scores, scenario_results, recommendations,
   spr_schedule, data_sources, user_views. FastAPI + Supabase + auth.
   This becomes the "shared/" folder.

STAGE 3 — Knowledge Graph + Schema Freeze (Day 2)
   Build Supplier -> Route -> Port -> Refinery -> Fuel Type in NetworkX.
   Simultaneously, the team agrees and freezes the JSON contracts in
   shared/schemas/ for risk-score, simulate, recommend, and
   spr-schedule. Once frozen, nobody changes a contract without telling
   everyone — this is what makes Stage 4 parallel work possible.

--- FOLDER SPLIT HAPPENS HERE — Stages 4-8 run in parallel ---

STAGE 4 — Risk Agent (Day 2-4, Member 1, folder: risk-agent/)
   Reads GDELT, aisstream.io, OFAC, EIA. LangGraph pipeline: extract ->
   classify -> assign corridor -> severity -> risk score -> store.
   Returns a reasoning trail. Exposes POST /risk-score matching the
   frozen schema. Tested standalone with its own test data.

STAGE 5 — Scenario Simulation Engine (Day 2-5, Member 2, folder:
   scenario-engine/)
   Monte Carlo / elasticity models calibrated on real EIA historical
   price-shock data. Exposes POST /simulate. Tested standalone against
   mocked risk-score input matching the frozen schema.

STAGE 6 — Procurement Agent (Day 3-5, Member 3, folder:
   procurement-agent/)
   Ranks suppliers/routes on price, transit, risk, grade compatibility,
   using the knowledge graph and real supplier/refinery data. Exposes
   POST /recommend. Tested standalone.

STAGE 7 — SPR Optimization Agent (Day 3-6, Member 3 or 4, folder:
   spr-agent/)
   Linear programming against India's ~9.5-day SPR cover baseline.
   Exposes POST /spr-schedule. Tested standalone.

STAGE 8 — Frontend + Digital Twin, built against mocks (Day 2-6,
   Member 4, folder: frontend/)
   Builds the 3-tier product shell (Citizen / Analyst / Policy views),
   onboarding chooser, map, charts, PDF/CSV export — all against mock
   responses shaped like the frozen schemas, so the UI is fully working
   before any real agent finishes.

--- FOLDERS MERGE BACK HERE ---

STAGE 9 — Coordinator + Real Integration (Day 6-7, everyone)
   Build coordinator/ to call all four agents and resolve conflicts
   (e.g. cost vs. security) into one final recommendation. Swap the
   frontend's mocks for real service URLs. This is the first day
   everything actually talks to everything else.

STAGE 10 — End-to-End Testing & Bug Fixing (Day 7-8, everyone)
   Run full scenarios start to finish. Fix broken contracts, timing
   issues, and edge cases (e.g. an agent timing out, a stale cache).
   This is also when the India-data scraper's output gets validated
   against the manual CSV fallback.

STAGE 11 — Documentation + Architecture Deck (Day 8-9, one or two
   people while others keep fixing bugs)
   Architecture diagram, one-pager, presentation deck, README per
   folder explaining what each service does and its contract.

STAGE 12 — Demo Hardening & Rehearsal (Day 9-10, everyone)
   Freeze a cached "golden snapshot" of all live data the night before
   the demo. Present from cache with a visible timestamp, live mode as
   a bonus toggle. Rehearse assuming the internet fails at the worst
   possible moment — it should still work.

================================================================================
6. TEAM DISTRIBUTION
================================================================================

Member 1 — risk-agent/
   GDELT/AIS/OFAC/EIA ingestion, LangGraph, risk scoring, reasoning
   trail.

Member 2 — scenario-engine/
   Monte Carlo, elasticity models, forecast APIs, GDP/fuel impact.

Member 3 — procurement-agent/ (+ knowledge_graph/)
   Supplier ranking, route selection, NetworkX graph logic.

Member 4 — frontend/ (+ shared/ setup, deployment)
   FastAPI/Supabase foundation, auth, 3-tier product shell, onboarding,
   export, caching/fallback layer, deployment.

(spr-agent/ and ppac-scraper/ get assigned to whoever has bandwidth
after their primary folder stabilizes — both are small and self
contained.)

================================================================================
7. TECH STACK
================================================================================

Layer            | Technology
-----------------|-------------------------------------------------------
Frontend         | Next.js 15 + TypeScript
UI               | Tailwind + shadcn/ui
Maps             | Mapbox GL JS
Charts           | Recharts
Backend          | FastAPI (one microservice per agent folder)
AI Workflow      | LangGraph
LLM              | Gemini 2.5 Flash
Database         | Supabase (PostgreSQL)
Vector Search    | pgvector
Graph Logic      | NetworkX
Live Oil Data    | EIA API v2
News/Events      | GDELT
AIS Ship Data    | aisstream.io + AISHub
Sanctions        | OFAC SDN list
India Gov Data   | PPAC/MoP scraper + CSV cache
Optimization     | SciPy
Containerization | Docker + docker-compose (one container per folder)
Deployment       | Vercel (frontend) + Railway (services) + Supabase

================================================================================
8. WHAT MAKES THIS STAND OUT
================================================================================

Real, live, verifiable data instead of synthetic numbers, shown with
visible "last synced at" timestamps. A demo that opens on the
plain-English Citizen View before descending into the Analyst and Policy
views. A visible reasoning trail behind every score, so the system reads
as an advisory intelligence layer, not a black box. And a codebase that
was built in true parallel — four independent, individually testable
microservices — rather than four people fighting over one repo.
================================================================================
