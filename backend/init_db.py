import os
import sys
from services.strategy_service import init_database

if __name__ == "__main__":
    # Initialize the database tables
    print("Initializing database tables...")
    success = init_database()
    
    if success:
        print("Database initialization complete!")
    else:
        print("Database initialization failed.")
        sys.exit(1) 