"""
Migration script to create options_data table for storing historical option prices.

This table stores option price data with strike, right (call/put), and expiration,
supporting multiple contracts per underlying symbol.
"""

import os
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


def create_options_data_table():
    """Create options_data table with proper schema"""

    conn = psycopg2.connect(**{k: v for k, v in DB_CONFIG.items() if v is not None})

    try:
        with conn.cursor() as cursor:
            # Create options_data table
            print("Creating options_data table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS options_data (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    strike DECIMAL(10, 2) NOT NULL,
                    "right" CHAR(1) NOT NULL,
                    expiration DATE NOT NULL,
                    date TIMESTAMP NOT NULL,
                    "open" DECIMAL(10, 4) NOT NULL,
                    high DECIMAL(10, 4) NOT NULL,
                    low DECIMAL(10, 4) NOT NULL,
                    "close" DECIMAL(10, 4) NOT NULL,
                    volume BIGINT DEFAULT 0,
                    bar_interval VARCHAR(20) DEFAULT '1 day',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_option_bar
                        UNIQUE(symbol, strike, "right", expiration, date, bar_interval)
                )
            """)
            print("✓ options_data table created")

            # Create index for faster lookups
            print("Creating index on options_data...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_options_data_lookup
                ON options_data (symbol, strike, "right", expiration, date, bar_interval)
            """)
            print("✓ Index created")

            # Add constraint check for right column (must be 'C' or 'P')
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'check_option_right'
                    ) THEN
                        ALTER TABLE options_data
                        ADD CONSTRAINT check_option_right
                        CHECK ("right" IN ('C', 'P'));
                    END IF;
                END $$;
            """)
            print("✓ Check constraint added (right must be 'C' or 'P')")

            conn.commit()
            print("\n✅ Migration completed successfully!")

            # Display table info
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'options_data'
                ORDER BY ordinal_position
            """)

            print("\nTable Schema:")
            print(f"{'Column':<20} {'Type':<25} {'Nullable':<10}")
            print("-" * 55)
            for row in cursor.fetchall():
                col_name, data_type, max_len, nullable = row
                type_str = f"{data_type}" + (f"({max_len})" if max_len else "")
                print(f"{col_name:<20} {type_str:<25} {nullable:<10}")

            # Display constraints
            cursor.execute("""
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'options_data'::regclass
            """)

            print("\nConstraints:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 80)
    print("OPTIONS_DATA TABLE MIGRATION")
    print("=" * 80)
    print()

    create_options_data_table()

    print("\n" + "=" * 80)
    print("Next Steps:")
    print("  1. Verify table with: psql -d tradinghub -c '\\d options_data'")
    print("  2. Create IBKR option service: backend/services/ibkr_option_service.py")
    print("  3. Test option data fetching from IBKR")
    print("=" * 80)
