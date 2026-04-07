"""Debug chunked data fetching with detailed logging"""

import sys
import os
import logging

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

# Set up detailed logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chunking_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_chunk_planning():
    """Test how chunks are planned for 2000-2025 range"""
    import pandas as pd
    from datetime import timedelta

    start_date = '2000-11-08'
    end_date = '2025-12-08'

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    total_days = (end_dt - start_dt).days

    logger.info(f"="*80)
    logger.info(f"Testing chunk planning for {start_date} to {end_date}")
    logger.info(f"Total days: {total_days}")
    logger.info(f"="*80)

    chunks = []
    current_start = start_dt

    while current_start < end_dt:
        # Calculate chunk end (10 years from start or end_date, whichever is earlier)
        chunk_end = min(current_start + timedelta(days=3650), end_dt)  # 10 years

        chunk_start_str = current_start.strftime('%Y-%m-%d')
        chunk_end_str = chunk_end.strftime('%Y-%m-%d')

        chunks.append((chunk_start_str, chunk_end_str))
        logger.info(f"Chunk {len(chunks)}: {chunk_start_str} to {chunk_end_str}")

        # Move to next chunk (add 1 day to avoid overlap)
        current_start = chunk_end + timedelta(days=1)

    logger.info(f"Total chunks planned: {len(chunks)}")
    return chunks

def test_actual_chunking():
    """Test actual chunked data fetch with detailed logging"""
    from market_data import MarketData

    logger.info(f"\n" + "="*80)
    logger.info(f"Testing ACTUAL chunked fetch for SPY 2000-2025")
    logger.info(f"="*80)

    try:
        market_data = MarketData('SPY')
        result = market_data._fetch_data_in_chunks('SPY', '2000-11-08', '2025-12-08')
        logger.info(f"Chunked fetch result: {result}")

        # Check database
        from ibkr_data_service import ibkr_service
        df = ibkr_service.get_data_from_db('SPY', '2000-11-08', '2025-12-08')
        logger.info(f"Database check after chunking:")
        logger.info(f"  Records: {len(df)}")
        if not df.empty:
            logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")

        return result

    except Exception as e:
        logger.error(f"Error during chunked fetch: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_database_before():
    """Check what's in the database before we start"""
    from ibkr_data_service import ibkr_service

    logger.info(f"\n" + "="*80)
    logger.info(f"Database check BEFORE chunked fetch")
    logger.info(f"="*80)

    df = ibkr_service.get_data_from_db('SPY', '2000-01-01', '2025-12-31')
    logger.info(f"SPY records in database: {len(df)}")
    if not df.empty:
        logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    else:
        logger.info("No SPY data in database")

if __name__ == "__main__":
    logger.info("\n" + "="*80)
    logger.info("CHUNKED DATA FETCHING DEBUG TEST")
    logger.info("="*80)

    # Step 1: Check current database state
    check_database_before()

    # Step 2: Plan chunks (no API calls)
    chunks = test_chunk_planning()

    # Step 3: Actually fetch chunks
    # Uncomment when ready to test actual fetching
    # test_actual_chunking()

    logger.info("\n" + "="*80)
    logger.info("DEBUG TEST COMPLETED - Check chunking_debug.log for details")
    logger.info("="*80)
