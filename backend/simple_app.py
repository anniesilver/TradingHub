import logging
import os
import socket
import sys
import traceback
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from services.strategy_service import import_strategy, run_spy_power_cashflow, run_options_martin, run_spy500_leader
from services.wheel_service import run_wheel, wheel_params
from services.options_martin_service import options_martin_params, run_options_martin_kit
from services.spy_power_cashflow_service import run_spy_power_cashflow_rules, spy_power_cashflow_params
from services import paper_test_service
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


@app.route("/api/strategies/WHEEL/params", methods=["GET"])
def get_wheel_params():
    """The Wheel rules' parameters (defaults, ranges, help) straight from algo_trading/shared."""
    try:
        return jsonify(wheel_params())
    except Exception as e:
        logger.error(f"Error reading Wheel parameters: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/strategies/SPY_POWER_CASHFLOW_RULES/params", methods=["GET"])
def get_spy_power_cashflow_params():
    """The SPY_POWER_CASHFLOW rules' parameters (defaults, ranges, help) straight from algo_trading/shared."""
    try:
        return jsonify(spy_power_cashflow_params())
    except Exception as e:
        logger.error(f"Error reading SPY_POWER_CASHFLOW parameters: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/strategies/OPTIONS_MARTIN/params", methods=["GET"])
def get_options_martin_params():
    """The OPTIONS_MARTIN rules' parameters (defaults, ranges, help) straight from algo_trading/shared."""
    try:
        return jsonify(options_martin_params())
    except Exception as e:
        logger.error(f"Error reading OPTIONS_MARTIN parameters: {str(e)}")
        return jsonify({"error": str(e)}), 500


def _from_this_pc() -> bool:
    """Paper-test routes change what the server trades, so only TradingHub's own page may call
    them: a browser always sends Origin on cross-site requests, and any other website's is refused
    (CORS(app) above allows every origin for the read-only routes)."""
    origin = request.headers.get("Origin")
    if origin is None:
        return True  # not from a web page (e.g. curl on this PC)
    from urllib.parse import urlparse
    return urlparse(origin).hostname in ("localhost", "127.0.0.1")


@app.before_request
def guard_paper_test():
    if request.path.startswith("/api/paper-test") and not _from_this_pc():
        return jsonify({"error": "paper tests can only be started from TradingHub on this PC"}), 403
    return None


@app.route("/api/paper-test/<strategy_id>", methods=["GET"])
def paper_test_status(strategy_id):
    """The strategy's paper test on the trade-engine server: what runs, what it holds."""
    try:
        return jsonify(paper_test_service.status(strategy_id, quotes=request.args.get("quotes", "1") != "0"))
    except paper_test_service.PaperTestError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Paper test status error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/paper-test/<strategy_id>/start", methods=["POST"])
def paper_test_start(strategy_id):
    """Start a paper test with the page's parameters. close_out: close what it holds first."""
    data = request.get_json() or {}
    try:
        return jsonify(paper_test_service.start(strategy_id, data.get("config") or {}, data.get("dry_run", False),
                                                data.get("close_out", False), data.get("label", "")))
    except paper_test_service.PaperTestError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Paper test start error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/paper-test/<strategy_id>/cancel", methods=["POST"])
def paper_test_cancel(strategy_id):
    """Drop a test that is still waiting for its close-out."""
    try:
        return jsonify(paper_test_service.cancel(strategy_id))
    except paper_test_service.PaperTestError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/paper-tests", methods=["GET"])
def paper_tests_history():
    """Every paper test so far (finished and running, legacy runs included), from the database.
    ?strategy=WHEEL|OPTIONS_MARTIN|<server name>  ?trades=1 adds every trade
    ?sync=0 skips copying the latest from the trade-engine server first."""
    from services import paper_test_history_service as history

    strategy = request.args.get("strategy") or None
    if strategy:
        strategy = paper_test_service.SERVER_NAMES.get(strategy, strategy)
    sync_error = None
    if request.args.get("sync", "1") != "0":
        try:
            history.sync()
        except Exception as e:  # server unreachable: still show what the database has
            sync_error = str(e)
            logger.warning(f"Paper test history sync failed: {e}")
    try:
        tests = history.list_tests(strategy, with_trades=request.args.get("trades") == "1")
    except Exception as e:
        logger.error(f"Paper test history error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    return jsonify({"tests": tests, "sync_error": sync_error})


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

        # WHEEL runs the shared tradekit rules (algo_trading/shared), not an old-style simulator
        if data["strategy_type"] == "WHEEL":
            try:
                results = run_wheel(data["config"], start_date, end_date, initial_balance)
                return jsonify(results)
            except ValueError as e:
                logger.error(f"WHEEL settings error: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"WHEEL execution error: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({"error": f"Strategy execution failed: {str(e)}"}), 500

        # SPY_POWER_CASHFLOW on the shared rules; the old simulator stays as SPY_POWER_CASHFLOW
        if data["strategy_type"] == "SPY_POWER_CASHFLOW_RULES":
            try:
                results = run_spy_power_cashflow_rules(data["config"], start_date, end_date, initial_balance)
                return jsonify(results)
            except ValueError as e:
                logger.error(f"SPY_POWER_CASHFLOW_RULES settings error: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"SPY_POWER_CASHFLOW_RULES execution error: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({"error": f"Strategy execution failed: {str(e)}"}), 500

        # OPTIONS_MARTIN runs the shared tradekit rules too; the old simulator is OPTIONS_MARTIN_LEGACY
        if data["strategy_type"] == "OPTIONS_MARTIN":
            try:
                results = run_options_martin_kit(data["config"], start_date, end_date, initial_balance)
                return jsonify(results)
            except ValueError as e:
                logger.error(f"OPTIONS_MARTIN settings error: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"OPTIONS_MARTIN execution error: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({"error": f"Strategy execution failed: {str(e)}"}), 500

        # Import strategy modules
        legacy = data["strategy_type"] == "OPTIONS_MARTIN_LEGACY"
        TradingSimulator, OptionStrategy, success = import_strategy(
            "OPTIONS_MARTIN" if legacy else data["strategy_type"])
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
            elif legacy:
                logger.info("Running the old OPTIONS_MARTIN simulator with real option data...")
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
            elif data["strategy_type"] == "SPY500_LEADER":
                logger.info("Running SPY500_LEADER simulation...")
                results = run_spy500_leader(
                    TradingSimulator,
                    OptionStrategy,  # This is actually LeaderStrategy for SPY500_LEADER
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
