"""
Migrate market_data.date column from DATE to TIMESTAMP

This is CRITICAL for intraday bar support (30 mins, 1 hour, etc.)
- DATE type: Only stores date (2025-12-01), time is lost
- TIMESTAMP type: Stores both date and time (2025-12-01 09:30:00)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'services', '.env')
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


def migrate_to_timestamp():
    """Change date column from DATE to TIMESTAMP"""
    try:
        conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        cursor = conn.cursor()

        print("="*80)
        print("Migrating market_data.date from DATE to TIMESTAMP")
        print("="*80)

        # Check current type
        cursor.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data' AND column_name = 'date'
        """)
        current_type = cursor.fetchone()[0]
        print(f"\nCurrent date column type: {current_type}")

        if current_type == 'timestamp without time zone':
            print("✓ Column is already TIMESTAMP - no migration needed")
            conn.close()
            return True

        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM market_data")
        record_count = cursor.fetchone()[0]
        print(f"Existing records: {record_count:,}")

        # Show sample data before migration
        cursor.execute("""
            SELECT symbol, date, bar_interval
            FROM market_data
            ORDER BY date DESC
            LIMIT 5
        """)
        print("\nSample data BEFORE migration:")
        print(f"{'Symbol':<10} {'Date':<25} {'Interval'}")
        print("-"*50)
        for row in cursor.fetchall():
            print(f"{row[0]:<10} {str(row[1]):<25} {row[2]}")

        # Perform migration
        print("\n1. Converting DATE to TIMESTAMP...")
        print("   Note: Existing dates will be converted to timestamps at 00:00:00")

        cursor.execute("""
            ALTER TABLE market_data
            ALTER COLUMN date TYPE TIMESTAMP USING date::timestamp
        """)

        print("   ✓ Column type changed to TIMESTAMP")

        # Update indexes if needed
        print("\n2. Checking indexes...")
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'market_data'
        """)
        indexes = cursor.fetchall()
        for idx_name, idx_def in indexes:
            print(f"   - {idx_name}")

        # Commit changes
        conn.commit()
        print("\n3. ✓ Migration committed successfully")

        # Verify the change
        cursor.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data' AND column_name = 'date'
        """)
        new_type = cursor.fetchone()[0]
        print(f"\n4. Verified new type: {new_type}")

        # Show sample data after migration
        cursor.execute("""
            SELECT symbol, date, bar_interval
            FROM market_data
            ORDER BY date DESC
            LIMIT 5
        """)
        print("\nSample data AFTER migration:")
        print(f"{'Symbol':<10} {'Date':<25} {'Interval'}")
        print("-"*50)
        for row in cursor.fetchall():
            print(f"{row[0]:<10} {str(row[1]):<25} {row[2]}")

        print("\n" + "="*80)
        print("✅ Migration completed successfully!")
        print("="*80)
        print("\nIMPORTANT: Existing daily bars now have timestamps at 00:00:00")
        print("           New intraday data will store with proper timestamps")
        print("           (e.g., 2025-12-01 09:30:00, 2025-12-01 10:00:00, etc.)")
        print("="*80)

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_to_timestamp()
    sys.exit(0 if success else 1)
