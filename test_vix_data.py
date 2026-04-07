"""Test VIX data availability"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG
from ibapi.contract import Contract
import time

def test_vix_data():
    """Test VIX data with 25Y duration"""
    print("\n" + "="*80)
    print("Testing VIX - 25 Year Historical Data")
    print("="*80)

    client = IBKRDataClient(client_id=600)

    if not client.connect_to_ibkr(IBKR_CONFIG['host'], IBKR_CONFIG['port']):
        print("Failed to connect")
        return

    time.sleep(2)

    # VIX contract
    contract = Contract()
    contract.symbol = 'VIX'
    contract.secType = 'IND'
    contract.exchange = 'CBOE'
    contract.currency = 'USD'

    client.data = []
    client.data_received.clear()

    print(f"\nRequesting VIX data:")
    print(f"  Duration: 25 Y")
    print(f"  End date: '' (current)")
    print(f"  Data type: TRADES")

    client.reqHistoricalData(
        reqId=0,
        contract=contract,
        endDateTime='',
        durationStr='25 Y',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    print("\nWaiting for data...")
    if client.data_received.wait(timeout=60):
        print(f"\n✅ Received {len(client.data)} bars")

        if len(client.data) > 0:
            print(f"\nFirst 5 bars:")
            for bar in client.data[:5]:
                print(f"  {bar['date']}: ${bar['close']:.2f}")

            print(f"\nLast 5 bars:")
            for bar in client.data[-5:]:
                print(f"  {bar['date']}: ${bar['close']:.2f}")

            print(f"\n{'='*80}")
            print(f"VIX DATE RANGE: {client.data[0]['date']} to {client.data[-1]['date']}")
            print(f"Total bars: {len(client.data)}")
            print(f"{'='*80}")
        else:
            print("❌ No data received")
    else:
        print("❌ Timeout")

    client.disconnect_from_ibkr()

if __name__ == "__main__":
    test_vix_data()
