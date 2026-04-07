"""Diagnose why TSLA option data is not being cached"""
import os
import psycopg2
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def diagnose_cache():
    """Check database for TSLA 600C data and diagnose caching issue"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Query TSLA 600C data
        query = """
            SELECT
                COUNT(*) as total_bars,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                bar_interval,
                COUNT(DISTINCT bar_interval) as interval_count
            FROM options_data
            WHERE symbol = 'TSLA'
                AND strike = 600.0
                AND "right" = 'C'
                AND expiration = '2026-06-18'
            GROUP BY bar_interval
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print("=" * 80)
        print("TSLA 600C exp=2026-06-18 - Database Cache Diagnostic")
        print("=" * 80)

        if not results:
            print("\n❌ NO DATA FOUND IN DATABASE")
            print("   This explains why it's fetching from IBKR every time!")
            print("\nPossible reasons:")
            print("   1. Data was not saved to database after fetch")
            print("   2. Expiration date format mismatch")
            print("   3. Database save failed silently")
            return

        for row in results:
            total, earliest, latest, interval, count = row
            print(f"\n✓ Data found in database:")
            print(f"  Bar interval: {interval}")
            print(f"  Total bars: {total}")
            print(f"  Date range: {earliest} to {latest}")

            # Calculate date range
            start_dt = pd.to_datetime(earliest)
            end_dt = pd.to_datetime(latest)
            days_coverage = (end_dt - start_dt).days

            print(f"  Coverage: {days_coverage} days")

        # Now test the actual query that get_option_data_from_db uses
        print("\n" + "=" * 80)
        print("Testing actual database query used by get_option_data_from_db()")
        print("=" * 80)

        test_start = '2025-11-07'
        test_end = '2026-01-06'
        test_interval = '30 mins'

        test_query = """
            SELECT COUNT(*)
            FROM options_data
            WHERE symbol = %s
                AND strike = %s
                AND "right" = %s
                AND expiration = %s
                AND date >= %s
                AND date <= %s
                AND bar_interval = %s
        """

        cursor.execute(test_query, ('TSLA', 600.0, 'C', '2026-06-18', test_start, test_end, test_interval))
        count = cursor.fetchone()[0]

        print(f"\nQuery parameters:")
        print(f"  symbol: TSLA")
        print(f"  strike: 600.0")
        print(f"  right: C")
        print(f"  expiration: 2026-06-18")
        print(f"  start_date: {test_start}")
        print(f"  end_date: {test_end}")
        print(f"  bar_interval: {test_interval}")
        print(f"\nResult: {count} bars")

        if count == 0:
            print("\n❌ QUERY RETURNS 0 BARS!")
            print("   This is why it's re-fetching from IBKR!")
            print("\nLikely issues:")
            print("   1. bar_interval doesn't match exactly (check spaces, case)")
            print("   2. Expiration date format mismatch")
            print("   3. Date range is outside stored data")

            # Check what bar_intervals exist
            cursor.execute("""
                SELECT DISTINCT bar_interval
                FROM options_data
                WHERE symbol = 'TSLA' AND strike = 600.0 AND "right" = 'C'
            """)
            intervals = cursor.fetchall()
            print(f"\n   Available bar_intervals in DB: {[row[0] for row in intervals]}")

        else:
            print(f"\n✓ Query would return {count} bars - SHOULD USE CACHE!")
            print("   Issue might be in the coverage check logic")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_cache()
