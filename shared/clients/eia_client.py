"""
EIA Client — Fetches latest daily Brent crude oil spot price.

Endpoint: https://api.eia.gov/v2/petroleum/pri/spt/data/
Auth: API key via query parameter
"""

import os
import requests
from dotenv import load_dotenv

# Load .env from the project root (two levels up from shared/clients/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

EIA_API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"


def fetch_latest_brent_price() -> dict:
    """
    Fetch the most recent daily Brent crude spot price from EIA v2 API.

    Returns:
        dict: {"date": "YYYY-MM-DD", "price": float, "unit": str}

    Raises:
        ValueError: If no API key is set or no data is returned.
        requests.HTTPError: On API errors.
    """
    if not EIA_API_KEY or EIA_API_KEY == "your_key_here":
        raise ValueError(
            "EIA_API_KEY is not set. "
            "Register at https://www.eia.gov/opendata/register.php "
            "and add your key to the .env file."
        )

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

    response = requests.get(BASE_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    # Navigate into the response structure
    records = data.get("response", {}).get("data", [])
    if not records:
        raise ValueError(
            "EIA returned no data records. Check your API key and query parameters. "
            f"Raw response: {data}"
        )

    record = records[0]
    return {
        "date": record.get("period"),
        "price": float(record.get("value")) if record.get("value") is not None else None,
        "unit": record.get("units", "$/barrel"),
        "product": record.get("product-name", "Brent"),
    }


if __name__ == "__main__":
    try:
        result = fetch_latest_brent_price()
        print(f"[PASS] EIA Brent Price: {result}")
    except Exception as e:
        print(f"[FAIL] EIA Error: {e}")
