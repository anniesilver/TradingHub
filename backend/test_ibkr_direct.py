"""Direct test of IBKR reqHistoricalData to see raw response"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG
import time

client = IBKRDataClient(IBKR_CONFIG["client_id"])

print("Connecting to IBKR...")
client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"])
time.sleep(2)

print("\n" + "="*80)
print("Testing 30-min bars with '1 M' period (per IBKR docs)")
print("="*80)

# Request exactly as IBKR documentation shows
data = client.fetch_historical_data("SPY", "1 M", "30 mins")

print(f"\nReceived {len(data)} bars")
print("\nFirst 10 bars:")
print(f"{'Index':<6} {'Date':<35} {'Close':<10} {'Volume':<10}")
print("-"*80)
for i, bar in enumerate(data[:10]):
    print(f"{i:<6} {bar['date']:<35} {bar['close']:<10.2f} {bar['volume']:<10}")

# Check if timestamps have time component
if len(data) > 0:
    first_date = data[0]['date']
    print(f"\nFirst date string: '{first_date}'")
    print(f"Length: {len(first_date)}")
    print(f"Has space: {' ' in first_date}")

    if ' ' in first_date.strip():
        print("\n✅ Data has timestamps - these are INTRADAY bars")
    else:
        print("\n❌ Data has NO timestamps - these are DAILY bars")
        print("    IBKR returned daily data even though we requested 30-min bars!")

client.disconnect_from_ibkr()
