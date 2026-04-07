"""Simple test: Fetch Sep 2000 data for SPY and VIX"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataClient, IBKR_CONFIG
from ibapi.contract import Contract
import time

def test_month_data(symbol, end_date, data_type="MIDPOINT"):
    """Fetch one month of data and display results"""
    print("\n" + "="*80)
    print(f"TESTING: {symbol} - September 2000")
    print(f"Data type: {data_type}")
    print("="*80)

    # Create client
    client = IBKRDataClient(client_id=400)

    # Connect
    if not client.connect_to_ibkr(IBKR_CONFIG['host'], IBKR_CONFIG['port']):
        print("Failed to connect")
        return

    time.sleep(2)

    # Create contract
    contract = Contract()
    contract.symbol = symbol
    contract.currency = 'USD'

    if symbol == 'VIX':
        contract.secType = 'IND'
        contract.exchange = 'CBOE'
    else:
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.primaryExchange = 'ARCA'  # SPY primary exchange

    # Request data
    client.data = []
    client.data_received.clear()

    period = "1 M"  # Just 1 month
    bar_size = "1 day"

    print(f"\nRequesting:")
    print(f"  Symbol: {symbol}")
    print(f"  Period: {period}")
    print(f"  End date: {end_date}")
    print(f"  Data type: {data_type}")

    client.reqHistoricalData(
        reqId=0,
        contract=contract,
        endDateTime=end_date,
        durationStr=period,
        barSizeSetting=bar_size,
        whatToShow=data_type,
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    # Wait for data
    print("\nWaiting for data...")
    if client.data_received.wait(timeout=30):
        print(f"\nReceived {len(client.data)} bars")

        if len(client.data) > 0:
            print(f"\n{'Date':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Volume':<10}")
            print("-" * 70)
            for bar in client.data:
                print(f"{bar['date']:<12} {bar['open']:<10.2f} {bar['high']:<10.2f} {bar['low']:<10.2f} {bar['close']:<10.2f} {bar['volume']:<10}")

            print(f"\nFirst date: {client.data[0]['date']}")
            print(f"Last date: {client.data[-1]['date']}")
        else:
            print("No data received from IBKR")
    else:
        print("Timeout waiting for data")

    # Disconnect
    client.disconnect_from_ibkr()
    time.sleep(2)

def test_grok_approach(symbol, duration, data_type):
    """Test Grok's approach: large duration with empty endDateTime"""
    print("\n" + "="*80)
    print(f"TESTING GROK APPROACH: {symbol} - {duration}")
    print(f"Data type: {data_type}")
    print("="*80)

    client = IBKRDataClient(client_id=500)

    if not client.connect_to_ibkr(IBKR_CONFIG['host'], IBKR_CONFIG['port']):
        print("Failed to connect")
        return

    time.sleep(2)

    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.primaryExchange = 'ARCA'
    contract.currency = 'USD'

    client.data = []
    client.data_received.clear()

    print(f"\nRequesting:")
    print(f"  Duration: {duration}")
    print(f"  End date: '' (EMPTY = current/latest)")
    print(f"  Data type: {data_type}")

    client.reqHistoricalData(
        reqId=0,
        contract=contract,
        endDateTime='',  # EMPTY = current/latest
        durationStr=duration,
        barSizeSetting='1 day',
        whatToShow=data_type,
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    print("\nWaiting for data (60s timeout)...")
    if client.data_received.wait(timeout=60):
        print(f"\n✅ Received {len(client.data)} bars")

        if len(client.data) > 0:
            print(f"\nFirst 3 bars:")
            for bar in client.data[:3]:
                print(f"  {bar['date']}: ${bar['close']:.2f}")

            print(f"\nLast 3 bars:")
            for bar in client.data[-3:]:
                print(f"  {bar['date']}: ${bar['close']:.2f}")

            print(f"\nDATE RANGE: {client.data[0]['date']} to {client.data[-1]['date']}")
        else:
            print("❌ No data received")
    else:
        print("❌ Timeout")

    client.disconnect_from_ibkr()
    time.sleep(2)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SPY Historical Data - Testing GROK's Approach")
    print("="*80)

    # Test Grok's approach: large duration + empty endDateTime
    print("\n⚠️  NOTE: TWS charts typically show ADJUSTED_LAST prices")
    print("Testing all common whatToShow types:\n")

    test_grok_approach('SPY', '25 Y', 'TRADES')
    test_grok_approach('SPY', '25 Y', 'MIDPOINT')
    test_grok_approach('SPY', '25 Y', 'ADJUSTED_LAST')  # TWS default
    test_grok_approach('SPY', '25 Y', 'HISTORICAL_VOLATILITY')

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
