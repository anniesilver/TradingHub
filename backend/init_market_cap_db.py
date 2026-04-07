"""Initialize database tables for SPY500_LEADER strategy market cap data"""

import os
import sys
import logging

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'services', '.env'))

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


def get_connection():
    """Get database connection"""
    return psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v})


def create_tables():
    """Create tables for S&P 500 market cap data"""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            # Table: sp500_constituents
            # Tracks historical S&P 500 membership
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sp500_constituents (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    company_name VARCHAR(255),
                    date_added DATE DEFAULT CURRENT_DATE,
                    date_removed DATE,
                    sector VARCHAR(100),
                    sub_industry VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date_added)
                )
            """)
            logger.info("Created table: sp500_constituents")

            # Table: market_cap_daily
            # Stores daily market cap for all S&P 500 stocks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_cap_daily (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    market_cap BIGINT NOT NULL,
                    shares_outstanding BIGINT,
                    close_price DECIMAL(12, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """)
            logger.info("Created table: market_cap_daily")

            # Create indexes for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_cap_daily_date
                ON market_cap_daily(date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_cap_daily_symbol
                ON market_cap_daily(symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_cap_daily_rank
                ON market_cap_daily(date, market_cap DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sp500_constituents_symbol
                ON sp500_constituents(symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sp500_constituents_dates
                ON sp500_constituents(date_added, date_removed)
            """)
            logger.info("Created indexes")

            conn.commit()
            logger.info("All tables and indexes created successfully")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        conn.close()


def drop_tables():
    """Drop the market cap tables (use with caution)"""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS market_cap_daily CASCADE")
            cursor.execute("DROP TABLE IF EXISTS sp500_constituents CASCADE")
            conn.commit()
            logger.info("Dropped market cap tables")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error dropping tables: {e}")
        raise
    finally:
        conn.close()


def check_tables():
    """Check if tables exist and show row counts"""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            # Check sp500_constituents
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'sp500_constituents'
                )
            """)
            constituents_exists = cursor.fetchone()[0]

            # Check market_cap_daily
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'market_cap_daily'
                )
            """)
            market_cap_exists = cursor.fetchone()[0]

            print(f"sp500_constituents table exists: {constituents_exists}")
            print(f"market_cap_daily table exists: {market_cap_exists}")

            if constituents_exists:
                cursor.execute("SELECT COUNT(*) FROM sp500_constituents")
                count = cursor.fetchone()[0]
                print(f"sp500_constituents rows: {count}")

            if market_cap_exists:
                cursor.execute("SELECT COUNT(*) FROM market_cap_daily")
                count = cursor.fetchone()[0]
                print(f"market_cap_daily rows: {count}")

                # Show date range
                cursor.execute("SELECT MIN(date), MAX(date) FROM market_cap_daily")
                min_date, max_date = cursor.fetchone()
                if min_date and max_date:
                    print(f"market_cap_daily date range: {min_date} to {max_date}")

    except Exception as e:
        logger.error(f"Error checking tables: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Initialize market cap database tables')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables first')
    parser.add_argument('--check', action='store_true', help='Check table status only')
    args = parser.parse_args()

    if args.check:
        check_tables()
    elif args.drop:
        print("WARNING: This will drop all market cap data!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            drop_tables()
            create_tables()
        else:
            print("Aborted")
    else:
        create_tables()
        check_tables()
