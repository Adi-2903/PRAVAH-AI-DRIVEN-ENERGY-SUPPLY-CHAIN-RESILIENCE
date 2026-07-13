"""
test_store_resilience.py — Stage 4 regression for audit finding H1.

Persistence is a best-effort side effect: a broken Supabase config (malformed
URL, missing `supabase` package) must never turn a successfully-scored request
into an HTTP 500. Before the fix, client construction sat outside the try/except.
"""
from datetime import datetime, timezone

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _raise(*args, **kwargs):
    raise RuntimeError("bad SUPABASE_URL")


def test_store_risk_swallows_client_construction_errors(monkeypatch):
    import store
    monkeypatch.setattr(store, "_client", _raise)
    out = store.store_risk(
        "hormuz",
        {"score": 50.0, "confidence": 0.7, "reasoning_trail": [],
         "key_events": [], "data_sources": ["fixtures"]},
        AS_OF,
    )
    assert out["stored"] is False
    assert "RuntimeError" in out["reason"]


def test_pipeline_persist_survives_broken_client(monkeypatch):
    import store
    from graph import run_pipeline
    monkeypatch.setattr(store, "_client", _raise)
    result, sources, store_info = run_pipeline("hormuz", AS_OF, use_live=False, persist=True)
    # scoring still succeeds and stays in-contract; persistence fails gracefully
    assert 0.0 <= result["score"] <= 100.0
    assert store_info["stored"] is False
