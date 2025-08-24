"""Market data API routes"""

from datetime import datetime
from flask import Blueprint, jsonify, request
import sys
import os
import pandas as pd

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

from ibkr_data_service import ibkr_service

# Create blueprint
market_data_bp = Blueprint('market_data', __name__)


@market_data_bp.route('/api/market-data/refresh/<symbol>', methods=['POST'])
def refresh_market_data(symbol):
    """Manually refresh market data for a symbol"""
    try:
        result = ibkr_service.refresh_data(symbol.upper())
        return jsonify(result), 200 if result['success'] else 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error refreshing data: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@market_data_bp.route('/api/market-data/status/<symbol>', methods=['GET'])
def get_data_status(symbol):
    """Get data status and coverage for a symbol"""
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date', '2015-01-01')
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Check what data we have in the database
        df = ibkr_service.get_data_from_db(symbol.upper(), start_date, end_date)
        
        if df.empty:
            return jsonify({
                'symbol': symbol.upper(),
                'has_data': False,
                'data_range': None,
                'record_count': 0,
                'last_updated': None,
                'coverage_start': None,
                'coverage_end': None
            }), 200
        
        return jsonify({
            'symbol': symbol.upper(),
            'has_data': True,
            'data_range': f"{df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}",
            'record_count': len(df),
            'coverage_start': df.index.min().strftime('%Y-%m-%d'),
            'coverage_end': df.index.max().strftime('%Y-%m-%d'),
            'requested_start': start_date,
            'requested_end': end_date,
            'complete_coverage': (
                pd.to_datetime(start_date) >= df.index.min() and 
                pd.to_datetime(end_date) <= df.index.max()
            )
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error checking data status: {str(e)}'
        }), 500


@market_data_bp.route('/api/market-data/test-connection', methods=['GET'])
def test_ibkr_connection():
    """Test IBKR connection"""
    try:
        from ibkr_data_service import IBKRDataClient, IBKR_CONFIG
        
        client = IBKRDataClient()
        success = client.connect_to_ibkr(IBKR_CONFIG["host"], IBKR_CONFIG["port"])
        
        if success:
            client.disconnect_from_ibkr()
            return jsonify({
                'success': True,
                'message': 'IBKR connection successful',
                'config': {
                    'host': IBKR_CONFIG["host"],
                    'port': IBKR_CONFIG["port"],
                    'client_id': IBKR_CONFIG["client_id"]
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'IBKR connection failed',
                'config': {
                    'host': IBKR_CONFIG["host"],
                    'port': IBKR_CONFIG["port"],
                    'client_id': IBKR_CONFIG["client_id"]
                }
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'IBKR connection test error: {str(e)}'
        }), 500


@market_data_bp.route('/api/market-data/available-symbols', methods=['GET'])
def get_available_symbols():
    """Get list of available symbols for data fetching"""
    return jsonify({
        'symbols': [
            {
                'symbol': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'type': 'STK',
                'exchange': 'SMART'
            },
            {
                'symbol': 'VIX',
                'name': 'CBOE Volatility Index',
                'type': 'IND',
                'exchange': 'CBOE'
            },
            {
                'symbol': 'QQQ',
                'name': 'Invesco QQQ Trust',
                'type': 'STK',
                'exchange': 'SMART'
            }
        ]
    })