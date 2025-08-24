"""Setup script for IBKR integration in TradingHub"""

import os
import sys
import subprocess
from pathlib import Path

def print_step(step_num, description):
    print(f"\n{'='*50}")
    print(f"Step {step_num}: {description}")
    print(f"{'='*50}")

def main():
    print("TradingHub IBKR Integration Setup")
    print("This script will help you set up the IBKR integration")
    
    # Step 1: Check Python environment
    print_step(1, "Checking Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Step 2: Install dependencies
    print_step(2, "Installing Dependencies")
    print("Installing ibapi package...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "ibapi==9.81.1.post1"], check=True)
        print("✓ ibapi installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing ibapi: {e}")
        return False
    
    # Step 3: Initialize database
    print_step(3, "Initializing Database")
    try:
        # Add backend to path and run database initialization
        backend_path = os.path.join(os.getcwd(), "backend")
        sys.path.insert(0, backend_path)
        
        from backend.init_all_db import main as init_db
        if init_db():
            print("✓ Database tables created successfully")
        else:
            print("✗ Database initialization failed")
            return False
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        print("Please ensure PostgreSQL is running and .env file is configured")
        return False
    
    # Step 4: Check environment configuration
    print_step(4, "Environment Configuration")
    env_example_path = "backend/services/.env.example"
    env_path = "backend/services/.env"
    
    if os.path.exists(env_path):
        print("✓ .env file found")
    else:
        print(f"✗ .env file not found at {env_path}")
        print(f"Please copy {env_example_path} to {env_path} and configure it")
        return False
    
    # Step 5: Test IBKR connection (optional)
    print_step(5, "IBKR Connection Test (Optional)")
    print("To test IBKR connection:")
    print("1. Start TWS or IB Gateway")
    print("2. Configure API settings in TWS/Gateway:")
    print("   - Enable API connections")
    print("   - Set socket port (default: 7496 for TWS, 4002 for Gateway)")
    print("   - Add 127.0.0.1 to trusted IPs")
    print("3. Test connection using: python backend/routes/market_data.py (test endpoint)")
    
    # Step 6: Usage instructions
    print_step(6, "Usage Instructions")
    print("Integration complete! Here's how to use it:")
    print("\n1. API Endpoints available:")
    print("   - POST /api/market-data/refresh/<symbol> - Refresh data for a symbol")
    print("   - GET /api/market-data/status/<symbol> - Check data status")
    print("   - GET /api/market-data/test-connection - Test IBKR connection")
    print("   - GET /api/market-data/available-symbols - List available symbols")
    
    print("\n2. Data flow:")
    print("   - Database checked first for requested date range")
    print("   - If data missing, IBKR API fetches and stores data")
    print("   - CSV fallback available if IBKR fails")
    
    print("\n3. Supported symbols:")
    print("   - SPY (SPDR S&P 500 ETF)")
    print("   - VIX (CBOE Volatility Index)")
    print("   - More symbols can be added easily")
    
    print("\n✓ IBKR Integration setup complete!")
    print("Start the Flask server with: python backend/simple_app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n✗ Setup failed. Please check the errors above and try again.")
        sys.exit(1)
    else:
        print("\n✓ Setup completed successfully!")