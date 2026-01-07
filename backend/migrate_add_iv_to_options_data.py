"""
Database migration script to add implied_volatility column to options_data table.

This migration adds the implied_volatility (IV) column to store historical implied
volatility data alongside option price data (OHLCV). IV is a critical metric for
options trading strategies that helps identify optimal entry/exit points.

Usage:
    python backend/migrate_add_iv_to_options_data.py

Prerequisites:
    - options_data table must exist (created by migrate_create_options_data.py)
    - Database credentials configured in backend/services/.env
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)


def get_db_connection():
    """Create database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "tradinghub"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def check_column_exists(cursor, table_name, column_name):
    """Check if column already exists in table"""
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        );
    """,
        (table_name, column_name),
    )
    return cursor.fetchone()[0]


def add_iv_column_migration():
    """Add implied_volatility column to options_data table"""
    print("=" * 80)
    print("DATABASE MIGRATION: Add implied_volatility to options_data table")
    print("=" * 80)

    conn = None
    try:
        # Connect to database
        print("\n1. Connecting to database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"   Connected to database: {os.getenv('DB_NAME', 'tradinghub')}")

        # Check if options_data table exists
        print("\n2. Checking if options_data table exists...")
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'options_data'
            );
        """
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            print("   ERROR: options_data table does not exist!")
            print("   Please run migrate_create_options_data.py first")
            return False

        print("   Table exists: options_data")

        # Check if implied_volatility column already exists
        print("\n3. Checking if implied_volatility column already exists...")
        column_exists = check_column_exists(cursor, "options_data", "implied_volatility")

        if column_exists:
            print("   Column already exists: implied_volatility")
            print("   Migration already applied, skipping...")
            return True

        print("   Column does not exist, proceeding with migration...")

        # Add implied_volatility column
        print("\n4. Adding implied_volatility column...")
        cursor.execute(
            """
            ALTER TABLE options_data
            ADD COLUMN implied_volatility DECIMAL(10, 6);
        """
        )
        print("   Column added: implied_volatility DECIMAL(10, 6)")

        # Create index on IV for efficient queries
        print("\n5. Creating index on implied_volatility...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_options_iv
            ON options_data (implied_volatility);
        """
        )
        print("   Index created: idx_options_iv")

        # Commit changes
        conn.commit()
        print("\n6. Committing changes to database...")
        print("   Changes committed successfully")

        # Verify migration
        print("\n7. Verifying migration...")
        cursor.execute(
            """
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'options_data' AND column_name = 'implied_volatility';
        """
        )
        column_info = cursor.fetchone()

        if column_info:
            col_name, data_type, max_length, precision, scale = column_info
            print(f"   Column verified: {col_name}")
            print(f"   Data type: {data_type}")
            print(f"   Precision: {precision}, Scale: {scale}")
        else:
            print("   ERROR: Failed to verify column creation")
            return False

        # Display updated table schema
        print("\n8. Updated options_data table schema:")
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'options_data'
            ORDER BY ordinal_position;
        """
        )
        columns = cursor.fetchall()

        print("\n   Column Name              | Data Type        | Nullable")
        print("   " + "-" * 65)
        for col_name, data_type, nullable in columns:
            print(f"   {col_name:24} | {data_type:16} | {nullable}")

        cursor.close()

        print("\n" + "=" * 80)
        print("MIGRATION SUCCESSFUL")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Update ibkr_option_service.py to fetch IV data from IBKR")
        print("  2. Modify OPTIONS_MARTIN strategy to use IV for entry filtering")
        print("  3. Test IV fetching with: python test_with_real_data.py")

        return True

    except psycopg2.Error as e:
        print(f"\nDATABASE ERROR: {e}")
        if conn:
            conn.rollback()
        return False

    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    print("\n")
    success = add_iv_column_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. See errors above.")
        sys.exit(1)
