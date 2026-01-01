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
        self.data = []
        self.data_received = threading.Event()
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
        logger.info(f"Received option bar: reqId={reqId}, date={bar.date}, close={bar.close}")
        self.data.append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Called when historical data request is complete"""
        logger.info(f"Historical option data request {reqId} completed. Received {len(self.data)} bars")
        self.data_received.set()

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
        Fetch historical option data from IBKR

        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            strike: Strike price (e.g., 450.0)
            right: 'C' for call, 'P' for put
            expiration: Contract expiration in YYYYMMDD format
            period: Period of data (e.g., '1 M', '5 D')
            bar_size: Bar size (e.g., '30 mins', '1 day')

        Returns:
            List of bar data dictionaries
        """
        try:
            logger.info(f"Fetching option data: {symbol} {strike}{right} exp={expiration}")

            # Create option contract (EXACTLY as loading_option-his.py lines 115-123)
            contract = Contract()
            contract.symbol = symbol
            contract.secType = 'OPT'
            contract.exchange = 'SMART'
            contract.currency = 'USD'
            contract.lastTradeDateOrContractMonth = expiration  # YYYYMMDD format
            contract.strike = strike
            contract.right = right  # 'C' or 'P'
            contract.multiplier = '100'  # Standard option multiplier
            contract.includeExpired = 1  # Include expired contracts (needed for historical data)

            # Initialize data storage
            self.data = []

            # Request historical option data (EXACTLY as loading_option-his.py line 139-140)
            # IMPORTANT: Use "TRADES" for options, not "MIDPOINT"
            req_id = 0
            self.reqHistoricalData(
                req_id,
                contract,
                '',  # End date (empty = latest available)
                period,
                bar_size,
                "TRADES",  # Data type for options
                1,  # Regular trading hours only
                1,  # Date format (1 = yyyyMMdd HH:mm:ss)
                False,  # Keep up to date = False (like loading_option-his.py)
                []  # Chart options
            )

            # Wait for data
            time.sleep(10)  # Allow time for data return

            logger.info(f"Raw option data received: {len(self.data)} bars")

            if len(self.data) < 1:
                raise Exception(f'Failed loading option data for {symbol} {strike}{right}. Try again.')

            logger.info(f'Finished loading option data for {symbol} {strike}{right}')
            return self.data.copy()

        except Exception as e:
            logger.error(f"Error fetching option data: {str(e)}")
            raise

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
                            (symbol, strike, "right", expiration, date, "open", high, low, "close", volume, bar_interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, strike, "right", expiration, date, bar_interval)
                        DO UPDATE SET
                            "open" = EXCLUDED."open",
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            "close" = EXCLUDED."close",
                            volume = EXCLUDED.volume,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        symbol, strike, right, exp_date, date_obj,
                        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume'],
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

            query = """
                SELECT date, "open" as open, high, low, "close" as close, volume
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
                    'volume': 'Volume'
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
        try:
            # First, try database
            df = self.get_option_data_from_db(
                symbol, strike, right, expiration, start_date, end_date, bar_interval
            )

            # Check if we have complete data coverage
            if not df.empty:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)

                logger.info(f"DB coverage - Range: {df.index.min()} to {df.index.max()}")
                logger.info(f"Requested range: {start_dt} to {end_dt}")

                # Allow 5-day gap for weekends/holidays
                start_gap_days = (df.index.min() - start_dt).days
                end_gap_days = (end_dt - df.index.max()).days

                if start_gap_days >= -5 and start_gap_days <= 5 and end_gap_days >= -5 and end_gap_days <= 5:
                    logger.info(f"Complete option data found in DB")
                    return df[start_dt:end_dt]

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
