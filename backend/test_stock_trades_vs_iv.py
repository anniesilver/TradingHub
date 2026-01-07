"""Test if stock TRADES and IV return matching bar counts"""
import os
import sys
import threading
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class TestStockDataClient(EWrapper, EClient):
    """Test client to fetch both TRADES and IV from stock"""

    def __init__(self, client_id=999):
        EClient.__init__(self, self)
        self.client_id = client_id
        self.trades_data = []
        self.iv_data = []
        self.trades_received = threading.Event()
        self.iv_received = threading.Event()

    def connect_to_ibkr(self, host="127.0.0.1", port=7496):
        """Connect to IBKR"""
        try:
            self.connect(host, port, self.client_id)
            thread = threading.Thread(target=self.run, daemon=True)
            thread.start()
            time.sleep(1)  # Wait for connection
            return self.isConnected()
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect_from_ibkr(self):
        """Disconnect"""
        self.disconnect()

    def historicalData(self, reqId: int, bar):
        """Receive historical data bars"""
        if reqId == 0:  # TRADES
            print(f"TRADES bar: {bar.date}, close={bar.close}")
            self.trades_data.append({
                'date': bar.date,
                'close': bar.close
            })
        elif reqId == 1:  # IV
            print(f"IV bar: {bar.date}, iv={bar.close}")
            self.iv_data.append({
                'date': bar.date,
                'iv': bar.close
            })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Called when request completes"""
        if reqId == 0:
            print(f"\n✓ TRADES request complete: {len(self.trades_data)} bars")
            print(f"  Date range: {self.trades_data[0]['date'] if self.trades_data else 'N/A'} to {self.trades_data[-1]['date'] if self.trades_data else 'N/A'}")
            self.trades_received.set()
        elif reqId == 1:
            print(f"\n✓ IV request complete: {len(self.iv_data)} bars")
            print(f"  Date range: {self.iv_data[0]['date'] if self.iv_data else 'N/A'} to {self.iv_data[-1]['date'] if self.iv_data else 'N/A'}")
            self.iv_received.set()

def test_stock_data_match():
    """Test if stock TRADES and IV return same bar counts"""
    print("=" * 80)
    print("TESTING: Stock TRADES vs Stock IV Bar Count Match")
    print("=" * 80)
    print("\nHypothesis: Fetching TRADES and IV from the SAME stock contract")
    print("            with identical parameters should return IDENTICAL bar counts")
    print("=" * 80)

    client = TestStockDataClient()

    try:
        # Connect
        if not client.connect_to_ibkr("127.0.0.1", 7496):
            print("❌ Failed to connect to IBKR")
            return False

        print("\n✓ Connected to IBKR")

        # Create stock contract
        stock = Contract()
        stock.symbol = "SPY"
        stock.secType = "STK"
        stock.exchange = "SMART"
        stock.currency = "USD"

        # Test parameters (matching what we use for options)
        period = "1 M"
        bar_size = "30 mins"

        print(f"\nTest Parameters:")
        print(f"  Symbol: {stock.symbol}")
        print(f"  Contract Type: {stock.secType}")
        print(f"  Period: {period}")
        print(f"  Bar Size: {bar_size}")
        print(f"  Trading Hours: Regular only (1)")

        # Request 1: Stock TRADES
        print(f"\n" + "=" * 80)
        print("REQUEST 1: Stock TRADES Data")
        print("=" * 80)

        client.reqHistoricalData(
            0,  # reqId
            stock,
            '',  # End date
            period,
            bar_size,
            "TRADES",  # whatToShow
            1,  # useRTH (regular trading hours only)
            1,  # formatDate
            False,
            []
        )

        # Wait for TRADES
        if not client.trades_received.wait(timeout=30):
            print("❌ Timeout waiting for TRADES data")
            return False

        time.sleep(2)  # Wait before second request

        # Request 2: Stock IV
        print(f"\n" + "=" * 80)
        print("REQUEST 2: Stock IV (OPTION_IMPLIED_VOLATILITY)")
        print("=" * 80)

        client.reqHistoricalData(
            1,  # reqId
            stock,
            '',  # End date
            period,
            bar_size,
            "OPTION_IMPLIED_VOLATILITY",  # whatToShow
            1,  # useRTH (regular trading hours only)
            1,  # formatDate
            False,
            []
        )

        # Wait for IV
        if not client.iv_received.wait(timeout=30):
            print("❌ Timeout waiting for IV data")
            return False

        # Compare results
        print(f"\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)

        trades_count = len(client.trades_data)
        iv_count = len(client.iv_data)

        print(f"\nBar counts:")
        print(f"  TRADES: {trades_count} bars")
        print(f"  IV:     {iv_count} bars")
        print(f"  Difference: {abs(trades_count - iv_count)} bars")

        if trades_count == iv_count:
            print(f"\n✅ SUCCESS: Bar counts MATCH EXACTLY!")
            print(f"   Both requests returned {trades_count} bars")
            print(f"   NO forward/backward fill logic needed!")

            # Check if dates also match
            trades_dates = set(bar['date'] for bar in client.trades_data)
            iv_dates = set(bar['date'] for bar in client.iv_data)

            if trades_dates == iv_dates:
                print(f"\n✅ PERFECT MATCH: All timestamps are identical!")
                print(f"   This proves IBKR returns identical bars for same contract")
            else:
                print(f"\n⚠️  Bar counts match but timestamps differ")
                print(f"   TRADES has {len(trades_dates - iv_dates)} unique dates")
                print(f"   IV has {len(iv_dates - trades_dates)} unique dates")
        else:
            print(f"\n❌ MISMATCH: Bar counts DO NOT match")
            print(f"   Difference: {abs(trades_count - iv_count)} bars")
            print(f"   This is unexpected for the same contract!")

            if client.trades_data and client.iv_data:
                print(f"\n   TRADES range: {client.trades_data[0]['date']} to {client.trades_data[-1]['date']}")
                print(f"   IV range:     {client.iv_data[0]['date']} to {client.iv_data[-1]['date']}")

        print("=" * 80)

        return trades_count == iv_count

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.disconnect_from_ibkr()

if __name__ == "__main__":
    print("\nIMPORTANT: Make sure IBKR TWS/Gateway is running!")
    input("Press Enter to start test...")

    result = test_stock_data_match()

    if result:
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        print("The current approach of fetching from DIFFERENT contracts is the problem!")
        print("  - Option TRADES (from option contract)")
        print("  - Stock IV (from stock contract)")
        print("\nSolution: Fetch BOTH from the same contract to guarantee matching bars")
    else:
        print("\n" + "=" * 80)
        print("Further investigation needed...")
