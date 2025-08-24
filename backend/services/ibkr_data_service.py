"""Interactive Brokers API data service for TradingHub"""

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
    "client_id": int(os.environ.get("IBKR_CLIENT_ID", "123")),
}


class IBKRDataClient(EWrapper, EClient):
    """IBKR API client for fetching historical market data"""
    
    def __init__(self, client_id: int = 123):
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
        logger.info(f"Received bar: reqId={reqId}, date={bar.date}, close={bar.close}")
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
        logger.info(f"Historical data request {reqId} completed. Received {len(self.data)} bars")
        self.data_received.set()
    
    def connect_to_ibkr(self, host: str = "127.0.0.1", port: int = 7496) -> bool:
        """Connect to IBKR TWS/Gateway - exact approach from loading_data.py"""
        try:
            self.connect(host, port, self.client_id)
            logger.info("Connection Successful")
        except Exception as e:
            logger.error(f"Connection Failed: {e}")
            return False
        
        # Start the socket in a thread (exactly like loading_data.py)
        def run_loop():
            self.run()
            
        api_thread = threading.Thread(target=run_loop, daemon=True)
        api_thread.start()
        
        time.sleep(1)  # Sleep interval to allow time for connection to server
        return True
    
    def fetch_historical_data(self, symbol: str, period: str = "10 Y", bar_size: str = "1 day") -> List[Dict]:
        """Fetch historical data for a symbol - exact approach from loading_data.py"""
        try:
            logger.info(f'getting {symbol}')
            
            # Create contract object (exactly like loading_data.py)
            contract = Contract()    
            contract.symbol = str(symbol)
            contract.currency = 'USD'
            
            # Configure contract based on symbol type
            if symbol in ["VIX"]:
                # this is for VIX
                contract.secType = 'IND'
                contract.exchange = 'CBOE'
                data_type = "TRADES"
            else:
                # For normal tickers like SPY - use TRADES since MIDPOINT needs market data subscription
                contract.secType = 'STK'
                contract.exchange = 'SMART'
                data_type = "TRADES"
            
            # Initialize variable to store candle (exactly like loading_data.py)
            self.data = []
            
            # Request historical candles
            req_id = 0  # Use 0 like in loading_data.py (stock_list.index(i))
            self.reqHistoricalData(req_id, contract, '', period, bar_size, data_type, 1, 1, True, [])
            
            # sleep to allow enough time for data to be returned (extend for larger datasets)
            time.sleep(10)
            
            logger.info(f"Raw data received: {self.data}")
            
            if len(self.data) < 1:
                raise Exception(f'faliled loading data for {symbol}. try it again')  # Exact message
            
            logger.info(f'finish the loading data for {symbol}')
            return self.data.copy()
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise
    
    def disconnect_from_ibkr(self):
        """Disconnect from IBKR"""
        try:
            self.disconnect()
            logger.info("Disconnected from IBKR")
        except Exception as e:
            logger.error(f"Error disconnecting from IBKR: {str(e)}")


class IBKRDataService:
    """Service for managing IBKR data fetching and database storage"""
    
    def __init__(self):
        self.client = None
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def create_market_data_table(self):
        """Create market_data table if it doesn't exist"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL,
                        date DATE NOT NULL,
                        open DECIMAL(10, 4) NOT NULL,
                        high DECIMAL(10, 4) NOT NULL,
                        low DECIMAL(10, 4) NOT NULL,
                        close DECIMAL(10, 4) NOT NULL,
                        volume BIGINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, date)
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date 
                    ON market_data (symbol, date)
                """)
                
                conn.commit()
                logger.info("Market data table created successfully")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating market data table: {str(e)}")
            raise
        finally:
            conn.close()
    
    def get_data_from_db(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get market data from database"""
        conn = self.get_db_connection()
        try:
            query = """
                SELECT symbol, date, open, high, low, close, volume
                FROM market_data 
                WHERE symbol = %s AND date >= %s AND date <= %s
                ORDER BY date
            """
            
            df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            logger.info(f"Retrieved {len(df)} records from DB for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving data from DB: {str(e)}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def save_data_to_db(self, symbol: str, data: List[Dict]):
        """Save market data to database"""
        if not data:
            return
        
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                for bar in data:
                    # Convert date string to date object
                    date_obj = datetime.strptime(bar['date'], '%Y%m%d').date()
                    
                    cursor.execute("""
                        INSERT INTO market_data (symbol, date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, date) 
                        DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        symbol, date_obj, bar['open'], bar['high'], 
                        bar['low'], bar['close'], bar['volume']
                    ))
                
                conn.commit()
                logger.info(f"Saved {len(data)} records to DB for {symbol}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving data to DB: {str(e)}")
            raise
        finally:
            conn.close()
    
    def fetch_and_store_data(self, symbol: str, period: str = "10 Y") -> bool:
        """Fetch data from IBKR and store in database"""
        try:
            # Connect to IBKR
            self.client = IBKRDataClient(IBKR_CONFIG["client_id"])
            if not self.client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
                raise Exception("Failed to connect to IBKR")
            
            # Fetch data
            logger.info(f"Fetching {period} of data for {symbol}")
            data = self.client.fetch_historical_data(symbol, period)
            
            if data:
                # Save to database
                self.save_data_to_db(symbol, data)
                logger.info(f"Successfully fetched and stored data for {symbol}")
                return True
            else:
                logger.warning(f"No data received for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return False
        finally:
            if self.client:
                self.client.disconnect_from_ibkr()
    
    def get_market_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get market data with DB-first approach, fallback to IBKR"""
        try:
            # First try database
            df = self.get_data_from_db(symbol, start_date, end_date)
            
            # Check if we have complete data coverage
            if not df.empty:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                
                # Check if we have data for the full range
                if df.index.min() <= start_dt and df.index.max() >= end_dt:
                    logger.info(f"Complete data found in DB for {symbol}")
                    return df[start_dt:end_dt]
            
            # If data is missing, fetch from IBKR
            logger.info(f"Incomplete data in DB, fetching from IBKR for {symbol}")
            if self.fetch_and_store_data(symbol):
                # Try database again
                return self.get_data_from_db(symbol, start_date, end_date)
            else:
                raise Exception(f"Failed to fetch data from IBKR for {symbol}")
                
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            raise
    
    def refresh_data(self, symbol: str) -> Dict[str, Any]:
        """Manually refresh data for a symbol"""
        try:
            # Use shorter period for API calls to avoid timeouts
            success = self.fetch_and_store_data(symbol, "1 Y")  # 1 year instead of 10 years
            return {
                "success": success,
                "message": f"Data refresh {'successful' if success else 'failed'} for {symbol}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error refreshing data: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# Global service instance
ibkr_service = IBKRDataService()