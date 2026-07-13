"""
conftest.py — Shared fixtures for the entire test suite.

Run all tests with:
    pytest "TESTING FILES/" -v --tb=short
"""
import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Path setup — make all project modules importable from any test file
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHARED = os.path.join(ROOT, "shared")
SCENARIO = os.path.join(ROOT, "scenario-engine")
SPR = os.path.join(ROOT, "spr-agent")

for p in [ROOT, SHARED, SCENARIO, SPR]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Sample API response payloads (used across Stage 1 tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_eia_response():
    return {
        "response": {
            "data": [
                {
                    "period": "2026-07-10",
                    "value": "85.43",
                    "units": "$/barrel",
                    "product-name": "Brent",
                }
            ]
        }
    }


@pytest.fixture
def sample_gdelt_row():
    """Simulates a parsed first row from a GDELT 2.0 event export."""
    return {
        "GLOBALEVENTID": 123456789,
        "SQLDATE": "20260710",
        "Actor1CountryCode": "IRN",
        "Actor2CountryCode": "USA",
        "GoldsteinScale": -7.4,
        "NumMentions": 25,
        "AvgTone": -5.2,
        "ActionGeo_CountryCode": "IR",
        "ActionGeo_Lat": 26.5,
        "ActionGeo_Long": 56.2,
        "SOURCEURL": "https://example.com/hormuz-tension",
    }


@pytest.fixture
def sample_ais_message():
    """Simulates a single decoded AIS PositionReport WebSocket message."""
    return {
        "message_type": "PositionReport",
        "mmsi": 477213500,
        "ship_name": "TANKER ARTEMIS",
        "latitude": 26.1,
        "longitude": 56.4,
        "speed": 12.5,
        "course": 270.0,
        "timestamp": "2026-07-10T14:30:00Z",
    }


@pytest.fixture
def sample_ofac_result_sanctioned():
    return {
        "entity": "NATIONAL IRANIAN OIL COMPANY",
        "sanctioned": True,
        "match_count": 3,
        "matches": [
            {
                "ent_num": "4001",
                "SDN_Name": "NATIONAL IRANIAN OIL COMPANY",
                "SDN_Type": "-0- ",
                "Program": "IRAN",
                "Remarks": "state-owned",
            }
        ],
    }


@pytest.fixture
def sample_ofac_result_clear():
    return {
        "entity": "TOTALLY SAFE SHIPPING CO",
        "sanctioned": False,
        "match_count": 0,
        "matches": [],
    }


# ---------------------------------------------------------------------------
# Scenario Engine — valid request payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_simulate_request():
    return {
        "risk_score": 75.0,
        "corridor": "hormuz",
        "shock_duration_days": 30,
        "num_simulations": 2000,
        "current_brent_usd": 85.0,
        "elasticity_assumptions": {
            "price_elasticity_of_demand": -0.05,
            "pass_through_rate_to_pump": 0.6,
            "gdp_sensitivity_per_10pct_oil_shock": -0.15,
        },
    }


@pytest.fixture
def valid_spr_request():
    N = 7
    return {
        "planning_horizon_days": N,
        "current_reserve_days": 9.5,
        "min_safety_floor_days": 3.0,
        "daily_risk_scores": [80.0] * N,
        "daily_price_forecast_usd_per_bbl": [100.0] * N,
        "max_daily_drawdown_days": 1.0,
    }
