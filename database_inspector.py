#!/usr/bin/env python3
"""
Database Inspector
Directly investigates what data is actually in the database vs what's being retrieved
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'services'))

import psycopg2
import pandas as pd
from datetime import datetime

def get_db_connection():
    """Get database connection using same method as backend"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="tradinghub",
            user="postgres",
            password="Annie123"
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def inspect_database():
    """Inspect what's actually in the database"""
    print("=" * 80)
    print("DATABASE INSPECTION REPORT")
    print("=" * 80)

    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return

    try:
        cursor = conn.cursor()

        # 1. Check total records in market_data table
        print("1. TOTAL RECORDS IN MARKET_DATA TABLE:")
        cursor.execute("SELECT COUNT(*) FROM market_data")
        total_records = cursor.fetchone()[0]
        print(f"   Total records: {total_records:,}")

        # 2. Check SPY records specifically
        print("\n2. SPY RECORDS BREAKDOWN:")
        cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol = 'SPY'")
        spy_records = cursor.fetchone()[0]
        print(f"   SPY records: {spy_records:,}")

        # 3. Check date range of SPY data
        print("\n3. SPY DATE RANGE:")
        cursor.execute("""
            SELECT MIN(date) as earliest, MAX(date) as latest
            FROM market_data WHERE symbol = 'SPY'
        """)
        date_range = cursor.fetchone()
        print(f"   Earliest: {date_range[0]}")
        print(f"   Latest: {date_range[1]}")

        # 4. Check year-by-year breakdown
        print("\n4. SPY RECORDS BY YEAR:")
        cursor.execute("""
            SELECT EXTRACT(YEAR FROM date) as year, COUNT(*) as count
            FROM market_data WHERE symbol = 'SPY'
            GROUP BY EXTRACT(YEAR FROM date)
            ORDER BY year
        """)
        yearly_data = cursor.fetchall()

        for year, count in yearly_data:
            print(f"   {int(year)}: {count:,} records")

        # 5. Check specific 2000-2009 period
        print("\n5. 2000-2009 PERIOD ANALYSIS:")
        cursor.execute("""
            SELECT COUNT(*) FROM market_data
            WHERE symbol = 'SPY' AND date >= '2000-01-01' AND date <= '2009-12-31'
        """)
        period_records = cursor.fetchone()[0]
        print(f"   2000-2009 records: {period_records:,}")

        # 6. Test the exact query used by the backend
        print("\n6. BACKEND QUERY TEST:")
        query = """
            SELECT symbol, date, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s AND date >= %s AND date <= %s
            ORDER BY date
        """

        df = pd.read_sql_query(query, conn, params=('SPY', '2000-01-03', '2009-12-31'))
        print(f"   Backend query returns: {len(df):,} records")

        if not df.empty:
            print(f"   Date range in results: {df['date'].min()} to {df['date'].max()}")

            # Check for gaps
            print("\n7. CHECKING FOR DATA GAPS:")
            df['date'] = pd.to_datetime(df['date'])
            df_sorted = df.sort_values('date')

            # Find largest gaps
            df_sorted['date_diff'] = df_sorted['date'].diff()
            large_gaps = df_sorted[df_sorted['date_diff'] > pd.Timedelta(days=7)]

            if not large_gaps.empty:
                print("   Large gaps found (>7 days):")
                for idx, row in large_gaps.head(10).iterrows():
                    print(f"     Gap after {row['date']}: {row['date_diff'].days} days")
            else:
                print("   No large gaps found")

            # Sample some early records
            print("\n8. SAMPLE EARLY RECORDS (2000-2001):")
            early_records = df_sorted[df_sorted['date'] < '2002-01-01'].head(5)
            for idx, row in early_records.iterrows():
                print(f"     {row['date'].date()}: Close ${row['close']:.2f}")

        # 9. Check for data quality issues
        print("\n9. DATA QUALITY CHECK:")
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN open IS NULL THEN 1 END) as null_open,
                COUNT(CASE WHEN close IS NULL THEN 1 END) as null_close,
                COUNT(CASE WHEN high IS NULL THEN 1 END) as null_high,
                COUNT(CASE WHEN low IS NULL THEN 1 END) as null_low
            FROM market_data WHERE symbol = 'SPY'
        """)
        quality = cursor.fetchone()
        print(f"   Total records: {quality[0]:,}")
        print(f"   NULL opens: {quality[1]:,}")
        print(f"   NULL closes: {quality[2]:,}")
        print(f"   NULL highs: {quality[3]:,}")
        print(f"   NULL lows: {quality[4]:,}")

    except Exception as e:
        print(f"❌ Database inspection failed: {e}")
    finally:
        conn.close()

def check_vix_data():
    """Check VIX data availability"""
    print("\n" + "=" * 80)
    print("VIX DATA INSPECTION")
    print("=" * 80)

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Check VIX records
        cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol = 'VIX'")
        vix_records = cursor.fetchone()[0]
        print(f"VIX records: {vix_records:,}")

        if vix_records > 0:
            cursor.execute("""
                SELECT MIN(date) as earliest, MAX(date) as latest
                FROM market_data WHERE symbol = 'VIX'
            """)
            date_range = cursor.fetchone()
            print(f"VIX date range: {date_range[0]} to {date_range[1]}")

    except Exception as e:
        print(f"❌ VIX inspection failed: {e}")
    finally:
        conn.close()

def main():
    """Main inspection function"""
    print("Starting database inspection...")
    print("This will check what data is actually stored vs what's being retrieved")
    print()

    inspect_database()
    check_vix_data()

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    print("\nKey findings should help identify:")
    print("1. Whether all 5,027 records are actually in the database")
    print("2. Date range coverage and gaps")
    print("3. Data quality issues")
    print("4. Why backend query only returns 1,075 records")

if __name__ == "__main__":
    main()