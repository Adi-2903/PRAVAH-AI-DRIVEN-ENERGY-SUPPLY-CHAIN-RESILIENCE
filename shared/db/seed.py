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
# `name` is lowercase and canonical — see the note in schema.sql. These exact
# strings must match the node names used in knowledge_graph.py (lowercased)
# and the enum values in shared/schemas/*.py.
corridors = [
    {"name": "hormuz",  "display_name": "Strait of Hormuz",       "chokepoint_lat": 26.6, "chokepoint_lng": 56.25, "typical_transit_days": 25, "tankers_per_day_avg": 17},
    {"name": "redsea",  "display_name": "Red Sea / Bab-el-Mandeb","chokepoint_lat": 12.5, "chokepoint_lng": 43.3,  "typical_transit_days": 20, "tankers_per_day_avg": 12},
    {"name": "cape",    "display_name": "Cape of Good Hope",       "chokepoint_lat": -34.4,"chokepoint_lng": 18.5,  "typical_transit_days": 45, "tankers_per_day_avg": 5},
    {"name": "domestic","display_name": "Domestic Pipeline",       "chokepoint_lat": 22.0, "chokepoint_lng": 79.0,  "typical_transit_days": 3,  "tankers_per_day_avg": 0},
]
supabase.table("corridors").upsert(corridors, on_conflict="name").execute()
print(f"Seeded {len(corridors)} corridors.")

# --- Seed Data Sources ---
# is_live stays False here — it is NOT a static flag. Tell the Stage 1
# person to flip is_live=True (and set last_synced / record_count) the
# moment their client successfully pulls a real record, e.g.:
#   supabase.table("data_sources").update({
#       "is_live": True, "last_synced": datetime.utcnow().isoformat(), "record_count": 1
#   }).eq("name", "eia_api").execute()
# Otherwise this table just sits stale and nobody notices when a source
# actually goes live.
sources = [
    {"name": "eia_api",    "is_live": False},
    {"name": "gdelt",      "is_live": False},
    {"name": "aisstream",  "is_live": False},
    {"name": "ofac",       "is_live": False},
]
supabase.table("data_sources").upsert(sources, on_conflict="name").execute()
print(f"Seeded {len(sources)} data sources.")

print("\n✅ Seed complete.")
