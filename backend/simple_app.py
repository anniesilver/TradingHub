import logging
import os
import socket
import sys
import traceback
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from services.strategy_service import import_strategy, run_spy_power_cashflow, run_options_martin
from routes.market_data import market_data_bp


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error as e:
            logger.error(f"Port check error: {e}")
            return True


# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(market_data_bp)


@app.before_request
def log_request():
    logger.debug("Received request: %s %s", request.method, request.url)
    logger.debug("Headers: %s", request.headers)
    return None


@app.route("/", methods=["GET"])
def home():
    logger.info("Home endpoint called")
    return jsonify({"message": "Hello from Flask!"})


@app.route("/api/test", methods=["GET"])
def test():
    logger.info("Test endpoint called")
    return jsonify({"status": "ok", "timestamp": str(datetime.now())})


@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    logger.info("Strategies endpoint called")
    try:
        strategies = {"strategies": [{"id": "SPY_POWER_CASHFLOW", "name": "SPY Power Cashflow"}]}
        return jsonify(strategies)
    except Exception as e:
        logger.error(f"Error in strategies endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    logger.info("Simulation endpoint called")
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        logger.info(f"Received simulation request: {data}")
        logger.info(f"Request keys: {list(data.keys())}")
        logger.info(f"Config: {data.get('config')}")
        logger.info(f"initialBalance: {data.get('initialBalance')}")
        logger.info(f"initial_balance: {data.get('initial_balance')}")

        # Validate required fields
        required_fields = ["strategy_type", "config", "start_date", "end_date"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400

        # Parse dates
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")

        # Validate date range
        if start_date > end_date:
            return jsonify({"error": "Start date must be before end date"}), 400

        # Get initial balance from request or use default
        try:
            # Define possible parameter locations and names
            initial_balance = None
            param_locations = [
                ("root", "initial_balance"),
                ("root", "initialBalance"),
                ("config", "initial_balance"),
                ("config", "initialBalance"),
            ]

            # Check each possible location
            for location, param_name in param_locations:
                if location == "root" and param_name in data and data[param_name] is not None:
                    initial_balance = float(data[param_name])
                    logger.info(f"Using {param_name} from request: {initial_balance}")
                    break
                elif (
                    location == "config"
                    and "config" in data
                    and isinstance(data["config"], dict)
                    and param_name in data["config"]
                    and data["config"][param_name] is not None
                ):
                    initial_balance = float(data["config"][param_name])
                    logger.info(f"Using {param_name} from config: {initial_balance}")
                    break

            # If still None, use default
            if initial_balance is None:
                initial_balance = 500000.0
                logger.info(f"Using default initial balance: {initial_balance}")

        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing initial balance: {e}")
            initial_balance = 500000.0  # Fallback to default
            logger.info(f"Using fallback initial balance: {initial_balance}")

        # Import strategy modules
        TradingSimulator, OptionStrategy, success = import_strategy(data["strategy_type"])
        if not success:
            return jsonify({"error": "Failed to import strategy modules"}), 500

        # Run the actual strategy simulation
        try:
            if data["strategy_type"] == "SPY_POWER_CASHFLOW":
                logger.info("Running SPY Power Cashflow simulation with real simulator...")
                results = run_spy_power_cashflow(
                    TradingSimulator,
                    OptionStrategy,
                    data["config"],
                    start_date,
                    end_date,
                    initial_balance,
                )
                if results:
                    logger.info(f"Generated results for date range {start_date} to {end_date}")
                    # Log the first data point to verify structure
                    first_date = list(results.keys())[0]
                    logger.info(f"First data point structure: {results[first_date]}")
                    return jsonify(results)
                else:
                    return jsonify({"error": "Strategy simulation failed"}), 500
            elif data["strategy_type"] == "OPTIONS_MARTIN":
                logger.info("Running OPTIONS_MARTIN simulation with real option data...")
                results = run_options_martin(
                    TradingSimulator,
                    OptionStrategy,
                    data["config"],
                    start_date,
                    end_date,
                    initial_balance,
                )
                if results:
                    logger.info(f"Generated results for date range {start_date} to {end_date}")
                    first_date = list(results.keys())[0]
                    logger.info(f"First data point structure: {results[first_date]}")
                    return jsonify(results)
                else:
                    return jsonify({"error": "Strategy simulation failed"}), 500
            else:
                return jsonify({"error": "Unsupported strategy type"}), 400

        except Exception as e:
            logger.error(f"Strategy execution error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": f"Strategy execution failed: {str(e)}"}), 500

    except ValueError as e:
        logger.error(f"Date parsing error: {str(e)}")
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Error in simulation endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    try:
        port = 8080  # Using the working port

        # Log diagnostic information
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")

        # Check if port is already in use
        if is_port_in_use(port):
            logger.error(f"Port {port} is already in use!")
            sys.exit(1)

        logger.info(f"Starting Flask server on port {port}...")

        # Use the working configuration
        app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=False,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
