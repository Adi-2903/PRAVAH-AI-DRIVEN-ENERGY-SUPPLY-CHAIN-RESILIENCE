"""
OFAC Client — Downloads and searches the SDN (Specially Designated Nationals) list.

Source: https://www.treasury.gov/ofac/downloads/sdn.csv
Auth: None (public data)

The SDN CSV file is large (~30K+ entries). This client caches it locally
after the first download to avoid repeated fetches during development.
The cached file is excluded from git via .gitignore (*.csv rule).
"""

import os
import requests
import pandas as pd

SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
# Fallback: the newer OFAC Sanctions List Service (SLS) endpoint
SDN_CSV_URL_FALLBACK = (
    "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
)
# Third fallback: OpenSanctions provides pre-processed OFAC SDN data from fast CDN
SDN_CSV_URL_OPENSANCTIONS = (
    "https://data.opensanctions.org/datasets/latest/us_ofac_sdn/source.csv"
)

# Cache file lives next to this script (gitignored by *.csv rule)
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(CACHE_DIR, "sdn_cache.csv")

# Known sanctioned entity for hardcoded test validation.
# This must ALWAYS return True — if it doesn't, the matching logic has a bug.
KNOWN_SANCTIONED_ENTITY = "NATIONAL IRANIAN OIL COMPANY"

# SDN CSV column names (from OFAC documentation)
SDN_COLUMNS = [
    "ent_num",
    "SDN_Name",
    "SDN_Type",
    "Program",
    "Title",
    "Call_Sign",
    "Vess_type",
    "Tonnage",
    "GRT",
    "Vess_flag",
    "Vess_owner",
    "Remarks",
]

# Timeout: (connect_timeout, read_timeout) — S3 may connect fast but stream slowly
DOWNLOAD_TIMEOUT = (15, 180)


def _download_sdn_list() -> pd.DataFrame:
    """
    Download the SDN CSV from the US Treasury OFAC website.
    Tries multiple URLs in order, using streaming downloads for resilience.
    Caches it locally for subsequent runs.

    Returns:
        pd.DataFrame: The parsed SDN list.
    """
    urls = [SDN_CSV_URL, SDN_CSV_URL_FALLBACK, SDN_CSV_URL_OPENSANCTIONS]
    last_error = None

    for url in urls:
        try:
            print(f"  -> Downloading SDN list from {url} ...")
            # Use streaming download to handle large files on slow connections
            response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
            response.raise_for_status()

            # Stream the content to disk in chunks
            with open(CACHE_FILE, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  [OK] SDN list cached to {CACHE_FILE}")

            return _parse_sdn_csv(CACHE_FILE)
        except Exception as e:
            print(f"  [WARN] Failed to download from {url}: {e}")
            last_error = e

    raise RuntimeError(
        f"Failed to download SDN list from all sources. Last error: {last_error}"
    )


def _parse_sdn_csv(filepath: str) -> pd.DataFrame:
    """
    Parse the SDN CSV file.

    The OFAC SDN CSV does not have a consistent header row and uses
    a fixed column layout. We assign our own column names.
    """
    df = pd.read_csv(
        filepath,
        header=None,
        names=SDN_COLUMNS,
        dtype=str,
        on_bad_lines="skip",
        encoding="latin-1",  # Some entries have non-UTF8 characters
    )
    return df


def _load_sdn_list() -> pd.DataFrame:
    """
    Load the SDN list, using the local cache if available.
    Downloads fresh if no cache exists.
    """
    if os.path.exists(CACHE_FILE):
        print(f"  [OK] Using cached SDN list from {CACHE_FILE}")
        return _parse_sdn_csv(CACHE_FILE)
    else:
        return _download_sdn_list()


def check_entity_sanctions(entity_name: str) -> dict:
    """
    Check whether an entity name appears on the OFAC SDN list.

    Uses case-insensitive substring matching on the SDN_Name column.

    Args:
        entity_name: The name to search for (e.g., "NATIONAL IRANIAN OIL COMPANY").

    Returns:
        dict: {
            "entity": str,           # The queried entity name
            "sanctioned": bool,      # Whether any matches were found
            "match_count": int,      # Number of matches
            "matches": list[dict],   # Up to 5 matching records
        }
    """
    df = _load_sdn_list()

    # Case-insensitive substring search
    search_term = entity_name.upper()
    mask = df["SDN_Name"].fillna("").str.upper().str.contains(search_term, regex=False)
    matches = df[mask]

    match_records = []
    for _, row in matches.head(5).iterrows():
        match_records.append({
            "ent_num": row.get("ent_num"),
            "SDN_Name": row.get("SDN_Name"),
            "SDN_Type": row.get("SDN_Type"),
            "Program": row.get("Program"),
            "Remarks": row.get("Remarks"),
        })

    return {
        "entity": entity_name,
        "sanctioned": len(matches) > 0,
        "match_count": len(matches),
        "matches": match_records,
    }


if __name__ == "__main__":
    try:
        # Run the hardcoded test case — this MUST return sanctioned=True
        result = check_entity_sanctions(KNOWN_SANCTIONED_ENTITY)
        if result["sanctioned"]:
            print(f"[PASS] OFAC Check: {result}")
        else:
            print(
                f"[WARN] OFAC WARNING: Known sanctioned entity '{KNOWN_SANCTIONED_ENTITY}' "
                f"was NOT found! Your matching logic may have a bug. Result: {result}"
            )
    except Exception as e:
        print(f"[FAIL] OFAC Error: {e}")
