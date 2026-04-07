#!/usr/bin/env python3
"""
Test program to fetch historical data in chunks to overcome IBKR API limitations
"""

import sys
import os
from datetime import datetime, timedelta
import time
import logging

# Add backend services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

from ibkr_data_service import IBKRDataService, IBKRDataClient, IBKR_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_date_chunks(start_date_str: str, end_date_str: str, max_years: int = 10):
    """
    Split a date range into chunks of max_years each

    Args:
        start_date_str: Start date in 'YYYY-MM-DD' format
        end_date_str: End date in 'YYYY-MM-DD' format
        max_years: Maximum years per chunk (default: 10)

    Returns:
        List of (start_date, end_date, period_str) tuples
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    total_days = (end_date - start_date).days
    total_years = total_days / 365.25

    logger.info(f"Total date range: {start_date_str} to {end_date_str} ({total_years:.1f} years)")

    if total_years <= max_years:
        # Single chunk
        period_str = f"{int(total_years) + 1} Y"  # Add 1 to ensure we get all data
        return [(start_date_str, end_date_str, period_str)]

    # Multiple chunks needed
    chunks = []
    current_start = start_date

    while current_start < end_date:
        # Calculate chunk end date (max_years from current start)
        chunk_end = min(
            current_start + timedelta(days=max_years * 365),
            end_date
        )

        chunk_start_str = current_start.strftime('%Y-%m-%d')
        chunk_end_str = chunk_end.strftime('%Y-%m-%d')

        # Calculate period for this chunk
        chunk_years = (chunk_end - current_start).days / 365.25
        period_str = f"{int(chunk_years) + 1} Y"

        chunks.append((chunk_start_str, chunk_end_str, period_str))
        logger.info(f"Chunk: {chunk_start_str} to {chunk_end_str} ({period_str})")

        # Move to next chunk
        current_start = chunk_end + timedelta(days=1)

    return chunks


def fetch_data_in_chunks(symbol: str, start_date: str, end_date: str):
    """
    Fetch historical data in chunks and combine results

    Args:
        symbol: Trading symbol (e.g., 'SPY')
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        Combined data from all chunks
    """
    logger.info(f"Starting chunked data fetch for {symbol}")

    # Calculate chunks
    chunks = calculate_date_chunks(start_date, end_date, max_years=10)

    ibkr_service = IBKRDataService()
    all_data = []

    for i, (chunk_start, chunk_end, period) in enumerate(chunks):
        logger.info(f"Fetching chunk {i+1}/{len(chunks)}: {chunk_start} to {chunk_end} ({period})")

        try:
            # Connect to IBKR for this chunk
            client = IBKRDataClient(IBKR_CONFIG["client_id"] + i)  # Use different client ID for each chunk
            if not client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"]):
                logger.error(f"Failed to connect to IBKR for chunk {i+1}")
                continue

            # Fetch data for this chunk
            logger.info(f"Requesting {period} of data for {symbol}")
            chunk_data = client.fetch_historical_data(symbol, period)

            if chunk_data:
                logger.info(f"Chunk {i+1}: Received {len(chunk_data)} records")
                all_data.extend(chunk_data)

                # Save chunk to database
                ibkr_service.save_data_to_db(symbol, chunk_data)
                logger.info(f"Chunk {i+1}: Saved {len(chunk_data)} records to database")
            else:
                logger.warning(f"Chunk {i+1}: No data received")

            # Disconnect client
            client.disconnect_from_ibkr()

            # Wait between chunks to avoid rate limiting
            if i < len(chunks) - 1:  # Don't wait after last chunk
                logger.info("Waiting 5 seconds before next chunk...")
                time.sleep(5)

        except Exception as e:
            logger.error(f"Error fetching chunk {i+1}: {e}")
            continue

    logger.info(f"Completed chunked fetch: {len(all_data)} total records")
    return all_data


def test_chunked_fetch():
    """Test the chunked data fetching approach"""

    # Test case 1: Request data from 2000 to 2005 (should split into chunks)
    logger.info("="*60)
    logger.info("TEST CASE 1: Fetching SPY data from 2000-01-01 to 2005-12-31")
    logger.info("="*60)

    try:
        data = fetch_data_in_chunks('SPY', '2000-01-01', '2005-12-31')
        logger.info(f"Test 1 completed: {len(data)} records fetched")

        if data:
            # Show date range of fetched data
            dates = [item['date'] for item in data]
            logger.info(f"Data range: {min(dates)} to {max(dates)}")

        # Check what's in the database
        ibkr_service = IBKRDataService()
        db_data = ibkr_service.get_data_from_db('SPY', '2000-01-01', '2005-12-31')
        logger.info(f"Database now contains {len(db_data)} records for 2000-2005")

    except Exception as e:
        logger.error(f"Test 1 failed: {e}")

    logger.info("\n")

    # Test case 2: Check if we can now get 2000-2003 data
    logger.info("="*60)
    logger.info("TEST CASE 2: Checking if 2000-2003 data is now available")
    logger.info("="*60)

    try:
        ibkr_service = IBKRDataService()
        db_data = ibkr_service.get_data_from_db('SPY', '2000-01-01', '2003-12-31')

        if not db_data.empty:
            logger.info(f"SUCCESS! Found {len(db_data)} records for 2000-2003")
            logger.info(f"Date range: {db_data.index.min()} to {db_data.index.max()}")
        else:
            logger.warning("No data found for 2000-2003 period")

    except Exception as e:
        logger.error(f"Test 2 failed: {e}")


if __name__ == "__main__":
    logger.info("Starting chunked data fetch test...")
    test_chunked_fetch()
    logger.info("Test completed!")