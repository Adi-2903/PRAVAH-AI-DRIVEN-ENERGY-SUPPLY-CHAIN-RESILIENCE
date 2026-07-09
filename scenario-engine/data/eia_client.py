import os
import json
import time
import csv
import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("eia_client")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "eia_cache.json")
FALLBACK_FILE = os.path.join(DATA_DIR, "fallback_brent_history.csv")

# Global status tracking
STATUS = {
    "live_working": False,
    "last_fetched": None,
    "cached_days_count": 0,
    "current_source": "fallback_cache"
}

def load_fallback_data() -> list[dict]:
    """Loads history from the bundled CSV file."""
    results = []
    if not os.path.exists(FALLBACK_FILE):
        logger.warning(f"Fallback CSV file not found at {FALLBACK_FILE}")
        return results
    
    try:
        with open(FALLBACK_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "date" in row and "price_usd" in row:
                    try:
                        results.append({
                            "date": row["date"],
                            "price_usd": float(row["price_usd"])
                        })
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"Error reading fallback CSV: {e}")
        
    return results

def get_cached_data() -> tuple[list[dict], float]:
    """Reads data from local cache if it exists, along with cache timestamp."""
    if not os.path.exists(CACHE_FILE):
        return [], 0.0
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            if "timestamp" in cache and "data" in cache:
                return cache["data"], float(cache["timestamp"])
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
    return [], 0.0

def save_to_cache(data: list[dict]):
    """Saves data to local cache JSON file with current timestamp."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        cache_content = {
            "timestamp": time.time(),
            "data": data
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_content, f, indent=2)
        logger.info(f"Successfully cached {len(data)} records to {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Failed to write cache: {e}")

def fetch_brent_spot_history(start_date: str, end_date: str) -> list[dict]:
    """
    Fetches daily Brent crude spot prices from EIA API v2.
    Checks 6h cache first. If empty/expired/failed, hits API.
    Falls back to local CSV on failure.
    """
    global STATUS
    
    # 1. Check local JSON cache first
    cached_data, cache_time = get_cached_data()
    now = time.time()
    
    # Cache is valid for 6 hours (6 * 3600 seconds)
    if cached_data and (now - cache_time < 6 * 3600):
        logger.info("Using valid local JSON cache for Brent spot history")
        STATUS["live_working"] = True  # We assume live was working or cache is fine
        STATUS["last_fetched"] = datetime.fromtimestamp(cache_time, tz=timezone.utc).isoformat()
        STATUS["cached_days_count"] = len(cached_data)
        STATUS["current_source"] = "fallback_cache"
        
        # Filter and sort
        filtered = [x for x in cached_data if start_date <= x["date"] <= end_date]
        return sorted(filtered, key=lambda x: x["date"])
    
    # 2. Try EIA API
    api_key = os.getenv("EIA_API_KEY", "").strip()
    if not api_key:
        logger.warning("EIA_API_KEY environment variable not set. Falling back to CSV.")
        STATUS["live_working"] = False
        STATUS["current_source"] = "fallback_cache"
        
        fallback = load_fallback_data()
        STATUS["cached_days_count"] = len(fallback)
        filtered = [x for x in fallback if start_date <= x["date"] <= end_date]
        return sorted(filtered, key=lambda x: x["date"])
    
    # Try different facet endpoints for RBRTE
    # URL 1: Using facets[series][]
    url_series = (
        f"https://api.eia.gov/v2/petroleum/pri/spt/data/?"
        f"frequency=daily&data[0]=value&facets[series][]=RBRTE&"
        f"sort[0][column]=period&sort[0][direction]=desc&length=1000&api_key={api_key}"
    )
    # URL 2: Using facets[product][] (as in prompt description)
    url_product = (
        f"https://api.eia.gov/v2/petroleum/pri/spt/data/?"
        f"frequency=daily&data[0]=value&facets[product][]=RBRTE&"
        f"sort[0][column]=period&sort[0][direction]=desc&length=1000&api_key={api_key}"
    )
    
    raw_data = None
    success = False
    
    # We will try both URLs to be robust
    for url in [url_series, url_product]:
        try:
            logger.info(f"Attempting to fetch Brent prices from EIA API URL: {url.replace(api_key, 'HIDDEN')}")
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                json_res = response.json()
                if "response" in json_res and "data" in json_res["response"]:
                    raw_data = json_res["response"]["data"]
                    if raw_data:
                        success = True
                        break
        except Exception as e:
            logger.warning(f"Error fetching from EIA URL: {e}")
            
    if success and raw_data:
        parsed_records = []
        for item in raw_data:
            period = item.get("period")
            value = item.get("value")
            if not period or value is None:
                continue
            try:
                price_usd = float(value)
                parsed_records.append({
                    "date": period,
                    "price_usd": price_usd
                })
            except ValueError:
                continue
                
        if parsed_records:
            # Update cache and status
            save_to_cache(parsed_records)
            STATUS["live_working"] = True
            STATUS["last_fetched"] = datetime.now(timezone.utc).isoformat()
            STATUS["cached_days_count"] = len(parsed_records)
            STATUS["current_source"] = "live_eia"
            
            # Filter and sort
            filtered = [x for x in parsed_records if start_date <= x["date"] <= end_date]
            return sorted(filtered, key=lambda x: x["date"])
            
    # 3. Fallback on Failure
    logger.warning("EIA API call failed or returned no data. Falling back to bundled CSV.")
    STATUS["live_working"] = False
    STATUS["current_source"] = "fallback_cache"
    
    fallback = load_fallback_data()
    STATUS["cached_days_count"] = len(fallback)
    filtered = [x for x in fallback if start_date <= x["date"] <= end_date]
    return sorted(filtered, key=lambda x: x["date"])

def get_data_status() -> dict:
    """Returns the current data source and status info."""
    global STATUS
    # Recalculate cached days dynamically if needed
    if STATUS["cached_days_count"] == 0:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    STATUS["cached_days_count"] = len(json.load(f).get("data", []))
            except:
                pass
        if STATUS["cached_days_count"] == 0:
            STATUS["cached_days_count"] = len(load_fallback_data())
            
    return STATUS
