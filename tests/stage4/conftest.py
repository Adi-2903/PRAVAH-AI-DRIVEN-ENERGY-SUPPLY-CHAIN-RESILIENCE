"""
conftest.py — Stage 4 (risk-agent) test fixtures & path setup.

Self-contained so these tests run on the `vraj` branch even without the
repo-root TESTING FILES/conftest.py. Makes the frozen schemas AND the
risk-agent's own modules importable, and guarantees no test writes to the live
Supabase project.

Run just the Stage 4 suite with:
    pytest "TESTING FILES/stage4" -v --tb=short
"""
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Path setup
#   ROOT        -> `from shared.schemas.risk_score import ...` (main.py style)
#   SHARED      -> `from schemas.risk_score import ...`        (team convention)
#   RISK_AGENT  -> `from graph import ...`, `from scoring... import ...`
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SHARED = os.path.join(ROOT, "shared")
RISK_AGENT = os.path.join(ROOT, "risk-agent")

for _p in (ROOT, SHARED, RISK_AGENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Safety net: never touch the shared Supabase project from a test.
# store._client() returns None -> store_risk() cleanly no-ops.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_db_writes(monkeypatch):
    try:
        import store
        monkeypatch.setattr(store, "_client", lambda: None)
    except Exception:
        pass
    yield


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
CORRIDORS = ("hormuz", "redsea", "cape", "domestic")
ALERT_LEVELS = ("low", "elevated", "high", "critical")
SEVERITIES = ("low", "medium", "high", "critical")


@pytest.fixture
def corridors():
    return CORRIDORS


@pytest.fixture
def as_of():
    from datetime import datetime, timezone
    return datetime(2026, 7, 11, tzinfo=timezone.utc)
