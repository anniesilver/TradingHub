"""Test Option TRADES vs Stock TRADES bar counts"""
import os
import sys
import threading
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class TestTradesClient(EWrapper, EClient):
    """Test client to fetch TRADES from both option and stock"""

    def __init__(self, client_id=999):
        EClient.__init__(self, self)
        self.client_id = client_id
        self.option_trades = []
        self.stock_trades = []
        self.option_received = threading.Event()
        self.stock_received = threading.Event()

    def connect_to_ibkr(self, host="127.0.0.1", port=7496):
        """Connect to IBKR"""
        try:
            self.connect(host, port, self.client_id)
            thread = threading.Thread(target=self.run, daemon=True)
            thread.start()
            time.sleep(1)
            return self.isConnected()
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect_from_ibkr(self):
        """Disconnect"""
        self.disconnect()

    def historicalData(self, reqId: int, bar):
        """Receive historical data bars"""
        if reqId == 0:  # Option TRADES
            self.option_trades.append({
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        elif reqId == 1:  # Stock TRADES
            self.stock_trades.append({
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Called when request completes"""
        if reqId == 0:
            print(f"\n✓ Option TRADES complete: {len(self.option_trades)} bars")
            if self.option_trades:
                print(f"  Range: {self.option_trades[0]['date']} to {self.option_trades[-1]['date']}")
            self.option_received.set()
        elif reqId == 1:
            print(f"\n✓ Stock TRADES complete: {len(self.stock_trades)} bars")
            if self.stock_trades:
                print(f"  Range: {self.stock_trades[0]['date']} to {self.stock_trades[-1]['date']}")
            self.stock_received.set()

def test_option_vs_stock_trades():
    """Test if option TRADES and stock TRADES have same bar counts"""
    print("=" * 80)
    print("TESTING: Option TRADES vs Stock TRADES")
    print("=" * 80)
    print("\nHypothesis: The 16:00 bars are in BOTH option and stock TRADES")
    print("            (useRTH=1 includes closing auction)")
    print("=" * 80)

    client = TestTradesClient()

    try:
        if not client.connect_to_ibkr("127.0.0.1", 7496):
            print("❌ Failed to connect to IBKR")
            return False

        print("\n✓ Connected to IBKR")

        # Create option contract
        option = Contract()
        option.symbol = "SPY"
        option.secType = "OPT"
        option.exchange = "SMART"
        option.currency = "USD"
        option.lastTradeDateOrContractMonth = "20260220"
        option.strike = 680.0
        option.right = "C"
        option.multiplier = "100"

        # Create stock contract
        stock = Contract()
        stock.symbol = "SPY"
        stock.secType = "STK"
        stock.exchange = "SMART"
        stock.currency = "USD"

        period = "1 M"
        bar_size = "30 mins"

        print(f"\nTest Parameters:")
        print(f"  Period: {period}")
        print(f"  Bar Size: {bar_size}")
        print(f"  Trading Hours: Regular only (useRTH=1)")

        # Request 1: Option TRADES
        print(f"\n" + "=" * 80)
        print("REQUEST 1: Option TRADES (SPY 680C exp=20260220)")
        print("=" * 80)

        client.reqHistoricalData(
            0,  # reqId
            option,
            '',
            period,
            bar_size,
            "TRADES",
            1,  # useRTH
            1,
            False,
            []
        )

        if not client.option_received.wait(timeout=30):
            print("❌ Timeout waiting for option TRADES")
            return False

        time.sleep(2)

        # Request 2: Stock TRADES
        print(f"\n" + "=" * 80)
        print("REQUEST 2: Stock TRADES (SPY stock)")
        print("=" * 80)

        client.reqHistoricalData(
            1,  # reqId
            stock,
            '',
            period,
            bar_size,
            "TRADES",
            1,  # useRTH
            1,
            False,
            []
        )

        if not client.stock_received.wait(timeout=30):
            print("❌ Timeout waiting for stock TRADES")
            return False

        # Compare results
        print(f"\n" + "=" * 80)
        print("DETAILED COMPARISON")
        print("=" * 80)

        option_count = len(client.option_trades)
        stock_count = len(client.stock_trades)

        print(f"\nBar counts:")
        print(f"  Option TRADES: {option_count} bars")
        print(f"  Stock TRADES:  {stock_count} bars")
        print(f"  Difference: {abs(option_count - stock_count)} bars")

        # First 5 bars
        print("\n--- FIRST 5 BARS ---")
        print("\nOption TRADES:")
        for i, bar in enumerate(client.option_trades[:5]):
            print(f"  {i+1}. {bar['date']} - Close: ${bar['close']:.2f}")

        print("\nStock TRADES:")
        for i, bar in enumerate(client.stock_trades[:5]):
            print(f"  {i+1}. {bar['date']} - Close: ${bar['close']:.2f}")

        # Last 5 bars
        print("\n--- LAST 5 BARS ---")
        print("\nOption TRADES:")
        for i, bar in enumerate(client.option_trades[-5:]):
            print(f"  {option_count-4+i}. {bar['date']} - Close: ${bar['close']:.2f}")

        print("\nStock TRADES:")
        for i, bar in enumerate(client.stock_trades[-5:]):
            print(f"  {stock_count-4+i}. {bar['date']} - Close: ${bar['close']:.2f}")

        # NEW: Show last bar of each day for Option with FULL details
        print("\n" + "=" * 80)
        print("OPTION TRADES - LAST BAR OF EACH DAY (Full Details)")
        print("=" * 80)

        # Group option bars by date (YYYYMMDD)
        days = {}
        for bar in client.option_trades:
            day = bar['date'].split()[0]  # Extract YYYYMMDD
            if day not in days:
                days[day] = []
            days[day].append(bar)

        # Show last bar of each day (last 10 days only to avoid too much output)
        sorted_days = sorted(days.keys())[-10:]

        for day in sorted_days:
            day_bars = days[day]
            last_bar = day_bars[-1]

            print(f"\n{day} - Last bar of the day:")
            print(f"  Time: {last_bar['date']}")
            print(f"  Open:   ${last_bar['open']:.2f}")
            print(f"  High:   ${last_bar['high']:.2f}")
            print(f"  Low:    ${last_bar['low']:.2f}")
            print(f"  Close:  ${last_bar['close']:.2f}")
            print(f"  Volume: {last_bar['volume']}")

            # Show time of last bar
            time_part = last_bar['date'].split()[1] if len(last_bar['date'].split()) > 1 else "N/A"
            print(f"  --> Bar time: {time_part}")

        print("\n" + "=" * 80)

        # Check for 16:00 bars
        option_dates = set(bar['date'] for bar in client.option_trades)
        stock_dates = set(bar['date'] for bar in client.stock_trades)

        only_in_option = option_dates - stock_dates
        only_in_stock = stock_dates - option_dates

        if only_in_option:
            print(f"\n--- DATES ONLY IN OPTION ({len(only_in_option)} bars) ---")
            for date in sorted(only_in_option)[:10]:
                print(f"  {date}")
            if len(only_in_option) > 10:
                print(f"  ... and {len(only_in_option)-10} more")

        if only_in_stock:
            print(f"\n--- DATES ONLY IN STOCK ({len(only_in_stock)} bars) ---")
            for date in sorted(only_in_stock)[:10]:
                print(f"  {date}")
            if len(only_in_stock) > 10:
                print(f"  ... and {len(only_in_stock)-10} more")

        # Conclusion
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)

        if option_count == stock_count:
            print("✅ Option and Stock TRADES have SAME bar count")
            print("   The 16:00 bars are in BOTH (part of useRTH=1)")
            print("   This means the issue is: TRADES vs IV data type mismatch")
        else:
            print("⚠️  Option and Stock TRADES have DIFFERENT bar counts")
            print("   This is unexpected - need further investigation")

        print("=" * 80)

        return True

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
    test_option_vs_stock_trades()
