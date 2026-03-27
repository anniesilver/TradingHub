"""Yahoo Finance data service for S&P 500 market cap data - No API key required"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

import pandas as pd
import requests
import yfinance as yf
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'tradinghub'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
}


class YFinanceDataService:
    """Service to fetch S&P 500 market cap data from Yahoo Finance"""

    def __init__(self):
        self.conn = None

    def get_db_connection(self):
        """Get database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v})
        return self.conn

    def get_sp500_constituents(self) -> pd.DataFrame:
        """
        Fetch current S&P 500 constituents from Wikipedia
        Returns DataFrame with columns: Symbol, Security, GICS Sector, GICS Sub-Industry, etc.
        """
        logger.info("Fetching S&P 500 constituents from Wikipedia...")

        # Wikipedia maintains a table of S&P 500 companies
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        # Use requests with proper headers to avoid 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse HTML tables
        tables = pd.read_html(response.text)

        # First table contains current constituents
        sp500_df = tables[0]

        # Clean up symbol column (remove dots, replace with dashes for Yahoo Finance)
        sp500_df['Symbol'] = sp500_df['Symbol'].str.replace('.', '-', regex=False)

        logger.info(f"Found {len(sp500_df)} S&P 500 constituents")
        return sp500_df

    def get_market_cap(self, symbol: str) -> Optional[int]:
        """Get current market cap for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            market_cap = info.get('marketCap')
            return market_cap
        except Exception as e:
            logger.warning(f"Error fetching market cap for {symbol}: {e}")
            return None

    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical price data for a symbol
        Returns DataFrame with Date, Open, High, Low, Close, Volume
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            df = df.reset_index()
            df['Symbol'] = symbol
            return df
        except Exception as e:
            logger.warning(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def save_constituents_to_db(self, constituents_df: pd.DataFrame):
        """Save S&P 500 constituents to database"""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                for _, row in constituents_df.iterrows():
                    cursor.execute("""
                        INSERT INTO sp500_constituents (symbol, company_name, sector, sub_industry, date_added)
                        VALUES (%s, %s, %s, %s, CURRENT_DATE)
                        ON CONFLICT (symbol, date_added) DO UPDATE SET
                            company_name = EXCLUDED.company_name,
                            sector = EXCLUDED.sector,
                            sub_industry = EXCLUDED.sub_industry,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        row['Symbol'],
                        row.get('Security', ''),
                        row.get('GICS Sector', ''),
                        row.get('GICS Sub-Industry', '')
                    ))

                conn.commit()
                logger.info(f"Saved {len(constituents_df)} constituents to database")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving constituents: {e}")
            raise

    def save_market_cap_to_db(self, symbol: str, date: datetime, market_cap: int,
                               close_price: float = None, shares_outstanding: int = None):
        """Save market cap data to database"""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO market_cap_daily (symbol, date, market_cap, close_price, shares_outstanding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        market_cap = EXCLUDED.market_cap,
                        close_price = EXCLUDED.close_price,
                        shares_outstanding = EXCLUDED.shares_outstanding
                """, (symbol, date, market_cap, close_price, shares_outstanding))

                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving market cap for {symbol}: {e}")
            raise

    def sync_current_market_caps(self, symbols: List[str] = None):
        """
        Sync current market caps for all S&P 500 stocks
        This fetches live market cap data from Yahoo Finance
        """
        if symbols is None:
            constituents = self.get_sp500_constituents()
            symbols = constituents['Symbol'].tolist()

        logger.info(f"Syncing market caps for {len(symbols)} symbols...")
        today = datetime.now().date()

        success_count = 0
        error_count = 0

        for i, symbol in enumerate(symbols):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                market_cap = info.get('marketCap')
                if market_cap:
                    close_price = info.get('previousClose') or info.get('regularMarketPrice')
                    shares = info.get('sharesOutstanding')

                    self.save_market_cap_to_db(
                        symbol=symbol,
                        date=today,
                        market_cap=market_cap,
                        close_price=close_price,
                        shares_outstanding=shares
                    )
                    success_count += 1

                    if (i + 1) % 50 == 0:
                        logger.info(f"Processed {i + 1}/{len(symbols)} symbols...")
                else:
                    logger.warning(f"No market cap data for {symbol}")
                    error_count += 1

                # Rate limiting - be gentle with Yahoo Finance
                time.sleep(0.2)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                error_count += 1

        logger.info(f"Sync complete: {success_count} success, {error_count} errors")
        return success_count, error_count

    def get_top_market_cap(self, date: datetime = None, limit: int = 10) -> pd.DataFrame:
        """
        Get top companies by market cap from database
        """
        if date is None:
            date = datetime.now().date()

        conn = self.get_db_connection()

        query = """
            SELECT symbol, market_cap, close_price, shares_outstanding
            FROM market_cap_daily
            WHERE date = %s
            ORDER BY market_cap DESC
            LIMIT %s
        """

        df = pd.read_sql_query(query, conn, params=(date, limit))
        return df

    def get_leader_history(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get the #1 market cap company for each day in the date range
        """
        conn = self.get_db_connection()

        query = """
            WITH daily_ranks AS (
                SELECT
                    date,
                    symbol,
                    market_cap,
                    ROW_NUMBER() OVER (PARTITION BY date ORDER BY market_cap DESC) as rank
                FROM market_cap_daily
                WHERE date BETWEEN %s AND %s
            )
            SELECT date, symbol, market_cap
            FROM daily_ranks
            WHERE rank = 1
            ORDER BY date
        """

        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        return df

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()


def main():
    """Main function to sync S&P 500 data"""
    service = YFinanceDataService()

    try:
        # Step 1: Get and save constituents
        logger.info("=" * 50)
        logger.info("Step 1: Fetching S&P 500 constituents...")
        constituents = service.get_sp500_constituents()
        service.save_constituents_to_db(constituents)

        # Step 2: Sync current market caps
        logger.info("=" * 50)
        logger.info("Step 2: Syncing current market caps...")
        symbols = constituents['Symbol'].tolist()
        success, errors = service.sync_current_market_caps(symbols)

        # Step 3: Show top 10 by market cap
        logger.info("=" * 50)
        logger.info("Step 3: Top 10 companies by market cap:")
        top10 = service.get_top_market_cap(limit=10)
        for _, row in top10.iterrows():
            market_cap_b = row['market_cap'] / 1e9
            logger.info(f"  {row['symbol']}: ${market_cap_b:.1f}B")

        logger.info("=" * 50)
        logger.info("Sync complete!")

    finally:
        service.close()


if __name__ == '__main__':
    main()
