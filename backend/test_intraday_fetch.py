"""
Test script to verify 30-minute intraday data fetching from IBKR

This tests the IBKR API directly to see if intraday bars are properly returned.
"""

import sys
import os
from datetime import datetime, timedelta

# Add services path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG

def test_intraday_fetch():
    """Test fetching 30-min bars directly from IBKR"""

    print("="*80)
    print("Testing 30-Minute Intraday Data Fetch from IBKR")
    print("="*80)

    # Create client
    client = IBKRDataClient(IBKR_CONFIG["client_id"])

    # Connect
    print("\n1. Connecting to IBKR...")
    if not client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
        print("❌ Connection failed!")
        return False

    print("✓ Connected successfully")

    # Test different periods to find what works for 30-min bars
    test_configs = [
        ("1 D", "30 mins", "1 day of 30-min bars (should get ~13 bars)"),
        ("5 D", "30 mins", "5 days of 30-min bars (should get ~65 bars)"),
        ("10 D", "30 mins", "10 days of 30-min bars (should get ~130 bars)"),
        ("1 M", "30 mins", "1 month of 30-min bars"),
        ("2 M", "30 mins", "2 months of 30-min bars"),
    ]

    for period, bar_size, description in test_configs:
        print(f"\n2. Testing: {description}")
        print(f"   Period: {period}, Bar Size: {bar_size}")

        try:
            # Fetch data
            data = client.fetch_historical_data("SPY", period, bar_size)

            print(f"   ✓ Received {len(data)} bars")

            if len(data) > 0:
                print(f"\n   First 5 bars:")
                for i, bar in enumerate(data[:5]):
                    print(f"     {i+1}. Date: {bar['date']:30s} | Close: ${bar['close']:7.2f} | Volume: {bar['volume']}")

                # Check if these are actually intraday bars
                first_date = data[0]['date']
                has_time = ' ' in first_date.strip()

                if has_time:
                    print(f"\n   ✅ SUCCESS: Data contains timestamps (intraday bars)")
                else:
                    print(f"\n   ❌ ISSUE: Data has no timestamps (looks like daily bars)")

                # If successful, we found the right parameters
                if has_time and len(data) > 10:
                    print(f"\n{'='*80}")
                    print(f"✅ FOUND WORKING CONFIGURATION:")
                    print(f"   Period: {period}")
                    print(f"   Bar Size: {bar_size}")
                    print(f"   Result: {len(data)} intraday bars")
                    print(f"{'='*80}")
                    break
            else:
                print(f"   ⚠️  No data returned")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Disconnect
    client.disconnect_from_ibkr()
    print("\n3. Disconnected from IBKR")

    return True


if __name__ == "__main__":
    success = test_intraday_fetch()
    exit(0 if success else 1)
