"""Import VIX historical data from CSV into database"""

import csv
import os
import sys
from datetime import datetime

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


def import_vix_history():
    """Import VIX historical data from CSV file"""

    csv_path = os.path.join(os.path.dirname(__file__), "backend", "services", "VIX_History.csv")

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return False

    print(f"Reading VIX history from {csv_path}")

    # Connect to database
    try:
        conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        print("Connected to database successfully")
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False

    try:
        with conn.cursor() as cursor:
            # Read CSV file
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows_imported = 0
                rows_updated = 0

                for row in reader:
                    # Parse date from MM/DD/YYYY format
                    date_str = row['DATE']
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()

                    # Insert or update record
                    cursor.execute("""
                        INSERT INTO market_data (symbol, date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, date)
                        DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING (xmax = 0) AS inserted
                    """, (
                        'VIX',
                        date_obj,
                        float(row['OPEN']),
                        float(row['HIGH']),
                        float(row['LOW']),
                        float(row['CLOSE']),
                        0  # Volume not available in CSV
                    ))

                    # Check if it was an insert or update
                    result = cursor.fetchone()
                    if result and result[0]:
                        rows_imported += 1
                    else:
                        rows_updated += 1

                    # Commit every 1000 rows for performance
                    if (rows_imported + rows_updated) % 1000 == 0:
                        conn.commit()
                        print(f"Progress: {rows_imported + rows_updated} rows processed...")

            # Final commit
            conn.commit()

            print(f"\n{'='*60}")
            print(f"VIX Historical Data Import Complete")
            print(f"{'='*60}")
            print(f"Rows imported (new): {rows_imported}")
            print(f"Rows updated (existing): {rows_updated}")
            print(f"Total rows processed: {rows_imported + rows_updated}")
            print(f"{'='*60}\n")

            # Show data range
            cursor.execute("""
                SELECT MIN(date), MAX(date), COUNT(*)
                FROM market_data
                WHERE symbol = 'VIX'
            """)
            min_date, max_date, total_count = cursor.fetchone()
            print(f"VIX data in database:")
            print(f"  Date range: {min_date} to {max_date}")
            print(f"  Total records: {total_count}")

            return True

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Failed to import data: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("VIX Historical Data Importer")
    print("="*60)

    success = import_vix_history()

    if success:
        print("\nImport successful! VIX historical data is now in the database.")
        print("The system will now use database data first and only fetch missing data from IBKR.")
        sys.exit(0)
    else:
        print("\nImport failed. Please check the error messages above.")
        sys.exit(1)
