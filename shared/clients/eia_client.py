# shared/clients/eia_client.py
import os
import requests
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status

# Load .env from the project root (two levels up from shared/clients/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

EIA_API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

def fetch_latest_brent_price() -> dict:
    """
    Fetch the most recent daily Brent crude spot price from EIA v2 API.
    If successful, updates the 'eia_api' data source status in Supabase.
    If unsuccessful or API key is missing, returns fallback mock data.
    """
    if not EIA_API_KEY or EIA_API_KEY == "your_key_here":
        msg = "EIA_API_KEY is not configured in the environment variables."
        print(f"[EIA Client] Warning: {msg}")
        update_data_source_status("eia_api", False, 0, msg)
        return {
            "date": "2026-07-10",
            "price": 82.50,
            "unit": "$/barrel",
            "product": "Brent",
            "note": "fallback mock price"
        }

    params = {
        "api_key": EIA_API_KEY,
        "frequency": "daily",
        "data[0]": "value",
        "facets[product][]": "EPCBRENT",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 1,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        records = data.get("response", {}).get("data", [])
        
        if not records:
            # Fallback to RBRTE product code if EPCBRENT is empty
            params["facets[product][]"] = "RBRTE"
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            records = data.get("response", {}).get("data", [])
            
        if not records:
            raise ValueError("No price records returned by EIA API")

        record = records[0]
        result = {
            "date": record.get("period"),
            "price": float(record.get("value")) if record.get("value") is not None else None,
            "unit": record.get("units", "$/barrel"),
            "product": record.get("product-name", "Brent"),
        }
        update_data_source_status("eia_api", True, 1, "Success")
        return result
    except Exception as e:
        msg = f"Failed to fetch from EIA: {e}"
        print(f"[EIA Client] Error: {msg}")
        update_data_source_status("eia_api", False, 0, msg)
        return {
            "date": "2026-07-10",
            "price": 82.50,
            "unit": "$/barrel",
            "product": "Brent",
            "note": f"fallback mock price (error: {e})"
        }

if __name__ == "__main__":
    try:
        result = fetch_latest_brent_price()
        print(f"[PASS] EIA Brent Price: {result}")
    except Exception as e:
        print(f"[FAIL] EIA Error: {e}")
