"""
Database migration script to add bar_interval support to market_data table.

This migration:
1. Adds bar_interval column with default '1 day' (backward compatible)
2. Creates composite index on (symbol, bar_interval, date) for performance
3. Maintains backward compatibility with existing queries

Usage:
    python backend/migrate_market_data_for_intervals.py
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'services', '.env'))

def get_db_connection():
    """Create database connection from environment variables"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'tradinghub'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

def migrate():
    """Run the migration"""
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Starting migration: Adding bar_interval column to market_data table...")

        # Step 1: Check if column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='market_data' AND column_name='bar_interval';
        """)

        if cursor.fetchone():
            print("✓ Column 'bar_interval' already exists. Skipping column addition.")
        else:
            # Add bar_interval column with default '1 day'
            print("Adding bar_interval column...")
            cursor.execute("""
                ALTER TABLE market_data
                ADD COLUMN bar_interval VARCHAR(20) DEFAULT '1 day' NOT NULL;
            """)
            print("✓ Column 'bar_interval' added successfully with default '1 day'")

        # Step 2: Create composite index if it doesn't exist
        print("Creating composite index on (symbol, bar_interval, date)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_data_symbol_interval_date
            ON market_data (symbol, bar_interval, date DESC);
        """)
        print("✓ Composite index created successfully")

        # Step 3: Update statistics for query planner
        print("Analyzing table for query optimization...")
        cursor.execute("ANALYZE market_data;")
        print("✓ Table statistics updated")

        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("   - bar_interval column added with default '1 day'")
        print("   - Composite index created for performance")
        print("   - Existing queries will continue to work unchanged")

        # Show sample data
        cursor.execute("""
            SELECT symbol, bar_interval, date, open, close
            FROM market_data
            LIMIT 5;
        """)
        print("\nSample data after migration:")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]} | {row[1]} | {row[2]} | Open: ${row[3]:.2f} | Close: ${row[4]:.2f}")
        else:
            print("  (No data in market_data table yet)")

    except psycopg2.Error as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def rollback():
    """Rollback the migration (optional - for development)"""
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Rolling back migration...")

        # Drop index
        cursor.execute("DROP INDEX IF EXISTS idx_market_data_symbol_interval_date;")
        print("✓ Index dropped")

        # Drop column (WARNING: This will delete data!)
        cursor.execute("ALTER TABLE market_data DROP COLUMN IF EXISTS bar_interval;")
        print("✓ Column dropped")

        conn.commit()
        print("✅ Rollback completed")

    except psycopg2.Error as e:
        print(f"❌ Rollback failed: {e}")
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        confirm = input("⚠️  WARNING: This will DROP the bar_interval column and all interval data. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            rollback()
        else:
            print("Rollback cancelled")
    else:
        migrate()
