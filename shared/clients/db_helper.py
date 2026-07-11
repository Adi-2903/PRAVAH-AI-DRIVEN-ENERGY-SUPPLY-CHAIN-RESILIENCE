# shared/clients/db_helper.py
import os
import sys
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

# Ensure stdout encodes UTF-8 properly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

def get_supabase_client():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        try:
            return create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"[Supabase] Connection error: {e}", file=sys.stderr)
            return None
    return None

def update_data_source_status(name: str, is_live: bool, record_count: int, status_msg: str):
    supabase = get_supabase_client()
    if not supabase:
        print(f"[Supabase Fallback] Could not sync '{name}' to DB: Supabase credentials not set.")
        return False
    try:
        data = {
            "is_live": is_live,
            "last_synced": datetime.now(timezone.utc).isoformat(),
            "record_count": record_count,
            "status_msg": status_msg
        }
        supabase.table("data_sources").update(data).eq("name", name).execute()
        print(f"✅ [Supabase] Synced source '{name}' status to DB.")
        return True
    except Exception as e:
        print(f"❌ [Supabase] Failed to update data source '{name}': {e}", file=sys.stderr)
        return False
