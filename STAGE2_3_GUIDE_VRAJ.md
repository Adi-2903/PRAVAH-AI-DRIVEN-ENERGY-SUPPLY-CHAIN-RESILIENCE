# Pravah: Stage 2 & 3 Build Guide
### For: Vraj
### Owner: shared/ folder (DB + Backend Foundation + Schema Freeze)

Hey Vraj! This guide is **yours to own**. While the others are pulling live data (Stage 1),
you are building the foundation that every single agent will talk to. Think of yourself as
the infrastructure person — you are building the roads, not the cars.

Your work is in **two phases**:
- **Stage 2**: Database tables + FastAPI shell + Supabase auth
- **Stage 3**: Knowledge graph + JSON Schema Freeze (the most critical step in the whole project)

You don't need Stage 1 to be done to start Stage 2. Begin immediately.

---

## 📦 Your Folder: `shared/`

```text
shared/
├── db/
│   ├── schema.sql            ← All CREATE TABLE statements
│   ├── migrations/           ← Future migrations go here
│   └── seed.py               ← Inserts some starting data (countries, corridors)
├── schemas/                  ← FROZEN JSON CONTRACTS (Stage 3)
│   ├── risk_score.json
│   ├── simulate.json
│   ├── recommend.json
│   └── spr_schedule.json
├── clients/                  ← Stage 1 person fills this
└── requirements.txt
```

---

## 🔑 Prerequisites

1. **Supabase account**: Sign up free at https://supabase.com and create a new project called `pravah`.
2. **Get your credentials** from Supabase dashboard → Settings → API:
   - `SUPABASE_URL` (looks like: https://xyzxyz.supabase.co)
   - `SUPABASE_ANON_KEY` (public anonymous key)
   - `SUPABASE_SERVICE_KEY` (secret service key — keep safe!)
3. **Add to `.env` file** at the project root:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here
```

4. **Install Python packages**. Create `shared/requirements.txt`:

```text
fastapi
uvicorn
supabase
python-dotenv
networkx
pydantic
python-jose[cryptography]
passlib[bcrypt]
```

---

## 📋 STAGE 2 — Database Tables

### Step 1: Create `shared/db/schema.sql`

Go to your Supabase project → SQL Editor and run the following SQL to create all the tables.
Also save this file in `shared/db/schema.sql` for version control.

```sql
-- ================================================
-- PRAVAH — Master Database Schema
-- ================================================

-- Lookup: Countries
CREATE TABLE countries (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(3) UNIQUE NOT NULL,  -- ISO 3166-1 alpha-3, e.g. 'SAU'
    name        TEXT NOT NULL,
    region      TEXT,                         -- e.g. 'Middle East'
    import_share_pct FLOAT                   -- India's oil import share from this country
);

-- Lookup: Suppliers (crude oil producers/exporters)
CREATE TABLE suppliers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    country_id  INT REFERENCES countries(id),
    grade       TEXT,                         -- 'Arab Light', 'Basra Heavy', etc.
    api_gravity FLOAT,
    sulphur_pct FLOAT,
    active      BOOLEAN DEFAULT TRUE
);

-- Shipping corridors
CREATE TABLE corridors (
    id              SERIAL PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,     -- e.g. 'hormuz', 'redsea', 'cape'
    display_name    TEXT,
    chokepoint_lat  FLOAT,
    chokepoint_lng  FLOAT,
    typical_transit_days INT,
    tankers_per_day_avg INT
);

-- Refineries
CREATE TABLE refineries (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    capacity_mbpd FLOAT,                     -- Million barrels per day
    primary_grade TEXT,                      -- crude grade it is configured for
    lat         FLOAT,
    lng         FLOAT
);

-- Ships (tankers being tracked)
CREATE TABLE ships (
    id          SERIAL PRIMARY KEY,
    mmsi        VARCHAR(9) UNIQUE,           -- AIS MMSI number
    name        TEXT,
    flag        VARCHAR(3),                  -- country code
    imo         TEXT,
    ship_type   TEXT,
    deadweight  INT,
    last_lat    FLOAT,
    last_lng    FLOAT,
    last_seen   TIMESTAMPTZ,
    is_sanctioned BOOLEAN DEFAULT FALSE
);

-- Risk events ingested from GDELT / news
CREATE TABLE risk_events (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'gdelt', 'manual', 'aisstream'
    headline        TEXT,
    corridor_id     INT REFERENCES corridors(id),
    country_id      INT REFERENCES countries(id),
    event_date      TIMESTAMPTZ NOT NULL,
    goldstein_scale FLOAT,                    -- GDELT conflict scale (-10 to +10)
    severity        TEXT,                     -- 'low', 'medium', 'high', 'critical'
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Risk scores computed by the Risk Agent
CREATE TABLE risk_scores (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    corridor_id     INT REFERENCES corridors(id),
    score           FLOAT NOT NULL,           -- 0 to 100
    confidence      FLOAT,
    reasoning_trail JSONB,                    -- full LangGraph chain output
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    data_sources    TEXT[]                    -- which sources informed this
);

-- Results from the Scenario Simulation Engine
CREATE TABLE scenario_results (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    corridor_id     INT REFERENCES corridors(id),
    risk_score_id   UUID REFERENCES risk_scores(id),
    brent_p10       FLOAT,
    brent_p50       FLOAT,
    brent_p90       FLOAT,
    pump_price_p50  FLOAT,
    gdp_impact_p50  FLOAT,
    num_simulations INT,
    computed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Procurement recommendations from the Procurement Agent
CREATE TABLE recommendations (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_id     UUID REFERENCES scenario_results(id),
    supplier_id     INT REFERENCES suppliers(id),
    corridor_id     INT REFERENCES corridors(id),
    rank            INT,
    score           FLOAT,
    rationale       TEXT,
    estimated_cost_usd FLOAT,
    transit_days    INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- SPR (Strategic Petroleum Reserve) release schedules
CREATE TABLE spr_schedule (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_id     UUID REFERENCES scenario_results(id),
    release_mbpd    FLOAT,                   -- million barrels per day
    duration_days   INT,
    start_date      DATE,
    cover_days_before FLOAT,
    cover_days_after  FLOAT,
    optimization_notes TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Track external data source health
CREATE TABLE data_sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,        -- 'eia_api', 'gdelt', 'aisstream', 'ofac'
    is_live     BOOLEAN DEFAULT FALSE,
    last_synced TIMESTAMPTZ,
    record_count INT,
    status_msg  TEXT
);

-- User-saved analysis views / sessions
CREATE TABLE user_views (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID,
    name        TEXT,
    view_type   TEXT,                        -- 'citizen', 'analyst', 'policy'
    config      JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Step 2: Create `shared/db/seed.py`
Once your tables are created, run this script once to pre-fill lookup tables so that
the agents have data to reference from Day 1.

```python
# shared/db/seed.py
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# --- Seed Countries ---
countries = [
    {"code": "SAU", "name": "Saudi Arabia", "region": "Middle East", "import_share_pct": 17.5},
    {"code": "IRQ", "name": "Iraq",         "region": "Middle East", "import_share_pct": 22.3},
    {"code": "ARE", "name": "UAE",           "region": "Middle East", "import_share_pct": 6.2},
    {"code": "RUS", "name": "Russia",        "region": "Eastern Europe", "import_share_pct": 19.4},
    {"code": "USA", "name": "United States", "region": "Americas",   "import_share_pct": 2.1},
    {"code": "NGA", "name": "Nigeria",       "region": "Africa",     "import_share_pct": 5.8},
]
supabase.table("countries").upsert(countries, on_conflict="code").execute()
print(f"Seeded {len(countries)} countries.")

# --- Seed Corridors ---
corridors = [
    {"name": "hormuz",  "display_name": "Strait of Hormuz",       "chokepoint_lat": 26.6, "chokepoint_lng": 56.25, "typical_transit_days": 25, "tankers_per_day_avg": 17},
    {"name": "redsea",  "display_name": "Red Sea / Bab-el-Mandeb","chokepoint_lat": 12.5, "chokepoint_lng": 43.3,  "typical_transit_days": 20, "tankers_per_day_avg": 12},
    {"name": "cape",    "display_name": "Cape of Good Hope",       "chokepoint_lat": -34.4,"chokepoint_lng": 18.5,  "typical_transit_days": 45, "tankers_per_day_avg": 5},
    {"name": "domestic","display_name": "Domestic Pipeline",       "chokepoint_lat": 22.0, "chokepoint_lng": 79.0,  "typical_transit_days": 3,  "tankers_per_day_avg": 0},
]
supabase.table("corridors").upsert(corridors, on_conflict="name").execute()
print(f"Seeded {len(corridors)} corridors.")

# --- Seed Data Sources ---
sources = [
    {"name": "eia_api",    "is_live": False},
    {"name": "gdelt",      "is_live": False},
    {"name": "aisstream",  "is_live": False},
    {"name": "ofac",       "is_live": False},
]
supabase.table("data_sources").upsert(sources, on_conflict="name").execute()
print(f"Seeded {len(sources)} data sources.")

print("\n✅ Seed complete.")
```

Run it with: `python shared/db/seed.py`

---

## 🌐 STAGE 3 — Knowledge Graph + SCHEMA FREEZE

This is the **most critical part of your job**. Stage 4 onwards (Risk, Scenario, Procurement,
SPR agents) are all built independently by different people — but they need to agree on what
data they send and receive. That agreement is the JSON schema freeze.

**Once you freeze these, they are law. Do not change them without informing the entire team.**

### Step 1: Build the Knowledge Graph (`shared/db/knowledge_graph.py`)

This represents India's energy supply chain as a graph: who supplies what,
through which route, to which port, to which refinery, producing which fuel.

```python
# shared/db/knowledge_graph.py
import networkx as nx

def build_supply_chain_graph():
    """
    Build the Pravah supply chain knowledge graph.
    Nodes: suppliers, corridors, ports, refineries, fuel_types
    Edges: represent flow of oil through the supply chain
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

    # --- Corridor Nodes ---
    corridors = [
        ("HORMUZ",  {"type": "corridor", "risk_baseline": 60, "tankers_per_day": 17}),
        ("REDSEA",  {"type": "corridor", "risk_baseline": 50, "tankers_per_day": 12}),
        ("CAPE",    {"type": "corridor", "risk_baseline": 15, "tankers_per_day": 5}),
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
    G.add_edge("SAU_ARAMCO", "HORMUZ",  transit_days=2,  share=0.85)
    G.add_edge("SAU_ARAMCO", "REDSEA",  transit_days=8,  share=0.15)
    G.add_edge("IRQ_SOMO",   "HORMUZ",  transit_days=3,  share=0.90)
    G.add_edge("IRQ_SOMO",   "CAPE",    transit_days=40, share=0.10)
    G.add_edge("RUS_ROSNEFT","REDSEA",  transit_days=12, share=0.70)
    G.add_edge("RUS_ROSNEFT","CAPE",    transit_days=35, share=0.30)
    G.add_edge("NGA_NNPC",   "CAPE",    transit_days=25, share=1.00)

    # --- Edges: Corridor → Port ---
    G.add_edge("HORMUZ", "PORT_VADINAR",  capacity_fraction=0.50)
    G.add_edge("HORMUZ", "PORT_KANDLA",   capacity_fraction=0.30)
    G.add_edge("HORMUZ", "PORT_MUMBAI",   capacity_fraction=0.20)
    G.add_edge("REDSEA", "PORT_MUMBAI",   capacity_fraction=0.60)
    G.add_edge("REDSEA", "PORT_PARADIP",  capacity_fraction=0.40)
    G.add_edge("CAPE",   "PORT_PARADIP",  capacity_fraction=1.00)

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
    """Return all end-to-end paths that pass through a given corridor node."""
    corridor_node = corridor_name.upper()
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
    
    paths = get_paths_for_corridor(G, "HORMUZ")
    print(f"\nPaths through Hormuz: {len(paths)}")
    for p in paths[:3]:  # print first 3
        print("  →", " → ".join(p))
```

Run it with: `python shared/db/knowledge_graph.py`
It should print the graph stats and show example supply chain paths.

---

### Step 2: Freeze the JSON Schemas (`shared/schemas/`)

**⚠️ THIS IS THE MOST IMPORTANT STEP — Once committed, these cannot change.**

Create each file exactly as defined below. All agents will import their Pydantic
models from these definitions.

#### `shared/schemas/risk_score.json`
*Used by: risk-agent (output), coordinator (input), frontend (display)*
```json
{
    "endpoint": "POST /risk-score",
    "version": "1.0",
    "request": {
        "corridor": "string  [hormuz|redsea|cape|domestic]",
        "as_of":    "string  [ISO 8601 datetime, e.g. 2026-07-10T00:00:00Z]"
    },
    "response": {
        "corridor":         "string",
        "score":            "float  [0.0 - 100.0]",
        "confidence":       "float  [0.0 - 1.0]",
        "alert_level":      "string [low|elevated|high|critical]",
        "reasoning_trail":  "array of strings [each step of the LangGraph chain]",
        "key_events":       "array of {headline: string, severity: string, date: string}",
        "computed_at":      "string [ISO 8601 datetime]",
        "data_sources":     "array of strings [e.g. gdelt, aisstream, ofac]"
    }
}
```

#### `shared/schemas/simulate.json`
*Used by: scenario-engine (output), coordinator (input), frontend (charts)*
```json
{
    "endpoint": "POST /simulate",
    "version": "1.0",
    "request": {
        "risk_score":           "float  [0.0 - 100.0]",
        "corridor":             "string [hormuz|redsea|cape|domestic]",
        "shock_duration_days":  "int    [1 - 365]",
        "num_simulations":      "int    [1000 - 20000]",
        "current_brent_usd":    "float  [price in USD per barrel]",
        "elasticity_assumptions": {
            "price_elasticity_of_demand":       "float [typically -0.05]",
            "pass_through_rate_to_pump":        "float [0.0 - 1.0]",
            "gdp_sensitivity_per_10pct_oil_shock": "float [typically -0.15]"
        }
    },
    "response": {
        "brent_price_distribution": {"p10": "float", "p50": "float", "p90": "float", "mean": "float", "std_dev": "float"},
        "daily_price_path":         "array of {day: int, p10: float, p50: float, p90: float}",
        "pump_price_impact":        {"current_inr_per_litre": "float", "projected_p50_inr_per_litre": "float", "projected_p90_inr_per_litre": "float"},
        "gdp_impact_pct":           {"p10": "float", "p50": "float", "p90": "float"},
        "calibration_note":         "string",
        "num_simulations_run":      "int",
        "computed_at":              "string [ISO 8601 datetime]",
        "data_source":              "string [live_eia|fallback_cache]",
        "volatility_calibrated_from": "string [date range]"
    }
}
```

#### `shared/schemas/recommend.json`
*Used by: procurement-agent (output), coordinator (input), frontend (procurement table)*
```json
{
    "endpoint": "POST /recommend",
    "version": "1.0",
    "request": {
        "blocked_corridors":    "array of strings [e.g. ['hormuz']]",
        "required_volume_mbpd": "float  [million barrels per day India needs]",
        "max_transit_days":     "int    [maximum acceptable transit days]",
        "scenario_id":          "string [UUID from /simulate response, optional]"
    },
    "response": {
        "recommendations": "array of {rank: int, supplier: string, country: string, corridor: string, grade: string, cost_index: float, transit_days: int, risk_score: float, rationale: string}",
        "total_suppliers_evaluated": "int",
        "graph_paths_analyzed":      "int",
        "computed_at":               "string [ISO 8601 datetime]"
    }
}
```

#### `shared/schemas/spr_schedule.json`
*Used by: spr-agent (output), coordinator (input), frontend (SPR display)*
```json
{
    "endpoint": "POST /spr-schedule",
    "version": "1.0",
    "request": {
        "shock_duration_days":  "int   [how long the disruption is expected to last]",
        "supply_gap_mbpd":      "float [how many million barrels per day India is short]",
        "current_cover_days":   "float [India's current SPR cover in days, typically ~9.5]"
    },
    "response": {
        "recommended_release_mbpd": "float",
        "release_duration_days":    "int",
        "start_date":               "string [YYYY-MM-DD]",
        "cover_days_before":        "float",
        "cover_days_after":         "float",
        "optimization_objective":   "string [description of what was optimized]",
        "constraint_notes":         "array of strings",
        "computed_at":              "string [ISO 8601 datetime]"
    }
}
```

---

## ✅ Acceptance Criteria (Definition of Done)

Stage 2 is done when:
- [ ] All 12 tables exist in Supabase (check the Table Editor in the dashboard)
- [ ] `seed.py` runs without errors and populates countries, corridors, data_sources
- [ ] You can connect to Supabase from Python using the `supabase-py` client

Stage 3 is done when:
- [ ] `python shared/db/knowledge_graph.py` runs and prints node/edge counts
- [ ] All 4 JSON files exist in `shared/schemas/`
- [ ] You have **sent a message to the team group chat** saying: *"SCHEMAS ARE FROZEN at [time]. Do not modify shared/schemas/ without team agreement."*

---

## 🤝 Handoff to the Team
Once both stages are done, message everyone with:
1. The Supabase project URL so they can see the tables
2. The **exact** contents of `shared/schemas/` (just share the files)
3. Confirm that `seed.py` has been run on the shared Supabase project

After this, the team can begin Stages 4-8 in true parallel. 🚀
