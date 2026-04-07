"""Test script to diagnose market data loading issues"""

import sys
import os
from datetime import datetime, timedelta

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import ibkr_service

def test_database_query():
    """Test database query directly"""
    print("=" * 60)
    print("Testing Database Connection and Data Availability")
    print("=" * 60)

    # Test with a date range that should be in the database
    start_date = "2020-01-01"
    end_date = "2025-09-20"  # Before the last available date

    print(f"\nTest 1: Query date range {start_date} to {end_date}")
    print("-" * 60)

    try:
        df = ibkr_service.get_data_from_db("SPY", start_date, end_date)
        if not df.empty:
            print(f"✓ SUCCESS: Retrieved {len(df)} records")
            print(f"  Date range: {df.index.min()} to {df.index.max()}")
        else:
            print("✗ FAIL: Database query returned empty DataFrame")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")

    # Test with current date range (should show the gap)
    yesterday = datetime.now() - timedelta(days=1)
    end_date_current = yesterday.strftime("%Y-%m-%d")
    start_date_current = (datetime.now() - timedelta(days=5*365)).strftime("%Y-%m-%d")

    print(f"\nTest 2: Query current default range {start_date_current} to {end_date_current}")
    print("-" * 60)

    try:
        df = ibkr_service.get_data_from_db("SPY", start_date_current, end_date_current)
        if not df.empty:
            print(f"✓ Partial SUCCESS: Retrieved {len(df)} records")
            print(f"  Date range: {df.index.min()} to {df.index.max()}")

            # Check for gap
            end_dt = datetime.strptime(end_date_current, "%Y-%m-%d")
            db_end = df.index.max()
            gap_days = (end_dt - db_end).days

            if gap_days > 5:
                print(f"  ⚠ WARNING: Data gap of {gap_days} days detected")
                print(f"  Missing data from {db_end.strftime('%Y-%m-%d')} to {end_date_current}")
                print(f"  This is why IBKR connection is being attempted!")
            else:
                print(f"  ✓ Coverage is complete (gap: {gap_days} days)")
        else:
            print("✗ FAIL: Database query returned empty DataFrame")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    print("The database has data but it's outdated.")
    print("The system tries to fetch missing data from IBKR, but TWS is not running.")
    print("\nSOLUTIONS:")
    print("1. Run simulations with dates before 2025-09-22 (use date range in frontend)")
    print("2. OR start TWS/IB Gateway to fetch updated data")
    print("3. OR use a CSV file with updated data if available")
    print("=" * 60)

if __name__ == "__main__":
    test_database_query()
