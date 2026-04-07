"""Find contracts with no IV data"""
import os
import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def check_no_iv():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "tradinghub"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

    cursor = conn.cursor()

    # Find contracts with 0 IV coverage
    cursor.execute("""
        SELECT symbol, strike, "right", expiration, bar_interval,
               COUNT(*) as total_bars,
               COUNT(implied_volatility) as bars_with_iv
        FROM options_data
        GROUP BY symbol, strike, "right", expiration, bar_interval
        HAVING COUNT(implied_volatility) = 0
    """)

    contracts = cursor.fetchall()

    print("=" * 100)
    print("CONTRACTS WITH 0% IV COVERAGE (need re-fetch)")
    print("=" * 100)

    if not contracts:
        print("\n✓ All contracts have IV data!")
    else:
        for symbol, strike, right, exp, interval, total, with_iv in contracts:
            print(f"{symbol} {strike}{right} exp={exp}, interval={interval}: {total} bars, 0 IV")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_no_iv()
