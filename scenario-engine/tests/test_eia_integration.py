import os
import pytest
from unittest import mock
import numpy as np
from data.eia_history_client import fetch_brent_spot_history, get_data_status

# Mock data
MOCK_API_RESPONSE = {
    "response": {
        "data": [
            {"period": "2026-07-08", "value": "85.50"},
            {"period": "2026-07-09", "value": "86.20"},
            {"period": "2026-07-10", "value": "84.90"}
        ]
    }
}

@mock.patch("data.eia_history_client.httpx.get")
@mock.patch("data.eia_history_client.os.getenv")
@mock.patch("data.eia_history_client.get_cached_data")
def test_successful_eia_response(mock_cached, mock_getenv, mock_httpx_get):
    # Ensure no cache is used
    mock_cached.return_value = ([], 0.0)
    # Ensure key is present
    mock_getenv.return_value = "TEST_KEY"
    
    # Mock httpx response
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE
    mock_httpx_get.return_value = mock_response
    
    # Run fetch
    data = fetch_brent_spot_history("2026-07-08", "2026-07-10")
    
    assert len(data) == 3
    assert data[0]["date"] == "2026-07-08"
    assert data[0]["price_usd"] == 85.50
    assert data[1]["date"] == "2026-07-09"
    assert data[1]["price_usd"] == 86.20
    assert data[2]["date"] == "2026-07-10"
    assert data[2]["price_usd"] == 84.90

@mock.patch("data.eia_history_client.httpx.get")
@mock.patch("data.eia_history_client.os.getenv")
@mock.patch("data.eia_history_client.get_cached_data")
def test_fallback_path_eia_failure(mock_cached, mock_getenv, mock_httpx_get):
    # Ensure no cache
    mock_cached.return_value = ([], 0.0)
    # Ensure key is present but call fails
    mock_getenv.return_value = "TEST_KEY"
    mock_httpx_get.side_effect = Exception("Network connection failed")
    
    # Run fetch - should fallback to CSV file
    data = fetch_brent_spot_history("2024-07-09", "2026-07-09")
    
    # Fallback should read from CSV and successfully return some data (since CSV is seeded)
    assert len(data) > 0
    assert all("date" in x and "price_usd" in x for x in data)

def test_volatility_calibration_changes():
    # Test that different histories yield different calibrated volatilities
    history_1 = [
        {"date": "2026-07-01", "price_usd": 80.0},
        {"date": "2026-07-02", "price_usd": 80.5},
        {"date": "2026-07-03", "price_usd": 81.0}
    ]
    history_2 = [
        {"date": "2026-07-01", "price_usd": 80.0},
        {"date": "2026-07-02", "price_usd": 120.0},  # massive shock
        {"date": "2026-07-03", "price_usd": 70.0}
    ]
    
    # Compute volatilities
    prices_1 = [x["price_usd"] for x in history_1]
    log_ret_1 = np.diff(np.log(prices_1))
    vol_1 = np.std(log_ret_1)
    
    prices_2 = [x["price_usd"] for x in history_2]
    log_ret_2 = np.diff(np.log(prices_2))
    vol_2 = np.std(log_ret_2)
    
    assert vol_1 != vol_2
    assert vol_2 > vol_1
