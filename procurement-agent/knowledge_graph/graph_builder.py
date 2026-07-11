import networkx as nx

def build_procurement_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # --- Suppliers ---
    # Costs reflect realistic 2024-25 import prices (USD/bbl landed India)
    suppliers = {
        "SAU_ARAMCO":  {"type": "supplier", "cost": 82.4,  "grade": "medium_sour",  "country": "Saudi Arabia"},
        "IRQ_SOMO":    {"type": "supplier", "cost": 79.8,  "grade": "medium_sour",  "country": "Iraq"},
        "UAE_ADNOC":   {"type": "supplier", "cost": 83.5,  "grade": "light_sweet",  "country": "UAE"},
        "RUS_ROSNEFT": {"type": "supplier", "cost": 68.0,  "grade": "medium_sour",  "country": "Russia"},
        "USA_WTI":     {"type": "supplier", "cost": 88.5,  "grade": "light_sweet",  "country": "USA"},
        "NGA_NNPC":    {"type": "supplier", "cost": 86.0,  "grade": "light_sweet",  "country": "Nigeria"},
        "KWT_KPC":     {"type": "supplier", "cost": 80.2,  "grade": "medium_sour",  "country": "Kuwait"},
        "MEX_PEMEX":   {"type": "supplier", "cost": 77.5,  "grade": "heavy_sour",   "country": "Mexico"},
    }
    for s_name, s_data in suppliers.items():
        G.add_node(s_name, **s_data)

    # --- Routes (each with distinct risk profiles) ---
    routes = {
        # Strait of Hormuz — currently high-risk
        "hormuz_saudi":  {"type": "route", "risk": 78,  "corridor": "Hormuz Strait", "display": "Hormuz (Saudi leg)"},
        "hormuz_iraq":   {"type": "route", "risk": 74,  "corridor": "Hormuz Strait", "display": "Hormuz (Iraq leg)"},
        "hormuz_uae":    {"type": "route", "risk": 76,  "corridor": "Hormuz Strait", "display": "Hormuz (UAE leg)"},
        "hormuz_kuwait": {"type": "route", "risk": 77,  "corridor": "Hormuz Strait", "display": "Hormuz (Kuwait leg)"},
        # Iraq direct overland/pipeline to Jamnagar via VLCC
        "basra_direct":  {"type": "route", "risk": 38,  "corridor": "Basra–India",   "display": "Basra Direct VLCC"},
        # Red Sea (Russia via Suez)
        "red_sea_suez":  {"type": "route", "risk": 85,  "corridor": "Red Sea/Suez",  "display": "Red Sea / Suez"},
        # Cape of Good Hope (bypass Hormuz & Red Sea)
        "cape_russia":   {"type": "route", "risk": 18,  "corridor": "Cape Route",    "display": "Cape of Good Hope (Russia)"},
        "cape_nigeria":  {"type": "route", "risk": 16,  "corridor": "Cape Route",    "display": "Cape of Good Hope (Nigeria)"},
        "cape_mexico":   {"type": "route", "risk": 14,  "corridor": "Trans-Atlantic", "display": "Trans-Atlantic / Cape"},
        # Pacific to India (USA)
        "pacific_india": {"type": "route", "risk": 12,  "corridor": "Pacific–India", "display": "Pacific–India"},
    }
    for r_name, r_data in routes.items():
        G.add_node(r_name, **r_data)

    # --- Ports ---
    ports = {
        "PORT_VADINAR":  {"type": "port", "display": "Vadinar Port"},
        "PORT_KANDLA":   {"type": "port", "display": "Kandla Port"},
        "PORT_MUMBAI":   {"type": "port", "display": "Mumbai JNPT"},
        "PORT_PARADIP":  {"type": "port", "display": "Paradip Port"},
        "PORT_MANGALORE":{"type": "port", "display": "Mangalore Port"},
        "PORT_VIZAG":    {"type": "port", "display": "Visakhapatnam"},
    }
    for p_name, p_data in ports.items():
        G.add_node(p_name, **p_data)

    # --- Refineries ---
    refineries = {
        "REF_JAMNAGAR":  {"type": "refinery", "display": "Jamnagar (RIL)"},
        "REF_VADINAR":   {"type": "refinery", "display": "Vadinar (Nayara)"},
        "REF_MUMBAI":    {"type": "refinery", "display": "Mumbai (BPCL/HPCL)"},
        "REF_PARADIP":   {"type": "refinery", "display": "Paradip (IOCL)"},
        "REF_MANGALORE": {"type": "refinery", "display": "Mangalore (MRPL)"},
        "REF_VIZAG":     {"type": "refinery", "display": "Visakhapatnam (HPCL)"},
    }
    for r_name, r_data in refineries.items():
        G.add_node(r_name, **r_data)

    # --- Crude Grades ---
    grades = {
        "GRADE_MEDIUM_SOUR": {"type": "grade", "display": "Medium Sour"},
        "GRADE_LIGHT_SWEET": {"type": "grade", "display": "Light Sweet"},
        "GRADE_HEAVY_SOUR":  {"type": "grade", "display": "Heavy Sour"},
    }
    for g_name, g_data in grades.items():
        G.add_node(g_name, **g_data)

    # ── Edges: Supplier → Route (transit_days reflects realistic voyage days) ──
    G.add_edge("SAU_ARAMCO",  "hormuz_saudi",  transit_days=9)
    G.add_edge("IRQ_SOMO",    "hormuz_iraq",   transit_days=10)
    G.add_edge("IRQ_SOMO",    "basra_direct",  transit_days=12)
    G.add_edge("UAE_ADNOC",   "hormuz_uae",    transit_days=8)
    G.add_edge("KWT_KPC",     "hormuz_kuwait", transit_days=10)
    G.add_edge("RUS_ROSNEFT", "red_sea_suez",  transit_days=18)
    G.add_edge("RUS_ROSNEFT", "cape_russia",   transit_days=42)
    G.add_edge("NGA_NNPC",    "cape_nigeria",  transit_days=24)
    G.add_edge("USA_WTI",     "pacific_india", transit_days=28)
    G.add_edge("MEX_PEMEX",   "cape_mexico",   transit_days=32)

    # ── Edges: Route → Port ──
    G.add_edge("hormuz_saudi",  "PORT_VADINAR")
    G.add_edge("hormuz_iraq",   "PORT_KANDLA")
    G.add_edge("hormuz_uae",    "PORT_VADINAR")
    G.add_edge("hormuz_kuwait", "PORT_VADINAR")
    G.add_edge("basra_direct",  "PORT_VADINAR")
    G.add_edge("red_sea_suez",  "PORT_PARADIP")
    G.add_edge("cape_russia",   "PORT_MANGALORE")
    G.add_edge("cape_nigeria",  "PORT_MANGALORE")
    G.add_edge("cape_mexico",   "PORT_MANGALORE")
    G.add_edge("pacific_india", "PORT_VIZAG")

    # ── Edges: Port → Refinery ──
    G.add_edge("PORT_VADINAR",   "REF_JAMNAGAR")
    G.add_edge("PORT_VADINAR",   "REF_VADINAR")
    G.add_edge("PORT_KANDLA",    "REF_JAMNAGAR")
    G.add_edge("PORT_MUMBAI",    "REF_MUMBAI")
    G.add_edge("PORT_PARADIP",   "REF_PARADIP")
    G.add_edge("PORT_MANGALORE", "REF_MANGALORE")
    G.add_edge("PORT_VIZAG",     "REF_VIZAG")

    # ── Edges: Refinery → Grade (compatibility 0–1) ──
    G.add_edge("REF_JAMNAGAR",  "GRADE_MEDIUM_SOUR", compatibility=0.95)
    G.add_edge("REF_JAMNAGAR",  "GRADE_LIGHT_SWEET",  compatibility=0.88)
    G.add_edge("REF_JAMNAGAR",  "GRADE_HEAVY_SOUR",   compatibility=0.72)

    G.add_edge("REF_VADINAR",   "GRADE_MEDIUM_SOUR", compatibility=0.92)
    G.add_edge("REF_VADINAR",   "GRADE_LIGHT_SWEET",  compatibility=0.85)
    G.add_edge("REF_VADINAR",   "GRADE_HEAVY_SOUR",   compatibility=0.68)

    G.add_edge("REF_MUMBAI",    "GRADE_MEDIUM_SOUR", compatibility=0.88)
    G.add_edge("REF_MUMBAI",    "GRADE_LIGHT_SWEET",  compatibility=0.82)

    G.add_edge("REF_PARADIP",   "GRADE_MEDIUM_SOUR", compatibility=0.90)
    G.add_edge("REF_PARADIP",   "GRADE_HEAVY_SOUR",   compatibility=0.75)

    G.add_edge("REF_MANGALORE", "GRADE_LIGHT_SWEET",  compatibility=0.92)
    G.add_edge("REF_MANGALORE", "GRADE_MEDIUM_SOUR", compatibility=0.80)

    G.add_edge("REF_VIZAG",     "GRADE_LIGHT_SWEET",  compatibility=0.90)
    G.add_edge("REF_VIZAG",     "GRADE_MEDIUM_SOUR", compatibility=0.78)

    return G


def get_grade_compatibility(graph: nx.DiGraph, refinery: str, grade: str) -> float:
    if graph.has_edge(refinery, grade):
        return graph[refinery][grade].get("compatibility", 0.0)
    return 0.0
