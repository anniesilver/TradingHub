"""Backfill missing IV values in database using forward-fill"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def backfill_iv():
    """Forward-fill missing IV values in options_data table"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Get all option contracts with missing IV
        cursor.execute("""
            SELECT DISTINCT symbol, strike, "right", expiration, bar_interval
            FROM options_data
            WHERE implied_volatility IS NULL
        """)

        contracts = cursor.fetchall()

        if not contracts:
            print("✓ No missing IV values found!")
            return

        print(f"Found {len(contracts)} contracts with missing IV values")
        print("=" * 80)

        total_filled = 0

        for symbol, strike, right, expiration, interval in contracts:
            print(f"\nProcessing: {symbol} {strike}{right} exp={expiration}, interval={interval}")

            # Get all rows for this contract, ordered by date
            cursor.execute("""
                SELECT id, date, implied_volatility
                FROM options_data
                WHERE symbol = %s AND strike = %s AND "right" = %s
                    AND expiration = %s AND bar_interval = %s
                ORDER BY date ASC
            """, (symbol, strike, right, expiration, interval))

            rows = cursor.fetchall()

            # Forward-fill missing IV values
            last_known_iv = None
            forward_updates = []

            for row_id, date, iv in rows:
                if iv is not None:
                    last_known_iv = iv
                elif last_known_iv is not None:
                    # Missing IV but we have a previous value - forward fill
                    forward_updates.append((last_known_iv, row_id))

            # Backward-fill from the first known IV (for NULLs at beginning)
            first_known_iv = None
            backward_updates = []

            for row_id, date, iv in rows:
                if iv is not None:
                    first_known_iv = iv
                    break  # Found first known IV

            if first_known_iv is not None:
                for row_id, date, iv in rows:
                    if iv is None and row_id not in [u[1] for u in forward_updates]:
                        # NULL at beginning, not already forward-filled
                        backward_updates.append((first_known_iv, row_id))

            total_updates = forward_updates + backward_updates

            if total_updates:
                # Batch update
                cursor.executemany("""
                    UPDATE options_data
                    SET implied_volatility = %s
                    WHERE id = %s
                """, total_updates)

                conn.commit()
                total_filled += len(total_updates)
                print(f"  Forward-filled: {len(forward_updates)}, Backward-filled: {len(backward_updates)}")
            else:
                print(f"  No IV values found to fill with")

        print("\n" + "=" * 80)
        print(f"✓ Backfill complete! Filled {total_filled} missing IV values")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM options_data WHERE implied_volatility IS NULL")
        remaining_nulls = cursor.fetchone()[0]
        print(f"  Remaining NULL IV values: {remaining_nulls}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    backfill_iv()
