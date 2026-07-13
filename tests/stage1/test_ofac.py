"""
test_ofac.py — OFAC client unit tests.
"""
import sys, os
CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "clients")
if CLIENTS_DIR not in sys.path:
    sys.path.insert(0, CLIENTS_DIR)

import pytest
import pandas as pd
from unittest.mock import patch
import ofac_client


def make_sdn_df(names):
    return pd.DataFrame({
        "SDN_Name": names, "SDN_Type": ["-0-"] * len(names),
        "Program": ["IRAN"] * len(names), "ent_num": range(len(names)),
        "Remarks": [""] * len(names),
    })


def test_ofac_known_sanctioned_entity():
    """NATIONAL IRANIAN OIL COMPANY must ALWAYS be sanctioned (uses real local cache)."""
    result = ofac_client.check_entity_sanctions(ofac_client.KNOWN_SANCTIONED_ENTITY)
    assert result["sanctioned"] is True
    assert result["match_count"] > 0

def test_ofac_result_structure():
    result = ofac_client.check_entity_sanctions(ofac_client.KNOWN_SANCTIONED_ENTITY)
    assert "entity" in result
    assert "sanctioned" in result
    assert "match_count" in result
    assert "matches" in result
    assert isinstance(result["sanctioned"], bool)
    assert isinstance(result["match_count"], int)
    assert isinstance(result["matches"], list)

def test_ofac_clear_entity():
    result = ofac_client.check_entity_sanctions("TOTALLY CLEAR SHIPPING COMPANY XYZ999")
    assert result["sanctioned"] is False
    assert result["match_count"] == 0

def test_ofac_case_insensitive():
    upper = ofac_client.check_entity_sanctions("NATIONAL IRANIAN OIL COMPANY")
    lower = ofac_client.check_entity_sanctions("national iranian oil company")
    assert upper["sanctioned"] == lower["sanctioned"]

def test_ofac_matches_capped_at_five():
    sdn_df = make_sdn_df([f"IRANIAN ENTITY {i}" for i in range(20)])
    with patch.object(ofac_client, "_load_sdn_list", return_value=sdn_df):
        result = ofac_client.check_entity_sanctions("IRANIAN ENTITY")
    assert len(result["matches"]) <= 5

def test_ofac_match_record_structure():
    result = ofac_client.check_entity_sanctions(ofac_client.KNOWN_SANCTIONED_ENTITY)
    if result["matches"]:
        match = result["matches"][0]
        assert "SDN_Name" in match
        assert "SDN_Type" in match
        assert "Program" in match

def test_ofac_null_names_do_not_crash():
    df = make_sdn_df(["VALID ENTITY", None, "ANOTHER ENTITY"])
    with patch.object(ofac_client, "_load_sdn_list", return_value=df):
        result = ofac_client.check_entity_sanctions("VALID ENTITY")
    assert result["sanctioned"] is True

def test_ofac_empty_sdn_list_returns_clear():
    df = pd.DataFrame({"SDN_Name": pd.Series([], dtype=str), "SDN_Type": [], "Program": [],
                       "ent_num": [], "Remarks": []})
    with patch.object(ofac_client, "_load_sdn_list", return_value=df):
        result = ofac_client.check_entity_sanctions("ANYONE")
    assert result["sanctioned"] is False
