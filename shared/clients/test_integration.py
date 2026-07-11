# shared/clients/test_integration.py
import os
import pytest
from fastapi.testclient import TestClient

# Ensure python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.main import app
from shared.clients.eia_client import fetch_latest_brent_price
from shared.clients.gdelt_client import fetch_latest_events
from shared.clients.ais_client import get_sample_ship_position
from shared.clients.ofac_client import check_entity_sanctions, KNOWN_SANCTIONED_ENTITY
from shared.db.knowledge_graph import build_supply_chain_graph

client = TestClient(app)

def test_ingestion_and_graph_integration():
    """
    Integration test that triggers realistic ingestion cycles, rebuilds the
    knowledge graph, and asserts the system status accurately reflects the state.
    """
    # 1. Trigger realistic ingestion cycle (these will write to DB if Supabase is configured)
    eia_result = fetch_latest_brent_price()
    assert eia_result is not None
    assert "price" in eia_result

    gdelt_result = fetch_latest_events()
    assert gdelt_result is not None
    
    ais_result = get_sample_ship_position()
    assert ais_result is not None
    
    ofac_result = check_entity_sanctions(KNOWN_SANCTIONED_ENTITY)
    assert ofac_result is not None
    assert ofac_result["sanctioned"] == True
    
    # 2. Rebuild knowledge graph and assert it reflects state
    G = build_supply_chain_graph()
    assert G.number_of_nodes() > 0
    
    # Suppliers should be present (either from DB or fallback)
    assert "SAU_ARAMCO" in G.nodes()
    assert "hormuz" in G.nodes()
    
    # 3. Hit /system-status and assert it accurately reflects state
    response = client.get("/system-status")
    assert response.status_code == 200
    data = response.json()
    
    assert "data_sources" in data
    assert "database" in data
    assert "knowledge_graph" in data
    
    kg_data = data["knowledge_graph"]
    assert kg_data["nodes"] == G.number_of_nodes()
    assert kg_data["edges"] == G.number_of_edges()
    
    # Check that EIA source is reported
    assert "eia" in data["data_sources"]
    assert data["data_sources"]["eia"]["status"] in ["live", "fallback"]
