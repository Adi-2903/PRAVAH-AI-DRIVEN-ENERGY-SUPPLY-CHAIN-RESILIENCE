# shared/clients/ais_client.py
import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status

load_dotenv()

async def get_sample_ship_position() -> dict:
    """
    Connects to wss://stream.aisstream.io/v0/stream,
    subscribes to Strait of Hormuz bounding box,
    fetches one PositionReport, closes connection,
    and updates 'aisstream' data source status in Supabase.
    """
    api_key = os.getenv("AISSTREAM_API_KEY", "").strip()
    if not api_key:
        msg = "AISSTREAM_API_KEY is not configured in the environment variables."
        print(f"[AIS Client] Warning: {msg}")
        update_data_source_status("aisstream", False, 0, msg)
        return {
            "mmsi": "477995600",
            "name": "MOCK TANKER (ST. OF HORMUZ)",
            "lat": 26.5000,
            "lng": 56.1000,
            "timestamp": "2026-07-11T12:00:00Z",
            "note": "fallback mock position"
        }

    url = "wss://stream.aisstream.io/v0/stream"
    subscribe_msg = {
        "APIKey": api_key,
        "BoundingBoxes": [[[24.0, 55.5], [27.5, 57.5]]]  # Strait of Hormuz
    }

    try:
        async with websockets.connect(url) as websocket:
            # 1. Send subscription message immediately (within 3 seconds)
            await websocket.send(json.dumps(subscribe_msg))
            print("[AIS Client] Sent subscription request for Strait of Hormuz bounding box.")

            # 2. Wait for one PositionReport message with a 15-second timeout
            async def receive_report():
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("MessageType") == "PositionReport":
                        return data
                return None

            try:
                report = await asyncio.wait_for(receive_report(), timeout=15.0)
                if report:
                    metadata = report.get("MetaData", {})
                    pos_report = report.get("Message", {}).get("PositionReport", {})
                    
                    mmsi = metadata.get("MMSI") or pos_report.get("UserID")
                    ship_name = metadata.get("ShipName", "").strip()
                    lat = metadata.get("latitude") or pos_report.get("Latitude")
                    lng = metadata.get("longitude") or pos_report.get("Longitude")
                    time_utc = metadata.get("time_utc")
                    
                    result = {
                        "mmsi": str(mmsi) if mmsi else None,
                        "name": ship_name or "Unknown Ship",
                        "lat": float(lat) if lat is not None else None,
                        "lng": float(lng) if lng is not None else None,
                        "timestamp": time_utc
                    }
                    
                    # Update database status
                    update_data_source_status("aisstream", True, 1, "Success")
                    return result
                else:
                    raise ValueError("Connection closed without receiving any PositionReport.")
            except asyncio.TimeoutError:
                msg = "Timeout waiting for ship position in Strait of Hormuz box."
                print(f"[AIS Client] Warning: {msg}")
                update_data_source_status("aisstream", False, 0, msg)
                return {
                    "mmsi": "477995600",
                    "name": "MOCK TANKER (ST. OF HORMUZ)",
                    "lat": 26.5000,
                    "lng": 56.1000,
                    "timestamp": "2026-07-11T12:00:00Z",
                    "note": f"fallback mock position (timeout)"
                }
    except Exception as e:
        msg = f"Websocket connection error: {e}"
        print(f"[AIS Client] Error: {msg}")
        update_data_source_status("aisstream", False, 0, msg)
        return {
            "mmsi": "477995600",
            "name": "MOCK TANKER (ST. OF HORMUZ)",
            "lat": 26.5000,
            "lng": 56.1000,
            "timestamp": "2026-07-11T12:00:00Z",
            "note": f"fallback mock position (error: {e})"
        }
