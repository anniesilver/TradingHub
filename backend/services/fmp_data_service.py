"""Financial Modeling Prep (FMP) API integration for market cap data"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class FMPDataService:
    """Financial Modeling Prep API integration for S&P 500 market cap data"""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str = None):
        """Initialize FMP service

        Args:
            api_key: FMP API key. If not provided, reads from FMP_API_KEY env var
        """
        self.api_key = api_key or os.environ.get('FMP_API_KEY')
        if not self.api_key:
            logger.warning("FMP API key not provided. Set FMP_API_KEY environment variable.")

        self.session = requests.Session()
        self.rate_limit_delay = 0.25  # Delay between requests to avoid rate limiting

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """Make API request with error handling

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            raise ValueError("FMP API key is required. Set FMP_API_KEY environment variable.")

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key

        try:
            time.sleep(self.rate_limit_delay)  # Rate limiting
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request failed: {e}")
            return None

    def get_sp500_constituents(self) -> pd.DataFrame:
        """Get current S&P 500 constituents

        Returns:
            DataFrame with columns: symbol, name, sector, subSector, etc.
        """
        data = self._make_request("sp500_constituent")

        if not data:
            logger.warning("No S&P 500 constituent data returned")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        logger.info(f"Retrieved {len(df)} S&P 500 constituents")
        return df

    def get_historical_sp500_changes(self) -> pd.DataFrame:
        """Get historical S&P 500 additions/removals

        Returns:
            DataFrame with historical constituent changes
        """
        data = self._make_request("historical/sp500_constituent")

        if not data:
            logger.warning("No historical S&P 500 change data returned")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if 'dateAdded' in df.columns:
            df['dateAdded'] = pd.to_datetime(df['dateAdded'])
        logger.info(f"Retrieved {len(df)} historical S&P 500 changes")
        return df

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """Get company profile including current market cap

        Args:
            symbol: Stock symbol

        Returns:
            Company profile dictionary or None
        """
        data = self._make_request(f"profile/{symbol}")

        if data and len(data) > 0:
            return data[0]
        return None

    def get_historical_market_cap(self, symbol: str, start_date: str = None,
                                   end_date: str = None, limit: int = 5000) -> pd.DataFrame:
        """Get historical daily market cap for a symbol

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum records to return

        Returns:
            DataFrame with columns: date, symbol, marketCap
        """
        params = {'limit': limit}

        data = self._make_request(f"historical-market-capitalization/{symbol}", params)

        if not data:
            logger.warning(f"No historical market cap data for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data)

        if df.empty:
            return df

        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        df['symbol'] = symbol

        # Rename marketCap to market_cap for consistency
        if 'marketCap' in df.columns:
            df = df.rename(columns={'marketCap': 'market_cap'})

        # Filter by date range if provided
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]

        df = df.sort_values('date').reset_index(drop=True)
        logger.info(f"Retrieved {len(df)} market cap records for {symbol}")
        return df

    def get_historical_price(self, symbol: str, start_date: str = None,
                              end_date: str = None) -> pd.DataFrame:
        """Get historical OHLCV price data

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        params = {}
        if start_date:
            params['from'] = start_date
        if end_date:
            params['to'] = end_date

        data = self._make_request(f"historical-price-full/{symbol}", params)

        if not data or 'historical' not in data:
            logger.warning(f"No historical price data for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data['historical'])

        if df.empty:
            return df

        df['date'] = pd.to_datetime(df['date'])
        df['symbol'] = symbol

        # Standardize column names
        column_map = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'adjClose': 'adj_close',
        }
        df = df.rename(columns=column_map)

        df = df.sort_values('date').reset_index(drop=True)
        logger.info(f"Retrieved {len(df)} price records for {symbol}")
        return df

    def get_bulk_market_cap(self, symbols: List[str], start_date: str,
                            end_date: str) -> pd.DataFrame:
        """Get historical market cap for multiple symbols

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date

        Returns:
            Combined DataFrame with all symbols' market cap data
        """
        all_data = []

        for i, symbol in enumerate(symbols):
            logger.info(f"Fetching market cap for {symbol} ({i+1}/{len(symbols)})")
            try:
                df = self.get_historical_market_cap(symbol, start_date, end_date)
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                logger.error(f"Error fetching market cap for {symbol}: {e}")

        if not all_data:
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"Retrieved total {len(combined)} market cap records for {len(symbols)} symbols")
        return combined

    def sync_sp500_data(self, start_date: str, end_date: str, db_connection=None) -> bool:
        """
        Sync all S&P 500 data to local database

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data
            db_connection: Optional database connection

        Returns:
            True if successful
        """
        try:
            # Get current constituents
            constituents = self.get_sp500_constituents()

            if constituents.empty:
                logger.error("Could not retrieve S&P 500 constituents")
                return False

            symbols = constituents['symbol'].tolist()
            logger.info(f"Syncing data for {len(symbols)} S&P 500 companies")

            # Get market cap data for all symbols
            market_cap_df = self.get_bulk_market_cap(symbols, start_date, end_date)

            if market_cap_df.empty:
                logger.error("No market cap data retrieved")
                return False

            # Save to database if connection provided
            if db_connection:
                self._save_to_database(db_connection, constituents, market_cap_df)

            logger.info("S&P 500 data sync complete")
            return True

        except Exception as e:
            logger.error(f"Error syncing S&P 500 data: {e}")
            return False

    def _save_to_database(self, conn, constituents_df: pd.DataFrame,
                          market_cap_df: pd.DataFrame):
        """Save data to PostgreSQL database

        Args:
            conn: Database connection
            constituents_df: S&P 500 constituents data
            market_cap_df: Market cap historical data
        """
        cursor = conn.cursor()

        try:
            # Save constituents
            for _, row in constituents_df.iterrows():
                cursor.execute("""
                    INSERT INTO sp500_constituents (symbol, company_name, sector, sub_industry)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol, date_added) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        sector = EXCLUDED.sector,
                        sub_industry = EXCLUDED.sub_industry,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    row.get('symbol'),
                    row.get('name'),
                    row.get('sector'),
                    row.get('subSector')
                ))

            # Save market cap data
            for _, row in market_cap_df.iterrows():
                cursor.execute("""
                    INSERT INTO market_cap_daily (symbol, date, market_cap)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        market_cap = EXCLUDED.market_cap
                """, (
                    row['symbol'],
                    row['date'],
                    row['market_cap']
                ))

            conn.commit()
            logger.info("Data saved to database successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving to database: {e}")
            raise


# Convenience function for quick access
def get_fmp_service() -> FMPDataService:
    """Get FMP service instance

    Returns:
        FMPDataService instance
    """
    return FMPDataService()
