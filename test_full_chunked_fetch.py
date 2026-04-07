"""Test FULL chunked data fetching for 2000-2025 range"""

import sys
import os
import logging

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataService, IBKR_CONFIG
import pandas as pd
from datetime import timedelta

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chunked_fetch_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def calculate_fetch_period(start_date: str, end_date: str) -> str:
    """Calculate appropriate IBKR period string from date range"""
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # Calculate time span in days
    time_span_days = (end_dt - start_dt).days

    # Add buffer (20% extra) to ensure coverage for weekends/holidays
    buffer_days = int(time_span_days * 0.2)
    total_days_needed = time_span_days + buffer_days

    # Convert to IBKR period format (using fixed thresholds)
    if total_days_needed <= 2250:  # ~5 years + buffer
        return "5 Y"
    elif total_days_needed <= 4400:  # ~10 years + buffer
        return "10 Y"
    else:
        return "20 Y"

def test_chunked_fetch():
    """Test fetching 2000-2025 in three chunks"""

    print("\n" + "="*80)
    print("FULL CHUNKED FETCH TEST: 2000-2025")
    print("="*80)

    start_date = '2000-11-08'
    end_date = '2025-12-08'
    symbol = 'SPY'

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # Plan chunks
    chunks = []
    current_start = start_dt

    while current_start < end_dt:
        chunk_end = min(current_start + timedelta(days=3650), end_dt)  # 10 years
        chunk_start_str = current_start.strftime('%Y-%m-%d')
        chunk_end_str = chunk_end.strftime('%Y-%m-%d')
        chunks.append((chunk_start_str, chunk_end_str))
        current_start = chunk_end + timedelta(days=1)

    print(f"\nPlanned {len(chunks)} chunks:")
    for i, (cs, ce) in enumerate(chunks, 1):
        period = calculate_fetch_period(cs, ce)
        print(f"  Chunk {i}: {cs} to {ce} (period: {period})")

    # Check database before
    print(f"\n" + "="*80)
    print("DATABASE CHECK - BEFORE FETCH")
    print("="*80)
    service = IBKRDataService()
    df_before = service.get_data_from_db(symbol, '2000-01-01', '2025-12-31')
    print(f"Records before: {len(df_before)}")
    if not df_before.empty:
        print(f"Date range: {df_before.index.min()} to {df_before.index.max()}")

    # Fetch each chunk
    print(f"\n" + "="*80)
    print("FETCHING CHUNKS")
    print("="*80)

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        print(f"\n{'='*80}")
        print(f"CHUNK {i+1}/{len(chunks)}: {chunk_start} to {chunk_end}")
        print(f"{'='*80}")

        # Calculate period
        period = calculate_fetch_period(chunk_start, chunk_end)
        print(f"Calculated period: {period}")

        # Format end_date for IBKR API with timezone
        # IBKR requires timezone - use US/Eastern for US stocks
        chunk_end_dt = pd.to_datetime(chunk_end)
        ibkr_end_date = chunk_end_dt.strftime("%Y%m%d 23:59:59 US/Eastern")
        print(f"IBKR end_date: {ibkr_end_date}")

        # Use unique client ID
        chunk_client_id = 100 + i
        print(f"Client ID: {chunk_client_id}")

        # Fetch this chunk
        print(f"\nAttempting to fetch...")
        try:
            result = service.fetch_and_store_data(
                symbol,
                period,
                end_date=ibkr_end_date,
                client_id=chunk_client_id
            )

            if result:
                print(f"✅ Chunk {i+1} fetch SUCCESS")

                # Check what got saved
                df_chunk = service.get_data_from_db(symbol, chunk_start, chunk_end)
                print(f"   Database records for this chunk: {len(df_chunk)}")
                if not df_chunk.empty:
                    print(f"   Date range: {df_chunk.index.min()} to {df_chunk.index.max()}")
            else:
                print(f"❌ Chunk {i+1} fetch FAILED (returned False)")
                return False

        except Exception as e:
            print(f"❌ Chunk {i+1} fetch EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Wait between chunks
        if i < len(chunks) - 1:
            print(f"\nWaiting 3 seconds before next chunk...")
            import time
            time.sleep(3)

    # Check database after
    print(f"\n" + "="*80)
    print("DATABASE CHECK - AFTER FETCH")
    print("="*80)
    df_after = service.get_data_from_db(symbol, '2000-01-01', '2025-12-31')
    print(f"Records after: {len(df_after)}")
    if not df_after.empty:
        print(f"Date range: {df_after.index.min()} to {df_after.index.max()}")

    print(f"\n" + "="*80)
    print(f"ALL {len(chunks)} CHUNKS FETCHED SUCCESSFULLY!")
    print("="*80)
    return True

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CHUNKED FETCH TEST SUITE")
    print("="*80)
    print(f"IBKR Config: {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}")
    print("IMPORTANT: Ensure TWS or IB Gateway is running!")
    print("="*80)

    try:
        test_chunked_fetch()
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
