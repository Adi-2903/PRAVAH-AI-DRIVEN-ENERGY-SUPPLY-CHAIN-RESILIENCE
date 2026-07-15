# Deploying Pravah

Free native deploy (no containers), runs like localhost. The frontend already falls back to bundled
mock data on any error, so the UI never blanks — even mid–cold-start.

Two supported options — **Option A (Vercel only) is recommended: one platform, free, no second host, no CORS.**

---

## Option A — Vercel only (frontend + backend on one project) ✅ recommended

The backend runs as a **Vercel Python Function** (`frontend/api/index.py`, auto-generated
from `api.py`) in the *same* Vercel project as the Next.js frontend. Same origin ⇒ the
browser calls `/api/simulate`, `/api/corridors`, … with **no CORS and no second host**.

Why it fits: the backend is stateless pure-compute — no DB, no filesystem, no workers,
no websockets; every endpoint runs in ms (heaviest is ~52 ms). `scipy` was removed (the
SPR optimiser uses an exact greedy), so the function bundle is ~70 MB, well under Vercel's
250 MB limit.

**Files that make it work (already in the repo):**
- `frontend/api/index.py` — the FastAPI app mounted under `/api` (run `python scripts/build_vercel_api.py` to regenerate it after editing `api.py`).
- `frontend/requirements.txt` — Python deps for the function (no uvicorn, no scipy).
- `frontend/vercel.json` — routes `/api/*` to the function, `maxDuration: 60`.
- `frontend/app/lib/api.ts` — defaults every service base to `/api` (same-origin), so **no env vars are required**.

**Deploy steps:**
1. Push the repo to GitHub.
2. Vercel → **Add New → Project** → import the repo.
3. **Root Directory = `frontend`** (critical — the Python function and `requirements.txt` live there).
4. Framework auto-detects Next.js. **No environment variables needed** (the `/api` default is baked in). Optional: `EIA_API_KEY` for live Brent history.
5. Deploy → note the URL. Smoke-test:
   ```
   curl https://<your-app>.vercel.app/api/health           # {"status":"ok"}
   curl https://<your-app>.vercel.app/api/corridors         # live risk scores
   ```
6. Open the app — every tab shows the **"Live backend"** badge, served from the same domain.

**Limits to know (Vercel Hobby/free):** function bundle ≤ 250 MB (we're ~70 MB ✓);
`maxDuration` ≤ 60 s (set in `vercel.json`; only relevant if you enable live GDELT via
`?live=true`, which chains up to ~24 s); ~1–3 s cold start (numpy import); Hobby is for
non-commercial use (a hackathon prototype qualifies).

**Local dev for Option A:** `vercel dev` runs both the Next app and the Python function
together at `http://localhost:3000` with `/api/*` working. (Plain `npm run dev` won't serve
`/api` — set `frontend/.env.local` to a running `uvicorn api:app` on :8000 instead.)

---

## Option B — Vercel (frontend) + Render (backend)

Use this only if you outgrow the Vercel function limits. Native Python, no containers.

## What gets deployed

| Piece | Host | What it is |
|---|---|---|
| **Frontend** (`frontend/`) | **Vercel** (free) | Next.js 15 app |
| **Backend** (`api.py`) | **Render** free web service | ONE self-contained FastAPI file |

`api.py` is a **single-file monolith**: the 3 agents the UI calls live
(scenario-engine + spr-agent + procurement-agent) merged into one FastAPI app,
with all models, the supply-chain graph, the EIA client, and the Brent history
CSV **inlined**. No `shared/` folder, no data files, no package structure — drop
`api.py` + `requirements.txt` anywhere and run `uvicorn api:app`.

One URL serves every endpoint (paths are unique, no collision):

```
POST /simulate        GET /simulate/mock     GET /data-status     (scenario)
POST /spr-schedule    GET /spr-schedule/mock                      (spr)
POST /recommend       GET /market            GET /graph           (procurement)
POST /risk-score      GET /corridors                              (risk)
POST /final-recommendation                                        (coordinator)
GET  /health          GET /                                       (app)
```

**Every frontend view now calls the backend live** (with an automatic offline
fallback so the UI never blanks):

| View | Live endpoint(s) |
|---|---|
| Command Center | `GET /corridors`, `GET /market` |
| Risk Intelligence | `GET /corridors` (scores + reasoning + scoring events) |
| Citizen View | `POST /final-recommendation`, `GET /corridors`, `GET /market` |
| Scenario Modeller | `POST /simulate`, `GET /data-status` |
| Strategic Reserves | `POST /simulate` → `POST /spr-schedule` (real inputs), `GET /corridors` |
| Procurement | `POST /recommend`, `GET /market` |
| App shell (ticker, composite index) | `GET /corridors`, `GET /market` |

The original per-agent folders remain in the repo for local dev; `api.py` is the
single deployable that serves all of the above.

---

## 1. Backend → Render (free, native Python)

1. Push this repo (including `api.py`, `requirements.txt`, `render.yaml`, `runtime.txt`) to GitHub.
2. Render Dashboard → **New → Web Service** → connect the repo → pick the branch.
   (Or **New → Blueprint** to auto-read `render.yaml`.)
3. Settings (already encoded in `render.yaml`):
   - **Root Directory:** *(leave blank / repo root)*
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
   - **Health Check Path:** `/health`
   - **Python version:** pinned by `runtime.txt` (`python-3.12.8`). If Render
     rejects it, delete `runtime.txt` (Render uses its default 3.x — the code
     runs on 3.11–3.13) or set a patch Render supports.
4. Environment variables — **none required**. Optional:
   - `EIA_API_KEY` — real Brent history for the Simulator (else embedded-CSV fallback).
   - `ALLOWED_ORIGINS` — set to your Vercel URL after §2 (see §3).
5. Deploy → note the URL, e.g. `https://pravah-backend.onrender.com`.
6. Smoke-test:
   ```bash
   curl https://pravah-backend.onrender.com/health
   curl -X POST https://pravah-backend.onrender.com/spr-schedule \
     -H "Content-Type: application/json" \
     -d '{"planning_horizon_days":7,"current_reserve_days":9.5,"min_safety_floor_days":6.0,"max_daily_drawdown_days":1.0,"daily_risk_scores":[85,88,82,70,60,55,50],"daily_price_forecast_usd_per_bbl":[102.5,104,101,95,90,88,85]}'
   ```

---

## 2. Frontend → Vercel

1. Vercel → **Add New → Project** → import the same repo.
2. **Root Directory = `frontend`** (critical). Framework auto-detects Next.js.
   `frontend/.npmrc` (`legacy-peer-deps=true`) is respected, so `npm install` succeeds.
3. **Environment Variables** (Production) — point every service URL at the one Render URL:
   ```
   NEXT_PUBLIC_SCENARIO_URL     = https://pravah-backend.onrender.com
   NEXT_PUBLIC_SPR_URL          = https://pravah-backend.onrender.com
   NEXT_PUBLIC_PROCUREMENT_URL  = https://pravah-backend.onrender.com
   NEXT_PUBLIC_RISK_URL         = https://pravah-backend.onrender.com
   NEXT_PUBLIC_COORDINATOR_URL  = https://pravah-backend.onrender.com
   ```
   All five are **required** — every view now calls the backend live (Risk
   Intelligence, Command Center and Citizen View use `RISK`/`COORDINATOR`).
   These are inlined at **build time** — set them **before** deploying (redeploy if changed).
4. Deploy → note the Vercel URL.

---

## 3. Wire CORS (one step, don't skip)

Browser calls go directly from the Vercel page to Render, so Render must allow that origin:
- On Render, set **`ALLOWED_ORIGINS`** = your Vercel URL (e.g. `https://pravah.vercel.app`) → redeploy the backend.
- Both ends are HTTPS, so there's no mixed-content block.
- For a quick demo you may leave `ALLOWED_ORIGINS` unset (defaults to `*`).

---

## 4. Cold-start (free tier)

Render's free instance sleeps after ~15 min idle; the first request then takes
~30–60s. During that window the frontend times out (5–8s) and shows **mock data**,
then live data once warm — never a blank screen. For a demo, hit
`https://pravah-backend.onrender.com/health` ~1 min before presenting, or add a
free keep-alive ping (UptimeRobot / cron-job.org every ~10 min).

---

## 5. Verify end-to-end

- Open the Vercel app → **every** tab (Command Center, Risk Intelligence, Scenario
  Modeller, Strategic Reserves, Procurement, Citizen View) shows a **"Live backend"**
  badge and values computed by the Python code (corridor scores, composite index,
  market prices, scenario paths, SPR schedule).
- Stop the Render service → every tab falls back to the bundled sample data with an
  **"Offline (sample)"** badge, never blank. Restart → live returns.
- The app shell's ticker, composite-risk index and alert level are all driven by
  `GET /corridors` + `GET /market` — no hardcoded values remain.

---

## Run the backend locally (optional)

`api.py` needs no special working directory:
```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```
Then set the frontend's `NEXT_PUBLIC_*` vars to `http://127.0.0.1:8000` (a ready-made
`frontend/.env.local` example does exactly this), and run `npm run dev` in `frontend/`.

## Security note
`.env` (gitignored) holds a live Supabase `service_role` key. This deployment does
**not** use Supabase or that key — do not upload `.env` to Render. Rotate the key in
the Supabase dashboard if it was ever shared/pushed.
