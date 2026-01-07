import importlib.util
import os
import sys

import pandas as pd
import numpy as np  # Add numpy import for isinf function
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import DictCursor, Json

# CRITICAL FIX: Create absolute paths to the strategy modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # Get two directories up
os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{BASE_DIR}"
print(f"Set PYTHONPATH to include: {BASE_DIR}")

# Load environment variables from .env file (with graceful fallback)
env_path = os.path.join(os.path.dirname(__file__), ".env")
root_env_path = os.path.join(os.getcwd(), ".env")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print("Loaded .env from services directory")
elif os.path.exists(root_env_path):
    load_dotenv(dotenv_path=root_env_path)
    print("Loaded .env from project root")
else:
    print("No .env file found, using default configuration")

# Base path for all strategies
ALGO_BASE_PATH = os.environ.get("ALGO_BASE_PATH", "C:/ALGO/algo_trading")

# Dictionary of available strategies
STRATEGY_PATHS = {
    "SPY_POWER_CASHFLOW": os.path.join(ALGO_BASE_PATH, "SPY_POWER_CASHFLOW"),
    "OPTIONS_MARTIN": os.path.join(ALGO_BASE_PATH, "OPTIONS_MARTIN"),
}

# Add all strategy paths to sys.path for importing
for path in STRATEGY_PATHS.values():
    if path not in sys.path and os.path.exists(path):
        sys.path.append(path)
        print(f"Added strategy path: {path}")

# Database connection parameters from environment variables
DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT"),
}

# Remove None values if they exist to let psycopg2 use its own defaults
DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if v is not None}


# Check for required database configuration
def validate_db_config():
    """Validate that required database configuration is present"""
    required_keys = ["dbname", "user", "password"]
    missing_keys = [key for key in required_keys if key not in DB_CONFIG or not DB_CONFIG[key]]

    if missing_keys:
        print(f"ERROR: Missing required database configuration: {', '.join(missing_keys)}")
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
        print("Please install them using: pip install " + " ".join(missing_packages))
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
            "trading_simulator",
            "option_strategy",
            "market_data",
            "position",
            "config",
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

        elif strategy_type == "OPTIONS_MARTIN":
            try:
                # Import OPTIONS_MARTIN modules
                print(f"Importing OPTIONS_MARTIN from {path}")
                sys.path.insert(0, path)

                module_files = os.listdir(path)
                print(f"Files in OPTIONS_MARTIN directory: {module_files}")

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
                print(f"Detailed import error for OPTIONS_MARTIN: {str(e)}")
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
        print("Connecting to database with parameters:")
        print(f"  dbname: {DB_CONFIG.get('dbname')}")
        print(f"  user: {DB_CONFIG.get('user')}")
        # Only print host and port if they exist in the config
        if "host" in DB_CONFIG:
            print(f"  host: {DB_CONFIG.get('host')}")
        if "port" in DB_CONFIG:
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
                        data["balance"],
                        data["trades_count"],
                        data["profit_loss"],
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


def run_spy_power_cashflow(TradingSimulator, OptionStrategy, config, start_dt, end_dt, initial_balance=None):
    """Run the SPY_POWER_CASHFLOW strategy simulation."""
    strategy_path = STRATEGY_PATHS["SPY_POWER_CASHFLOW"]
    original_path = sys.path.copy()

    try:
        if strategy_path not in sys.path:
            sys.path.insert(0, strategy_path)
            print(f"Temporarily added {strategy_path} to sys.path")

        # Import unified market data class with database-first approach
        # Use explicit path-based import to avoid conflict with strategy's local MarketData
        import importlib.util
        current_services_path = os.path.dirname(__file__)
        market_data_path = os.path.join(current_services_path, "market_data.py")
        spec = importlib.util.spec_from_file_location("unified_market_data", market_data_path)
        unified_market_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unified_market_data_module)
        MarketData = unified_market_data_module.MarketData

        spec = importlib.util.spec_from_file_location("position", os.path.join(strategy_path, "position.py"))
        position_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(position_module)
        PositionTracker = position_module.PositionTracker

        spec = importlib.util.spec_from_file_location("config", os.path.join(strategy_path, "config.py"))
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        Config = config_module.Config

        # Create a Config object
        strategy_config = Config()

        # Apply config values from frontend rather than hardcoding
        # Transfer any config parameters from the frontend to the strategy_config
        if "SYMBOL" in config:
            strategy_config.SYMBOL = config["SYMBOL"]
        else:
            # Fallback to default value for backwards compatibility
            strategy_config.SYMBOL = "SPY"

        # Set strategy type from the request data
        strategy_config.STRATEGY_TYPE = "SPY_POWER_CASHFLOW"

        # Get initial balance from request
        try:
            # Define possible parameter locations and names
            balance_sources = [
                ("parameter", initial_balance),
                ("config", "initial_balance"),
                ("config", "initialBalance"),
                ("config", "INITIAL_CASH"),
            ]

            # Check each possible source
            # balance_set = False
            for source_type, source in balance_sources:
                if source_type == "parameter" and source is not None:
                    strategy_config.INITIAL_CASH = float(source)
                    print(f"Using initial balance from parameter: {source}")
                    # balance_set = True
                    break
                elif source_type == "config" and source in config:
                    strategy_config.INITIAL_CASH = float(config[source])
                    print(f"Using {source} from config: {config[source]}")
                    # balance_set = True
                    break

        except (ValueError, TypeError) as e:
            print(f"Error parsing initial balance: {e}, using default")

        # Apply all config parameters from frontend to strategy_config
        # Print frontend config for debugging
        print("\n=== BACKEND PARAMETER DEBUG ===")
        print("Full config from frontend:", config)
        print("\n=== Individual Config Parameters ===")
        for key, value in config.items():
            print(f"{key}: {value} (type: {type(value)})")

        # Specifically check for monthly withdrawal rate parameter
        print("\n=== MONTHLY WITHDRAWAL RATE DEBUG ===")
        if "MONTHLY_WITHDRAWAL_RATE" in config:
            print(f"MONTHLY_WITHDRAWAL_RATE found: {config['MONTHLY_WITHDRAWAL_RATE']}%")
        else:
            print("MONTHLY_WITHDRAWAL_RATE not found in config")

        # Check for old parameter name (should not be present)
        if "MONTHLY_WITHDRAWAL" in config:
            print(f"WARNING: Old MONTHLY_WITHDRAWAL parameter found: {config['MONTHLY_WITHDRAWAL']} (should use MONTHLY_WITHDRAWAL_RATE instead)")

        print("=== END WITHDRAWAL RATE DEBUG ===")

        for key, value in config.items():
            # Set attribute directly if it matches a strategy_config attribute
            # and is not already handled
            if key != "SYMBOL" and key != "INITIAL_CASH" and hasattr(strategy_config, key):
                try:
                    if isinstance(value, (int, float)):
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config")
                    elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
                        setattr(strategy_config, key, float(value))
                        print(f"Set {key} = {value} from frontend config (converted to float)")
                    else:
                        setattr(strategy_config, key, value)
                        print(f"Set {key} = {value} from frontend config (non-numeric)")
                except (ValueError, TypeError) as e:
                    print(f"Error setting {key} from value {value}: {e}, using default")

        print("\n=== Final Config for simulation ===")
        for attr in dir(strategy_config):
            if not attr.startswith("__"):  # Skip private attributes
                print(f"{attr}: {getattr(strategy_config, attr)}")

        # Initialize components with debug prints
        print("\n=== Initializing MarketData ===")
        market_data = MarketData(symbol=strategy_config.SYMBOL)
        print(f"MarketData symbol: {market_data.symbol}")

        # Convert datetime objects to string dates first
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")

        # Load data with user-specified date range
        print(f"Loading market data for date range: {start_date_str} to {end_date_str}")
        market_data.load_data(start_date=start_date_str, end_date=end_date_str)
        print(f"Market data loaded successfully")

        print("\n=== Initializing PositionTracker ===")
        position = PositionTracker(strategy_config.INITIAL_CASH, strategy_config)
        print(f"PositionTracker initial balance: {position.cash}")

        print("\n=== Initializing OptionStrategy ===")
        strategy = OptionStrategy(strategy_config)
        print(f"OptionStrategy type: {strategy_config.STRATEGY_TYPE}")

        print("\n=== Creating TradingSimulator ===")
        simulator = TradingSimulator(market_data, position, strategy, strategy_config)
        print("TradingSimulator created with all components")

        print("\n=== Running Simulation ===")
        print(f"Running simulation from {start_date_str} to {end_date_str}")

        results_df = simulator.run(start_date=start_date_str, end_date=end_date_str)

        # Process results
        daily_results = {}
        if results_df is not None and not results_df.empty:
            print(f"Original Results DataFrame columns: {results_df.columns.tolist()}")
            
            # Make a copy to avoid modifying the original
            cleaned_df = results_df.copy()

            # Ensure the index is datetime
            if not isinstance(cleaned_df.index, pd.DatetimeIndex):
                cleaned_df.index = pd.to_datetime(cleaned_df.index)

            # Clean DataFrame to handle NaN and Inf values
            print("Cleaning DataFrame of NaN and Infinity values")
            cleaned_df = cleaned_df.replace([float('inf'), float('-inf')], 0)
            cleaned_df = cleaned_df.fillna(0)  # Replace NaN with zeros
            
            # Normalize column names (replace spaces with underscores)
            print("Normalizing column names")
            cleaned_df.columns = [col.replace(' ', '_') for col in cleaned_df.columns]
            
            # Print normalized column names for debugging
            print(f"Normalized DataFrame columns: {cleaned_df.columns.tolist()}")

            # Calculate SPY buy & hold value using Close prices from results_df
            # New approach: Calculate shares purchased on first day, then keep that constant
            first_day_close = cleaned_df["Close"].iloc[0]
            initial_cash = strategy_config.INITIAL_CASH
            spy_shares_bought = initial_cash / first_day_close if first_day_close > 0 else 0
            print(
                f"SPY Buy & Hold: Initial cash ${initial_cash:.2f}, first day close ${first_day_close:.2f}, "
                f"shares bought {spy_shares_bought:.2f}"
            )

            # Calculate daily value based on fixed shares
            spy_values = cleaned_df["Close"] * spy_shares_bought

            # Only include actual trading days - exclude weekends and holidays
            trading_days = cleaned_df.index.tolist()

            # Define helper functions for safe value conversion
            def safe_float(value, default=0.0, decimal_places=4):
                """
                Safely convert a value to a float with specified decimal places.
                Returns default if value is NaN, Inf, or cannot be converted.
                """
                try:
                    val = float(value)
                    # Check for infinity or NaN using numpy instead of pandas
                    if pd.isna(val) or np.isinf(val):
                        print(f"Warning: Detected NaN or Inf value: {value}, using default {default}")
                        return default
                    # Round to specified decimal places
                    return round(val, decimal_places)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Error converting value to float: {value}, {str(e)}, using default {default}")
                    return default
            
            def safe_int(value, default=0):
                """
                Safely convert a value to an integer.
                Returns default if value is NaN or cannot be converted.
                """
                try:
                    val = int(float(value))  # Convert to float first in case it's a float string
                    if pd.isna(val):
                        print(f"Warning: Detected NaN value for int conversion: {value}, using default {default}")
                        return default
                    return val
                except (ValueError, TypeError) as e:
                    print(f"Warning: Error converting value to int: {value}, {str(e)}, using default {default}")
                    return default
            
            # Function to get value from row with multiple possible column names
            def get_column_value(row_data, possible_names, default=0):
                """
                Try multiple possible column names to get a value from a DataFrame row.
                Returns default if none of the column names exist.
                """
                # Convert Series index to list for easier checking
                available_columns = list(row_data.index)
                
                for name in possible_names:
                    if name in available_columns:
                        val = row_data.get(name, default)
                        # Print for debugging on first row
                        if row_data.name == cleaned_df.index[0]:
                            print(f"Found column '{name}' with value: {val}")
                        return val
                
                # If we get here, none of the columns were found
                if row_data.name == cleaned_df.index[0]:
                    print(f"Warning: None of the columns {possible_names} found, using default {default}")
                return default

            print("\n=== Processing daily results ===")
            print(f"DataFrame columns: {list(cleaned_df.columns)}")
            print(f"Sample Interests_Paid values: {cleaned_df['Interests_Paid'].head().tolist() if 'Interests_Paid' in cleaned_df.columns else 'Column not found'}")
            for idx, row in cleaned_df.iterrows():
                # Skip dates that aren't in the original DataFrame
                if idx not in trading_days:
                    continue

                date_str = idx.strftime("%Y-%m-%d")
                
                # Map simulator output fields to frontend expected fields with safe conversion
                # We check for multiple possible column names since the DataFrame may use different formats
                result_dict = {
                    "Portfolio_Value": safe_float(get_column_value(row, ["Portfolio_Value", "Portfolio Value", "portfolio_value"]), 0.0),
                    "Cash_Balance": safe_float(get_column_value(row, ["Cash_Balance", "Cash Balance", "cash_balance"]), 0.0),
                    "Close": safe_float(row.get("Close", 0.0)),
                    "Margin_Ratio": safe_float(get_column_value(row, ["Margin_Ratio", "Margin Ratio", "margin_ratio"]), 0.0),
                    "spy_value": safe_float(spy_values.get(idx, 0.0)),
                    "Interest_Paid": safe_float(get_column_value(row, ["Interest_Paid", "Interests_Paid", "Interests Paid", "interests_paid"]), 0.0),
                    "Premiums_Received": safe_float(get_column_value(row, ["Premiums_Received", "Premiums Received", "premiums_received"]), 0.0),
                    "Commissions_Paid": safe_float(get_column_value(row, ["Commissions_Paid", "Commissions Paid", "commissions_paid"]), 0.0),
                    "Open_Positions": safe_int(get_column_value(row, ["Open_Positions", "Open Positions", "open_positions"]), 0),
                    "Closed_Positions": safe_int(get_column_value(row, ["Closed_Positions", "Closed Positions", "closed_positions"]), 0),
                    "Open": safe_float(row.get("Open", 0.0)),
                    "High": safe_float(row.get("High", 0.0)),
                    "Low": safe_float(row.get("Low", 0.0)),
                    "VIX": safe_float(row.get("VIX", 0.0)),
                    "Trading_Log": str(get_column_value(row, ["Trading_Log", "Trading Log", "trading_log"], "")),
                }
                
                # Add to daily results
                daily_results[date_str] = result_dict
                
                # Print the first day's data for debugging
                if idx == cleaned_df.index[0]:
                    print("First day data sample (after processing):")
                    for k, v in result_dict.items():
                        print(f"  {k}: {v}")

            print(f"Processed {len(daily_results)} days of data")
            
            # Verify there's no NaN or Infinity in the results
            print("Verifying no NaN or Infinity values in the final results...")
            for date_str, data in daily_results.items():
                for key, value in data.items():
                    if isinstance(value, (int, float)) and (pd.isna(value) or np.isinf(value)):
                        print(f"Warning: Found invalid value in final results: {key}={value} for date {date_str}")
                        # Fix the value
                        if key in ["Open_Positions", "Closed_Positions"]:
                            daily_results[date_str][key] = 0
                        else:
                            daily_results[date_str][key] = 0.0

        else:
            print("Warning: No results data returned from strategy simulation")

        return daily_results

    except Exception as e:
        print(f"Error in run_spy_power_cashflow: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise
    finally:
        sys.path = original_path


def run_options_martin(TradingSimulator, OptionStrategy, config, start_dt, end_dt, initial_balance=None):
    """Run the OPTIONS_MARTIN strategy simulation."""
    strategy_path = STRATEGY_PATHS["OPTIONS_MARTIN"]
    original_path = sys.path.copy()

    try:
        if strategy_path not in sys.path:
            sys.path.insert(0, strategy_path)
            print(f"Temporarily added {strategy_path} to sys.path")

        # Import strategy modules using explicit path-based imports
        import importlib.util

        spec = importlib.util.spec_from_file_location("position", os.path.join(strategy_path, "position.py"))
        position_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(position_module)
        PositionTracker = position_module.PositionTracker

        spec = importlib.util.spec_from_file_location("config", os.path.join(strategy_path, "config.py"))
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        Config = config_module.Config

        # Import MarketData from OPTIONS_MARTIN (handles option price loading via IBKR service)
        spec = importlib.util.spec_from_file_location("market_data", os.path.join(strategy_path, "market_data.py"))
        market_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(market_data_module)
        MarketData = market_data_module.MarketData

        # Create a Config object
        strategy_config = Config()

        # Apply config values from frontend
        strategy_config.SYMBOL = config.get("SYMBOL", "SPY")
        strategy_config.STRATEGY_TYPE = "OPTIONS_MARTIN"

        # OPTION-SPECIFIC PARAMETERS
        strategy_config.STRIKE = float(config.get("STRIKE", 600.0))
        strategy_config.RIGHT = config.get("RIGHT", "C")
        strategy_config.EXPIRATION = config.get("EXPIRATION", "20260220")

        # MARTINGALE PARAMETERS
        strategy_config.INC_INDEX = float(config.get("INC_INDEX", 2.0))
        strategy_config.DEC_INDEX = float(config.get("DEC_INDEX", 0.6))
        strategy_config.MAX_ADD_LOADS = int(config.get("MAX_ADD_LOADS", 5))
        strategy_config.OPEN_POSITION = int(config.get("OPEN_POSITION", 2))
        strategy_config.BAR_INTERVAL = config.get("BAR_INTERVAL", "30 mins")

        # IV FILTERING PARAMETERS
        strategy_config.USE_IV_FILTER = config.get("USE_IV_FILTER", True)
        strategy_config.IV_ENTRY_THRESHOLD = float(config.get("IV_ENTRY_THRESHOLD", 0.30))
        strategy_config.USE_IV_SPIKE_EXIT = config.get("USE_IV_SPIKE_EXIT", False)
        strategy_config.IV_EXIT_THRESHOLD = float(config.get("IV_EXIT_THRESHOLD", 0.50))

        # Get initial balance from request
        try:
            balance_sources = [
                ("parameter", initial_balance),
                ("config", "initial_balance"),
                ("config", "initialBalance"),
                ("config", "INITIAL_CASH"),
            ]

            for source_type, source in balance_sources:
                if source_type == "parameter" and source is not None:
                    strategy_config.INITIAL_CASH = float(source)
                    print(f"Using initial balance from parameter: {source}")
                    break
                elif source_type == "config" and source in config:
                    strategy_config.INITIAL_CASH = float(config[source])
                    print(f"Using {source} from config: {config[source]}")
                    break
        except (ValueError, TypeError) as e:
            print(f"Error parsing initial balance: {e}, using default")

        # Debug print config
        print("\n=== OPTIONS_MARTIN CONFIG DEBUG ===")
        print("Full config from frontend:", config)
        print(f"\nOption Contract: {strategy_config.SYMBOL} {strategy_config.STRIKE}{strategy_config.RIGHT} exp={strategy_config.EXPIRATION}")
        print(f"Initial Cash: ${strategy_config.INITIAL_CASH:,.2f}")
        print(f"Entry Size: {strategy_config.OPEN_POSITION} contracts")
        print(f"Exit Target: {strategy_config.INC_INDEX}x")
        print(f"Add-Load Trigger: {strategy_config.DEC_INDEX}x")
        print(f"Max Pyramids: {strategy_config.MAX_ADD_LOADS}")
        print(f"Bar Interval: {strategy_config.BAR_INTERVAL}")
        print(f"\nIV Filtering:")
        print(f"  Use IV Filter: {strategy_config.USE_IV_FILTER}")
        print(f"  IV Entry Threshold: {strategy_config.IV_ENTRY_THRESHOLD}")
        print(f"  Use IV Spike Exit: {strategy_config.USE_IV_SPIKE_EXIT}")
        print(f"  IV Exit Threshold: {strategy_config.IV_EXIT_THRESHOLD}")
        print("=== END CONFIG DEBUG ===")

        # Initialize components
        print("\n=== Initializing MarketData for OPTION ===")
        market_data = MarketData(
            symbol=strategy_config.SYMBOL,
            strike=strategy_config.STRIKE,
            right=strategy_config.RIGHT,
            expiration=strategy_config.EXPIRATION,
            config=strategy_config
        )

        # Convert datetime objects to string dates
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")

        # Load option price data
        print(f"Loading option data for date range: {start_date_str} to {end_date_str}")
        market_data.load_data(start_date=start_date_str, end_date=end_date_str)
        print(f"Option data loaded successfully")

        print("\n=== Initializing PositionTracker ===")
        position = PositionTracker(strategy_config.INITIAL_CASH, strategy_config)
        print(f"PositionTracker initial balance: {position.cash}")

        print("\n=== Initializing OptionStrategy ===")
        strategy = OptionStrategy(strategy_config)
        print(f"OptionStrategy type: {strategy_config.STRATEGY_TYPE}")

        print("\n=== Creating TradingSimulator ===")
        simulator = TradingSimulator(market_data, position, strategy, strategy_config)
        print("TradingSimulator created with all components")

        print("\n=== Running Simulation ===")
        print(f"Running simulation from {start_date_str} to {end_date_str}")

        results_df = simulator.run(start_date=start_date_str, end_date=end_date_str)

        # Process results (same structure as SPY_POWER_CASHFLOW)
        daily_results = {}
        if results_df is not None and not results_df.empty:
            print(f"Results DataFrame columns: {results_df.columns.tolist()}")

            # Helper function for safe float conversion
            def safe_float(value):
                if pd.isna(value) or value is None:
                    return 0.0
                if isinstance(value, (int, float)):
                    if np.isinf(value):
                        return 0.0
                    return float(value)
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0

            def get_column_value(row, possible_names, default):
                for name in possible_names:
                    if name in row.index and not pd.isna(row.get(name)):
                        return row[name]
                return default

            # Clean dataframe
            cleaned_df = results_df.replace([np.inf, -np.inf], np.nan).fillna(0)
            print(f"Cleaned DataFrame shape: {cleaned_df.shape}")
            print(f"Cleaned DataFrame columns: {cleaned_df.columns.tolist()}")

            # Calculate IV statistics for frontend display
            iv_stats = None
            print(f"🔍 Checking for ImpliedVolatility column...")
            print(f"🔍 'ImpliedVolatility' in columns? {'ImpliedVolatility' in cleaned_df.columns}")
            if 'ImpliedVolatility' in cleaned_df.columns:
                iv_values = cleaned_df['ImpliedVolatility'].replace(0, np.nan).dropna()
                if len(iv_values) > 0:
                    iv_stats = {
                        'iv_min': float(iv_values.min()),
                        'iv_max': float(iv_values.max()),
                        'iv_mean': float(iv_values.mean()),
                        'iv_median': float(iv_values.median()),
                        'iv_std': float(iv_values.std()),
                    }
                    print(f"\nIV Statistics for this backtest:")
                    print(f"  Min: {iv_stats['iv_min']:.4f}")
                    print(f"  Max: {iv_stats['iv_max']:.4f}")
                    print(f"  Mean: {iv_stats['iv_mean']:.4f}")
                    print(f"  Median: {iv_stats['iv_median']:.4f}")
                    print(f"  Std Dev: {iv_stats['iv_std']:.4f}")

            # Process each row into daily_results format
            for idx in cleaned_df.index:
                row = cleaned_df.loc[idx]
                date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)

                result_dict = {
                    "Cash_Balance": safe_float(row.get("Cash_Balance", 0.0)),
                    "Position": int(safe_float(row.get("Position", 0))),
                    "Position_Balance": safe_float(row.get("Position_Balance", 0.0)),
                    "Portfolio_Value": safe_float(row.get("Portfolio_Value", 0.0)),
                    "Total_Rounds": int(safe_float(row.get("Total_Rounds", 0))),
                    "Total_Profit": safe_float(row.get("Total_Profit", 0.0)),
                    "Close": safe_float(row.get("Close", 0.0)),
                    "Open": safe_float(row.get("Open", 0.0)),
                    "High": safe_float(row.get("High", 0.0)),
                    "Low": safe_float(row.get("Low", 0.0)),
                    "Trading_Log": str(get_column_value(row, ["Trading_Log", "Trading Log", "trading_log"], "")),
                }

                daily_results[date_str] = result_dict

            # Add IV statistics as metadata
            if iv_stats:
                daily_results['__metadata__'] = {'iv_statistics': iv_stats}

            print(f"Processed {len(daily_results)} days of data")

        else:
            print("Warning: No results data returned from strategy simulation")

        return daily_results

    except Exception as e:
        print(f"Error in run_options_martin: {str(e)}")
        import traceback
        print(traceback.format_exc())
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
                days[day_data["date"].strftime("%Y-%m-%d")] = {
                    "balance": day_data["balance"],
                    "trades_count": day_data["trades_count"],
                    "profit_loss": day_data["profit_loss"],
                }

            simulation["daily_results"] = days
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
                "name": strategy_name,
                "path": path,
                "config_options": get_strategy_config_options(strategy_name),
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
    if strategy_name == "SPY_POWER_CASHFLOW":
        return {
            "symbol": "SPY",
            "buy_time": "9:35",
            "sell_time": "15:45",
            "stop_loss_pct": 0.50,
            "take_profit_pct": 1.00,
            "strategy_type": "power_cashflow",
            "option_type": "call",
            "dte_min": 1,
            "dte_max": 5,
            "delta_min": 0.40,
            "delta_max": 0.60,
            "commission": 0.65,
        }
    else:
        return {}


def test_imports():
    """Test function to verify imports work correctly"""
    try:
        print("Importing MarketData...")
        from market_data import MarketData  # noqa:F401

        print("Successfully imported MarketData")
        return True
    except ImportError as e:
        print(f"Failed to import MarketData: {str(e)}")
        return False
