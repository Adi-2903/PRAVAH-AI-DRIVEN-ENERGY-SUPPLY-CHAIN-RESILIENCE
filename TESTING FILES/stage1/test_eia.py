"""
test_eia.py — EIA client unit tests. Mocks all HTTP calls. No API key required.
"""
import sys, os
# Ensure shared/clients is importable
CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "clients")
if CLIENTS_DIR not in sys.path:
    sys.path.insert(0, CLIENTS_DIR)

import pytest
import requests as _requests
from unittest.mock import patch, MagicMock
import eia_client  # ensure it's in sys.modules before any patching


def make_mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


# ── HAPPY PATH ───────────────────────────────────────────────────────────────

def test_eia_returns_parsed_dict(sample_eia_response):
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=make_mock_response(sample_eia_response)):
        result = eia_client.fetch_latest_brent_price()
    assert isinstance(result, dict)
    assert "date" in result
    assert "price" in result
    assert "unit" in result

def test_eia_price_is_float(sample_eia_response):
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=make_mock_response(sample_eia_response)):
        result = eia_client.fetch_latest_brent_price()
    assert isinstance(result["price"], float)
    assert result["price"] > 0

def test_eia_date_is_string(sample_eia_response):
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=make_mock_response(sample_eia_response)):
        result = eia_client.fetch_latest_brent_price()
    assert isinstance(result["date"], str)
    assert len(result["date"]) > 0


# ── MISSING KEY ───────────────────────────────────────────────────────────────

def test_eia_raises_on_missing_key():
    with patch.object(eia_client, "EIA_API_KEY", ""):
        with pytest.raises(ValueError, match="EIA_API_KEY"):
            eia_client.fetch_latest_brent_price()

def test_eia_raises_on_placeholder_key():
    with patch.object(eia_client, "EIA_API_KEY", "your_key_here"):
        with pytest.raises(ValueError, match="EIA_API_KEY"):
            eia_client.fetch_latest_brent_price()


# ── EMPTY DATA ────────────────────────────────────────────────────────────────

def test_eia_raises_on_empty_data():
    empty = {"response": {"data": []}}
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=make_mock_response(empty)):
        with pytest.raises(ValueError, match="no data"):
            eia_client.fetch_latest_brent_price()


# ── NULL PRICE ────────────────────────────────────────────────────────────────

def test_eia_handles_null_price():
    null_price = {"response": {"data": [
        {"period": "2026-07-10", "value": None, "units": "$/barrel", "product-name": "Brent"}
    ]}}
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=make_mock_response(null_price)):
        result = eia_client.fetch_latest_brent_price()
    assert result["price"] is None


# ── HTTP ERROR ────────────────────────────────────────────────────────────────

def test_eia_raises_on_http_error():
    mock = MagicMock()
    mock.raise_for_status.side_effect = _requests.HTTPError("429 Rate Limited")
    with patch.object(eia_client, "EIA_API_KEY", "fake_key"), \
         patch("eia_client.requests.get", return_value=mock):
        with pytest.raises(_requests.HTTPError):
            eia_client.fetch_latest_brent_price()
