"""Test chunked data fetching for 20+ year date ranges"""

import sys
import os

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataService, IBKR_CONFIG
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_single_fetch():
    """Test single fetch (should work)"""
    print("\n" + "="*80)
    print("TEST 1: Single Fetch (current data, no end_date)")
    print("="*80)
    service = IBKRDataService()

    # This should work - current data with empty end_date
    result = service.fetch_and_store_data('SPY', '10 Y', end_date='')
    print(f"✅ Result: {result}")
    return result

def test_historical_chunk():
    """Test historical chunk with end_date"""
    print("\n" + "="*80)
    print("TEST 2: Historical Chunk (2000-2010 with end_date)")
    print("="*80)
    service = IBKRDataService()

    # This is what currently fails - historical end_date with keepUpToDate=True
    # After fix, this should work with keepUpToDate=False
    result = service.fetch_and_store_data('SPY', '10 Y', end_date='20101106 23:59:59', client_id=100)
    print(f"✅ Result: {result}")
    return result

def test_period_calculation():
    """Test period calculation logic"""
    print("\n" + "="*80)
    print("TEST 3: Period Calculation")
    print("="*80)

    # Need to import market_data module
    import pandas as pd
    from datetime import timedelta

    # Simulate the calculation
    test_cases = [
        ('2000-11-08', '2010-11-06', '10 Y'),  # 10-year chunk
        ('2010-11-07', '2020-11-04', '10 Y'),  # 10-year chunk
        ('2020-11-05', '2025-12-08', '5 Y'),   # 5-year chunk
    ]

    for start, end, expected in test_cases:
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        time_span_days = (end_dt - start_dt).days

        # NEW logic with 20% buffer and adjusted thresholds
        buffer_days = int(time_span_days * 0.2)
        total_days_needed = time_span_days + buffer_days

        # Determine period (NEW thresholds)
        if total_days_needed <= 2250:
            period = "5 Y"
        elif total_days_needed <= 4400:
            period = "10 Y"
        else:
            period = "20 Y"

        status = "✅" if period == expected else "❌"
        print(f"{status} {start} to {end}: {time_span_days} days + {buffer_days} buffer = {total_days_needed} total → {period} (expected {expected})")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CHUNKED DATA FETCHING TEST SUITE")
    print("="*80)
    print(f"IBKR Config: {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}, client_id={IBKR_CONFIG['client_id']}")

    try:
        # Test 3: Period calculation first (no API calls)
        test_period_calculation()

        # Test 1: Single fetch (should already work)
        # test_single_fetch()

        # Test 2: Historical chunk (this is what we're fixing)
        # test_historical_chunk()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
