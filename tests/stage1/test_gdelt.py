"""
test_gdelt.py — GDELT client unit tests. Mocks all HTTP calls and zipfile extraction.
"""
import sys, os
CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "clients")
if CLIENTS_DIR not in sys.path:
    sys.path.insert(0, CLIENTS_DIR)

import pytest
import io, zipfile
from unittest.mock import patch, MagicMock
import gdelt_client


def make_zip_with_csv(csv_content: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("20260710120000.export.CSV", csv_content)
    return buf.getvalue()


def make_tab_row(**fields):
    row = [""] * 61
    col_map = {0: "GLOBALEVENTID", 1: "SQLDATE", 7: "Actor1CountryCode",
               17: "Actor2CountryCode", 30: "GoldsteinScale", 31: "NumMentions",
               34: "AvgTone", 53: "ActionGeo_CountryCode", 56: "ActionGeo_Lat",
               57: "ActionGeo_Long", 60: "SOURCEURL"}
    reverse = {v: k for k, v in col_map.items()}
    for name, val in fields.items():
        if name in reverse:
            row[reverse[name]] = str(val)
    return "\t".join(row)


def build_mocks(tab_row: str):
    lastupdate_content = "12345 md5abc https://example.com/test.export.CSV.zip\n"
    zip_content = make_zip_with_csv(tab_row)
    mock1 = MagicMock()
    mock1.text = lastupdate_content
    mock1.raise_for_status.return_value = None
    mock2 = MagicMock()
    mock2.content = zip_content
    mock2.raise_for_status.return_value = None
    return mock1, mock2


def test_gdelt_returns_required_keys():
    tab_row = make_tab_row(GLOBALEVENTID=99, Actor1CountryCode="IRN",
                           GoldsteinScale=-7.4, ActionGeo_Lat=26.5,
                           ActionGeo_Long=56.2, SOURCEURL="https://example.com")
    mock1, mock2 = build_mocks(tab_row)
    with patch("gdelt_client.requests.get", side_effect=[mock1, mock2]):
        result = gdelt_client.fetch_latest_events()
    assert "GLOBALEVENTID" in result
    assert "GoldsteinScale" in result
    assert "ActionGeo_Lat" in result
    assert "SOURCEURL" in result

def test_gdelt_numeric_fields_are_numeric():
    tab_row = make_tab_row(GoldsteinScale=-3.5, AvgTone=-2.1,
                           ActionGeo_Lat=25.0, ActionGeo_Long=56.0)
    mock1, mock2 = build_mocks(tab_row)
    with patch("gdelt_client.requests.get", side_effect=[mock1, mock2]):
        result = gdelt_client.fetch_latest_events()
    for field in ["GoldsteinScale", "AvgTone", "ActionGeo_Lat", "ActionGeo_Long"]:
        val = result.get(field)
        assert val is None or isinstance(val, float), f"{field}: expected float or None, got {type(val)}"

def test_gdelt_raises_on_empty_csv():
    empty_zip = make_zip_with_csv("")
    lastupdate = "12345 md5 https://example.com/test.export.CSV.zip\n"
    mock1 = MagicMock(text=lastupdate)
    mock1.raise_for_status.return_value = None
    mock2 = MagicMock(content=empty_zip)
    mock2.raise_for_status.return_value = None
    with patch("gdelt_client.requests.get", side_effect=[mock1, mock2]):
        with pytest.raises((ValueError, Exception), match=r"empty|No columns"):
            gdelt_client.fetch_latest_events()

def test_gdelt_raises_on_malformed_lastupdate():
    mock1 = MagicMock(text="only_one_token\n")
    mock1.raise_for_status.return_value = None
    with patch("gdelt_client.requests.get", return_value=mock1):
        with pytest.raises(ValueError, match="format"):
            gdelt_client.fetch_latest_events()

def test_gdelt_empty_numeric_field_returns_none():
    """Empty string in numeric field must map to None, not crash."""
    tab_row = "\t" * 60  # 61 empty fields
    mock1, mock2 = build_mocks(tab_row)
    with patch("gdelt_client.requests.get", side_effect=[mock1, mock2]):
        result = gdelt_client.fetch_latest_events()
    assert result.get("GoldsteinScale") is None
    assert result.get("ActionGeo_Lat") is None
