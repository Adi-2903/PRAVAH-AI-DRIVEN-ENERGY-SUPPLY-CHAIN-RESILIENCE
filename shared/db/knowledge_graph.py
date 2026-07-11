# shared/db/knowledge_graph.py
import sys
import networkx as nx

# Windows consoles default to cp1252, which can't encode the → arrows printed
# in the demo block below. Reconfigure stdout to UTF-8 so `python
# shared/db/knowledge_graph.py` runs identically on Windows, macOS and Linux.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def build_supply_chain_graph():
    """
    Build the Pravah supply chain knowledge graph.
    Nodes: suppliers, corridors, ports, refineries, fuel_types
    Edges: represent flow of oil through the supply chain

    Corridor node IDs are lowercase (hormuz, redsea, cape) to match
    corridors.name in the database exactly — do not reintroduce
    uppercase variants anywhere in this file.
    """
    G = nx.DiGraph()

    # --- Supplier Nodes ---
    suppliers = [
        ("SAU_ARAMCO", {"type": "supplier", "country": "SAU", "grade": "Arab Light", "capacity_mbpd": 10.0}),
        ("IRQ_SOMO",   {"type": "supplier", "country": "IRQ", "grade": "Basra Light", "capacity_mbpd": 4.5}),
        ("RUS_ROSNEFT",{"type": "supplier", "country": "RUS", "grade": "Urals",       "capacity_mbpd": 5.0}),
        ("NGA_NNPC",   {"type": "supplier", "country": "NGA", "grade": "Bonny Light", "capacity_mbpd": 1.5}),
    ]
    G.add_nodes_from(suppliers)

    # --- Corridor Nodes (lowercase — matches corridors.name in the DB) ---
    corridors = [
        ("hormuz",  {"type": "corridor", "risk_baseline": 60, "tankers_per_day": 17}),
        ("redsea",  {"type": "corridor", "risk_baseline": 50, "tankers_per_day": 12}),
        ("cape",    {"type": "corridor", "risk_baseline": 15, "tankers_per_day": 5}),
    ]
    G.add_nodes_from(corridors)

    # --- Port Nodes ---
    ports = [
        ("PORT_MUMBAI",    {"type": "port", "capacity_mbpd": 1.2, "lat": 18.93, "lng": 72.84}),
        ("PORT_KANDLA",    {"type": "port", "capacity_mbpd": 0.9, "lat": 23.00, "lng": 70.22}),
        ("PORT_VADINAR",   {"type": "port", "capacity_mbpd": 1.5, "lat": 22.47, "lng": 69.77}),
        ("PORT_PARADIP",   {"type": "port", "capacity_mbpd": 0.5, "lat": 20.32, "lng": 86.61}),
    ]
    G.add_nodes_from(ports)

    # --- Refinery Nodes ---
    refineries = [
        ("REF_JAMNAGAR",  {"type": "refinery", "capacity_mbpd": 1.24, "operator": "Reliance"}),
        ("REF_MUMBAI",    {"type": "refinery", "capacity_mbpd": 0.24, "operator": "BPCL"}),
        ("REF_PARADIP",   {"type": "refinery", "capacity_mbpd": 0.30, "operator": "IOCL"}),
    ]
    G.add_nodes_from(refineries)

    # --- Fuel Type Nodes ---
    fuels = [
        ("FUEL_DIESEL",  {"type": "fuel"}),
        ("FUEL_PETROL",  {"type": "fuel"}),
        ("FUEL_LPG",     {"type": "fuel"}),
        ("FUEL_ATF",     {"type": "fuel"}),
    ]
    G.add_nodes_from(fuels)

    # --- Edges: Supplier → Corridor (which route does each supplier use?) ---
    G.add_edge("SAU_ARAMCO", "hormuz",  transit_days=2,  share=0.85)
    G.add_edge("SAU_ARAMCO", "redsea",  transit_days=8,  share=0.15)
    G.add_edge("IRQ_SOMO",   "hormuz",  transit_days=3,  share=0.90)
    G.add_edge("IRQ_SOMO",   "cape",    transit_days=40, share=0.10)
    G.add_edge("RUS_ROSNEFT","redsea",  transit_days=12, share=0.70)
    G.add_edge("RUS_ROSNEFT","cape",    transit_days=35, share=0.30)
    G.add_edge("NGA_NNPC",   "cape",    transit_days=25, share=1.00)

    # --- Edges: Corridor → Port ---
    G.add_edge("hormuz", "PORT_VADINAR",  capacity_fraction=0.50)
    G.add_edge("hormuz", "PORT_KANDLA",   capacity_fraction=0.30)
    G.add_edge("hormuz", "PORT_MUMBAI",   capacity_fraction=0.20)
    G.add_edge("redsea", "PORT_MUMBAI",   capacity_fraction=0.60)
    G.add_edge("redsea", "PORT_PARADIP",  capacity_fraction=0.40)
    G.add_edge("cape",   "PORT_PARADIP",  capacity_fraction=1.00)

    # --- Edges: Port → Refinery ---
    G.add_edge("PORT_VADINAR", "REF_JAMNAGAR", pipeline=True)
    G.add_edge("PORT_KANDLA",  "REF_JAMNAGAR", pipeline=False, road_km=120)
    G.add_edge("PORT_MUMBAI",  "REF_MUMBAI",   pipeline=True)
    G.add_edge("PORT_PARADIP", "REF_PARADIP",  pipeline=True)

    # --- Edges: Refinery → Fuel Type ---
    for refinery in ["REF_JAMNAGAR", "REF_MUMBAI", "REF_PARADIP"]:
        for fuel in ["FUEL_DIESEL", "FUEL_PETROL", "FUEL_LPG", "FUEL_ATF"]:
            G.add_edge(refinery, fuel)

    return G


def get_paths_for_corridor(G, corridor_name: str):
    """Return all end-to-end paths that pass through a given corridor node.
    corridor_name should be lowercase (hormuz, redsea, cape, domestic) to
    match the node IDs used in the graph above."""
    corridor_node = corridor_name.lower()
    if corridor_node not in G:
        return []

    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]
    fuels     = [n for n, d in G.nodes(data=True) if d.get("type") == "fuel"]

    all_paths = []
    for supplier in suppliers:
        for fuel in fuels:
            try:
                for path in nx.all_simple_paths(G, supplier, fuel):
                    if corridor_node in path:
                        all_paths.append(path)
            except nx.NetworkXNoPath:
                pass
    return all_paths


if __name__ == "__main__":
    G = build_supply_chain_graph()
    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    paths = get_paths_for_corridor(G, "hormuz")
    print(f"\nPaths through Hormuz: {len(paths)}")
    for p in paths[:3]:  # print first 3
        print("  →", " → ".join(p))
