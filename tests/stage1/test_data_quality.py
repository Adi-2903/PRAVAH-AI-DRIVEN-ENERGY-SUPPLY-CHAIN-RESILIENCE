"""
test_data_quality.py — Data quality edge case tests for all three live clients.
"""
import sys, os
CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "clients")
if CLIENTS_DIR not in sys.path:
    sys.path.insert(0, CLIENTS_DIR)

import pytest
import io, zipfile
import pandas as pd
from unittest.mock import patch, MagicMock
import eia_spot_client as eia_client, ofac_client, gdelt_client


def make_eia_mock(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock

def make_sdn_df(names):
    return pd.DataFrame({
        "SDN_Name": names, "SDN_Type": ["-0-"] * len(names),
        "Program": ["X"] * len(names), "ent_num": range(len(names)),
        "Remarks": [""] * len(names),
    })


# ── EIA ──────────────────────────────────────────────────────────────────────

def test_eia_missing_period_returns_none():
    response = {"response": {"data": [{"value": "85.0", "units": "$/barrel", "product-name": "Brent"}]}}
    with patch.object(eia_client, "EIA_API_KEY", "fake"), \
         patch("eia_spot_client.requests.get", return_value=make_eia_mock(response)):
        result = eia_client.fetch_latest_brent_price()
    assert result["date"] is None

def test_eia_negative_price_not_silently_dropped():
    response = {"response": {"data": [
        {"period": "2026-07-10", "value": "-5.0", "units": "$/barrel", "product-name": "Brent"}
    ]}}
    with patch.object(eia_client, "EIA_API_KEY", "fake"), \
         patch("eia_spot_client.requests.get", return_value=make_eia_mock(response)):
        result = eia_client.fetch_latest_brent_price()
    assert result["price"] is not None  # value returned, not silently None

def test_eia_missing_data_key_raises():
    response = {"response": {}}
    with patch.object(eia_client, "EIA_API_KEY", "fake"), \
         patch("eia_spot_client.requests.get", return_value=make_eia_mock(response)):
        with pytest.raises(ValueError):
            eia_client.fetch_latest_brent_price()


# ── OFAC ─────────────────────────────────────────────────────────────────────

def test_ofac_null_names_do_not_crash():
    df = make_sdn_df(["VALID ENTITY", None, "ANOTHER"])
    with patch.object(ofac_client, "_load_sdn_list", return_value=df):
        result = ofac_client.check_entity_sanctions("VALID ENTITY")
    assert result["sanctioned"] is True

def test_ofac_empty_list_returns_clear():
    df = pd.DataFrame({"SDN_Name": pd.Series([], dtype=str), "SDN_Type": [],
                       "Program": [], "ent_num": [], "Remarks": []})
    with patch.object(ofac_client, "_load_sdn_list", return_value=df):
        result = ofac_client.check_entity_sanctions("ANYONE")
    assert result["sanctioned"] is False
    assert result["match_count"] == 0

def test_ofac_empty_entity_name_does_not_crash():
    df = make_sdn_df(["IRAN CORP", "RUSSIA BANK"])
    with patch.object(ofac_client, "_load_sdn_list", return_value=df):
        result = ofac_client.check_entity_sanctions("")
    assert isinstance(result["sanctioned"], bool)


# ── GDELT ─────────────────────────────────────────────────────────────────────

def test_gdelt_empty_numeric_field_returns_none():
    tab_row = "\t" * 60  # 61 empty fields
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.CSV", tab_row)
    zip_bytes = buf.getvalue()

    lastupdate = "12345 md5 https://example.com/test.zip\n"
    mock1 = MagicMock(text=lastupdate)
    mock1.raise_for_status.return_value = None
    mock2 = MagicMock(content=zip_bytes)
    mock2.raise_for_status.return_value = None

    with patch("gdelt_client.requests.get", side_effect=[mock1, mock2]):
        result = gdelt_client.fetch_latest_events()

    assert result.get("GoldsteinScale") is None
    assert result.get("ActionGeo_Lat") is None
