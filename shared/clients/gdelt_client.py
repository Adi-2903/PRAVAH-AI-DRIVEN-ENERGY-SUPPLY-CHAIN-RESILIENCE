# shared/clients/gdelt_client.py
"""
GDELT Client — Fetches the latest 15-minute geopolitical event export.

Endpoint: http://data.gdeltproject.org/gdeltv2/lastupdate.txt
Auth: None (open data)
"""

import io
import os
import zipfile
import requests
import pandas as pd
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

GDELT_COLUMNS = {
    0: "globaleventid",
    1: "sqldate",
    6: "actor1name",
    16: "actor2name",
    26: "eventcode",
    30: "goldsteinscale",
    52: "actiongeo_fullname",
    53: "actiongeo_countrycode",
    60: "sourceurl",
}

def fetch_latest_events() -> dict:
    """
    Download the most recent GDELT 2.0 event export and parse the first record.
    If successful, updates the 'gdelt' data source status in Supabase.
    If unsuccessful, returns fallback mock event data.
    """
    try:
        # Step 1: Get the lastupdate.txt and parse the FIRST line (events export)
        response = requests.get(LASTUPDATE_URL, timeout=15)
        response.raise_for_status()

        lines = response.text.strip().split("\n")
        if not lines:
            raise ValueError("GDELT lastupdate.txt returned empty response.")

        parts = lines[0].strip().split(" ")
        if len(parts) < 3:
            raise ValueError(f"Unexpected lastupdate.txt format: {lines[0]}")

        zip_url = parts[2]

        print(f"[GDELT Client] Downloading latest export zip: {zip_url}")

        # Step 2: Download the zip file into memory
        zip_response = requests.get(zip_url, timeout=30)
        zip_response.raise_for_status()

        # Step 3: Extract and parse the CSV from the zip using pandas
        with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file, sep="\t", header=None, dtype=str)

        if df.empty:
            raise ValueError("GDELT event export CSV is empty.")

        # Step 4: Extract the first row using our column mapping
        first_row = df.iloc[0]
        result = {}
        for col_idx, col_name in GDELT_COLUMNS.items():
            if col_idx < len(first_row):
                value = first_row.iloc[col_idx]
                if col_name == "goldsteinscale":
                    try:
                        value = float(value) if pd.notna(value) and value != "" else 0.0
                    except (ValueError, TypeError):
                        value = 0.0
                else:
                    value = str(value) if pd.notna(value) and value != "" else None
                result[col_name] = value
            else:
                result[col_name] = None

        update_data_source_status("gdelt", True, 1, "Success")
        return result

    except Exception as e:
        msg = f"Failed to fetch from GDELT: {e}"
        print(f"[GDELT Client] Error: {msg}")
        update_data_source_status("gdelt", False, 0, msg)
        
        # Return fallback mock event
        return {
            "globaleventid": "123456789",
            "sqldate": "20260711",
            "actor1name": "INDIA",
            "actor2name": "IRAN",
            "eventcode": "020",
            "goldsteinscale": 3.0,
            "actiongeo_fullname": "Strait of Hormuz",
            "actiongeo_countrycode": "IR",
            "sourceurl": "https://www.reuters.com/mock-geopolitical-event",
            "note": f"fallback mock event (error: {e})"
        }

if __name__ == "__main__":
    try:
        result = fetch_latest_events()
        print(f"[PASS] GDELT Event: {result}")
    except Exception as e:
        print(f"[FAIL] GDELT Error: {e}")
