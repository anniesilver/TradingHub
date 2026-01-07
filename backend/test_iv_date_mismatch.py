"""Test IV date range mismatch by deleting and re-fetching a contract"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add services path
services_path = os.path.join(os.path.dirname(__file__), 'services')
if services_path not in sys.path:
    sys.path.insert(0, services_path)

from ibkr_option_service import IBKROptionService

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def delete_test_contract():
    """Delete SPY 680C exp=2026-02-20 for testing"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Delete SPY 680C
        cursor.execute("""
            DELETE FROM options_data
            WHERE symbol = 'SPY'
                AND strike = 680.0
                AND "right" = 'C'
                AND expiration = '2026-02-20'
                AND bar_interval = '30 mins'
        """)

        deleted = cursor.rowcount
        conn.commit()

        print(f"✓ Deleted {deleted} bars of SPY 680C exp=2026-02-20 for testing")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error deleting: {e}")
        return False

def fetch_and_analyze():
    """Fetch SPY 680C and analyze date ranges"""
    print("\n" + "=" * 80)
    print("TESTING IV DATE RANGE MISMATCH")
    print("=" * 80)

    try:
        service = IBKROptionService()

        # Fetch SPY 680C exp=2026-02-20
        symbol = 'SPY'
        strike = 680.0
        right = 'C'
        expiration = '20260220'
        start_date = '2025-12-07'
        end_date = '2026-01-06'
        bar_interval = '30 mins'

        print(f"\nFetching: {symbol} {strike}{right} exp={expiration}")
        print(f"Requested range: {start_date} to {end_date}")
        print(f"Interval: {bar_interval}")
        print("\nWatch the logs for:")
        print("  - TRADES date range vs IV date range")
        print("  - BAR COUNT MISMATCH warning")
        print("  - Forward-fill statistics")
        print("\n" + "=" * 80 + "\n")

        df = service.get_option_data(
            symbol=symbol,
            strike=strike,
            right=right,
            expiration=expiration,
            start_date=start_date,
            end_date=end_date,
            bar_interval=bar_interval
        )

        if df is not None and len(df) > 0:
            print("\n" + "=" * 80)
            print("FETCH RESULTS")
            print("=" * 80)
            print(f"\nTotal bars fetched: {len(df)}")
            print(f"Date range in database: {df.index.min()} to {df.index.max()}")

            if 'ImpliedVolatility' in df.columns:
                iv_count = df['ImpliedVolatility'].notna().sum()
                null_count = df['ImpliedVolatility'].isna().sum()
                print(f"\nIV coverage:")
                print(f"  Bars with IV: {iv_count}/{len(df)} ({iv_count/len(df)*100:.1f}%)")
                print(f"  Bars with NULL IV: {null_count}")

                if null_count > 0:
                    # Show which bars have NULL IV
                    null_bars = df[df['ImpliedVolatility'].isna()]
                    print(f"\n  NULL IV date range: {null_bars.index.min()} to {null_bars.index.max()}")
                    print(f"  First 5 NULL bars:")
                    for idx in null_bars.index[:5]:
                        print(f"    {idx}")

                    # Check if NULLs are at beginning, middle, or end
                    first_null = df[df['ImpliedVolatility'].isna()].index.min()
                    last_null = df[df['ImpliedVolatility'].isna()].index.max()
                    first_valid = df[df['ImpliedVolatility'].notna()].index.min()
                    last_valid = df[df['ImpliedVolatility'].notna()].index.max()

                    print(f"\n  Analysis:")
                    if last_null < first_valid:
                        print(f"    NULLs are at BEGINNING (before IV data starts)")
                        print(f"    This means IBKR returned TRADES data earlier than IV data")
                    elif first_null > last_valid:
                        print(f"    NULLs are at END (after IV data ends)")
                        print(f"    This means IBKR returned TRADES data later than IV data")
                    else:
                        print(f"    NULLs are SCATTERED (gaps in IV data)")
                        print(f"    This means IV data has intermittent missing bars")

            return True
        else:
            print("❌ No data returned")
            return False

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("IV DATE RANGE MISMATCH TEST")
    print("=" * 80)
    print("\nThis test will:")
    print("1. Delete SPY 680C exp=2026-02-20 from database")
    print("2. Re-fetch from IBKR")
    print("3. Analyze if TRADES and IV have different date ranges")
    print("\nIMPORTANT: Make sure IBKR TWS/Gateway is running!")
    print("=" * 80)

    input("\nPress Enter to continue...")

    # Step 1: Delete
    if not delete_test_contract():
        sys.exit(1)

    # Step 2: Fetch and analyze
    print("\nWaiting 2 seconds before fetching...")
    import time
    time.sleep(2)

    fetch_and_analyze()
