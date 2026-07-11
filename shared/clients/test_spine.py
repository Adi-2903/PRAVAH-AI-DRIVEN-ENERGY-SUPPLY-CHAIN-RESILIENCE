# shared/clients/test_spine.py
import asyncio
import sys
from shared.clients.eia_client import fetch_latest_brent_price
from shared.clients.gdelt_client import fetch_latest_events
from shared.clients.ais_client import get_sample_ship_position
from shared.clients.ofac_client import check_entity_sanctions

# Ensure stdout encodes UTF-8 properly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_test_spine():
    print("==================================================")
    print("PRAVAH: Testing Live Data Spine Clients")
    print("==================================================\n")

    # 1. EIA crude price
    print("--- 1. Testing EIA Client ---")
    try:
        eia_res = fetch_latest_brent_price()
        print(f"✅ EIA (crude price): {eia_res}\n")
    except Exception as e:
        print(f"❌ EIA (crude price) failed: {e}\n")

    # 2. GDELT event record
    print("--- 2. Testing GDELT Client ---")
    try:
        gdelt_res = fetch_latest_events()
        print(f"✅ GDELT (event record): {gdelt_res}\n")
    except Exception as e:
        print(f"❌ GDELT (event record) failed: {e}\n")

    # 3. aisstream ship position (async)
    print("--- 3. Testing AIS Client ---")
    try:
        ais_res = asyncio.run(get_sample_ship_position())
        print(f"✅ aisstream (ship position): {ais_res}\n")
    except Exception as e:
        print(f"❌ aisstream (ship position) failed: {e}\n")

    # 4. OFAC sanctions check
    print("--- 4. Testing OFAC Client ---")
    try:
        # Check a known sanctioned entity (YAZD)
        ofac_res = check_entity_sanctions("YAZD")
        print(f"✅ OFAC (sanctions check for 'YAZD' - expected True): {ofac_res}")
        # Check a clean entity
        ofac_clean = check_entity_sanctions("A RANDOM TANKER THAT IS NOT SANCTIONED")
        print(f"✅ OFAC (sanctions check for clean entity - expected False): {ofac_clean}\n")
    except Exception as e:
        print(f"❌ OFAC (sanctions check) failed: {e}\n")

    print("==================================================")
    print("Test Spine Run Complete.")
    print("==================================================")

if __name__ == "__main__":
    run_test_spine()
