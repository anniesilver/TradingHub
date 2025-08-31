"""Enhanced Market data handling module with IBKR integration"""

import os
import sys
from typing import Optional, Union

import numpy as np
import pandas as pd
from scipy.stats import norm

# Add the current directory to Python path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from ibkr_data_service import ibkr_service


class EnhancedMarketData:
    """Enhanced MarketData class that uses DB-first approach with IBKR fallback"""
    
    def __init__(self, symbol: str):
        """Initialize market data"""
        self.symbol = symbol
        self.data = None
        self._data_loaded = False

    def load_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Load market data using DB-first approach with IBKR fallback"""
        # Return already loaded data if available and covers the requested range
        if self._data_loaded and self.data is not None:
            if start_date is None and end_date is None:
                return self.data
            # Check if current data covers the requested range
            if (start_date is None or pd.to_datetime(start_date) >= self.data.index.min()) and \
               (end_date is None or pd.to_datetime(end_date) <= self.data.index.max()):
                return self.data

        try:
            # Set default date range if not provided
            if start_date is None:
                start_date = "2015-01-01"  # 10 years of data
            if end_date is None:
                # Use yesterday's date to avoid issues when market is open (no close data for today yet)
                yesterday = pd.Timestamp.now() - pd.Timedelta(days=1)
                end_date = yesterday.strftime("%Y-%m-%d")

            print(f"Loading data for {self.symbol} from {start_date} to {end_date}")

            # Try to get SPY data from DB/IBKR
            spy_df = ibkr_service.get_market_data("SPY", start_date, end_date)
            
            # Try to get VIX data from DB/IBKR  
            vix_df = ibkr_service.get_market_data("VIX", start_date, end_date)

            if spy_df.empty:
                raise Exception("No SPY data available")
            
            if vix_df.empty:
                print("Warning: No VIX data available, using default volatility")
                # Create a default VIX series with reasonable values
                vix_df = pd.DataFrame(
                    index=spy_df.index,
                    data={'close': [20.0] * len(spy_df)}  # Default 20% volatility
                )

            print(f"Successfully loaded {len(spy_df)} SPY records and {len(vix_df)} VIX records")
            print(f"Data range: {spy_df.index.min()} to {spy_df.index.max()}")

        except Exception as e:
            print(f"Error loading data from IBKR service: {str(e)}")
            print("Attempting fallback to local CSV files...")
            
            # Fallback to CSV files
            try:
                # Try to find CSV files in the strategy directory
                strategy_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'algo_trading', 'SPY_POWER_CASHFLOW')
                spy_file = os.path.join(strategy_path, 'data', 'SPY-20 Y.csv')
                vix_file = os.path.join(strategy_path, 'data', 'VIX-20 Y.csv')
                
                if os.path.exists(spy_file) and os.path.exists(vix_file):
                    spy_df = pd.read_csv(spy_file)
                    vix_df = pd.read_csv(vix_file)
                    
                    # Process CSV data
                    spy_df['DateTime'] = pd.to_datetime(spy_df['DateTime'])
                    vix_df['DateTime'] = pd.to_datetime(vix_df['DateTime'])
                    spy_df.set_index('DateTime', inplace=True)
                    vix_df.set_index('DateTime', inplace=True)
                    
                    # Rename columns to match DB format
                    if 'Close' in spy_df.columns:
                        spy_df.rename(columns={'Close': 'close', 'Open': 'open', 
                                             'High': 'high', 'Low': 'low'}, inplace=True)
                    if 'Close' in vix_df.columns:
                        vix_df.rename(columns={'Close': 'close'}, inplace=True)
                    
                    print("Successfully loaded data from CSV fallback")
                else:
                    raise Exception("CSV fallback files not found")
                    
            except Exception as csv_error:
                print(f"CSV fallback also failed: {str(csv_error)}")
                raise Exception(f"Failed to load data from both IBKR service and CSV files: {str(e)}")

        # Merge SPY and VIX data
        # Align indexes and merge
        df = spy_df.copy()
        
        # Add VIX data, handling different index names
        vix_values = vix_df['close'].reindex(df.index, method='ffill')  # Forward fill missing VIX values
        df['VIX'] = vix_values / 100  # Convert VIX percentage to decimal

        # Ensure column names are standardized (use title case as expected by strategies)
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close'
        })

        # Convert columns to float
        for col in ['Open', 'High', 'Low', 'Close']:
            if col in df.columns:
                df[col] = df[col].astype(float)
        df['VIX'] = df['VIX'].astype(float)

        # Add tracking columns expected by strategies
        df['Portfolio_Value'] = 0.0
        df['Cash_Balance'] = 0.0
        df['Margin_Ratio'] = 0.0

        # Sort by date
        df.sort_index(inplace=True)

        print("\nData Summary:")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
        print(f"Total records: {len(df)}")

        print("\nVolatility Summary:")
        print(f"VIX range: {df['VIX'].min()*100:.1f}% to {df['VIX'].max()*100:.1f}%")

        self.data = df.copy()
        self._data_loaded = True
        return self.data

    def get_current_price(self, date: pd.Timestamp) -> float:
        """Get price for a given date"""
        if not self._data_loaded:
            self.load_data()
        return float(self.data.loc[date, 'Close'])

    def get_current_vix(self, date: pd.Timestamp) -> float:
        """Get VIX for a given date"""
        if not self._data_loaded:
            self.load_data()
        return float(self.data.loc[date, 'VIX'])

    def get_data_for_range(
        self, start_date: Optional[Union[pd.Timestamp, str]] = None, end_date: Optional[Union[pd.Timestamp, str]] = None
    ) -> pd.DataFrame:
        """Get data for a specific date range

        Args:
            start_date (pd.Timestamp, optional): Start date. Defaults to None (use earliest date).
            end_date (pd.Timestamp, optional): End date. Defaults to None (use latest date).

        Returns:
            pd.DataFrame: Filtered data for the specified date range
        """
        # Convert timestamps to strings for the load_data method
        # Handle both string and datetime inputs
        if isinstance(start_date, str):
            start_str = start_date
        else:
            start_str = start_date.strftime("%Y-%m-%d") if start_date else None
            
        if isinstance(end_date, str):
            end_str = end_date
        else:
            end_str = end_date.strftime("%Y-%m-%d") if end_date else None
        
        # Load data for the specific range
        if not self._data_loaded or start_str or end_str:
            self.load_data(start_str, end_str)

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

        return filtered_data

    def calculate_historical_volatility(self, window: int = 30) -> pd.Series:
        """Calculate historical volatility using daily returns.

        Args:
            window: Number of days to use for rolling volatility calculation (default: 30)

        Returns:
            pd.Series: Historical volatility series
        """
        if not self._data_loaded:
            self.load_data()
            
        # Calculate daily returns
        daily_returns = np.log(self.data['Close'] / self.data['Close'].shift(1))

        # Calculate rolling standard deviation and annualize
        # Multiply by sqrt(252) to annualize (252 trading days in a year)
        historical_vol = daily_returns.rolling(window=window).std() * np.sqrt(252)

        return historical_vol


# For backward compatibility, create an alias
MarketData = EnhancedMarketData