"""Test IBKR TWS/Gateway connection and data fetching"""

import sys
import os
from datetime import datetime, timedelta

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import ibkr_service, IBKR_CONFIG

def test_connection():
    """Test IBKR connection"""
    print("=" * 60)
    print("Testing IBKR TWS/Gateway Connection")
    print("=" * 60)
    print(f"\nConnection settings:")
    print(f"  Host: {IBKR_CONFIG['host']}")
    print(f"  Port: {IBKR_CONFIG['port']}")
    print(f"  Client ID: {IBKR_CONFIG['client_id']}")
    print()

    # Test 1: Try to connect and fetch minimal data
    print("Test 1: Attempting to connect and fetch 1 year of SPY data...")
    print("-" * 60)

    try:
        from ibkr_data_service import IBKRDataClient

        client = IBKRDataClient(IBKR_CONFIG["client_id"])
        print("✓ Client created")

        # Try to connect
        if client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
            print("✓ Connection established")

            # Wait for connection to be ready
            import time
            print("  Waiting for connection to be ready...", end="")
            time.sleep(3)
            print(" done")

            # Check if connected
            if client.isConnected():
                print("✓ Client is connected to TWS/Gateway")

                # Try to fetch a small amount of data
                print("  Fetching 1 year of historical data...")
                try:
                    data = client.fetch_historical_data("SPY", "1 Y", "1 day")
                    if data and len(data) > 0:
                        print(f"✓ SUCCESS: Received {len(data)} bars of data")
                        print(f"  Sample data: {data[0]}")
                    else:
                        print("✗ FAIL: No data received")
                except Exception as fetch_error:
                    print(f"✗ ERROR fetching data: {fetch_error}")

                # Disconnect
                client.disconnect_from_ibkr()
                print("✓ Disconnected")
            else:
                print("✗ Client reports not connected")
                print("  Check if TWS/Gateway is running")
                print("  Check if API settings are enabled:")
                print("    - Configure → API → Settings")
                print("    - Enable 'ActiveX and Socket Clients'")
        else:
            print("✗ Connection failed")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("TROUBLESHOOTING:")
    print("=" * 60)
    print("If connection failed, please verify:")
    print("1. TWS or IB Gateway is running")
    print("2. TWS/Gateway API is enabled:")
    print("   - Open TWS/Gateway")
    print("   - Go to: File → Global Configuration → API → Settings")
    print("   - Check 'Enable ActiveX and Socket Clients'")
    print("   - Verify port matches .env file (7496 for TWS, 4002 for Gateway)")
    print("3. If using Gateway, ensure it's connected to your IBKR account")
    print("4. Try using a different Client ID (change IBKR_CLIENT_ID in .env)")
    print("=" * 60)

if __name__ == "__main__":
    test_connection()
