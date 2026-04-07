"""Clear old option data to allow re-fetch with IV"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def clear_old_option_data():
    """Delete old option data for SPY 680C 20260220"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Delete old data
        cursor.execute("""
            DELETE FROM options_data
            WHERE symbol = 'SPY'
            AND strike = 680
            AND expiration = '2026-02-20'
        """)

        deleted_rows = cursor.rowcount
        conn.commit()

        print(f"✓ Deleted {deleted_rows} old option data rows (without IV)")
        print("  Ready to re-fetch with IV data")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    clear_old_option_data()
