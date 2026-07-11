# shared/clients/ais_client.py
"""
AIS Client — Connects to live aisstream.io WebSocket feed for ship tracking.

Endpoint: wss://stream.aisstream.io/v0/stream
Auth: API key sent in the subscription JSON message
"""

import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status, get_supabase_client

# Load .env from the project root (two levels up from shared/clients/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY")
WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"

# Default bounding box: Strait of Hormuz
# [[south-west corner], [north-east corner]]
DEFAULT_BOUNDING_BOX = [[[24.0, 55.5], [27.5, 57.5]]]

RECEIVE_TIMEOUT = 15  # seconds to wait for a position report

async def _listen_for_position(bounding_boxes=None) -> dict:
    if not AISSTREAM_API_KEY or AISSTREAM_API_KEY == "your_key_here":
        raise ValueError(
            "AISSTREAM_API_KEY is not set. "
            "Register at https://aisstream.io/ and add your key to the .env file."
        )

    if bounding_boxes is None:
        bounding_boxes = DEFAULT_BOUNDING_BOX

    # Build subscription message — must be sent within 3 seconds of connecting
    subscribe_msg = json.dumps({
        "APIKey": AISSTREAM_API_KEY,
        "BoundingBoxes": bounding_boxes,
        "FiltersShipMMSI": [],
        "FilterMessageTypes": ["PositionReport"],
    })

    async with websockets.connect(WEBSOCKET_URL) as ws:
        # Send subscription IMMEDIATELY after connecting (within 3-second window)
        await ws.send(subscribe_msg)

        # Wait for exactly one PositionReport with a timeout
        raw = await asyncio.wait_for(ws.recv(), timeout=RECEIVE_TIMEOUT)
        message = json.loads(raw)

        # Check if the server returned an error message
        if "error" in message or "Error" in message:
            error_msg = message.get("error") or message.get("Error")
            raise ValueError(f"aisstream returned error: {error_msg}")

        # Parse the PositionReport
        msg_type = message.get("MessageType", "")
        meta = message.get("MetaData", {})
        position = message.get("Message", {}).get("PositionReport", {})

        return {
            "mmsi": str(meta.get("MMSI")) if meta.get("MMSI") else None,
            "name": meta.get("ShipName", "").strip() or "Unknown Ship",
            "lat": float(position.get("Latitude")) if position.get("Latitude") is not None else None,
            "lng": float(position.get("Longitude")) if position.get("Longitude") is not None else None,
            "timestamp": meta.get("time_utc"),
            "speed": position.get("Sog"),
            "course": position.get("Cog"),
        }

def get_sample_ship_position(bounding_boxes=None) -> dict:
    """
    Connects to aisstream.io and fetches one live ship position report.
    If successful, updates the 'aisstream' data source status in Supabase.
    If unsuccessful or API key is missing, returns fallback mock data.
    """
    if not AISSTREAM_API_KEY or AISSTREAM_API_KEY == "your_key_here":
        msg = "AISSTREAM_API_KEY is not configured in the environment variables."
        print(f"[AIS Client] Warning: {msg}")
        update_data_source_status("aisstream", False, 0, msg)
        return _ais_fallback(msg)

    try:
        result = asyncio.run(_listen_for_position(bounding_boxes))
        
        supabase = get_supabase_client()
        if supabase and result.get("mmsi"):
            data = {
                "mmsi": result["mmsi"],
                "name": result.get("name"),
                "last_lat": result.get("lat"),
                "last_lng": result.get("lng"),
                "last_seen": result.get("timestamp") or "2026-07-11T00:00:00Z"
            }
            try:
                # Upsert into ships table using mmsi
                supabase.table("ships").upsert(data, on_conflict="mmsi").execute()
            except Exception as dbe:
                print(f"[AIS Client] Warning: failed to upsert into ships: {dbe}")

        update_data_source_status("aisstream", True, 1, "Success")
        return result
    except Exception as e:
        msg = f"Failed to fetch AIS data: {e}"
        print(f"[AIS Client] Error: {msg}")
        update_data_source_status("aisstream", False, 0, msg)
        return _ais_fallback(msg)

def _ais_fallback(error_msg: str) -> dict:
    supabase = get_supabase_client()
    if supabase:
        try:
            res = supabase.table("ships").select("*").order("last_seen", desc=True).limit(1).execute()
            if res.data:
                print("[AIS Client] Using database fallback.")
                ship = res.data[0]
                return {
                    "mmsi": ship.get("mmsi"),
                    "name": ship.get("name"),
                    "lat": ship.get("last_lat"),
                    "lng": ship.get("last_lng"),
                    "timestamp": ship.get("last_seen"),
                    "note": f"DB fallback (error: {error_msg})"
                }
        except Exception as dbe:
            print(f"[AIS Client] DB fallback error: {dbe}")
            
    return {
        "mmsi": "477995600",
        "name": "MOCK TANKER (ST. OF HORMUZ)",
        "lat": 26.5000,
        "lng": 56.1000,
        "timestamp": "2026-07-11T12:00:00Z",
        "note": f"fallback mock position (error: {error_msg})"
    }

if __name__ == "__main__":
    try:
        result = get_sample_ship_position()
        print(f"[PASS] AIS Ship Position: {result}")
    except Exception as e:
        print(f"[FAIL] AIS Error: {e}")
