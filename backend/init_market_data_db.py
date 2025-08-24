"""Initialize market data database table"""

import sys
import os

# Add the backend directory to the path so we can import our services
sys.path.insert(0, os.path.dirname(__file__))

from services.ibkr_data_service import IBKRDataService

def main():
    """Initialize the market data database table"""
    try:
        service = IBKRDataService()
        service.create_market_data_table()
        print("Market data table created successfully!")
        return True
    except Exception as e:
        print(f"Error creating market data table: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)