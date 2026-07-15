#!/usr/bin/env python3
"""Generate frontend/api/index.py (the Vercel Python Function) from api.py.

Vercel only uploads files under the project root (frontend/), so the backend
must live at frontend/api/index.py. Rather than hand-maintain a copy, this
script derives it mechanically from the single source of truth (root api.py),
applying exactly the changes Vercel needs:

  1. Mount the app under /api  — Vercel serves the function at /api/* and the
     browser calls same-origin /api/... paths, so the app's routes (/simulate,
     /corridors, ...) must match /api/simulate, /api/corridors, ...
  2. Calibrate volatility at import time — Vercel's Python runtime may not run
     ASGI lifespan events, so we don't rely on them.

Run from the repo root:  python scripts/build_vercel_api.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "api.py")
DST = os.path.join(ROOT, "frontend", "api", "index.py")

with open(SRC, "r", encoding="utf-8") as f:
    code = f.read()

# 1) Rename the app -> _inner (the mounted sub-app), drop the lifespan wiring.
code = code.replace(
    'app = FastAPI(title="Pravah Monolith Backend", version="1.0.0", lifespan=lifespan)',
    '_inner = FastAPI(title="Pravah Monolith Backend", version="1.0.0")',
)
assert "_inner = FastAPI(" in code, "FastAPI construction line not found — did api.py change?"
code = code.replace("app.add_middleware(", "_inner.add_middleware(")
code = code.replace("@app.", "@_inner.")  # all route + middleware decorators

header = (
    "# ─────────────────────────────────────────────────────────────────────────\n"
    "# AUTO-GENERATED from ../../api.py by scripts/build_vercel_api.py — DO NOT EDIT.\n"
    "# This is the Vercel Python Function. Edit api.py, then re-run the generator.\n"
    "# ─────────────────────────────────────────────────────────────────────────\n"
)

footer = (
    "\n\n"
    "# ── Vercel entrypoint ────────────────────────────────────────────────────\n"
    "# Calibrate at import time (Vercel may not run ASGI lifespan events).\n"
    "try:\n"
    "    calibrate_volatility()\n"
    "except Exception:\n"
    "    pass\n"
    "\n"
    "# Vercel serves this function under /api/*; mount the app there so its\n"
    "# routes (/simulate, /corridors, ...) resolve at /api/simulate, etc.\n"
    "app = FastAPI(title='Pravah (Vercel)')\n"
    "app.mount('/api', _inner)\n"
)

os.makedirs(os.path.dirname(DST), exist_ok=True)
with open(DST, "w", encoding="utf-8") as f:
    f.write(header + code + footer)

print(f"Wrote {DST} ({len(header + code + footer)} bytes)")
