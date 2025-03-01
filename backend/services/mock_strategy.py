import random
from datetime import datetime, timedelta

def generate_mock_data(start_date, end_date, initial_balance=10000.0):
    """Generate mock trading data for testing the API."""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    daily_results = {}
    current_balance = initial_balance
    
    current_date = start_dt
    while current_date <= end_dt:
        if current_date.weekday() < 5:  # Only trading days (Mon-Fri)
            # Generate random daily P&L between -3% and +5%
            daily_pl = current_balance * random.uniform(-0.03, 0.05)
            trades_count = random.randint(1, 5)
            
            current_balance += daily_pl
            
            date_str = current_date.strftime('%Y-%m-%d')
            daily_results[date_str] = {
                'balance': current_balance,
                'trades_count': trades_count,
                'profit_loss': daily_pl
            }
        
        current_date += timedelta(days=1)
    
    return daily_results 