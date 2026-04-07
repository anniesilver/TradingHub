"""Check all TSLA option expirations in database"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def check_all_expirations():
    """Check all TSLA 600C expirations in database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Query ALL TSLA 600C option data grouped by expiration
        query = """
            SELECT
                expiration,
                COUNT(*) as total_bars,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                bar_interval,
                COUNT(implied_volatility) as bars_with_iv
            FROM options_data
            WHERE symbol = 'TSLA'
                AND strike = 600.0
                AND "right" = 'C'
            GROUP BY expiration, bar_interval
            ORDER BY expiration, bar_interval
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print("=" * 100)
        print("ALL TSLA 600C EXPIRATIONS IN DATABASE")
        print("=" * 100)

        if not results:
            print("\n❌ NO TSLA 600C DATA FOUND IN DATABASE AT ALL")
            print("   This means data was never saved, or all fetch/save operations failed")
            return

        for row in results:
            expiration, total, earliest, latest, interval, iv_count = row
            print(f"\nExpiration: {expiration}")
            print(f"  Bar interval: {interval}")
            print(f"  Total bars: {total}")
            print(f"  Bars with IV: {iv_count} ({iv_count/total*100:.1f}%)")
            print(f"  Date range: {earliest} to {latest}")

        # Now check what format the expiration is stored as
        print("\n" + "=" * 100)
        print("EXPIRATION DATE FORMAT CHECK")
        print("=" * 100)

        cursor.execute("""
            SELECT DISTINCT expiration, pg_typeof(expiration)
            FROM options_data
            WHERE symbol = 'TSLA' AND strike = 600.0 AND "right" = 'C'
        """)

        formats = cursor.fetchall()
        for exp, type_name in formats:
            print(f"Expiration: {exp}, Type: {type_name}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_expirations()
