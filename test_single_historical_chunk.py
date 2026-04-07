"""Test a SINGLE historical chunk fetch to see if it works"""

import sys
import os
import logging

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataService, IBKR_CONFIG
import pandas as pd

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_historical_chunk_2000_2010():
    """Test fetching historical chunk: 2000-2010"""
    print("\n" + "="*80)
    print("TEST: Historical Chunk 2000-11-08 to 2010-11-06")
    print("="*80)

    service = IBKRDataService()

    # Calculate period
    start_date = '2000-11-08'
    end_date = '2010-11-06'

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    time_span_days = (end_dt - start_dt).days

    # Add 20% buffer
    buffer_days = int(time_span_days * 0.2)
    total_days_needed = time_span_days + buffer_days

    # Determine period (should be 10 Y)
    if total_days_needed <= 2250:
        period = "5 Y"
    elif total_days_needed <= 4400:
        period = "10 Y"
    else:
        period = "20 Y"

    print(f"Time span: {time_span_days} days")
    print(f"Buffer: {buffer_days} days")
    print(f"Total needed: {total_days_needed} days")
    print(f"Calculated period: {period}")

    # Format end_date for IBKR API
    chunk_end_dt = pd.to_datetime(end_date)
    ibkr_end_date = chunk_end_dt.strftime("%Y%m%d 23:59:59")
    print(f"IBKR end_date: {ibkr_end_date}")

    print(f"\nAttempting fetch...")
    print(f"  Symbol: SPY")
    print(f"  Period: {period}")
    print(f"  End date: {ibkr_end_date}")
    print(f"  Client ID: 100")

    # Try to fetch
    result = service.fetch_and_store_data('SPY', period, end_date=ibkr_end_date, client_id=100)

    print(f"\nFetch result: {result}")

    if result:
        # Check what got saved to database
        df = service.get_data_from_db('SPY', '2000-01-01', '2011-01-01')
        print(f"\nDatabase check for 2000-2010:")
        print(f"  Records: {len(df)}")
        if not df.empty:
            print(f"  Date range: {df.index.min()} to {df.index.max()}")
    else:
        print("\n❌ Fetch FAILED")

    return result

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SINGLE HISTORICAL CHUNK TEST")
    print("="*80)
    print(f"IBKR Config: {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}")
    print("="*80)

    try:
        test_historical_chunk_2000_2010()

        print("\n" + "="*80)
        print("TEST COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
