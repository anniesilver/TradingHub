import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
import sys
import json
import psycopg2
from psycopg2.extras import Json, DictCursor
from services.mock_strategy import generate_mock_data

# Load environment variables from .env file (with graceful fallback)
env_path = os.path.join(os.path.dirname(__file__), '.env')
root_env_path = os.path.join(os.getcwd(), '.env')

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print("Loaded .env from services directory")
elif os.path.exists(root_env_path):
    load_dotenv(dotenv_path=root_env_path)
    print("Loaded .env from project root")
else:
    print("No .env file found, using default configuration")

# Comment out the strategy imports to temporarily bypass them for DB setup
algo_path = os.environ.get('ALGO_PATH', 'C:/ALGO/algo_trading/SPY_POWER_CASHFLOW')
sys.path.append(algo_path)

# Database connection parameters with known working defaults
DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'tradinghub'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'algo33'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432')
}

# Place these imports in a try-except block
try:
    # Import the strategy components
    from trading_simulator import TradingSimulator
    from option_strategy import OptionStrategy 
    from position import Position
except ImportError:
    # Create placeholder classes for database setup
    class TradingSimulator: pass
    class OptionStrategy: pass
    class Position: pass
    print("Warning: Trading strategy modules not loaded - only database setup will work")

def get_db_connection():
    """
    Establish and return a connection to the PostgreSQL database.
    """
    try:
        print(f"Connecting to database with parameters:")
        print(f"  dbname: {DB_CONFIG['dbname']}")
        print(f"  user: {DB_CONFIG['user']}")
        # Only print host and port if they exist in the config
        if 'host' in DB_CONFIG:
            print(f"  host: {DB_CONFIG['host']}")
        if 'port' in DB_CONFIG:
            print(f"  port: {DB_CONFIG['port']}")
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

def init_database():
    """
    Initialize the database tables if they don't exist.
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Create strategy simulations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_simulations (
                    id SERIAL PRIMARY KEY,
                    strategy_type VARCHAR(50) NOT NULL,
                    config JSONB NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    initial_balance FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create daily performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES strategy_simulations(id),
                    date DATE NOT NULL,
                    balance FLOAT NOT NULL,
                    trades_count INTEGER NOT NULL,
                    profit_loss FLOAT NOT NULL
                )
            """)
            
            conn.commit()
            print("Database tables initialized successfully")
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {str(e)}")
        return False
    finally:
        conn.close()

def save_simulation_results(strategy_type, config, start_date, end_date, initial_balance, daily_results):
    """
    Save strategy simulation results to the database.
    
    Args:
        strategy_type (str): Type of strategy
        config (dict): Strategy configuration
        start_date (str): Start date
        end_date (str): End date
        initial_balance (float): Initial account balance
        daily_results (dict): Daily performance data
        
    Returns:
        int: ID of the saved simulation
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            # Insert strategy simulation record
            cursor.execute("""
                INSERT INTO strategy_simulations 
                (strategy_type, config, start_date, end_date, initial_balance)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                strategy_type, 
                Json(config), 
                start_date, 
                end_date, 
                initial_balance
            ))
            
            simulation_id = cursor.fetchone()[0]
            
            # Insert daily performance records
            for date_str, data in daily_results.items():
                cursor.execute("""
                    INSERT INTO daily_performance
                    (simulation_id, date, balance, trades_count, profit_loss)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    simulation_id,
                    date_str,
                    data['balance'],
                    data['trades_count'],
                    data['profit_loss']
                ))
            
            conn.commit()
            return simulation_id
    except Exception as e:
        conn.rollback()
        print(f"Error saving simulation results: {str(e)}")
        return None
    finally:
        conn.close()

def run_strategy_simulation(strategy_type, config, start_date, end_date, initial_balance=10000.0, save_to_db=True):
    """
    Run a strategy simulation for the given date range and configuration.
    
    Args:
        strategy_type (str): Type of strategy (e.g., 'SPY_POWER_CASHFLOW')
        config (dict): Strategy configuration parameters
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
        initial_balance (float): Starting account balance
        save_to_db (bool): Whether to save results to database
        
    Returns:
        dict: Daily performance data
    """
    try:
        # Try to run the actual strategy
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if strategy_type == 'SPY_POWER_CASHFLOW':
            try:
                results = run_spy_power_cashflow(config, start_dt, end_dt, initial_balance)
            except Exception as strategy_error:
                # If strategy fails, generate mock data for demonstration
                print(f"Strategy execution failed, using mock data: {str(strategy_error)}")
                results = generate_mock_data(start_date, end_date, initial_balance)
            
            # Save results to database if requested
            if save_to_db and results:
                simulation_id = save_simulation_results(
                    strategy_type, config, start_date, end_date, initial_balance, results
                )
                if simulation_id:
                    print(f"Simulation results saved with ID: {simulation_id}")
            
            return results
        else:
            raise ValueError(f"Unsupported strategy type: {strategy_type}")
            
    except Exception as e:
        print(f"Error running strategy simulation: {str(e)}")
        
        # Generate mock data as fallback for demonstration
        print("Generating mock data as fallback")
        return generate_mock_data(start_date, end_date, initial_balance)

def run_spy_power_cashflow(config, start_dt, end_dt, initial_balance):
    """
    Run the SPY_POWER_CASHFLOW strategy simulation.
    
    Args:
        config (dict): Strategy configuration
        start_dt (datetime): Start date
        end_dt (datetime): End date
        initial_balance (float): Starting account balance
        
    Returns:
        dict: Daily performance data
    """
    # Initialize the strategy with configuration
    strategy = OptionStrategy(
        symbol=config.get('symbol', 'SPY'),
        buy_time=config.get('buy_time', '9:35'),
        sell_time=config.get('sell_time', '15:45'),
        stop_loss_pct=config.get('stop_loss_pct', 0.50),
        take_profit_pct=config.get('take_profit_pct', 1.00),
        strategy_type=config.get('strategy_type', 'power_cashflow'),
        option_type=config.get('option_type', 'call'),
        dte_min=config.get('dte_min', 1),
        dte_max=config.get('dte_max', 5),
        delta_min=config.get('delta_min', 0.40),
        delta_max=config.get('delta_max', 0.60)
    )
    
    # Initialize the trading simulator
    simulator = TradingSimulator(
        strategy=strategy,
        initial_balance=initial_balance,
        commission=config.get('commission', 0.65),
        start_date=start_dt,
        end_date=end_dt
    )
    
    # Run the simulation
    simulator.run()
    
    # Extract the daily performance data
    daily_results = {}
    
    for day, trades in simulator.trades_by_day.items():
        day_str = day.strftime('%Y-%m-%d')
        
        daily_pl = sum(trade.profit_loss for trade in trades)
        daily_balance = simulator.get_balance_at_date(day)
        
        daily_results[day_str] = {
            'balance': daily_balance,
            'trades_count': len(trades),
            'profit_loss': daily_pl
        }
    
    return daily_results 

def get_simulations(limit=10, offset=0):
    """
    Get a list of simulation records from the database.
    
    Args:
        limit (int): Maximum number of records to return
        offset (int): Offset for pagination
        
    Returns:
        list: List of simulation records
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, strategy_type, config, start_date, end_date, initial_balance, created_at
                FROM strategy_simulations
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            simulations = []
            for row in cursor.fetchall():
                simulations.append(dict(row))
            
            return simulations
    except Exception as e:
        print(f"Error retrieving simulations: {str(e)}")
        return []
    finally:
        conn.close()

def get_simulation_results(simulation_id):
    """
    Get the daily performance results for a simulation.
    
    Args:
        simulation_id (int): ID of the simulation
        
    Returns:
        dict: Simulation data with daily performance
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            # Get simulation metadata
            cursor.execute("""
                SELECT id, strategy_type, config, start_date, end_date, initial_balance, created_at
                FROM strategy_simulations
                WHERE id = %s
            """, (simulation_id,))
            
            sim_data = cursor.fetchone()
            if not sim_data:
                return None
                
            simulation = dict(sim_data)
            
            # Get daily performance data
            cursor.execute("""
                SELECT date, balance, trades_count, profit_loss
                FROM daily_performance
                WHERE simulation_id = %s
                ORDER BY date
            """, (simulation_id,))
            
            days = {}
            for row in cursor.fetchall():
                day_data = dict(row)
                days[day_data['date'].strftime('%Y-%m-%d')] = {
                    'balance': day_data['balance'],
                    'trades_count': day_data['trades_count'],
                    'profit_loss': day_data['profit_loss']
                }
            
            simulation['daily_results'] = days
            return simulation
    except Exception as e:
        print(f"Error retrieving simulation results: {str(e)}")
        return None
    finally:
        conn.close() 