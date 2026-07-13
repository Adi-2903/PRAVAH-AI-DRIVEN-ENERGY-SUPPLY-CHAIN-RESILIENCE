# shared/clients/test_spine.py
"""
test_spine.py — Stage 1 Live Data Spine Integration Test

Imports all four client wrappers and runs them sequentially.
Each source is wrapped individually so one failure doesn't block the others.
"""

import sys
import os
import io

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure the shared/clients directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eia_spot_client import fetch_latest_brent_price
from gdelt_client import fetch_latest_events
from ais_client import get_sample_ship_position
from ofac_client import check_entity_sanctions, KNOWN_SANCTIONED_ENTITY

def main():
    print("=" * 70)
    print("  Pravah Stage 1 — Live Data Spine Test")
    print("=" * 70)
    print()

    sources = {
        "EIA (crude price)": fetch_latest_brent_price,
        "GDELT (event record)": fetch_latest_events,
        "aisstream (ship position)": get_sample_ship_position,
        "OFAC (sanctions check - sanctioned)": lambda: check_entity_sanctions(KNOWN_SANCTIONED_ENTITY),
        "OFAC (sanctions check - clean)": lambda: check_entity_sanctions("A RANDOM CLEAN TANKER"),
    }

    results = {}
    passed = 0
    failed = 0

    for label, fn in sources.items():
        print(f"--- Testing: {label} ---")
        try:
            result = fn()
            print(f"[PASS] {label}: {result}")
            results[label] = ("PASS", result)
            passed += 1
        except Exception as e:
            print(f"[FAIL] {label}: {e}")
            results[label] = ("FAIL", str(e))
            failed += 1
        print()

    # Summary
    print("=" * 70)
    print(f"  Results: {passed} passed, {failed} failed out of {len(sources)} sources")
    print("=" * 70)

    for label, (status, _) in results.items():
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {label}")

    print()
    if failed == 0:
        print("Stage 1 Complete — All data sources are live!")
    elif passed > 0:
        print(
            f"Partial pass ({passed}/{len(sources)}). "
            "Fix the failing sources next — the rest are ready."
        )
    else:
        print("All sources failed. Check API keys and network connectivity.")

    return failed

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
