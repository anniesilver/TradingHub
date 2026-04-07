"""Test if TRADES data type gives us earlier SPY data than MIDPOINT"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG
from ibapi.contract import Contract

def test_data_type(data_type):
    """Test fetching early SPY data with specified data type"""
    print(f"\n{'='*80}")
    print(f"Testing with data_type: {data_type}")
    print(f"{'='*80}")

    client = IBKRDataClient(client_id=200)

    # Connect
    if not client.connect_to_ibkr(IBKR_CONFIG['host'], IBKR_CONFIG['port']):
        print("Failed to connect")
        return

    import time
    time.sleep(2)

    # Create contract
    contract = Contract()
    contract.symbol = 'SPY'
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.currency = 'USD'

    # Request data - ask for data ending at 2005-01-01 to see how far back it goes
    client.data = []
    client.data_received.clear()

    end_date = "20050101 23:59:59 US/Eastern"
    period = "10 Y"  # This should give us 1995-2005 if available

    print(f"Requesting: period={period}, end_date={end_date}, whatToShow={data_type}")
    client.reqHistoricalData(0, contract, end_date, period, "1 day", data_type, 1, 1, False, [])

    # Wait for data
    if client.data_received.wait(timeout=30):
        if len(client.data) > 0:
            # Get earliest date
            dates = [bar['date'] for bar in client.data]
            print(f"Received {len(client.data)} bars")
            print(f"Earliest date: {min(dates)}")
            print(f"Latest date: {max(dates)}")
        else:
            print("No data received")
    else:
        print("Timeout waiting for data")

    client.disconnect_from_ibkr()
    time.sleep(2)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SPY EARLY DATA AVAILABILITY TEST")
    print("="*80)

    # Test MIDPOINT
    test_data_type("MIDPOINT")

    # Test TRADES
    test_data_type("TRADES")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
