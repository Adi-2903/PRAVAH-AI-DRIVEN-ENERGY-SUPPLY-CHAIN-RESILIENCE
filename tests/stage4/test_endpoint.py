"""
test_endpoint.py — Stage 4 endpoint tests via FastAPI TestClient (no live server).

These hit the actual `main.app` in-process. The pipeline is forced offline
(use_live=False) and non-persisting (persist=False) so the endpoint tests are
fast, deterministic, network-free and never write to Supabase — while still
exercising the real request parsing, routing, and response serialization.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

CORRIDORS = ("hormuz", "redsea", "cape", "domestic")
ALERT_LEVELS = {"low", "elevated", "high", "critical"}
SEVERITIES = {"low", "medium", "high", "critical"}


@pytest.fixture
def client(monkeypatch):
    import main
    from graph import run_pipeline as _real

    def _offline(corridor, as_of=None, use_live=True, persist=True):
        return _real(corridor, as_of, use_live=False, persist=False)

    monkeypatch.setattr(main, "run_pipeline", _offline)
    return TestClient(main.app)


def _body(corridor="hormuz"):
    return {"corridor": corridor, "as_of": datetime.now(timezone.utc).isoformat()}


# ── /health ─────────────────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── /risk-score happy path ──────────────────────────────────────────────────
@pytest.mark.parametrize("corridor", CORRIDORS)
def test_risk_score_returns_valid_contract(client, corridor):
    r = client.post("/risk-score", json=_body(corridor))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["corridor"] == corridor
    assert 0.0 <= b["score"] <= 100.0
    assert 0.0 <= b["confidence"] <= 1.0
    assert b["alert_level"] in ALERT_LEVELS
    assert isinstance(b["reasoning_trail"], list) and b["reasoning_trail"]
    assert isinstance(b["data_sources"], list)
    for ev in b["key_events"]:
        assert set(ev) >= {"headline", "severity", "date"}
        assert ev["severity"] in SEVERITIES


def test_response_matches_frozen_schema(client):
    """The serialized response must round-trip through the frozen contract."""
    from shared.contracts.risk_score import RiskScoreResponse
    r = client.post("/risk-score", json=_body("hormuz"))
    assert r.status_code == 200
    RiskScoreResponse.model_validate(r.json())   # raises if the contract is broken


# ── /risk-score validation ──────────────────────────────────────────────────
def test_rejects_non_canonical_corridor(client):
    r = client.post("/risk-score", json=_body("HORMUZ"))     # uppercase not allowed
    assert r.status_code == 422


def test_rejects_unknown_corridor(client):
    r = client.post("/risk-score", json=_body("suez"))       # not one of the four
    assert r.status_code == 422


def test_rejects_missing_corridor(client):
    r = client.post("/risk-score", json={"as_of": datetime.now(timezone.utc).isoformat()})
    assert r.status_code == 422


def test_rejects_missing_as_of(client):
    r = client.post("/risk-score", json={"corridor": "hormuz"})
    assert r.status_code == 422


def test_rejects_empty_body(client):
    r = client.post("/risk-score", json={})
    assert r.status_code == 422
