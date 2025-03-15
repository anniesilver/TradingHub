# pylint: disable=import-error
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import DictCursor, Json


# CRITICAL FIX: Create absolute paths to the strategy modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(
    os.path.dirname(SCRIPT_DIR)
)  # Get two directories up
os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:{BASE_DIR}"
print(f"Set PYTHONPATH to include: {BASE_DIR}")

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

# Base path for all strategies
ALGO_BASE_PATH = os.environ.get('ALGO_BASE_PATH', 'C:/ALGO/algo_trading')

# Dictionary of available strategies
STRATEGY_PATHS = {
    'SPY_POWER_CASHFLOW': os.path.join(ALGO_BASE_PATH, 'SPY_POWER_CASHFLOW'),
    'CCSPY': os.path.join(ALGO_BASE_PATH, 'CCSPY'),
}

# Add all strategy paths to sys.path for importing
for path in STRATEGY_PATHS.values():
    if path not in sys.path and os.path.exists(path):
        sys.path.append(path)
        print(f"Added strategy path: {path}")

# Database connection parameters from environment variables
DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'port': os.environ.get('DB_PORT'),
}

# Remove None values if they exist to let psycopg2 use its own defaults
DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if v is not None}


# Check for required database configuration
def validate_db_config():
    """Validate that required database configuration is present"""
    required_keys = ['dbname', 'user', 'password']
    missing_keys = [
        key
        for key in required_keys
        if key not in DB_CONFIG or not DB_CONFIG[key]
    ]

    if missing_keys:
        print(
            f"ERROR: Missing required database configuration: {', '.join(missing_keys)}"
        )
        print("Please check your .env file or environment variables")
        return False
    return True


# Dictionary to hold imported strategy modules
strategy_modules = {}


# Create stub classes for IDE to stop complaining
class StubMarketData:
    """Stub class to help with IDE imports"""

    pass


class StubPositionTracker:
    """Stub class to help with IDE imports"""

    pass


class StubConfig:
    """Stub class to help with IDE imports"""

    pass


# Add all possible strategy directories to sys.path at startup
def ensure_strategy_paths():
    """Make sure all strategy paths are in sys.path"""
    for path in STRATEGY_PATHS.values():
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
            print(f"Added strategy path to sys.path: {path}")

    # Also add the strategy parent directory
    parent_dir = os.path.dirname(ALGO_BASE_PATH)
    if os.path.exists(parent_dir) and parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        print(f"Added strategy parent directory to sys.path: {parent_dir}")

    # Add the current directory too
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print(f"Added current directory to sys.path: {current_dir}")

    print(f"sys.path now contains: {sys.path}")
    return True


# Call this at import time to ensure paths are set up
ensure_strategy_paths()


def ensure_strategy_dependencies():
    """
    Check for required dependencies and install them if necessary.
    """
    required_packages = ["pandas"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print(
            "Please install them using: pip install "
            + " ".join(missing_packages)
        )
        return False
    return True


def import_strategy(strategy_type):
    """
    Dynamically import strategy modules from the configured paths.

    Args:
        strategy_type (str): Name of the strategy to import

    Returns:
        tuple: (TradingSimulator, OptionStrategy, bool) or (None, None, False) if import fails
    """
    # First check dependencies
    if not ensure_strategy_dependencies():
        return None, None, False

    if strategy_type in strategy_modules:
        return strategy_modules[strategy_type]

    if strategy_type not in STRATEGY_PATHS:
        print(f"Unknown strategy type: {strategy_type}")
        return None, None, False

    path = STRATEGY_PATHS[strategy_type]
    if not os.path.exists(path):
        print(f"Strategy path does not exist: {path}")
        return None, None, False

    # Important: Clear sys.modules of any previous imports that might conflict
    for key in list(sys.modules.keys()):
        if key in [
            'trading_simulator',
            'option_strategy',
            'market_data',
            'position',
            'config',
        ]:
            del sys.modules[key]
            print(f"Removed previous import of {key} from sys.modules")

    # Add strategy path to system path if not already added
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"Added strategy path to sys.path: {path}")

    try:
        # Attempt to import the required modules
        # Log more detailed import attempts
        print(f"Attempting to import strategy modules from {path}")
        print(f"Current sys.path: {sys.path}")

        if strategy_type == "SPY_POWER_CASHFLOW":
            try:
                # Try explicit imports with full path
                print(f"Importing from {path}")
                sys.path.insert(0, path)

                # Look for the module files explicitly
                module_files = os.listdir(path)
                print(f"Files in strategy directory: {module_files}")

                # Import with more verbose error handling
                try:
                    from trading_simulator import TradingSimulator

                    print("Successfully imported TradingSimulator")
                except ImportError as e:
                    print(f"Failed to import TradingSimulator: {str(e)}")
                    raise

                try:
                    from option_strategy import OptionStrategy

                    print("Successfully imported OptionStrategy")
                except ImportError as e:
                    print(f"Failed to import OptionStrategy: {str(e)}")
                    raise

                strategy_modules[strategy_type] = (
                    TradingSimulator,
                    OptionStrategy,
                    True,
                )
                return TradingSimulator, OptionStrategy, True
            except Exception as e:
                print(f"Detailed import error: {str(e)}")
                raise
        elif strategy_type == "CCSPY":
            try:
                # Try explicit imports with full path
                print(f"Importing from {path}")
                sys.path.insert(0, path)

                # Look for the module files explicitly
                module_files = os.listdir(path)
                print(f"Files in strategy directory: {module_files}")

                # Import with more verbose error handling
                try:
                    from trading_simulator import TradingSimulator

                    print("Successfully imported TradingSimulator for CCSPY")
                except ImportError as e:
                    print(
                        f"Failed to import TradingSimulator for CCSPY: {str(e)}"
                    )
                    raise

                try:
                    from option_strategy import OptionStrategy

                    print("Successfully imported OptionStrategy for CCSPY")
                except ImportError as e:
                    print(
                        f"Failed to import OptionStrategy for CCSPY: {str(e)}"
                    )
                    raise

                strategy_modules[strategy_type] = (
                    TradingSimulator,
                    OptionStrategy,
                    True,
                )
                return TradingSimulator, OptionStrategy, True
            except Exception as e:
                print(f"Detailed import error for CCSPY: {str(e)}")
                raise

        print(f"Could not import strategy modules for {strategy_type}")
        return None, None, False
    except ImportError as e:
        print(f"Error importing strategy {strategy_type}: {str(e)}")
        return None, None, False


def get_db_connection():
    """
    Establish and return a connection to the PostgreSQL database.
    """
    if not validate_db_config():
        return None

    try:
        print(f"Connecting to database with parameters:")
        print(f"  dbname: {DB_CONFIG.get('dbname')}")
        print(f"  user: {DB_CONFIG.get('user')}")
        # Only print host and port if they exist in the config
        if 'host' in DB_CONFIG:
            print(f"  host: {DB_CONFIG.get('host')}")
        if 'port' in DB_CONFIG:
            print(f"  port: {DB_CONFIG.get('port')}")
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_simulations (
                    id SERIAL PRIMARY KEY,
                    strategy_type VARCHAR(50) NOT NULL,
                    config JSONB NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    initial_balance FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create daily performance table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES strategy_simulations(id),
                    date DATE NOT NULL,
                    balance FLOAT NOT NULL,
                    trades_count INTEGER NOT NULL,
                    profit_loss FLOAT NOT NULL
                )
            """
            )

            conn.commit()
            print("Database tables initialized successfully")
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {str(e)}")
        return False
    finally:
        conn.close()


def save_simulation_results(
    strategy_type, config, start_date, end_date, initial_balance, daily_results
):
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
            cursor.execute(
                """
                INSERT INTO strategy_simulations 
                (strategy_type, config, start_date, end_date, initial_balance)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    strategy_type,
                    Json(config),
                    start_date,
                    end_date,
                    initial_balance,
                ),
            )

            simulation_id = cursor.fetchone()[0]

            # Insert daily performance records
            for date_str, data in daily_results.items():
                cursor.execute(
                    """
                    INSERT INTO daily_performance
                    (simulation_id, date, balance, trades_count, profit_loss)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (
                        simulation_id,
                        date_str,
                        data['balance'],
                        data['trades_count'],
                        data['profit_loss'],
                    ),
                )

            conn.commit()
            return simulation_id
    except Exception as e:
        conn.rollback()
        print(f"Error saving simulation results: {str(e)}")
        return None
    finally:
        conn.close()


def run_strategy_simulation(
    strategy_type,
    config,
    start_date,
    end_date,
    initial_balance,
    save_to_db=True,
):
    """
    Run a strategy simulation for the given date range and configuration.
    Currently returns mock data for demonstration.

    Args:
        strategy_type (str): Type of strategy (e.g., 'SPY_POWER_CASHFLOW', 'CCSPY')
        config (dict): Strategy configuration parameters
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
        initial_balance (float): Starting account balance
        save_to_db (bool): Whether to save results to database

    Returns:
        dict: Daily performance data
    """
    try:
        # For now, always generate mock data
        from services.mock_strategy import generate_mock_data

        results = generate_mock_data(start_date, end_date, initial_balance)

        # Save results to database if requested
        if save_to_db and results:
            simulation_id = save_simulation_results(
                strategy_type,
                config,
                start_date,
                end_date,
                initial_balance,
                results,
            )
            if simulation_id:
                print(f"Simulation results saved with ID: {simulation_id}")

        return results

    except Exception as e:
        print(f"Error running strategy simulation: {str(e)}")
        return None


def run_spy_power_cashflow(
    TradingSimulator, OptionStrategy, config, start_dt, end_dt, initial_balance=None
):
    """Run the SPY_POWER_CASHFLOW strategy simulation."""
    strategy_path = STRATEGY_PATHS['SPY_POWER_CASHFLOW']
    original_path = sys.path.copy()

    try:
        if strategy_path not in sys.path:
            sys.path.insert(0, strategy_path)
            print(f"Temporarily added {strategy_path} to sys.path")

        # Import required modules using importlib
        spec = importlib.util.spec_from_file_location(
            "market_data", os.path.join(strategy_path, "market_data.py")
        )
        market_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(market_data_module)
        MarketData = market_data_module.MarketData

        spec = importlib.util.spec_from_file_location(
            "position", os.path.join(strategy_path, "position.py")
        )
        position_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(position_module)
        PositionTracker = position_module.PositionTracker

        spec = importlib.util.spec_from_file_location(
            "config", os.path.join(strategy_path, "config.py")
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        Config = config_module.Config

        # Create a Config object
        strategy_config = Config()
        
        # Apply config values from frontend rather than hardcoding
        # Transfer any config parameters from the frontend to the strategy_config
        if 'SYMBOL' in config:
            strategy_config.SYMBOL = config['SYMBOL']
        else:
            # Fallback to default value for backwards compatibility
            strategy_config.SYMBOL = 'SPY'
        
        # Set strategy type from the request data
        strategy_config.STRATEGY_TYPE = 'SPY_POWER_CASHFLOW'
        
        # Get initial balance from request
        try:
            # Define possible parameter locations and names
            balance_sources = [
                ('parameter', initial_balance),
                ('config', 'initial_balance'),
                ('config', 'initialBalance'),
                ('config', 'INITIAL_CASH')
            ]
            
            # Check each possible source
            balance_set = False
            for source_type, source in balance_sources:
                if source_type == 'parameter' and source is not None:
                    strategy_config.INITIAL_CASH = float(source)
                    print(f"Using initial balance from parameter: {source}")
                    balance_set = True
                    break
                elif source_type == 'config' and source in config:
                    strategy_config.INITIAL_CASH = float(config[source])
                    print(f"Using {source} from config: {config[source]}")
                    balance_set = True
                    break
                
        except (ValueError, TypeError) as e:
            print(f"Error parsing initial balance: {e}, using default")

        # Apply all config parameters from frontend to strategy_config
        # Print frontend config for debugging
        print("\n=== Config from frontend ===")
        for key, value in config.items():
            print(key, value)
            # Set attribute directly if it matches a strategy_config attribute 
            # and is not already handled
            if key != 'SYMBOL' and key != 'INITIAL_CASH' and hasattr(strategy_config, key):
                try:
                    if isinstance(value, (int, float)):
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config")
                    elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config (converted to float)")
                    else:
                        setattr(strategy_config, key, value)
                        print(f"Set {key} = {value} from frontend config (non-numeric)")
                except (ValueError, TypeError) as e:
                    print(f"Error setting {key} from value {value}: {e}, using default")

        print("\n=== Final Config for simulation ===")
        for attr in dir(strategy_config):
            if not attr.startswith('__'):  # Skip private attributes
                print(f"{attr}: {getattr(strategy_config, attr)}")

        # Initialize components with debug prints
        print("\n=== Initializing MarketData ===")
        market_data = MarketData(symbol=strategy_config.SYMBOL)
        print(f"MarketData symbol: {market_data.symbol}")

        print("\n=== Initializing PositionTracker ===")
        position = PositionTracker(
            strategy_config.INITIAL_CASH, strategy_config
        )
        print(f"PositionTracker initial balance: {position.cash}")

        print("\n=== Initializing OptionStrategy ===")
        strategy = OptionStrategy(strategy_config)
        print(f"OptionStrategy type: {strategy_config.STRATEGY_TYPE}")

        print("\n=== Creating TradingSimulator ===")
        simulator = TradingSimulator(
            market_data, position, strategy, strategy_config
        )
        print("TradingSimulator created with all components")

        print("\n=== Running Simulation ===")
        # Convert datetime objects to string dates in YYYY-MM-DD format for the simulator
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        print(f"Running simulation from {start_date} to {end_date}")
        
        results_df = simulator.run(start_date=start_date, end_date=end_date)
        
        # Process results
        daily_results = {}
        if results_df is not None and not results_df.empty:
            print(f"Results DataFrame columns: {results_df.columns.tolist()}")

            # Ensure the index is datetime
            if not isinstance(results_df.index, pd.DatetimeIndex):
                results_df.index = pd.to_datetime(results_df.index)

            # Calculate SPY buy & hold value using Close prices from results_df
            # New approach: Calculate shares purchased on first day, then keep that constant
            first_day_close = results_df['Close'].iloc[0]
            initial_cash = strategy_config.INITIAL_CASH
            spy_shares_bought = initial_cash / first_day_close
            print(f"SPY Buy & Hold: Initial cash ${initial_cash}, first day close ${first_day_close}, shares bought {spy_shares_bought}")
            
            # Calculate daily value based on fixed shares
            spy_values = results_df['Close'] * spy_shares_bought
            
            # Only include actual trading days - exclude weekends and holidays
            trading_days = results_df.index.tolist()
            
            for idx, row in results_df.iterrows():
                # Skip dates that aren't in the original DataFrame
                if idx not in trading_days:
                    continue
                    
                date_str = idx.strftime('%Y-%m-%d')
                # Map simulator output fields to frontend expected fields
                daily_results[date_str] = {
                    'Portfolio_Value': float(
                        row.get('Portfolio_Value', 0)
                    ),
                    'Cash_Balance': float(
                        row.get('Cash_Balance', 0)
                    ),
                    'Close': float(row.get('Close', 0)),
                    'Margin_Ratio': float(
                        row.get('Margin_Ratio', 0)
                    ),
                    'spy_value': float(spy_values.get(idx, 0)),                    
                    'Interest_Paid': float(
                        row.get('Interests_Paid', 0)                        
                    ),
                    'Premiums_Received': float(
                        row.get('Premiums_Received', 0)
                    ),
                    'Commissions_Paid': float(
                        row.get('Commissions_Paid', 0)
                    ),
                    'Open_Positions': int(
                        row.get('Open_Positions', 0)
                    ),
                    'Closed_Positions': int(
                        row.get('Closed_Positions', 0)
                    ),
                    'Open': float(row.get('Open', 0)),
                    'High': float(row.get('High', 0)),
                    'Low': float(row.get('Low', 0)),
                    'VIX': float(row.get('VIX', 0)),
                    'Trading_Log': str(
                        row.get('Trading_Log', '')
                    ),
                }

        return daily_results

    except Exception as e:
        print(f"Error in run_spy_power_cashflow: {str(e)}")
        raise
    finally:
        sys.path = original_path


def run_ccspy_strategy(
    TradingSimulator, OptionStrategy, config, start_dt, end_dt, initial_balance
):
    """Run the CCSPY strategy simulation."""
    strategy_path = STRATEGY_PATHS['CCSPY']
    original_path = sys.path.copy()

    try:
        if strategy_path not in sys.path:
            sys.path.insert(0, strategy_path)
            print(f"Temporarily added {strategy_path} to sys.path")

        # Import required modules using importlib
        spec = importlib.util.spec_from_file_location(
            "market_data", os.path.join(strategy_path, "market_data.py")
        )
        market_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(market_data_module)
        MarketData = market_data_module.MarketData

        spec = importlib.util.spec_from_file_location(
            "position", os.path.join(strategy_path, "position.py")
        )
        position_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(position_module)
        PositionTracker = position_module.PositionTracker

        spec = importlib.util.spec_from_file_location(
            "config", os.path.join(strategy_path, "config.py")
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        Config = config_module.Config

        # Create a Config object
        strategy_config = Config()        
        
        # Apply config values from frontend rather than hardcoding
        # Transfer any config parameters from the frontend to the strategy_config
        if 'SYMBOL' in config:
            strategy_config.SYMBOL = config['SYMBOL']
        else:
            # Fallback to default value for backwards compatibility
            strategy_config.SYMBOL = 'SPY'
        
        # Set strategy type from the request data
        strategy_config.STRATEGY_TYPE = 'CCSPY'

        # Set initial balance
        if initial_balance is not None:
            try:
                strategy_config.INITIAL_CASH = float(initial_balance)
                print(f"Using initial balance from parameter: {initial_balance}")
            except (ValueError, TypeError) as e:
                print(f"Error parsing initial balance: {e}, using default")
        elif 'INITIAL_CASH' in config:
            try:
                strategy_config.INITIAL_CASH = float(config['INITIAL_CASH'])
                print(f"Using INITIAL_CASH from config: {config['INITIAL_CASH']}")
            except (ValueError, TypeError) as e:
                print(f"Error parsing INITIAL_CASH: {e}, using default")
        
        # Apply all config parameters from frontend to strategy_config
        # Print frontend config for debugging
        print("\n=== Config from frontend ===")
        for key, value in config.items():
            print(key, value)
            # Set attribute directly if it matches a strategy_config attribute 
            # and is not already handled
            if key != 'SYMBOL' and key != 'INITIAL_CASH' and hasattr(strategy_config, key):
                try:
                    if isinstance(value, (int, float)):
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config")
                    elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config (converted to float)")
                    else:
                        setattr(strategy_config, key, value)
                        print(f"Set {key} = {value} from frontend config (non-numeric)")
                except (ValueError, TypeError) as e:
                    print(f"Error setting {key} from value {value}: {e}, using default")

        print("\n=== Final Config for simulation ===")
        for attr in dir(strategy_config):
            if not attr.startswith('__'):  # Skip private attributes
                print(f"{attr}: {getattr(strategy_config, attr)}")

        # Initialize components
        market_data = MarketData(symbol=strategy_config.SYMBOL)
        position = PositionTracker(strategy_config.INITIAL_CASH, strategy_config)
        strategy = OptionStrategy(strategy_config)

        # Create and run simulator
        simulator = TradingSimulator(
            market_data, position, strategy, strategy_config
        )
        results_df = simulator.run()

        # Process results
        daily_results = {}
        if results_df is not None and not results_df.empty:
            print(f"Results DataFrame columns: {results_df.columns.tolist()}")

            # Ensure the index is datetime
            if not isinstance(results_df.index, pd.DatetimeIndex):
                results_df.index = pd.to_datetime(results_df.index)

            # Calculate SPY buy & hold value using Close prices from results_df   
            # New approach: Calculate shares purchased on first day, then keep that constant
            first_day_close = results_df['Close'].iloc[0]
            spy_shares_bought = initial_balance / first_day_close
            print(f"CCSPY - SPY Buy & Hold: Initial cash ${initial_balance}, first day close ${first_day_close}, shares bought {spy_shares_bought}")
            
            # Calculate daily value based on fixed shares
            spy_values = results_df['Close'] * spy_shares_bought
            
            # Only include actual trading days - exclude weekends and holidays
            trading_days = results_df.index.tolist()

            for idx, row in results_df.iterrows():
                # Skip dates that aren't in the original DataFrame
                if idx not in trading_days:
                    continue
                    
                date_str = idx.strftime('%Y-%m-%d')
                daily_results[date_str] = {
                    'balance': float(
                        row.get('balance', row.get('portfolio_value', 0))
                    ),
                    'trades_count': int(row.get('trades_count', 0)),
                    'profit_loss': float(
                        row.get('profit_loss', row.get('daily_pnl', 0))
                    ),
                }
        else:
            print("Warning: No results data returned from strategy simulation")

        return daily_results
    except Exception as e:
        print(f"Error in run_ccspy_strategy: {str(e)}")
        raise
    finally:
        sys.path = original_path


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
            cursor.execute(
                """
                SELECT id, strategy_type, config, start_date, end_date, initial_balance, created_at
                FROM strategy_simulations
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """,
                (limit, offset),
            )

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
            cursor.execute(
                """
                SELECT id, strategy_type, config, start_date, end_date, initial_balance, created_at
                FROM strategy_simulations
                WHERE id = %s
            """,
                (simulation_id,),
            )

            sim_data = cursor.fetchone()
            if not sim_data:
                return None

            simulation = dict(sim_data)

            # Get daily performance data
            cursor.execute(
                """
                SELECT date, balance, trades_count, profit_loss
                FROM daily_performance
                WHERE simulation_id = %s
                ORDER BY date
            """,
                (simulation_id,),
            )

            days = {}
            for row in cursor.fetchall():
                day_data = dict(row)
                days[day_data['date'].strftime('%Y-%m-%d')] = {
                    'balance': day_data['balance'],
                    'trades_count': day_data['trades_count'],
                    'profit_loss': day_data['profit_loss'],
                }

            simulation['daily_results'] = days
            return simulation
    except Exception as e:
        print(f"Error retrieving simulation results: {str(e)}")
        return None
    finally:
        conn.close()


def get_available_strategies():
    """
    Get a list of available strategy types and their configuration options.

    Returns:
        list: List of strategy information dictionaries
    """
    strategies = []

    for strategy_name, path in STRATEGY_PATHS.items():
        if os.path.exists(path):
            # For now, just return the strategy name and path
            # In a real implementation, you might want to read additional metadata
            strategy_info = {
                'name': strategy_name,
                'path': path,
                'config_options': get_strategy_config_options(strategy_name),
            }
            strategies.append(strategy_info)

    return strategies


def get_strategy_config_options(strategy_name):
    """
    Get the configuration options for a specific strategy.
    This could be expanded to read from a configuration file or the strategy itself.

    Args:
        strategy_name (str): Name of the strategy

    Returns:
        dict: Dictionary of configuration options and their default values
    """
    if strategy_name == 'SPY_POWER_CASHFLOW':
        return {
            'symbol': 'SPY',
            'buy_time': '9:35',
            'sell_time': '15:45',
            'stop_loss_pct': 0.50,
            'take_profit_pct': 1.00,
            'strategy_type': 'power_cashflow',
            'option_type': 'call',
            'dte_min': 1,
            'dte_max': 5,
            'delta_min': 0.40,
            'delta_max': 0.60,
            'commission': 0.65,
        }
    elif strategy_name == 'CCSPY':
        return {
            'symbol': 'SPY',
            'buy_time': '9:35',
            'sell_time': '15:45',
            'stop_loss_pct': 0.50,
            'take_profit_pct': 1.00,
            'strategy_type': 'ccspy',
            'option_type': 'call',
            'dte_min': 1,
            'dte_max': 5,
            'delta_min': 0.40,
            'delta_max': 0.60,
            'commission': 0.65,
        }
    else:
        return {}


def test_imports():
    """Test function to verify imports work correctly"""
    try:
        print("Importing MarketData...")
        from market_data import MarketData

        print("Successfully imported MarketData")
        return True
    except ImportError as e:
        print(f"Failed to import MarketData: {str(e)}")
        return False
