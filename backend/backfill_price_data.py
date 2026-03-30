"""Backfill historical price data for top stocks to database"""

import os
import sys
import logging
from datetime import datetime
import time

import pandas as pd
import yfinance as yf
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'services', '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'tradinghub'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
}


def get_db_connection():
    return psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v})


def get_top_symbols(limit=50):
    """Get top symbols by market cap"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get unique symbols from latest data, ordered by market cap
            cursor.execute("""
                SELECT symbol FROM (
                    SELECT symbol, market_cap,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                    FROM market_cap_daily
                ) t WHERE rn = 1
                ORDER BY market_cap DESC
                LIMIT %s
            """, (limit,))
            return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def check_existing_data(symbol, start_date, end_date):
    """Check if price data already exists for a symbol"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM market_data
                WHERE symbol = %s AND date >= %s AND date <= %s
            """, (symbol, start_date, end_date))
            return cursor.fetchone()[0]
    finally:
        conn.close()


def save_price_data(symbol, start_date, end_date):
    """Fetch and save price data for a symbol"""
    try:
        # Check if data already exists
        existing = check_existing_data(symbol, start_date, end_date)
        if existing > 100:  # If we have substantial data, skip
            logger.info(f"  {symbol}: {existing} records already exist, skipping")
            return existing

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)

        if hist.empty:
            logger.warning(f"  {symbol}: No data from Yahoo Finance")
            return 0

        conn = get_db_connection()
        records_saved = 0

        try:
            with conn.cursor() as cursor:
                for date, row in hist.iterrows():
                    date_naive = date.tz_localize(None) if date.tzinfo else date

                    cursor.execute("""
                        INSERT INTO market_data (symbol, date, open, high, low, close, volume, bar_interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, '1 day')
                        ON CONFLICT (symbol, date, bar_interval) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """, (
                        symbol,
                        date_naive,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume'])
                    ))
                    records_saved += 1

                conn.commit()
        finally:
            conn.close()

        return records_saved

    except Exception as e:
        logger.error(f"  {symbol}: Error - {e}")
        return 0


def backfill_prices(start_date, end_date, top_n=50):
    """Backfill price data for top N companies"""
    logger.info(f"Backfilling price data from {start_date} to {end_date}")

    symbols = get_top_symbols(top_n)
    logger.info(f"Processing {len(symbols)} symbols")

    total = 0
    for i, symbol in enumerate(symbols):
        logger.info(f"Processing {symbol} ({i+1}/{len(symbols)})...")
        records = save_price_data(symbol, start_date, end_date)
        if records > 0:
            logger.info(f"  {symbol}: {records} records")
            total += records
        time.sleep(0.3)

    logger.info(f"Complete: {total} total records saved")


def check_coverage():
    """Show price data coverage"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT symbol, COUNT(*) as days, MIN(date), MAX(date)
                FROM market_data
                WHERE bar_interval = '1 day'
                GROUP BY symbol
                ORDER BY days DESC
                LIMIT 20
            """)
            print("\nPrice Data Coverage (top 20 symbols):")
            print("-" * 60)
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} days ({row[2].date()} to {row[3].date()})")
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2016-01-01')
    parser.add_argument('--end', default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--top', type=int, default=50)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    if args.check:
        check_coverage()
    else:
        backfill_prices(args.start, args.end, args.top)
        check_coverage()
