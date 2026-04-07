"""Test concurrent IBKR fetches to identify client ID conflicts"""

import sys
import os
import time
from datetime import datetime

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG

def test_concurrent_fetches():
    """Test fetching two symbols concurrently (like SPY and VIX)"""
    print("=" * 60)
    print("Testing Concurrent IBKR Fetches (SPY + VIX)")
    print("=" * 60)
    print("\nThis simulates what happens when the backend loads data")
    print("for both SPY and VIX at the same time.\n")

    # Test 1: Try with same client ID (current implementation)
    print("Test 1: Using SAME client ID for both (current behavior)")
    print("-" * 60)

    try:
        # First connection - SPY
        client1 = IBKRDataClient(IBKR_CONFIG["client_id"])  # ID: 123
        print(f"Created SPY client with ID: {IBKR_CONFIG['client_id']}")

        if client1.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
            print("✓ SPY client connected")

            # Second connection - VIX (same client ID)
            client2 = IBKRDataClient(IBKR_CONFIG["client_id"])  # ID: 123 (CONFLICT!)
            print(f"Created VIX client with ID: {IBKR_CONFIG['client_id']}")

            if client2.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
                print("✗ VIX client connected (this shouldn't work with same ID!)")
            else:
                print("✗ VIX client failed to connect (expected with same ID)")

            client1.disconnect_from_ibkr()
            client2.disconnect_from_ibkr()
    except Exception as e:
        print(f"✗ ERROR: {e}")

    time.sleep(2)

    # Test 2: Try with different client IDs (proposed fix)
    print("\nTest 2: Using DIFFERENT client IDs (proposed fix)")
    print("-" * 60)

    try:
        # First connection - SPY with ID 124
        client1 = IBKRDataClient(124)
        print(f"Created SPY client with ID: 124")

        if client1.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
            print("✓ SPY client connected")

            # Second connection - VIX with ID 125
            client2 = IBKRDataClient(125)
            print(f"Created VIX client with ID: 125")

            if client2.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
                print("✓ VIX client connected (different IDs work!)")

                # Try fetching small amounts of data
                print("  Fetching 1 month of SPY data...")
                data1 = client1.fetch_historical_data("SPY", "1 M", "1 day")
                print(f"  ✓ Got {len(data1)} bars for SPY")

                print("  Fetching 1 month of VIX data...")
                data2 = client2.fetch_historical_data("VIX", "1 M", "1 day")
                print(f"  ✓ Got {len(data2)} bars for VIX")
            else:
                print("✗ VIX client failed to connect")

            client1.disconnect_from_ibkr()
            client2.disconnect_from_ibkr()
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    print("If Test 1 showed connection issues and Test 2 succeeded,")
    print("then the problem is CLIENT ID CONFLICTS when loading")
    print("multiple symbols (SPY + VIX) simultaneously.")
    print()
    print("SOLUTION: Use unique client IDs for each connection")
    print("=" * 60)

if __name__ == "__main__":
    test_concurrent_fetches()
