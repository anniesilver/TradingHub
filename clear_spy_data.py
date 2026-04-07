"""Clear SPY data from database to force fresh fetch"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "backend", "services", ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# Database configuration
DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}

def clear_spy_data():
    """Delete all SPY data from market_data table"""
    try:
        conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        cursor = conn.cursor()

        # Check how much data exists
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM market_data WHERE symbol = 'SPY'")
        count, min_date, max_date = cursor.fetchone()

        print(f"\nCurrent SPY data in database:")
        print(f"  Records: {count}")
        print(f"  Date range: {min_date} to {max_date}")

        if count > 0:
            # Delete SPY data
            cursor.execute("DELETE FROM market_data WHERE symbol = 'SPY'")
            conn.commit()
            print(f"\n✅ Deleted {count} SPY records from database")
            print("Now run your simulation - it will fetch fresh data from IBKR in chunks")
        else:
            print("\n✅ No SPY data found in database")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("This will delete all SPY market data from the database")
    print("The data will be re-fetched from IBKR when you run the next simulation\n")

    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        clear_spy_data()
    else:
        print("Cancelled")
