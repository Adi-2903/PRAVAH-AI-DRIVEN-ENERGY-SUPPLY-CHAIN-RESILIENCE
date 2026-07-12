# Stage 8 (Frontend + Digital Twin) — Engineering Review & Test Plan

**Reviewer:** automated SWE review · **Branch:** `Preetansh` · **Commit under review:** `1974350` "Add frontend tiered views and intelligence modules" (author: Wolfy15 / jenilpaghdar)
**Scope:** `frontend/` — the Stage 8 deliverable per README: *3-tier product shell (Citizen / Analyst / Policy), onboarding chooser, map, charts, PDF/CSV export, all against mocks shaped like the frozen schemas.*

---

## 0. What Stage 8 shipped

| File | Status | Purpose |
|---|---|---|
| `app/citizen-view.tsx` | **new** | Full-screen Citizen view: risk gauge, plain-English headline, simple map, KPIs |
| `app/risk-intelligence.tsx` | **new** | Corridor risk cards + live signal feed + reasoning trail |
| `app/components/reasoning-trail.tsx` | **new** | Collapsible "why this score" panel (signals, weights, model, confidence) |
| `app/components/data-freshness.tsx` | **new** | "data as of / X min ago" freshness pill (live/stale/old) |
| `app/lib/mock-data.ts` | **new** | Centralized typed mock layer + `fetchWithFallback()` |
| `app/lib/export.ts` | **new** | PDF (jspdf) + CSV export helpers |
| `app/page.tsx` | modified | Tier switcher + citizen/analyst routing, SPA shell |
| `app/dashboard.tsx` | modified | +data-freshness pills, +Export Situation Report button |
| `app/procurement.tsx` `spr.tsx` `simulator.tsx` | modified | +export buttons only (fetch logic predates Stage 8) |

**Verdict:** the *new* work (Citizen view, Risk Intelligence, reasoning trail, data-freshness, export, mock layer) is well-built and visually strong. The main problems are **integration/consistency**: the clean new mock layer is only used by the 2 new views, while the 3 data modules keep their own hardcoded-URL fetch logic — and those two worlds disagree.

---

## 1. Verification results (reproduced from a clean clone state)

| Check | Command | Result |
|---|---|---|
| Clean install | `npm install` | ❌ **FAILS** — ERESOLVE peer conflict (see BUG-1) |
| Install (workaround) | `npm install --legacy-peer-deps` | ✅ OK — 776 pkgs, next 15.5.20, react 19.2.7 |
| Typecheck | `npx tsc --noEmit` | ✅ **PASS** (0 errors) |
| Production build | `next build` (Next 15) | ✅ **PASS** — compiles, types valid, 5 static routes, `/` = 295 kB First Load JS |
| Build via `npx next` | (pulled Next **16**) | ❌ FAILS — webpack config ↔ Turbopack conflict (see BUG-14) |
| Lint | `next lint` | ⚠️ exit 1 — 5 issues, but build skips lint (`ignoreDuringBuilds: true`) |

---

## 2. Bugs & gaps (prioritized)

### P0 — Blocker
**BUG-1 · Clean `npm install` fails (ERESOLVE).**
`react-simple-maps@3.0.0` declares peer `react@^16.8.0 || 17.x || 18.x`; the project pins `react@19.2.1`. A fresh clone cannot install without `--legacy-peer-deps`/`--force`. Your friend has a working `node_modules` locally, so it only breaks for everyone else / in CI / on deploy.
*Fix:* add `frontend/.npmrc` with `legacy-peer-deps=true` for an immediate unblock, and open a task to move off `react-simple-maps@3` (unmaintained for React 19) — either `react-simple-maps@^4` or render the procurement map with the same hand-rolled SVG approach used in citizen-view/dashboard.

### P1 — High (breaks the Stage-8 promise: "UI fully working before any agent finishes / never a blank screen")
**BUG-2 · Procurement tab has no offline fallback.**
`simulator.tsx` and `spr.tsx` fall back to locally-generated mock data when the backend is unreachable. `procurement.tsx` only sets `error` → the panel shows "Backend unavailable" / "No alternatives found". With no services running (the normal Stage-8 state), **Procurement is permanently empty**. Ironically `MOCK_RECOMMEND` already exists in `mock-data.ts` but isn't wired in.

**BUG-3 · Frontend API ports contradict `docker-compose.yml` (Stage-9 integration will silently fail).**

| Frontend calls | Compose maps | Mismatch |
|---|---|---|
| `127.0.0.1:8000/recommend` | procurement-agent → `8003` | wrong port |
| `127.0.0.1:8000/simulate` `/data-status` | scenario-engine → `8002` | wrong port + collides with recommend on 8000 |
| `127.0.0.1:8001/spr-schedule` | spr-agent → `8004` (`8001` = risk-agent) | points at the wrong service |

Procurement and Scenario are different microservices but both hardcode `:8000` — they can't coexist. When real services come up in Stage 9, none of these fetches hit the right target.

**BUG-4 · No env-based API config.** Every URL is a hardcoded `http://127.0.0.1:...` literal scattered across 3 files. This blocks deployment (Vercel frontend cannot reach `localhost`) and any non-local environment.

### P2 — Medium (correctness / consistency / spec gaps)
**BUG-5 · Two divergent data systems → the same number shown three ways.**
Hormuz risk is **82** (mock-data.ts, citizen-view, risk-intelligence) vs **78.2** (dashboard corridor table) vs composite **74** (sidebar widget + alert bar). `dashboard.tsx` imports `mock-data` only for timestamps, then renders its *own* hardcoded `riskData`/`feedItems`. Inconsistent headline numbers undercut a "real, verifiable data" demo.

**BUG-6 · `mock-data.ts` schemas don't match the modules that would consume them.**
`MOCK_RECOMMEND.ranked_suppliers` uses `country / price_usd / route_risk / grade_match / score / why`, but `procurement.tsx` expects `supplier / estimated_cost_usd_per_bbl / corridor_risk_score / composite_score / rank / reasoning`. Same divergence for SPR (`draw_bbl` vs `drawdown_days/reserve_after_days/...`). So the BUG-2 fix would break unless the shapes are reconciled — and only one of them matches `shared/schemas/`. This is exactly what the Stage-3 "frozen schema" was supposed to prevent; pick one source of truth.

**BUG-7 · Digital Twin not implemented.** Stage 8 is titled "Frontend + **Digital Twin**", but the `twin` tab is `disabled` and shows "Module Offline". `react-force-graph-2d` was added (presumably for it) but is unused.

**BUG-8 · Onboarding chooser missing.** README requires a "3-step onboarding chooser [that] routes a new user into one of the views." Reality: the app boots straight into Citizen view; the only tier control is the header `TierSwitcher` dropdown.

**BUG-9 · Policy tier is identical to Analyst tier.** `page.tsx` only branches `citizen` vs everything-else, so choosing "Policy Maker" renders the exact analyst shell. README calls for a distinct Policy/SPR-planner experience (saved/compared scenarios, drawdown schedule as the focus).

**BUG-10 · External runtime deps break the "works offline" demo (Stage 12's whole plan).**
`procurement.tsx` fetches `world-atlas` topojson from `cdn.jsdelivr.net` at runtime; `globals.css` pulls fonts from Google Fonts via `@import`. If the venue Wi-Fi drops, the procurement map is blank and typography falls back. Bundle the topojson locally and self-host fonts via `next/font`.

**BUG-11 · `/scenario` route is a dead stub** — it only `router.replace('/')`. Either build it (a Policy deep-link target) or delete it.

### P3 — Low (quality / hygiene / polish)
- **BUG-12 · Dead dependencies:** `motion`, `@google/genai`, `papaparse`, `@hookform/resolvers`, `class-variance-authority`, `react-force-graph-2d` are imported nowhere. (`export.ts`'s header comment even claims it "uses papaparse", but it hand-rolls CSV.) Remove to shrink install/attack surface.
- **BUG-13 · Lint errors hidden by config:** `next lint` fails on missing `key` prop for the `RANK_ICONS` array (`procurement.tsx:76`), unescaped apostrophes, and `set-state-in-effect`. `eslint.ignoreDuringBuilds: true` means CI never sees them.
- **BUG-14 · Version incoherence / forward-compat:** runtime is `next@^15` but `eslint-config-next@16` is a devDep, and `next.config.ts` carries a `webpack` block + an `eslint` key that **break/deprecate under Next 16** (which bare `npx next` pulls). Pin Next and align the toolchain, or migrate the config to Turbopack.
- **BUG-15 · Multiple lockfiles:** `hormuz/package-lock.json` (added recently) + `frontend/package-lock.json` make Next infer the wrong workspace root (build warning). Remove the stray one or set `outputFileTracingRoot`.
- **BUG-16 · `tsconfig.tsbuildinfo` is committed** (a generated incremental cache) — add to `.gitignore`.
- **BUG-17 · Scaffold leftovers in `next.config.ts`:** `picsum.photos` remote images + the AI-Studio `DISABLE_HMR` webpack block are unused.
- **BUG-18 · Mobile not implemented:** `useIsMobile` hook exists but is never imported; layouts use a fixed 256 px sidebar, `100vw`, and fixed multi-column grids → not usable at mobile width (README requires it).
- **BUG-19 · Simulator offline model:** the GBM fallback can produce a very wide P10–P90 fan; `std_dev` is derived two different ways (`(p90-p10)/3` in the fallback vs `/2.56` in `histData`). Cosmetic but visible.

---

## 3. Recommended fixes (highest leverage first)

1. **One API client** — `app/lib/api.ts` exposing `callAgent(service, path, body)` that reads `NEXT_PUBLIC_*_URL` and falls back through the existing `fetchWithFallback` to `mock-data.ts`. Route all 4 data modules through it. This single change resolves BUG-2, BUG-3, BUG-4 and unifies BUG-5/BUG-6.
2. **`.npmrc` `legacy-peer-deps=true`** now; ticket to replace `react-simple-maps`.
3. **Reconcile `mock-data.ts` with `shared/schemas/`** so there is exactly one contract shape per endpoint (the Stage-3 freeze). Delete the divergent inline arrays in `dashboard.tsx`.
4. **`.env.example`** documenting every `NEXT_PUBLIC_*` URL.
5. **Decide + label scope** for Digital Twin, Policy view, onboarding chooser — build them or explicitly mark "future" so judges see intent, not a disabled tab.
6. **Offline hardening:** self-host fonts (`next/font`) + bundle `world-atlas` JSON.

---

## 4. Test / QA plan (execute in this order)

### A. Build & environment gates (must pass before any manual QA)
```bash
cd frontend
npm install                 # EXPECT: currently fails → confirm .npmrc fix makes it pass
npx tsc --noEmit            # EXPECT: 0 errors
npx next lint               # EXPECT: triage the 5 findings
npm run build               # EXPECT: "Compiled successfully", 5 routes
npm run dev                 # smoke: app loads at :3000 with NO console errors
```

### B. Automated checks to add
- CI job running the 4 commands above (turn `ignoreDuringBuilds` off once lint is clean).
- Minimal render smoke tests (Vitest + React Testing Library): each view mounts without throwing when the backend is unreachable (this would have caught BUG-2).
- A tiny contract test asserting `mock-data.ts` objects satisfy the `shared/schemas` types.

### C. API / endpoint contract tests
For each endpoint, verify method, payload, response shape, **and port**:

| Module | Endpoint | Method | Payload keys | Must return | Correct port? |
|---|---|---|---|---|---|
| Procurement | `/recommend` | POST | current_supplier, *_weight, max_alternatives | `recommendations[]`, `current_supplier_baseline`, `market_data`, `computed_at` | ❌ 8000 → should be 8003 |
| Scenario | `/simulate` | POST | risk_score, corridor, shock_duration_days, num_simulations, elasticity_assumptions | `brent_price_distribution`, `daily_price_path[]`, `pump_price_impact`, `gdp_impact_pct` | ❌ 8000 → should be 8002 |
| Scenario | `/simulate/mock`, `/data-status` | GET | — | mock SimResult / DataStatus | ❌ 8000 |
| SPR | `/spr-schedule` (+ `/mock`) | POST/GET | planning_horizon_days, current_reserve_days, floors, daily arrays | `schedule[]`, `savings_*`, `reserve_never_below_floor` | ❌ 8001 → should be 8004 |

Test matrix per endpoint: (1) backend up + valid → live render; (2) backend up + 4xx/5xx → error path; (3) backend down → **fallback to mock** (currently only sim/spr pass this); (4) slow (>5 s) → `AbortSignal.timeout` path.

### D. Manual UX checklist (per view)
- **Citizen:** gauge animates to correct score/label/color; headline text matches score band; map chokepoint colors match `CORRIDOR_RISK_DATA`; "Go deeper" → Analyst; freshness pill shows "min ago"; numbers agree with other views (BUG-5).
- **Command Center:** KPIs render; corridor table numbers match Risk Intelligence (BUG-5); row/Model buttons navigate; "Export Situation Report" downloads a valid PDF (open it — check table + reasoning trail render, no "undefined").
- **Risk Intelligence:** corridor select updates reasoning trail; source filter (incl. "REUTERS" which has 0 items → empty-state copy); signal weights sum visually; dark-shipping badge shows.
- **Scenario Modeller:** every slider re-runs (debounced); preset pills apply; charts update; **PDF & CSV export open and contain real values**; offline mode badge appears when backend down; extreme inputs (days=90, risk=100) don't produce absurd/negative prices (BUG-19).
- **Procurement:** ⚠️ **currently empty with no backend** (BUG-2) — after fix, verify ranked list, map paths, weight sliders re-normalize to 1.0, impact HUD deltas, PDF export values.
- **SPR:** sliders re-optimize; chart + table + savings render; CSV export opens; safety-floor reference line respected.

### E. Cross-cutting QA
- **Offline demo (Stage-12 rehearsal):** turn Wi-Fi OFF, hard-reload every view. Expect: all views usable from cache, fonts intact, maps intact, visible "as of" timestamps. Today this fails (fonts, world-atlas, procurement).
- **Responsive:** test at 375 px / 768 px / 1280 px. Expect current failures (BUG-18) — sidebar, grids, ticker overflow.
- **Data freshness:** confirm pill flips live→stale→old at 5 min / 60 min / 24 h boundaries (mock uses `minutesAgo(3)` = green).
- **Accessibility quick pass:** keyboard focus on tab nav, dropdowns, sliders; color-contrast on the light-on-color badges; `alt`/`aria` on icon-only buttons.
- **Performance:** `/` First Load JS is 295 kB — check Lighthouse; dropping dead deps (BUG-12) and lazy-loading recharts/jspdf helps.
- **PDF/CSV integrity:** actually open exported files; verify CSV escaping (commas/quotes in `reasoning`/`why` fields) and multi-page PDF pagination.

### F. Demo-hardening / regression
- Freeze a golden mock snapshot; verify the app is fully navigable with **zero** backend services running.
- Confirm no `console.error` in any view during a full click-through.
- Re-run section A after every fix.

---

*Generated as a review aid — no application code was modified. Reproduced against a clean install on Windows / Node 22.17 / npm 10.9.*
