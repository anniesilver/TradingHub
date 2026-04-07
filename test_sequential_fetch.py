"""Test sequential IBKR fetches with same client ID"""

import sys
import os
import time

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import ibkr_service

def test_sequential_fetch():
    """Test fetching SPY then VIX sequentially (like the backend does)"""
    print("=" * 60)
    print("Testing Sequential IBKR Fetches (like backend does)")
    print("=" * 60)
    print("\nThis simulates exactly what the backend does:")
    print("1. Fetch SPY data")
    print("2. Disconnect")
    print("3. Fetch VIX data")
    print("4. Disconnect\n")

    # Clear some data to force IBKR fetch
    print("Step 1: Fetch SPY data (1 month)")
    print("-" * 60)

    try:
        result1 = ibkr_service.fetch_and_store_data("SPY", "1 M")
        if result1:
            print("✓ SPY fetch successful")
        else:
            print("✗ SPY fetch failed")
    except Exception as e:
        print(f"✗ SPY fetch error: {e}")

    print("\nStep 2: Wait a moment...")
    time.sleep(2)  # Give IBKR time to release the client ID

    print("\nStep 3: Fetch VIX data (1 month)")
    print("-" * 60)

    try:
        result2 = ibkr_service.fetch_and_store_data("VIX", "1 M")
        if result2:
            print("✓ VIX fetch successful")
        else:
            print("✗ VIX fetch failed")
    except Exception as e:
        print(f"✗ VIX fetch error: {e}")

    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    if result1 and result2:
        print("✓ Both fetches worked - sequential fetching is OK!")
        print("  The client ID conflict might only happen without proper")
        print("  disconnect timing or in concurrent scenarios.")
    else:
        print("✗ One or both fetches failed")
        print("  This indicates a problem with the fetch/disconnect logic")
    print("=" * 60)

if __name__ == "__main__":
    test_sequential_fetch()
