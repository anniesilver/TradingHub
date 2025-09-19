"""Unified Market Data Module - Database-first approach with IBKR fallback"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any, List

import numpy as np
import pandas as pd
from scipy.stats import norm

# Add the current directory to Python path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from ibkr_data_service import ibkr_service

# Configure logging
logger = logging.getLogger(__name__)


class MarketData:
    """Unified MarketData class that uses database-first approach with IBKR fallback"""

    def __init__(self, symbol: str):
        """Initialize market data

        Args:
            symbol: Trading symbol (e.g., 'SPY', 'VIX')
        """
        self.symbol = symbol
        self.data = None
        self._data_loaded = False
        self._last_loaded_range = None

        # Initialize database table on first use
        try:
            ibkr_service.create_market_data_table()
        except Exception as e:
            logger.warning(f"Could not initialize database table: {e}")

    def load_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Load market data using database-first approach with IBKR fallback

        Args:
            start_date: Start date in 'YYYY-MM-DD' format (if None, loads from earliest available)
            end_date: End date in 'YYYY-MM-DD' format (if None, loads to latest available)

        Returns:
            pd.DataFrame: Market data with datetime index
        """
        # Convert None dates to reasonable defaults
        if start_date is None:
            # Default to 5 years ago instead of hardcoded 2015
            start_date = (datetime.now() - timedelta(days=5*365)).strftime("%Y-%m-%d")
            logger.info(f"No start_date provided, using default: {start_date}")

        if end_date is None:
            # Use yesterday to avoid issues when market is open (no close data for today yet)
            yesterday = datetime.now() - timedelta(days=1)
            end_date = yesterday.strftime("%Y-%m-%d")
            logger.info(f"No end_date provided, using default: {end_date}")

        # Check if we already have data loaded for this range
        current_range = (start_date, end_date)
        if (self._data_loaded and
            self.data is not None and
            self._last_loaded_range == current_range):
            logger.info(f"Using cached data for {self.symbol} from {start_date} to {end_date}")
            return self.data

        logger.info(f"Loading market data for {self.symbol} from {start_date} to {end_date}")

        try:
            # Load primary symbol data
            primary_df = self._load_symbol_data(self.symbol, start_date, end_date)

            # For SPY strategies, also load VIX data
            if self.symbol == "SPY":
                try:
                    vix_df = self._load_symbol_data("VIX", start_date, end_date)

                    # Merge SPY and VIX data
                    if not vix_df.empty:
                        # Join VIX close prices as 'VIX' column
                        primary_df = primary_df.join(vix_df['close'].rename('VIX'), how='left')
                        # Fill any missing VIX values with forward fill
                        primary_df['VIX'] = primary_df['VIX'].fillna(method='ffill')
                        # Convert VIX to decimal if it's in percentage form
                        if primary_df['VIX'].max() > 1.0:
                            primary_df['VIX'] = primary_df['VIX'] / 100
                        logger.info("Successfully merged VIX data with SPY")
                    else:
                        # Set default VIX if we can't load it
                        primary_df['VIX'] = 0.20  # 20% default volatility
                        logger.warning("Could not load VIX data, using default 20% volatility")

                except Exception as e:
                    logger.warning(f"Error loading VIX data: {e}, using default volatility")
                    primary_df['VIX'] = 0.20  # 20% default volatility

            # Rename columns to match strategy expectations
            if 'close' in primary_df.columns:
                primary_df = primary_df.rename(columns={'close': 'Close'})
            if 'open' in primary_df.columns:
                primary_df = primary_df.rename(columns={'open': 'Open'})
            if 'high' in primary_df.columns:
                primary_df = primary_df.rename(columns={'high': 'High'})
            if 'low' in primary_df.columns:
                primary_df = primary_df.rename(columns={'low': 'Low'})
            if 'volume' in primary_df.columns:
                primary_df = primary_df.rename(columns={'volume': 'Volume'})

            # Add required tracking columns for strategy compatibility
            primary_df['Portfolio_Value'] = 0.0
            primary_df['Cash_Balance'] = 0.0
            primary_df['Margin_Ratio'] = 0.0
            primary_df['Premiums_Received'] = 0.0
            primary_df['Interest_Paid'] = 0.0
            primary_df['Trading_Log'] = ''

            # Ensure data is sorted by date
            primary_df.sort_index(inplace=True)

            # Store data and mark as loaded
            self.data = primary_df
            self._data_loaded = True
            self._last_loaded_range = current_range

            logger.info(f"Successfully loaded {len(primary_df)} records for {self.symbol}")
            logger.info(f"Date range: {primary_df.index[0]} to {primary_df.index[-1]}")

            return self.data

        except Exception as e:
            logger.error(f"Failed to load market data for {self.symbol}: {e}")
            raise

    def _load_symbol_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load data for a specific symbol using database-first approach

        Args:
            symbol: Trading symbol
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            pd.DataFrame: Market data for the symbol
        """
        try:
            logger.info(f"Loading data for {symbol} from {start_date} to {end_date}")

            # Try database first
            df = ibkr_service.get_data_from_db(symbol, start_date, end_date)

            if df.empty:
                logger.info(f"No data found in database for {symbol}, fetching from IBKR")

                # Fetch from IBKR and save to database - use longer period to ensure coverage
                logger.info(f"Fetching 20 years of data for {symbol} to ensure coverage")
                if ibkr_service.fetch_and_store_data(symbol, "20 Y"):
                    # Try database again after IBKR fetch
                    df = ibkr_service.get_data_from_db(symbol, start_date, end_date)

                    if df.empty:
                        # Try even longer period if still empty
                        logger.info(f"Still no data, trying 25 years for {symbol}")
                        if ibkr_service.fetch_and_store_data(symbol, "25 Y"):
                            df = ibkr_service.get_data_from_db(symbol, start_date, end_date)

                        if df.empty:
                            raise Exception(f"Still no data available for {symbol} after extended IBKR fetch")
                else:
                    raise Exception(f"Failed to fetch data from IBKR for {symbol}")

            # Check data coverage
            if not df.empty:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)

                # Log coverage information
                logger.info(f"Data coverage for {symbol}:")
                logger.info(f"  Requested: {start_date} to {end_date}")
                logger.info(f"  Available: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")

                # Check if we have reasonable coverage (allow for weekends/holidays)
                start_gap = (df.index.min() - start_dt).days
                end_gap = (end_dt - df.index.max()).days

                if start_gap > 10 or end_gap > 10:
                    logger.warning(f"Data gaps detected for {symbol}: start_gap={start_gap}, end_gap={end_gap}")

                    # Try to fetch more data if gaps are significant
                    logger.info(f"Attempting to fetch additional data for {symbol}")
                    if ibkr_service.fetch_and_store_data(symbol, "20 Y"):  # Fetch longer history
                        df = ibkr_service.get_data_from_db(symbol, start_date, end_date)
                        logger.info(f"After additional fetch: {len(df)} records available")

            return df

        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            raise

    def get_current_price(self, date: pd.Timestamp) -> float:
        """Get price for a given date"""
        if self.data is None or not self._data_loaded:
            self.load_data()
        return float(self.data.loc[date, 'Close'])

    def get_current_vix(self, date: pd.Timestamp) -> float:
        """Get VIX for a given date"""
        if self.data is None or not self._data_loaded:
            self.load_data()

        if 'VIX' in self.data.columns:
            return float(self.data.loc[date, 'VIX'])
        else:
            # Return default volatility if VIX not available
            return 0.20

    def get_data_for_range(
        self, start_date: Optional[Union[pd.Timestamp, str]] = None,
        end_date: Optional[Union[pd.Timestamp, str]] = None
    ) -> pd.DataFrame:
        """Get data for a specific date range

        Args:
            start_date (pd.Timestamp or str, optional): Start date. Defaults to None (use earliest date).
            end_date (pd.Timestamp or str, optional): End date. Defaults to None (use latest date).

        Returns:
            pd.DataFrame: Filtered data for the specified date range
        """
        # Convert string dates to pandas timestamps if needed
        if isinstance(start_date, str):
            start_str = start_date
            start_date = pd.to_datetime(start_date)
        else:
            start_str = start_date.strftime("%Y-%m-%d") if start_date else None

        if isinstance(end_date, str):
            end_str = end_date
            end_date = pd.to_datetime(end_date)
        else:
            end_str = end_date.strftime("%Y-%m-%d") if end_date else None

        # Load data with the requested range to ensure we have the right data
        if start_str or end_str:
            logger.info(f"Loading data for range: {start_str} to {end_str}")
            self.load_data(start_str, end_str)

        # Make sure data is loaded
        if not self._data_loaded:
            self.load_data()

        # Return all data if no range specified
        if start_date is None and end_date is None:
            return self.data.copy()

        # Filter data to specified range
        filtered_data = self.data.copy()

        if start_date is not None:
            filtered_data = filtered_data[filtered_data.index >= start_date]

        if end_date is not None:
            filtered_data = filtered_data[filtered_data.index <= end_date]

        if filtered_data.empty:
            raise ValueError(f"No data available for the specified date range: {start_date} to {end_date}")

        logger.info(f"Filtered data: {len(filtered_data)} records from {filtered_data.index[0]} to {filtered_data.index[-1]}")
        return filtered_data

    def calculate_historical_volatility(self, window: int = 30) -> pd.Series:
        """Calculate historical volatility using daily returns.

        Args:
            window: Number of days to use for rolling volatility calculation (default: 30)

        Returns:
            pd.Series: Historical volatility series
        """
        if self.data is None or not self._data_loaded:
            self.load_data()

        # Calculate daily returns
        daily_returns = np.log(self.data['Close'] / self.data['Close'].shift(1))

        # Calculate rolling standard deviation and annualize
        # Multiply by sqrt(252) to annualize (252 trading days in a year)
        historical_vol = daily_returns.rolling(window=window).std() * np.sqrt(252)

        return historical_vol

    def refresh_data(self) -> bool:
        """Force refresh data from IBKR API"""
        try:
            logger.info(f"Force refreshing data for {self.symbol}")

            # Clear cached data
            self.data = None
            self._data_loaded = False
            self._last_loaded_range = None

            # Force fetch from IBKR
            success = ibkr_service.fetch_and_store_data(self.symbol, "10 Y")

            if success:
                logger.info(f"Successfully refreshed data for {self.symbol}")
                return True
            else:
                logger.error(f"Failed to refresh data for {self.symbol}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing data for {self.symbol}: {e}")
            return False

    def get_data_status(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get information about data availability and coverage

        Args:
            start_date: Start date to check coverage for
            end_date: End date to check coverage for

        Returns:
            Dict with data status information
        """
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # Check database
            df = ibkr_service.get_data_from_db(self.symbol, start_date, end_date)

            if df.empty:
                return {
                    "symbol": self.symbol,
                    "has_data": False,
                    "records_count": 0,
                    "requested_range": f"{start_date} to {end_date}",
                    "message": "No data found in database"
                }

            return {
                "symbol": self.symbol,
                "has_data": True,
                "records_count": len(df),
                "requested_range": f"{start_date} to {end_date}",
                "available_range": f"{df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}",
                "coverage_complete": True,  # We could add more sophisticated coverage analysis here
                "message": "Data available"
            }

        except Exception as e:
            return {
                "symbol": self.symbol,
                "has_data": False,
                "error": str(e),
                "message": "Error checking data status"
            }


# Utility function for Black-Scholes calculations (preserved from original)
def black_scholes_call(S, K, T, r, sigma):
    """Calculate Black-Scholes call option price"""
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call_price