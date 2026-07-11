# shared/clients/gdelt_client.py
import os
import csv
import zipfile
import requests
from dotenv import load_dotenv
from shared.clients.db_helper import update_data_source_status

load_dotenv()

def fetch_latest_events() -> dict:
    """
    Downloads the latest GDELT 2.0 15-minute events export,
    parses the first event, cleans up temporary files,
    and updates the 'gdelt' data source status in Supabase.
    """
    last_update_url = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    temp_zip = "latest_gdelt_export.zip"
    temp_dir = "latest_gdelt_extracted"
    
    try:
        # 1. Fetch lastupdate.txt to find the latest export URL
        response = requests.get(last_update_url, timeout=10)
        if response.status_code != 200:
            raise requests.RequestException(f"Failed to fetch lastupdate.txt: status {response.status_code}")
            
        lines = response.text.strip().split("\n")
        if not lines:
            raise ValueError("Empty response from GDELT lastupdate.txt")
            
        # First line is the export CSV zip
        export_line = lines[0]
        parts = export_line.split(" ")
        if len(parts) < 3:
            raise ValueError(f"Unexpected format in lastupdate.txt line: {export_line}")
            
        zip_url = parts[2].strip()
        print(f"[GDELT Client] Downloading latest export zip: {zip_url}")
        
        # 2. Download the zip file
        zip_response = requests.get(zip_url, timeout=30)
        if zip_response.status_code != 200:
            raise requests.RequestException(f"Failed to download GDELT zip: status {zip_response.status_code}")
            
        with open(temp_zip, "wb") as f:
            f.write(zip_response.content)
            
        # 3. Extract the ZIP
        os.makedirs(temp_dir, exist_ok=True)
        extracted_files = []
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            extracted_files = zip_ref.namelist()
            
        if not extracted_files:
            raise FileNotFoundError("No files extracted from GDELT zip")
            
        csv_filename = os.path.join(temp_dir, extracted_files[0])
        
        # 4. Parse the first row of the tab-delimited CSV
        first_event = None
        with open(csv_filename, "r", encoding="utf-8", errors="ignore") as f:
            # GDELT 2.0 event CSV is tab-delimited
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) >= 61:
                    first_event = row
                    break
                    
        # 5. Clean up downloaded/extracted files immediately
        try:
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            if os.path.exists(csv_filename):
                os.remove(csv_filename)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_err:
            print(f"[GDELT Client] Cleanup warning: {cleanup_err}")
            
        if not first_event:
            raise ValueError("No valid event records found in GDELT CSV export")
            
        # Extract specific columns:
        # 0: GLOBALEVENTID, 1: SQLDATE, 6: Actor1Name, 16: Actor2Name, 26: EventCode
        # 30: GoldsteinScale, 52: ActionGeo_FullName, 53: ActionGeo_CountryCode, 60: SOURCEURL
        try:
            goldstein = float(first_event[30]) if first_event[30] else 0.0
        except ValueError:
            goldstein = 0.0
            
        result = {
            "globaleventid": first_event[0],
            "sqldate": first_event[1],
            "actor1name": first_event[6],
            "actor2name": first_event[16],
            "eventcode": first_event[26],
            "goldsteinscale": goldstein,
            "actiongeo_fullname": first_event[52],
            "actiongeo_countrycode": first_event[53],
            "sourceurl": first_event[60]
        }
        
        # Update data source status
        update_data_source_status("gdelt", True, 1, "Success")
        return result
        
    except Exception as e:
        msg = f"Failed to fetch from GDELT: {e}"
        print(f"[GDELT Client] Error: {msg}")
        update_data_source_status("gdelt", False, 0, msg)
        
        # Cleanup if files still exist
        try:
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
        except:
            pass
            
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
