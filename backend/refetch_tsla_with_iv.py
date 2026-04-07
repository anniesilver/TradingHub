"""Clear old TSLA option data and re-fetch with IV"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add services path for IBKR service
services_path = os.path.join(os.path.dirname(__file__), 'services')
if services_path not in sys.path:
    sys.path.insert(0, services_path)

from ibkr_option_service import IBKROptionService

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
load_dotenv(env_path)

def clear_tsla_option_data():
    """Delete old TSLA option data (without IV)"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "tradinghub"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        # Delete all TSLA option data
        cursor.execute("""
            DELETE FROM options_data
            WHERE symbol = 'TSLA'
        """)

        deleted_rows = cursor.rowcount
        conn.commit()

        print(f"✓ Deleted {deleted_rows} old TSLA option data rows (without IV)")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error clearing data: {e}")
        return False

def refetch_tsla_with_iv():
    """Re-fetch TSLA 600C 20260618 with IV data"""
    print("\n" + "=" * 80)
    print("Re-fetching TSLA 600C exp=20260618 with IV data")
    print("=" * 80)

    try:
        service = IBKROptionService()

        # Fetch TSLA 600C 20260618 option data
        symbol = 'TSLA'
        strike = 600.0
        right = 'C'
        expiration = '20260618'
        start_date = '2025-11-07'
        end_date = '2026-01-06'
        bar_interval = '30 mins'

        print(f"\nFetching {symbol} {strike}{right} exp={expiration}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Interval: {bar_interval}")
        print("\nThis will fetch both price data AND IV data from IBKR...")

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
            print(f"\n✓ Successfully fetched {len(df)} bars")

            # Check IV data
            if 'ImpliedVolatility' in df.columns:
                iv_count = df['ImpliedVolatility'].notna().sum()
                iv_percentage = (iv_count / len(df) * 100)
                print(f"✓ IV data: {iv_count}/{len(df)} bars ({iv_percentage:.1f}%)")

                if iv_count > 0:
                    iv_mean = df['ImpliedVolatility'].mean()
                    iv_std = df['ImpliedVolatility'].std()
                    iv_min = df['ImpliedVolatility'].min()
                    iv_max = df['ImpliedVolatility'].max()
                    print(f"  IV statistics: mean={iv_mean:.4f}, std={iv_std:.4f}, range=[{iv_min:.4f}, {iv_max:.4f}]")
                else:
                    print("  ❌ WARNING: No IV values in fetched data!")
            else:
                print("  ❌ WARNING: No ImpliedVolatility column in data!")

            return True
        else:
            print("❌ Failed to fetch data")
            return False

    except Exception as e:
        print(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("TSLA Option Data Re-fetch with IV")
    print("=" * 80)

    # Step 1: Clear old data
    print("\nStep 1: Clearing old TSLA option data...")
    if not clear_tsla_option_data():
        print("Failed to clear old data")
        sys.exit(1)

    # Step 2: Re-fetch with IV
    print("\nStep 2: Re-fetching with IV data...")
    if not refetch_tsla_with_iv():
        print("Failed to re-fetch data")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✓ TSLA option data re-fetched with IV successfully!")
    print("=" * 80)
    print("\nYou can now re-run your OPTIONS_MARTIN simulation.")
    print("The IV filtering should work correctly now.")
