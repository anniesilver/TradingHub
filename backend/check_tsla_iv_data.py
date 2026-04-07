"""Check if TSLA option data has IV values"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def check_tsla_iv_data():
    """Check TSLA option IV data availability"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Check TSLA option data
        cursor.execute("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(implied_volatility) as rows_with_iv,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                strike,
                expiration
            FROM options_data
            WHERE symbol = 'TSLA'
            GROUP BY strike, expiration
            ORDER BY expiration, strike
        """)

        results = cursor.fetchall()

        if not results:
            print("❌ No TSLA option data found in database")
            print("   You need to fetch TSLA option data from IBKR first")
            return False

        print("TSLA Option Data in Database:")
        print("=" * 80)
        for row in results:
            total, with_iv, min_date, max_date, strike, expiration = row
            iv_percentage = (with_iv / total * 100) if total > 0 else 0

            print(f"\nTSLA {strike}C exp={expiration}")
            print(f"  Total bars: {total}")
            print(f"  Bars with IV: {with_iv} ({iv_percentage:.1f}%)")
            print(f"  Date range: {min_date} to {max_date}")

            if with_iv == 0:
                print(f"  ❌ NO IV DATA - needs re-fetch")
            elif iv_percentage < 90:
                print(f"  ⚠️  PARTIAL IV DATA - consider re-fetch")
            else:
                print(f"  ✓ IV data available")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_tsla_iv_data()
