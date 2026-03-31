"""Backfill historical market cap data using Yahoo Finance"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List
import time

import pandas as pd
import yfinance as yf
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'services', '.env'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'tradinghub'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
}


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v})


def get_sp500_symbols() -> List[str]:
    """Get S&P 500 symbols from database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT symbol FROM sp500_constituents ORDER BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]
        return symbols
    finally:
        conn.close()


def get_top_symbols_by_market_cap(limit: int = 50) -> List[str]:
    """Get top N symbols by current market cap"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT symbol FROM (
                    SELECT symbol, market_cap,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                    FROM market_cap_daily
                ) t WHERE rn = 1
                ORDER BY market_cap DESC
                LIMIT %s
            """, (limit,))
            symbols = [row[0] for row in cursor.fetchall()]
        return symbols
    finally:
        conn.close()


def backfill_symbol(symbol: str, start_date: str, end_date: str) -> int:
    """
    Backfill historical market cap for a single symbol.

    Uses: Historical Price × Current Shares Outstanding = Estimated Historical Market Cap

    This is an approximation but works well for large companies where
    shares outstanding doesn't change dramatically (stock splits are
    already reflected in adjusted prices).
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get current shares outstanding
        info = ticker.info
        shares_outstanding = info.get('sharesOutstanding')

        if not shares_outstanding:
            logger.warning(f"{symbol}: No shares outstanding data")
            return 0

        # Get historical price data
        hist = ticker.history(start=start_date, end=end_date)

        if hist.empty:
            logger.warning(f"{symbol}: No historical data")
            return 0

        # Calculate historical market cap
        hist['market_cap'] = hist['Close'] * shares_outstanding

        # Save to database
        conn = get_db_connection()
        records_saved = 0

        try:
            with conn.cursor() as cursor:
                for date, row in hist.iterrows():
                    # Convert timezone-aware datetime to naive
                    date_naive = date.tz_localize(None) if date.tzinfo else date
                    date_str = date_naive.strftime('%Y-%m-%d')

                    market_cap = int(row['market_cap'])
                    close_price = float(row['Close'])

                    cursor.execute("""
                        INSERT INTO market_cap_daily (symbol, date, market_cap, close_price, shares_outstanding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, date) DO UPDATE SET
                            market_cap = EXCLUDED.market_cap,
                            close_price = EXCLUDED.close_price,
                            shares_outstanding = EXCLUDED.shares_outstanding
                    """, (symbol, date_str, market_cap, close_price, shares_outstanding))
                    records_saved += 1

                conn.commit()
        finally:
            conn.close()

        return records_saved

    except Exception as e:
        logger.error(f"{symbol}: Error - {e}")
        return 0


def backfill_market_cap_data(start_date: str, end_date: str, top_n: int = 50):
    """
    Backfill historical market cap data for top N companies.

    For efficiency, we only backfill the top N companies by current market cap,
    since only the top companies will ever be the "leader" in the strategy.
    """
    logger.info(f"Backfilling market cap data from {start_date} to {end_date}")

    # Get top symbols
    symbols = get_top_symbols_by_market_cap(top_n)
    logger.info(f"Will backfill {len(symbols)} symbols: {symbols[:10]}...")

    total_records = 0
    success_count = 0

    for i, symbol in enumerate(symbols):
        logger.info(f"Processing {symbol} ({i+1}/{len(symbols)})...")

        records = backfill_symbol(symbol, start_date, end_date)

        if records > 0:
            total_records += records
            success_count += 1
            logger.info(f"  {symbol}: {records} records saved")
        else:
            logger.warning(f"  {symbol}: No records saved")

        # Rate limiting
        time.sleep(0.3)

    logger.info(f"Backfill complete: {success_count}/{len(symbols)} symbols, {total_records} total records")
    return total_records


def check_data_coverage():
    """Check date range coverage in database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(DISTINCT date) as days,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM market_cap_daily
            """)
            row = cursor.fetchone()

            print(f"\nMarket Cap Data Coverage:")
            print(f"  Total records: {row[0]:,}")
            print(f"  Unique symbols: {row[1]}")
            print(f"  Trading days: {row[2]}")
            print(f"  Date range: {row[3]} to {row[4]}")

            # Show top 5 by record count
            cursor.execute("""
                SELECT symbol, COUNT(*) as days
                FROM market_cap_daily
                GROUP BY symbol
                ORDER BY days DESC
                LIMIT 5
            """)
            print(f"\nTop 5 symbols by data coverage:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} days")

    finally:
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Backfill historical market cap data')
    parser.add_argument('--start', default='2016-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default=datetime.now().strftime('%Y-%m-%d'), help='End date (YYYY-MM-DD)')
    parser.add_argument('--top', type=int, default=50, help='Number of top companies to backfill')
    parser.add_argument('--check', action='store_true', help='Only check data coverage')

    args = parser.parse_args()

    if args.check:
        check_data_coverage()
    else:
        print(f"Backfilling market cap data for top {args.top} companies")
        print(f"Date range: {args.start} to {args.end}")
        print("This will take several minutes...\n")

        backfill_market_cap_data(args.start, args.end, args.top)

        print("\n" + "="*50)
        check_data_coverage()
