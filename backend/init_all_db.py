"""Initialize all database tables for TradingHub"""

import sys
import os

# Add the backend directory to the path
backend_path = os.path.dirname(__file__)
sys.path.insert(0, backend_path)

def main():
    """Initialize all database tables"""
    print("Initializing TradingHub database...")
    
    try:
        # Initialize Flask-SQLAlchemy tables (users, products, etc.)
        print("\n1. Creating Flask-SQLAlchemy tables...")
        from app_factory import create_app
        
        app = create_app()
        with app.app_context():
            from app_factory import db
            # Import models to register them
            from models.user import User
            from models.product import Product, UserProduct, PerformanceRecord
            
            db.create_all()
            print("✓ Flask-SQLAlchemy tables created successfully")
    
    except Exception as e:
        print(f"✗ Error creating Flask-SQLAlchemy tables: {str(e)}")
        return False
    
    try:
        # Initialize strategy simulation tables (from strategy_service)
        print("\n2. Creating strategy simulation tables...")
        from services.strategy_service import init_database
        
        if init_database():
            print("✓ Strategy simulation tables created successfully")
        else:
            print("✗ Strategy simulation table creation failed")
            return False
    
    except Exception as e:
        print(f"✗ Error creating strategy simulation tables: {str(e)}")
        return False
    
    try:
        # Initialize IBKR market data tables
        print("\n3. Creating IBKR market data tables...")
        from services.ibkr_data_service import IBKRDataService
        
        service = IBKRDataService()
        service.create_market_data_table()
        print("✓ IBKR market data tables created successfully")
    
    except Exception as e:
        print(f"✗ Error creating IBKR market data tables: {str(e)}")
        return False
    
    print("\n✅ All database tables initialized successfully!")
    print("\nDatabase structure:")
    print("📦 Flask-SQLAlchemy tables:")
    print("   ├── users")
    print("   ├── products") 
    print("   ├── user_products")
    print("   └── performance_records")
    print("📦 Strategy simulation tables:")
    print("   ├── strategy_simulations")
    print("   └── daily_performance")
    print("📦 IBKR market data tables:")
    print("   └── market_data")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)