"""
Fix market_data table constraint to include bar_interval

This script:
1. Drops the old UNIQUE constraint on (symbol, date)
2. Creates a new UNIQUE constraint on (symbol, date, bar_interval)
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


def fix_constraint():
    """Fix the unique constraint to include bar_interval"""
    try:
        # Connect to database
        conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})
        cursor = conn.cursor()

        print("Fixing market_data table constraint...")
        print("=" * 60)

        # Check current constraints
        cursor.execute("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'market_data'::regclass
        """)
        constraints = cursor.fetchall()
        print("\nCurrent constraints:")
        for constraint_name, constraint_type in constraints:
            print(f"  - {constraint_name} (type: {constraint_type})")

        # Drop the old unique constraint if it exists
        print("\n1. Dropping old UNIQUE constraint on (symbol, date)...")
        try:
            cursor.execute("""
                ALTER TABLE market_data
                DROP CONSTRAINT IF EXISTS market_data_symbol_date_key
            """)
            print("   ✓ Old constraint dropped (if existed)")
        except Exception as e:
            print(f"   ⚠️  Could not drop constraint: {e}")

        # Create new unique constraint on (symbol, date, bar_interval)
        print("\n2. Creating new UNIQUE constraint on (symbol, date, bar_interval)...")
        try:
            cursor.execute("""
                ALTER TABLE market_data
                ADD CONSTRAINT market_data_symbol_date_interval_key
                UNIQUE (symbol, date, bar_interval)
            """)
            print("   ✓ New constraint created")
        except Exception as e:
            print(f"   ⚠️  Constraint may already exist: {e}")

        # Commit changes
        conn.commit()

        # Verify the fix
        cursor.execute("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'market_data'::regclass
        """)
        constraints = cursor.fetchall()
        print("\nUpdated constraints:")
        for constraint_name, constraint_type in constraints:
            print(f"  - {constraint_name} (type: {constraint_type})")

        print("\n" + "=" * 60)
        print("✅ Constraint fix completed successfully!")
        print("=" * 60)

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Error fixing constraint: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = fix_constraint()
    sys.exit(0 if success else 1)
