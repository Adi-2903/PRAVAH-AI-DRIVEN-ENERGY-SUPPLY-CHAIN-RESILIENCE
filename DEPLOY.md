# Deploying Pravah

Free native deploy (no containers) on Vercel, running like localhost. The frontend already falls back to bundled mock data on any error, so the UI never blanks.

The backend runs as a **Vercel Python Function** (`frontend/api/index.py`, auto-generated from `api.py`) in the *same* Vercel project as the Next.js frontend. Same origin means the browser calls `/api/simulate`, `/api/corridors`, etc. with **no CORS and no second host**.

Why it fits: the backend is stateless pure-compute — no database, no filesystem, no background workers; every endpoint runs in milliseconds (heaviest is ~52 ms). The function bundle is ~70 MB, well under Vercel's 250 MB limit.

---

## Deploy to Vercel (Frontend + Backend on one project) ✅

**Files that make it work (already in the repo):**
- `frontend/api/index.py` — the FastAPI app mounted under `/api` (run `python scripts/build_vercel_api.py` to regenerate it after editing `api.py`).
- `frontend/requirements.txt` — Python deps for the function.
- `frontend/vercel.json` — routes `/api/*` to the function, `maxDuration: 60`.
- `frontend/app/lib/api.ts` — defaults every service base to `/api` (same-origin), so **no env vars are required**.

**Deploy steps:**
1. Push the repo to GitHub.
2. Vercel → **Add New → Project** → import the repo.
3. Set **Root Directory = `frontend`** (critical — the Python function and its `requirements.txt` live there).
4. Framework auto-detects Next.js. **No environment variables needed** (the `/api` default is baked in). Optional: `EIA_API_KEY` for live Brent history.
5. Deploy → note the URL. Smoke-test:
   ```bash
   curl https://<your-app>.vercel.app/api/health           # {"status":"ok"}
   curl https://<your-app>.vercel.app/api/corridors         # live risk scores
   ```
6. Open the app — every tab shows the **"Live backend"** badge, served from the same domain.

**Limits to know (Vercel Hobby/free):** function bundle ≤ 250 MB (we're ~70 MB); `maxDuration` ≤ 60 s (set in `vercel.json`); ~1–3 s cold start (numpy import).

---

## Local Development

### Option 1: Unified local server (vercel dev)
Runs both the Next app and the Python function together at `http://localhost:3000` with `/api/*` working:
1. Install [Vercel CLI](https://vercel.com/cli): `npm i -g vercel`
2. Run `vercel dev` inside the `frontend` directory.

### Option 2: Split local servers
If you prefer running them separately:
1. **Start Backend**: Run from the root directory:
   ```bash
   pip install -r requirements.txt
   uvicorn api:app --host 0.0.0.0 --port 8000
   ```
2. **Start Frontend**: Create `frontend/.env.local` pointing to the backend:
   ```env
   NEXT_PUBLIC_SCENARIO_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_SPR_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_PROCUREMENT_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_RISK_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_COORDINATOR_URL=http://127.0.0.1:8000
   ```
   Then run `npm run dev` in the `frontend` directory.
