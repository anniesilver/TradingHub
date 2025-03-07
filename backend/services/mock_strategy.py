import random
from datetime import datetime, timedelta

def generate_mock_data(start_date, end_date, initial_balance=10000.0):
    """Generate mock trading data for testing the API."""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') if isinstance(end_date, str) else end_date
    
    daily_results = {}
    current_balance = initial_balance
    portfolio_value = initial_balance
    spy_price = 450.0  # Starting SPY price
    
    current_date = start_dt
    while current_date <= end_dt:
        if current_date.weekday() < 5:  # Only trading days (Mon-Fri)
            # Generate random daily changes
            daily_pl = portfolio_value * random.uniform(-0.03, 0.05)
            trades_count = random.randint(1, 5)
            spy_change = random.uniform(-0.02, 0.03)
            
            # Update values
            portfolio_value += daily_pl
            current_balance = portfolio_value * random.uniform(0.3, 0.7)  # Random cash balance
            spy_price *= (1 + spy_change)
            
            date_str = current_date.strftime('%Y-%m-%d')
            daily_results[date_str] = {
                'Portfolio_Value': portfolio_value,
                'Cash_Balance': current_balance,
                'Trades': trades_count,
                'Daily_PnL': daily_pl,
                'Interest_Paid': random.uniform(0, 10),
                'Premiums_Received': random.uniform(100, 500),
                'Commissions_Paid': trades_count * 0.65,
                'Open_Positions': random.randint(0, 3),
                'Closed_Positions': random.randint(0, 3),
                'Close': spy_price,
                'Open': spy_price * (1 + random.uniform(-0.005, 0.005)),
                'High': spy_price * (1 + random.uniform(0, 0.01)),
                'Low': spy_price * (1 + random.uniform(-0.01, 0)),
                'VIX': random.uniform(15, 25),
                'Margin_Ratio': random.uniform(0.1, 0.4),
                'Trading_Log': f"Executed {trades_count} trades"
            }
        
        current_date += timedelta(days=1)
    
    return daily_results 