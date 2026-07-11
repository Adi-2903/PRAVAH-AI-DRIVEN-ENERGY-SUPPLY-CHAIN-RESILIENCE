"""
GDELT Client — Fetches the latest 15-minute geopolitical event export.

Endpoint: http://data.gdeltproject.org/gdeltv2/lastupdate.txt
Auth: None (open data)

The lastupdate.txt file returns 3 lines:
  Line 1 → Events export (.export.CSV.zip)  ← we want this one
  Line 2 → Mentions export
  Line 3 → GKG (Global Knowledge Graph) export

The CSV inside the zip is tab-separated with NO header row.
Column indices are defined by the GDELT 2.0 Event Codebook.
"""

import io
import zipfile
import requests
import pandas as pd

LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# Key GDELT 2.0 Event column indices (0-based) from the codebook.
# Full spec: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
# The event export has 61 columns (0-60). Each Geo block has 8 fields:
#   Type, FullName, CountryCode, ADM1Code, ADM2Code, Lat, Long, FeatureID
# Actor1Geo: 35-42, Actor2Geo: 43-50, ActionGeo: 51-58, DATEADDED: 59, SOURCEURL: 60
GDELT_COLUMNS = {
    0: "GLOBALEVENTID",
    1: "SQLDATE",
    2: "MonthYear",
    3: "Year",
    4: "FractionDate",
    5: "Actor1Code",
    6: "Actor1Name",
    7: "Actor1CountryCode",
    8: "Actor1KnownGroupCode",
    12: "Actor1Type1Code",
    15: "Actor2Code",
    16: "Actor2Name",
    17: "Actor2CountryCode",
    26: "EventCode",
    27: "EventBaseCode",
    28: "EventRootCode",
    29: "QuadClass",
    30: "GoldsteinScale",
    31: "NumMentions",
    34: "AvgTone",
    51: "ActionGeo_Type",
    52: "ActionGeo_FullName",
    53: "ActionGeo_CountryCode",
    54: "ActionGeo_ADM1Code",
    56: "ActionGeo_Lat",
    57: "ActionGeo_Long",
    60: "SOURCEURL",
}


def fetch_latest_events() -> dict:
    """
    Download the most recent GDELT 2.0 event export and parse the first record.

    Returns:
        dict: Key fields from the first event row, including:
              GLOBALEVENTID, Actor1CountryCode, Actor2CountryCode,
              GoldsteinScale, ActionGeo_CountryCode, ActionGeo_Lat,
              ActionGeo_Long, SOURCEURL, and more.

    Raises:
        ValueError: If the lastupdate.txt response is malformed.
        requests.HTTPError: On HTTP errors.
    """
    # Step 1: Get the lastupdate.txt and parse the FIRST line (events export)
    response = requests.get(LASTUPDATE_URL, timeout=15)
    response.raise_for_status()

    lines = response.text.strip().split("\n")
    if not lines:
        raise ValueError("GDELT lastupdate.txt returned empty response.")

    # Each line is: <size_bytes> <md5_hash> <url>
    # We want line 0 (events export), NOT line 1 (mentions) or line 2 (GKG)
    parts = lines[0].strip().split(" ")
    if len(parts) < 3:
        raise ValueError(f"Unexpected lastupdate.txt format: {lines[0]}")

    zip_url = parts[2]  # The third token is the URL

    # Step 2: Download the zip file into memory
    zip_response = requests.get(zip_url, timeout=30)
    zip_response.raise_for_status()

    # Step 3: Extract and parse the CSV from the zip
    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
        csv_filename = zf.namelist()[0]
        with zf.open(csv_filename) as csv_file:
            # GDELT CSVs are tab-separated with NO header row
            df = pd.read_csv(csv_file, sep="\t", header=None, dtype=str)

    if df.empty:
        raise ValueError("GDELT event export CSV is empty.")

    # Step 4: Extract the first row using our column mapping
    first_row = df.iloc[0]
    result = {}
    for col_idx, col_name in GDELT_COLUMNS.items():
        if col_idx < len(first_row):
            value = first_row.iloc[col_idx]
            # Try to convert numeric fields
            if col_name in ("GoldsteinScale", "AvgTone", "ActionGeo_Lat",
                            "ActionGeo_Long", "FractionDate"):
                try:
                    value = float(value) if pd.notna(value) and value != "" else None
                except (ValueError, TypeError):
                    pass
            elif col_name in ("GLOBALEVENTID", "NumMentions", "Year",
                              "QuadClass", "ActionGeo_Type"):
                try:
                    value = int(value) if pd.notna(value) and value != "" else None
                except (ValueError, TypeError):
                    pass
            else:
                value = str(value) if pd.notna(value) and value != "" else None
            result[col_name] = value
        else:
            result[col_name] = None

    return result


if __name__ == "__main__":
    try:
        result = fetch_latest_events()
        print(f"[PASS] GDELT Event: {result}")
    except Exception as e:
        print(f"[FAIL] GDELT Error: {e}")
