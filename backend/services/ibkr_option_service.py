"""Interactive Brokers API option data service for TradingHub"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper
from psycopg2.extras import DictCursor

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}

# IBKR configuration
IBKR_CONFIG = {
    "host": os.environ.get("IBKR_HOST", "127.0.0.1"),
    "port": int(os.environ.get("IBKR_PORT", "7496")),
    "client_id": int(os.environ.get("IBKR_CLIENT_ID", "124")),  # Different from stock client
}


class IBKROptionClient(EWrapper, EClient):
    """IBKR API client for fetching historical option data"""

    def __init__(self, client_id: int = 124):
        EClient.__init__(self, self)
        self.client_id = client_id
        self.data = []  # For TRADES data
        self.iv_data = []  # For IMPLIED_VOLATILITY data
        self.data_received = threading.Event()
        self.iv_data_received = threading.Event()
        self.connection_successful = threading.Event()
        self.error_occurred = False
        self.error_message = ""

    def nextValidId(self, orderId: int):
        """Called when connection is established"""
        logger.info(f"IBKR connection established. Next valid order ID: {orderId}")
        self.connection_successful.set()

    def error(self, reqId: int, errorCode: int, errorString: str):
        """Handle API errors"""
        logger.error(f"IBKR Error - ReqId: {reqId}, Code: {errorCode}, Message: {errorString}")
        if errorCode in [502, 504]:  # Connection errors
            self.error_occurred = True
            self.error_message = f"Connection error: {errorString}"
        self.data_received.set()  # Unblock waiting threads

    def historicalData(self, reqId: int, bar):
        """Receive historical data bars"""
        if reqId == 0:  # TRADES data (price)
            logger.info(f"Received price bar: reqId={reqId}, date={bar.date}, close={bar.close}")
            self.data.append({
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        elif reqId == 1:  # OPTION_IMPLIED_VOLATILITY data
            logger.info(f"Received IV bar: reqId={reqId}, date={bar.date}, close={bar.close}")
            self.iv_data.append({
                'date': bar.date,
                'implied_volatility': bar.close  # IV is returned in the close field
            })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Called when historical data request is complete"""
        if reqId == 0:
            logger.info(f"TRADES data request {reqId} completed. Received {len(self.data)} bars")
            self.data_received.set()
        elif reqId == 1:
            logger.info(f"IV data request {reqId} completed. Received {len(self.iv_data)} bars")
            self.iv_data_received.set()

    def connect_to_ibkr(self, host: str = "127.0.0.1", port: int = 7496) -> bool:
        """Connect to IBKR TWS/Gateway"""
        try:
            self.connect(host, port, self.client_id)
            logger.info("Option client connection successful")
        except Exception as e:
            logger.error(f"Option client connection failed: {e}")
            return False

        # Start the socket in a thread
        def run_loop():
            self.run()

        api_thread = threading.Thread(target=run_loop, daemon=True)
        api_thread.start()

        time.sleep(1)  # Allow time for connection
        return True

    def fetch_option_data(
        self,
        symbol: str,
        strike: float,
        right: str,
        expiration: str,
        period: str = "1 M",
        bar_size: str = "30 mins"
    ) -> List[Dict]:
        """
        Fetch historical option data from IBKR (TRADES + underlying IV)

        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            strike: Strike price (e.g., 450.0)
            right: 'C' for call, 'P' for put
            expiration: Contract expiration in YYYYMMDD format
            period: Period of data (e.g., '1 M', '5 D')
            bar_size: Bar size (e.g., '30 mins', '1 day')

        Returns:
            List of bar data dictionaries (with IV included)
        """
        try:
            logger.info(f"Fetching option price + IV data: {symbol} {strike}{right} exp={expiration}")

            # Create option contract for price data
            option_contract = Contract()
            option_contract.symbol = symbol
            option_contract.secType = 'OPT'
            option_contract.exchange = 'SMART'
            option_contract.currency = 'USD'
            option_contract.lastTradeDateOrContractMonth = expiration
            option_contract.strike = strike
            option_contract.right = right
            option_contract.multiplier = '100'
            option_contract.includeExpired = 1

            # Create STOCK contract for IV data (IV of underlying)
            stock_contract = Contract()
            stock_contract.symbol = symbol
            stock_contract.secType = 'STK'  # STOCK, not OPT!
            stock_contract.exchange = 'SMART'
            stock_contract.currency = 'USD'

            # Initialize data storage
            self.data = []
            self.iv_data = []
            self.data_received.clear()
            self.iv_data_received.clear()

            # Request 1: Historical TRADES data (option prices)
            logger.info("Requesting option TRADES data...")
            self.reqHistoricalData(
                0,  # reqId = 0 for TRADES
                option_contract,
                '',  # End date (empty = latest available)
                period,
                bar_size,
                "TRADES",  # Data type for option prices
                1,  # Regular trading hours only
                1,  # Date format (1 = yyyyMMdd HH:mm:ss)
                False,  # Keep up to date = False
                []  # Chart options
            )

            # Wait for TRADES data
            self.data_received.wait(timeout=15)

            logger.info(f"Option TRADES data received: {len(self.data)} bars")
            if len(self.data) > 0:
                logger.info(f"  TRADES date range: {self.data[0]['date']} to {self.data[-1]['date']}")

            # Request 2: Historical IV data from UNDERLYING STOCK
            logger.info(f"Requesting IV data from underlying {symbol} stock...")
            self.reqHistoricalData(
                1,  # reqId = 1 for IV
                stock_contract,  # STOCK contract, not option!
                '',  # End date (empty = latest available)
                period,
                bar_size,
                "OPTION_IMPLIED_VOLATILITY",  # IV of underlying stock
                1,  # Regular trading hours only
                1,  # Date format (1 = yyyyMMdd HH:mm:ss)
                False,  # Keep up to date = False
                []  # Chart options
            )

            # Wait for IV data
            self.iv_data_received.wait(timeout=15)

            logger.info(f"Underlying IV data received: {len(self.iv_data)} bars")
            if len(self.iv_data) > 0:
                logger.info(f"  IV date range: {self.iv_data[0]['date']} to {self.iv_data[-1]['date']}")

            # CRITICAL FIX: Filter option TRADES to only include bars with matching IV data
            # This removes ALL settlement bars (16:00 regular days, 13:00 half-days, etc.)
            # Settlement bars are NOT real trading data - they're price snapshots
            # Characteristics: Open=High=Low=Close, Volume=0 or near-zero
            # See: OPTION_DATA_CLOSURE_SETTLEMENT_ISSUE.md for full explanation
            iv_dates = set(bar['date'] for bar in self.iv_data)
            original_count = len(self.data)
            self.data = [bar for bar in self.data if bar['date'] in iv_dates]
            filtered_count = original_count - len(self.data)

            if filtered_count > 0:
                logger.info(f"  Filtered out {filtered_count} settlement bars (not in IV data)")

            if len(self.data) > 0:
                logger.info(f"  TRADES after settlement filter: {len(self.data)} bars ({self.data[0]['date']} to {self.data[-1]['date']})")

            # Log the mismatch with detailed comparison
            if len(self.data) != len(self.iv_data):
                logger.warning(f"  ⚠️  BAR COUNT MISMATCH: TRADES={len(self.data)} bars, IV={len(self.iv_data)} bars (diff={len(self.data)-len(self.iv_data)})")
                logger.warning(f"  This will result in some bars having NULL IV values")

                # Print detailed comparison
                print("\n" + "="*80)
                print("DETAILED BAR COMPARISON - TRADES vs IV")
                print("="*80)

                # First 5 bars
                print("\n--- FIRST 5 BARS ---")
                print("\nTRADES (Option Contract):")
                for i, bar in enumerate(self.data[:5]):
                    print(f"  {i+1}. {bar['date']} - Close: ${bar['close']:.2f}")

                print("\nIV (Stock Contract):")
                for i, bar in enumerate(self.iv_data[:5]):
                    print(f"  {i+1}. {bar['date']} - IV: {bar['implied_volatility']:.4f}")

                # Last 5 bars
                print("\n--- LAST 5 BARS ---")
                print("\nTRADES (Option Contract):")
                for i, bar in enumerate(self.data[-5:]):
                    print(f"  {len(self.data)-4+i}. {bar['date']} - Close: ${bar['close']:.2f}")

                print("\nIV (Stock Contract):")
                for i, bar in enumerate(self.iv_data[-5:]):
                    print(f"  {len(self.iv_data)-4+i}. {bar['date']} - IV: {bar['implied_volatility']:.4f}")

                # Date range comparison
                print("\n--- DATE RANGE COMPARISON ---")
                print(f"TRADES: {self.data[0]['date']} to {self.data[-1]['date']} ({len(self.data)} bars)")
                print(f"IV:     {self.iv_data[0]['date']} to {self.iv_data[-1]['date']} ({len(self.iv_data)} bars)")

                # Check for gaps
                trades_dates = set(bar['date'] for bar in self.data)
                iv_dates = set(bar['date'] for bar in self.iv_data)

                only_in_trades = trades_dates - iv_dates
                only_in_iv = iv_dates - trades_dates

                if only_in_trades:
                    print(f"\n--- DATES ONLY IN TRADES ({len(only_in_trades)} bars) ---")
                    for date in sorted(only_in_trades)[:10]:  # Show first 10
                        print(f"  {date}")
                    if len(only_in_trades) > 10:
                        print(f"  ... and {len(only_in_trades)-10} more")

                if only_in_iv:
                    print(f"\n--- DATES ONLY IN IV ({len(only_in_iv)} bars) ---")
                    for date in sorted(only_in_iv)[:10]:  # Show first 10
                        print(f"  {date}")
                    if len(only_in_iv) > 10:
                        print(f"  ... and {len(only_in_iv)-10} more")

                print("="*80 + "\n")

            if len(self.data) < 1:
                raise Exception(f'Failed loading option price data for {symbol} {strike}{right}. Try again.')

            # Merge IV data with price data
            merged_data = self._merge_price_and_iv_data(self.data, self.iv_data)

            logger.info(f'Finished loading option data with IV for {symbol} {strike}{right}')
            return merged_data

        except Exception as e:
            logger.error(f"Error fetching option data: {str(e)}")
            raise

    def _merge_price_and_iv_data(self, price_data: List[Dict], iv_data: List[Dict]) -> List[Dict]:
        """
        Merge price and IV data on date (should be 1:1 match after 16:00 filter)

        Args:
            price_data: List of price bars (16:00 settlement bars already filtered out)
            iv_data: List of IV bars

        Returns:
            List of merged bars with IV included
        """
        # Create dict for fast IV lookup by date
        iv_dict = {bar['date']: bar['implied_volatility'] for bar in iv_data}

        # Merge IV into price data (should be exact 1:1 match)
        merged = []

        for price_bar in price_data:
            bar_date = price_bar['date']
            merged_bar = price_bar.copy()

            # Get IV for this bar
            merged_bar['implied_volatility'] = iv_dict.get(bar_date, None)

            merged.append(merged_bar)

        # Log statistics
        total_bars = len(merged)
        bars_with_iv = sum(1 for bar in merged if bar['implied_volatility'] is not None)
        bars_without_iv = total_bars - bars_with_iv

        logger.info(f"IV merge: {total_bars} total bars, {bars_with_iv} with IV ({bars_with_iv/total_bars*100:.1f}%)")

        if bars_without_iv > 0:
            logger.warning(f"  ⚠️  {bars_without_iv} bars missing IV - this should not happen after 16:00 filter!")
            logger.warning(f"  Check if 16:00 settlement filter is working correctly")

        return merged

    def disconnect_from_ibkr(self):
        """Disconnect from IBKR"""
        try:
            self.disconnect()
            logger.info("Disconnected option client from IBKR")
        except Exception as e:
            logger.error(f"Error disconnecting option client: {str(e)}")


class IBKROptionService:
    """Service for managing IBKR option data fetching and database storage"""

    def __init__(self):
        self.client = None

    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

    def save_option_data_to_db(
        self,
        symbol: str,
        strike: float,
        right: str,
        expiration: str,
        data: List[Dict],
        bar_interval: str = '30 mins'
    ):
        """
        Save option data to options_data table

        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' or 'P'
            expiration: Expiration date (YYYYMMDD string or date object)
            data: List of bar data dictionaries
            bar_interval: Bar interval (e.g., '30 mins', '1 day')
        """
        if not data:
            return

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Convert expiration to date object if string
                if isinstance(expiration, str):
                    exp_date = datetime.strptime(expiration, '%Y%m%d').date()
                else:
                    exp_date = expiration

                for bar in data:
                    # Parse date from IBKR format (handle double space for intraday)
                    date_str = bar['date'].strip()

                    try:
                        if ' ' in date_str:
                            # Intraday: "20240101  09:30:00" (double space!)
                            date_str_normalized = ' '.join(date_str.split())
                            date_obj = datetime.strptime(date_str_normalized, '%Y%m%d %H:%M:%S')
                        else:
                            # Daily: "20240101"
                            date_obj = datetime.strptime(date_str, '%Y%m%d')
                    except ValueError as e:
                        logger.error(f"Could not parse date: '{date_str}' - Error: {e}")
                        continue

                    # Insert with ON CONFLICT to handle duplicates
                    cursor.execute("""
                        INSERT INTO options_data
                            (symbol, strike, "right", expiration, date, "open", high, low, "close", volume,
                             implied_volatility, bar_interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, strike, "right", expiration, date, bar_interval)
                        DO UPDATE SET
                            "open" = EXCLUDED."open",
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            "close" = EXCLUDED."close",
                            volume = EXCLUDED.volume,
                            implied_volatility = EXCLUDED.implied_volatility,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        symbol, strike, right, exp_date, date_obj,
                        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume'],
                        bar.get('implied_volatility'),  # NEW: IV column
                        bar_interval
                    ))

                conn.commit()
                logger.info(f"Saved {len(data)} option bars to DB: {symbol} {strike}{right} exp={exp_date} interval={bar_interval}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving option data to DB: {str(e)}")
            raise
        finally:
            conn.close()

    def get_option_data_from_db(
        self,
        symbol: str,
        strike: float,
        right: str,
        expiration: str,
        start_date: str,
        end_date: str,
        bar_interval: str = '30 mins'
    ) -> pd.DataFrame:
        """
        Get option data from database

        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' or 'P'
            expiration: Expiration date (YYYYMMDD string)
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            bar_interval: Bar interval

        Returns:
            pd.DataFrame with date index and OHLCV columns
        """
        conn = self.get_db_connection()
        try:
            # Convert expiration to date
            if isinstance(expiration, str):
                exp_date = datetime.strptime(expiration, '%Y%m%d').date()
            else:
                exp_date = expiration

            # Debug logging
            log_file = os.path.join(os.path.dirname(__file__), "cache_debug.log")
            with open(log_file, "a") as f:
                f.write(f"  Querying DB with:\n")
                f.write(f"    symbol={symbol}, strike={strike}, right={right}\n")
                f.write(f"    expiration={exp_date} (type={type(exp_date).__name__})\n")
                f.write(f"    date range={start_date} to {end_date}\n")
                f.write(f"    bar_interval={bar_interval}\n")

            query = """
                SELECT date, "open" as open, high, low, "close" as close, volume, implied_volatility
                FROM options_data
                WHERE symbol = %s
                    AND strike = %s
                    AND "right" = %s
                    AND expiration = %s
                    AND date >= %s
                    AND date <= %s
                    AND bar_interval = %s
                ORDER BY date
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, strike, right, exp_date, start_date, end_date, bar_interval)
            )

            with open(log_file, "a") as f:
                f.write(f"  Query returned {len(df)} rows\n")

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.index.name = 'DateTime'  # Match expected column name

                # Capitalize column names to match expected format
                df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume',
                    'implied_volatility': 'ImpliedVolatility'
                }, inplace=True)

            logger.info(f"Retrieved {len(df)} option bars from DB: {symbol} {strike}{right} exp={exp_date}")
            return df

        except Exception as e:
            logger.error(f"Error retrieving option data from DB: {str(e)}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_option_data(
        self,
        symbol: str,
        strike: float,
        right: str,
        expiration: str,
        start_date: str,
        end_date: str,
        bar_interval: str = '30 mins'
    ) -> pd.DataFrame:
        """
        Get option data with database-first approach, IBKR fallback

        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' or 'P'
            expiration: Expiration date (YYYYMMDD string)
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            bar_interval: Bar interval

        Returns:
            pd.DataFrame with DateTime index and OHLCV columns
        """
        # Log to file for debugging
        import datetime
        log_file = os.path.join(os.path.dirname(__file__), "cache_debug.log")
        with open(log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{datetime.datetime.now()}] CACHE CHECK\n")
            f.write(f"Request: {symbol} {strike}{right} exp={expiration}\n")
            f.write(f"Range: {start_date} to {end_date}, interval={bar_interval}\n")

        print("\n" + "="*80)
        print(f"CHECKING DATABASE CACHE: {symbol} {strike}{right} exp={expiration}")
        print(f"Requested: {start_date} to {end_date}, interval={bar_interval}")
        print("="*80)

        try:
            # First, try database
            df = self.get_option_data_from_db(
                symbol, strike, right, expiration, start_date, end_date, bar_interval
            )

            db_bars = len(df) if not df.empty else 0
            print(f"Database query returned: {db_bars} bars")

            with open(log_file, "a") as f:
                f.write(f"DB query returned: {db_bars} bars\n")

            # Check if we have complete data coverage
            if not df.empty:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)

                logger.info(f"✓ DB has {len(df)} bars in database")
                logger.info(f"  DB coverage - Range: {df.index.min()} to {df.index.max()}")
                logger.info(f"  Requested range: {start_dt} to {end_dt}")

                # Check data coverage (allow DB to have extra data before/after)
                start_gap_days = (df.index.min() - start_dt).days  # Negative if DB starts earlier (GOOD)
                end_gap_days = (end_dt - df.index.max()).days      # Positive if DB ends earlier (need tolerance)

                logger.info(f"  Gap check - Start gap: {start_gap_days} days, End gap: {end_gap_days} days")

                # DB starting BEFORE requested is always good (negative gap)
                # DB starting up to 5 days AFTER requested is acceptable (positive gap <= 5)
                start_ok = start_gap_days <= 5

                # DB ending AFTER requested is always good (negative gap)
                # DB ending up to 5 days BEFORE requested is acceptable (positive gap <= 5)
                end_ok = end_gap_days <= 5

                with open(log_file, "a") as f:
                    f.write(f"Coverage check: start_gap={start_gap_days}d, end_gap={end_gap_days}d\n")
                    f.write(f"start_ok={start_ok}, end_ok={end_ok}\n")

                if start_ok and end_ok:
                    logger.info(f"✓ Complete option data found in DB - USING CACHED DATA (no IBKR fetch)")
                    print(f"✓ Using cached data from database ({len(df)} bars) - No IBKR connection needed")

                    with open(log_file, "a") as f:
                        f.write(f"DECISION: USING CACHE (returning {len(df[start_dt:end_dt])} bars)\n")

                    return df[start_dt:end_dt]
                else:
                    logger.info(f"⚠️  DB data incomplete - gaps outside tolerance - WILL FETCH FROM IBKR")
                    print(f"⚠️  Database data incomplete (start_ok={start_ok}, end_ok={end_ok}, gaps: start={start_gap_days}d, end={end_gap_days}d)")

                    with open(log_file, "a") as f:
                        f.write(f"DECISION: FETCH FROM IBKR (gaps outside tolerance)\n")
            else:
                logger.info(f"⚠️  No data in DB - WILL FETCH FROM IBKR")
                print(f"⚠️  No cached data found - fetching from IBKR...")

            # If data missing, fetch from IBKR
            logger.info(f"Fetching option data from IBKR: {symbol} {strike}{right} exp={expiration}")

            # Calculate period from date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            days_diff = (end_dt - start_dt).days

            # Calculate appropriate period for IBKR
            if days_diff <= 5:
                period = f"{days_diff} D"
            elif days_diff <= 30:
                period = "1 M"  # Per IBKR docs for 30-min bars
            else:
                period = f"{days_diff // 30} M"

            # Fetch from IBKR
            self.client = IBKROptionClient(IBKR_CONFIG["client_id"])
            if not self.client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
                raise Exception("Failed to connect to IBKR")

            data = self.client.fetch_option_data(
                symbol=symbol,
                strike=strike,
                right=right,
                expiration=expiration,
                period=period,
                bar_size=bar_interval
            )

            if data:
                # Save to database
                self.save_option_data_to_db(symbol, strike, right, expiration, data, bar_interval)

                # Query database again
                df = self.get_option_data_from_db(
                    symbol, strike, right, expiration, start_date, end_date, bar_interval
                )
                return df
            else:
                raise Exception(f"No option data received from IBKR")

        except Exception as e:
            logger.error(f"Error getting option data: {str(e)}")
            raise
        finally:
            if self.client:
                self.client.disconnect_from_ibkr()


# Global service instance
ibkr_option_service = IBKROptionService()
