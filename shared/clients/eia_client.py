# shared/clients/eia_client.py
import os
import requests
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status

load_dotenv()

def fetch_latest_brent_price() -> dict:
    """
    Fetches the latest Brent crude daily spot price from the EIA API v2.
    If the API call is successful, updates the 'eia_api' data source status in Supabase.
    """
    api_key = os.getenv("EIA_API_KEY", "").strip()
    if not api_key:
        msg = "EIA_API_KEY is not configured in the environment variables."
        print(f"[EIA Client] Warning: {msg}")
        update_data_source_status("eia_api", False, 0, msg)
        # Return fallback mock price for pipeline completeness
        return {"date": "2026-07-10", "price": 82.50, "note": "fallback mock price"}

    url = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
    params = {
        "frequency": "daily",
        "data[0]": "value",
        "facets[product][]": "EPCBRENT",  # Brent
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 1,
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            json_res = response.json()
            data = json_res.get("response", {}).get("data", [])
            if data:
                record = data[0]
                period = record.get("period")
                value = record.get("value")
                if period and value is not None:
                    price = float(value)
                    # Sync to database
                    update_data_source_status("eia_api", True, 1, "Success")
                    return {"date": period, "price": price}
            
            # If request returned empty data, try RBRTE product code as fallback
            params["facets[product][]"] = "RBRTE"
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                json_res = response.json()
                data = json_res.get("response", {}).get("data", [])
                if data:
                    record = data[0]
                    period = record.get("period")
                    value = record.get("value")
                    if period and value is not None:
                        price = float(value)
                        update_data_source_status("eia_api", True, 1, "Success")
                        return {"date": period, "price": price}
                        
            raise ValueError(f"Empty data or unexpected structure: {json_res}")
        else:
            raise requests.RequestException(f"EIA API responded with status {response.status_code}: {response.text}")
    except Exception as e:
        msg = f"Failed to fetch from EIA: {e}"
        print(f"[EIA Client] Error: {msg}")
        update_data_source_status("eia_api", False, 0, msg)
        # Return fallback mock price so the pipeline doesn't crash completely
        return {"date": "2026-07-10", "price": 82.50, "note": f"fallback mock price (error: {e})"}
