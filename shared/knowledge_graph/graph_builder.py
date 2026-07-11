import networkx as nx

def build_procurement_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    
    # --- Suppliers ---
    suppliers = {
        "saudi_arabia": {"type": "supplier", "cost": 82.4, "grade": "medium_sour"},
        "iraq": {"type": "supplier", "cost": 84.5, "grade": "medium_sour"},
        "uae": {"type": "supplier", "cost": 83.0, "grade": "light_sweet"},
        "russia": {"type": "supplier", "cost": 72.0, "grade": "medium_sour"},
        "us": {"type": "supplier", "cost": 86.0, "grade": "light_sweet"},
        "nigeria": {"type": "supplier", "cost": 88.0, "grade": "light_sweet"}
    }
    
    for s_name, s_data in suppliers.items():
        G.add_node(s_name, **s_data)
        
    # --- Routes ---
    routes = {
        "hormuz_strait": {"type": "route", "risk": 78},
        "red_sea": {"type": "route", "risk": 85},
        "cape_of_good_hope": {"type": "route", "risk": 20},
        "basra_to_jamnagar": {"type": "route", "risk": 34},
        "pacific_to_india": {"type": "route", "risk": 15},
    }
    
    for r_name, r_data in routes.items():
        G.add_node(r_name, **r_data)
        
    # --- Ports ---
    ports = {
        "jamnagar_port": {"type": "port"},
        "vadinar": {"type": "port"},
        "paradip": {"type": "port"},
        "mangalore": {"type": "port"},
        "vizag": {"type": "port"},
        "basra": {"type": "port"}
    }
    
    for p_name, p_data in ports.items():
        G.add_node(p_name, **p_data)
        
    # --- Refineries ---
    refineries = {
        "jamnagar": {"type": "refinery"},
        "vadinar_refinery": {"type": "refinery"},
        "paradip_refinery": {"type": "refinery"},
        "mangalore_refinery": {"type": "refinery"},
        "vizag_refinery": {"type": "refinery"},
    }
    
    for r_name, r_data in refineries.items():
        G.add_node(r_name, **r_data)
        
    # --- Grades (Fuels) ---
    grades = {
        "light_sweet": {"type": "grade"},
        "medium_sour": {"type": "grade"},
        "heavy_sour": {"type": "grade"},
    }
    
    for g_name, g_data in grades.items():
        G.add_node(g_name, **g_data)
        
    # Edges: Supplier -> Route
    G.add_edge("saudi_arabia", "hormuz_strait", transit_days=9)
    G.add_edge("iraq", "basra_to_jamnagar", transit_days=11)
    G.add_edge("iraq", "hormuz_strait", transit_days=10)
    G.add_edge("uae", "hormuz_strait", transit_days=8)
    G.add_edge("russia", "red_sea", transit_days=20)
    G.add_edge("russia", "cape_of_good_hope", transit_days=45)
    G.add_edge("us", "pacific_to_india", transit_days=30)
    G.add_edge("nigeria", "cape_of_good_hope", transit_days=25)
    
    # Route -> Port
    G.add_edge("hormuz_strait", "jamnagar_port")
    G.add_edge("basra_to_jamnagar", "basra")
    G.add_edge("basra", "jamnagar_port") # Link port to port to allow path? No, supplier -> route -> port
    
    # Wait, basra_to_jamnagar route -> basra port -> jamnagar refinery
    G.add_edge("basra_to_jamnagar", "jamnagar_port")
    
    G.add_edge("hormuz_strait", "vadinar")
    G.add_edge("red_sea", "paradip")
    G.add_edge("cape_of_good_hope", "mangalore")
    G.add_edge("cape_of_good_hope", "paradip")
    G.add_edge("pacific_to_india", "vizag")
    
    # Port -> Refinery
    G.add_edge("jamnagar_port", "jamnagar")
    G.add_edge("vadinar", "vadinar_refinery")
    G.add_edge("paradip", "paradip_refinery")
    G.add_edge("mangalore", "mangalore_refinery")
    G.add_edge("vizag", "vizag_refinery")
    
    # Refinery -> Grade
    G.add_edge("jamnagar", "medium_sour", compatibility=0.92)
    G.add_edge("jamnagar", "light_sweet", compatibility=0.85)
    G.add_edge("jamnagar", "heavy_sour", compatibility=0.7)
    
    G.add_edge("vadinar_refinery", "medium_sour", compatibility=0.9)
    G.add_edge("paradip_refinery", "medium_sour", compatibility=0.9)
    G.add_edge("mangalore_refinery", "light_sweet", compatibility=0.9)
    G.add_edge("vizag_refinery", "light_sweet", compatibility=0.9)
    
    return G

def get_grade_compatibility(graph: nx.DiGraph, refinery: str, grade: str) -> float:
    if graph.has_edge(refinery, grade):
        return graph[refinery][grade].get("compatibility", 0.0)
    return 0.0
