"""
AIS Client — Connects to live aisstream.io WebSocket feed for ship tracking.

Endpoint: wss://stream.aisstream.io/v0/stream
Auth: API key sent in the subscription JSON message

Gotchas handled:
  1. Bounding box filter to avoid global firehose (~300 msgs/sec)
  2. Subscription sent immediately within 3-second window
  3. 15-second timeout to avoid hanging on quiet bounding boxes
"""

import os
import json
import asyncio
import websockets
from dotenv import load_dotenv

# Load .env from the project root (two levels up from shared/clients/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY")
WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"

# Default bounding box: Strait of Hormuz
# [[south-west corner], [north-east corner]]
DEFAULT_BOUNDING_BOX = [[[24.0, 55.5], [27.5, 57.5]]]

RECEIVE_TIMEOUT = 30  # seconds to wait for a position report


async def _listen_for_position(bounding_boxes=None) -> dict:
    """
    Internal async function that connects to aisstream, subscribes to
    PositionReport messages within the bounding box, and returns the first one.

    Args:
        bounding_boxes: List of bounding boxes. Defaults to Strait of Hormuz.

    Returns:
        dict: Ship position data with mmsi, ship_name, latitude, longitude,
              speed, course, and timestamp.
    """
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

    try:
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
                "message_type": msg_type,
                "mmsi": meta.get("MMSI"),
                "ship_name": meta.get("ShipName", "").strip(),
                "latitude": position.get("Latitude"),
                "longitude": position.get("Longitude"),
                "speed": position.get("Sog"),  # Speed Over Ground (knots)
                "course": position.get("Cog"),  # Course Over Ground (degrees)
                "timestamp": meta.get("time_utc"),
            }
    except websockets.exceptions.ConnectionClosedError as e:
        raise ConnectionError(
            f"aisstream closed the connection: {e}. "
            "This usually means the API key is invalid or expired. "
            "Verify your AISSTREAM_API_KEY at https://aisstream.io/"
        )
    except websockets.exceptions.InvalidStatusCode as e:
        raise ConnectionError(
            f"aisstream rejected the connection with status {e.status_code}. "
            "Check your API key and try again."
        )


def get_sample_ship_position(bounding_boxes=None) -> dict:
    """
    Synchronous wrapper that connects to aisstream.io and fetches
    one live ship position report.

    Args:
        bounding_boxes: Optional list of bounding boxes.
                        Defaults to Strait of Hormuz [[[24.0, 55.5], [27.5, 57.5]]]

    Returns:
        dict: Ship position data.

    Raises:
        ValueError: If API key is not set.
        asyncio.TimeoutError: If no ship is seen within the timeout window.
    """
    try:
        return asyncio.run(_listen_for_position(bounding_boxes))
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"No ship position received within {RECEIVE_TIMEOUT}s. "
            "The bounding box may be quiet right now — "
            "try a busier region or increase the timeout."
        )


if __name__ == "__main__":
    try:
        result = get_sample_ship_position()
        print(f"[PASS] AIS Ship Position: {result}")
    except Exception as e:
        print(f"[FAIL] AIS Error: {e}")
