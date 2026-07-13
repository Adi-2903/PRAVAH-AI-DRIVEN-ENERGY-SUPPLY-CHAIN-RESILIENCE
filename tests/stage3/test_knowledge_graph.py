"""
test_knowledge_graph.py — NetworkX graph structural + algorithm tests.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "db"))

import networkx as nx
from knowledge_graph import build_supply_chain_graph, get_paths_for_corridor


@pytest.fixture(scope="module")
def G():
    return build_supply_chain_graph()


# ── NODE EXISTENCE ────────────────────────────────────────────────────────────

def test_graph_has_supplier_nodes(G):
    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]
    assert len(suppliers) >= 4

def test_graph_has_corridor_nodes(G):
    corridors = [n for n, d in G.nodes(data=True) if d.get("type") == "corridor"]
    assert "hormuz" in [n for n in corridors]
    assert "redsea" in [n for n in corridors]
    assert "cape" in [n for n in corridors]

def test_graph_has_port_nodes(G):
    ports = [n for n, d in G.nodes(data=True) if d.get("type") == "port"]
    assert len(ports) >= 3

def test_graph_has_refinery_nodes(G):
    refineries = [n for n, d in G.nodes(data=True) if d.get("type") == "refinery"]
    assert len(refineries) >= 2

def test_graph_has_fuel_nodes(G):
    fuels = [n for n, d in G.nodes(data=True) if d.get("type") == "fuel"]
    assert "FUEL_DIESEL" in fuels
    assert "FUEL_PETROL" in fuels


# ── EDGE INTEGRITY ────────────────────────────────────────────────────────────

def test_supplier_to_corridor_edges_exist(G):
    """Every supplier must have at least one corridor edge."""
    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]
    for s in suppliers:
        neighbors = list(G.successors(s))
        assert len(neighbors) > 0, f"{s} has no outgoing corridor edge"

def test_corridor_to_port_edges_exist(G):
    """Every corridor must connect to at least one port."""
    corridors = [n for n, d in G.nodes(data=True) if d.get("type") == "corridor"]
    for c in corridors:
        ports = [n for n in G.successors(c) if G.nodes[n].get("type") == "port"]
        assert len(ports) > 0, f"Corridor {c} has no port edges"

def test_port_to_refinery_edges_exist(G):
    """Every port must connect to at least one refinery."""
    ports = [n for n, d in G.nodes(data=True) if d.get("type") == "port"]
    for p in ports:
        refineries = [n for n in G.successors(p) if G.nodes[n].get("type") == "refinery"]
        assert len(refineries) > 0, f"Port {p} has no refinery edge"

def test_refinery_to_fuel_edges_exist(G):
    """Every refinery must connect to at least one fuel type."""
    refineries = [n for n, d in G.nodes(data=True) if d.get("type") == "refinery"]
    for r in refineries:
        fuels = [n for n in G.successors(r) if G.nodes[n].get("type") == "fuel"]
        assert len(fuels) > 0, f"Refinery {r} has no fuel edge"


# ── PATH TRAVERSAL ────────────────────────────────────────────────────────────

def test_full_traversal_hormuz_paths_exist(G):
    """At least one Supplier→Corridor→Port→Refinery→Fuel path through hormuz."""
    paths = get_paths_for_corridor(G, "hormuz")
    assert len(paths) > 0

def test_full_traversal_redsea_paths_exist(G):
    paths = get_paths_for_corridor(G, "redsea")
    assert len(paths) > 0

def test_full_traversal_cape_paths_exist(G):
    paths = get_paths_for_corridor(G, "cape")
    assert len(paths) > 0

def test_path_length_is_five_hops(G):
    """Each path must be exactly 5 nodes: Supplier→Corridor→Port→Refinery→Fuel."""
    paths = get_paths_for_corridor(G, "hormuz")
    for path in paths:
        assert len(path) == 5, f"Expected 5-node path, got {len(path)}: {path}"


# ── ALGORITHM EDGE CASES ──────────────────────────────────────────────────────

def test_disconnected_corridor_returns_empty(G):
    """get_paths_for_corridor with unknown corridor returns empty list."""
    result = get_paths_for_corridor(G, "nonexistent_corridor")
    assert result == []

def test_missing_supplier_no_crash(G):
    """Querying paths for a node that doesn't exist should return empty, not raise."""
    H = G.copy()
    H.remove_node("SAU_ARAMCO")
    paths = get_paths_for_corridor(H, "hormuz")
    assert isinstance(paths, list)  # should still work with remaining suppliers

def test_duplicate_node_not_added(G):
    """Adding a duplicate node should not create extra nodes in a copy."""
    H = G.copy()
    original_count = H.number_of_nodes()
    H.add_node("hormuz", type="corridor", risk_baseline=99)  # duplicate
    assert H.number_of_nodes() == original_count  # NetworkX updates attrs, no duplicate

def test_edge_weight_attributes_exist(G):
    """Edges between Supplier→Corridor must carry transit_days and share."""
    for u, v, data in G.edges(data=True):
        if G.nodes[u].get("type") == "supplier" and G.nodes[v].get("type") == "corridor":
            assert "transit_days" in data, f"Edge {u}→{v} missing transit_days"
            assert "share" in data, f"Edge {u}→{v} missing share"

def test_corridor_risk_baseline_valid_range(G):
    """All corridor baselines must be in [0, 100]."""
    for n, d in G.nodes(data=True):
        if d.get("type") == "corridor":
            baseline = d.get("risk_baseline", 0)
            assert 0 <= baseline <= 100, f"{n} baseline out of range: {baseline}"

def test_graph_is_directed(G):
    assert isinstance(G, nx.DiGraph)
