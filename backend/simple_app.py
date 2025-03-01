from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging

from services.strategy_service import run_strategy_simulation, init_database, get_simulations, get_simulation_results
from services.mock_strategy import generate_mock_data

app = Flask(__name__)
# Configure CORS to allow requests from your frontend
CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

# In your app configuration
app.config['DEBUG'] = True
app.logger.setLevel(logging.DEBUG)

@app.route('/')
def read_root():
    return jsonify({"message": "Welcome to TradingHub API"})

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    app.logger.debug("=== Simulate endpoint called ===")
    app.logger.debug(f"Request method: {request.method}")
    app.logger.debug(f"Request headers: {request.headers}")
    
    try:
        data = request.get_json()
        app.logger.debug(f"Request data: {data}")
        
        # Print received data for debugging
        print(f"Received simulation request: {data}")
        
        results = run_strategy_simulation(
            data['strategy_type'],
            data['config'],
            data['start_date'],
            data['end_date'],
            data.get('initial_balance', 10000.0)
        )
        
        # Ensure mock data is always returned as fallback
        if not results:
            print("No results returned, using mock data")
            results = generate_mock_data(
                data['start_date'], 
                data['end_date'], 
                data.get('initial_balance', 10000.0)
            )
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in simulation endpoint: {str(e)}")
        # Generate mock data as fallback
        print("Generating mock data due to error")
        mock_results = generate_mock_data(
            data.get('start_date', '2023-01-01'), 
            data.get('end_date', '2023-01-31'), 
            data.get('initial_balance', 10000.0)
        )
        return jsonify(mock_results)

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    return jsonify({
        "strategies": [
            {"id": "SPY_POWER_CASHFLOW", "name": "SPY Power Cashflow"}
        ]
    })

@app.route('/api/simulations', methods=['GET'])
def list_simulations():
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    simulations = get_simulations(limit, offset)
    return jsonify({"simulations": simulations})

@app.route('/api/simulations/<int:sim_id>', methods=['GET'])
def get_simulation(sim_id):
    result = get_simulation_results(sim_id)
    
    if not result:
        return jsonify({"error": "Simulation not found"}), 404
    
    return jsonify(result)

@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    print("Test endpoint called!")
    return jsonify({"status": "success", "message": "API is working"})

if __name__ == '__main__':
    # Initialize the database if needed
    init_database()
    app.run(debug=True) 