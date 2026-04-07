#!/usr/bin/env python3
"""
Withdrawal Rate Comparison Test
Compares different monthly withdrawal rates for SPY_POWER_CASHFLOW strategy
from 2010-08-23 to 2025-09-22 with $200,000 initial investment
"""

import requests
import json
import pandas as pd
from datetime import datetime

# Configuration
API_URL = 'http://127.0.0.1:8080/api/simulate'
START_DATE = '2010-08-23'
END_DATE = '2025-09-22'
INITIAL_BALANCE = 200000
WITHDRAWAL_RATES = [0.5, 0.8, 1.0, 1.2]

def run_simulation(withdrawal_rate):
    """Run simulation with specified withdrawal rate"""
    payload = {
        "strategy_type": "SPY_POWER_CASHFLOW",
        "start_date": START_DATE,
        "end_date": END_DATE,
        "initial_balance": INITIAL_BALANCE,
        "config": {
            "SYMBOL": "SPY",
            "INITIAL_CASH": INITIAL_BALANCE,
            "MONTHLY_WITHDRAWAL_RATE": withdrawal_rate
        }
    }

    print(f"Running simulation with {withdrawal_rate}% monthly withdrawal rate...")

    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error running simulation for {withdrawal_rate}%: {e}")
        return None

def calculate_statistics(simulation_data):
    """Calculate key statistics from simulation data"""
    if not simulation_data:
        return None

    # Convert to list of daily data
    daily_data = []
    for date_str, data in simulation_data.items():
        daily_data.append({
            'date': date_str,
            'portfolio_value': data.get('Portfolio_Value', 0),
            'interest_paid': data.get('Interest_Paid', 0),
            'premiums_received': data.get('Premiums_Received', 0),
            'trading_log': data.get('Trading_Log', '')
        })

    # Sort by date
    daily_data.sort(key=lambda x: x['date'])

    if len(daily_data) < 2:
        return None

    # Calculate totals
    total_interest = sum(day['interest_paid'] for day in daily_data)
    total_premiums = sum(day['premiums_received'] for day in daily_data)

    # Calculate total withdrawals from trading logs
    total_withdrawals = 0
    for day in daily_data:
        log = day['trading_log']
        if 'Monthly withdrawal:' in log or 'WITHDRAWAL-CALC:' in log:
            # Extract withdrawal amount from log
            import re
            # Look for patterns like "Monthly withdrawal: $4,750.65" or "WITHDRAWAL-CALC: ... = $4,997.71"
            withdrawal_patterns = [
                r'Monthly withdrawal: \$([0-9,]+\.?[0-9]*)',
                r'WITHDRAWAL-CALC:.*=\s*\$([0-9,]+\.?[0-9]*)'
            ]
            for pattern in withdrawal_patterns:
                match = re.search(pattern, log)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    total_withdrawals += float(amount_str)
                    break

    # Calculate final portfolio value
    final_portfolio_value = daily_data[-1]['portfolio_value']
    initial_portfolio_value = daily_data[0]['portfolio_value']

    # Calculate annualized returns
    start_date = datetime.strptime(daily_data[0]['date'], '%Y-%m-%d')
    end_date = datetime.strptime(daily_data[-1]['date'], '%Y-%m-%d')
    years = (end_date - start_date).days / 365.25

    # Portfolio-only annualized return (excluding withdrawals)
    portfolio_only_return = 0
    if years > 0 and initial_portfolio_value > 0:
        portfolio_only_return = (pow(final_portfolio_value / initial_portfolio_value, 1/years) - 1) * 100

    # Total return including withdrawals but excluding interest costs
    total_value_generated = final_portfolio_value + total_withdrawals
    total_return_gross = 0
    if years > 0 and initial_portfolio_value > 0:
        total_return_gross = (pow(total_value_generated / initial_portfolio_value, 1/years) - 1) * 100

    # Net total return including withdrawals and deducting interest costs
    net_total_value = final_portfolio_value + total_withdrawals - total_interest
    net_total_return = 0
    if years > 0 and initial_portfolio_value > 0:
        net_total_return = (pow(net_total_value / initial_portfolio_value, 1/years) - 1) * 100

    return {
        'total_withdrawals': total_withdrawals,
        'total_premiums': total_premiums,
        'total_interest': total_interest,
        'final_portfolio_value': final_portfolio_value,
        'total_value_generated': total_value_generated,
        'net_total_value': net_total_value,
        'portfolio_only_return': portfolio_only_return,
        'total_return_gross': total_return_gross,
        'net_total_return': net_total_return,
        'years': years
    }

def main():
    """Main function to run all simulations and compare results"""
    print("=" * 80)
    print("SPY POWER CASHFLOW STRATEGY - WITHDRAWAL RATE COMPARISON")
    print("=" * 80)
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Investment: ${INITIAL_BALANCE:,}")
    print(f"Withdrawal Rates: {WITHDRAWAL_RATES}% monthly")
    print("=" * 80)

    results = []

    for rate in WITHDRAWAL_RATES:
        print(f"\nProcessing {rate}% withdrawal rate...")
        simulation_data = run_simulation(rate)

        if simulation_data:
            stats = calculate_statistics(simulation_data)
            if stats:
                results.append({
                    'Withdrawal Rate (%)': rate,
                    'Total Withdrawals ($)': stats['total_withdrawals'],
                    'Total Premiums ($)': stats['total_premiums'],
                    'Total Interest ($)': stats['total_interest'],
                    'Final Portfolio ($)': stats['final_portfolio_value'],
                    'Portfolio Return (%)': stats['portfolio_only_return'],
                    'Gross Total Return (%)': stats['total_return_gross'],
                    'Net Total Return (%)': stats['net_total_return'],
                    'Period (Years)': stats['years']
                })
                print(f"✓ Completed: Final portfolio ${stats['final_portfolio_value']:,.2f}, "
                      f"Net return {stats['net_total_return']:.2f}% annually")
            else:
                print(f"✗ Failed to calculate statistics for {rate}%")
        else:
            print(f"✗ Failed to run simulation for {rate}%")

    if not results:
        print("\nNo successful simulations to compare.")
        return

    # Create comparison table
    df = pd.DataFrame(results)

    print("\n" + "=" * 120)
    print("WITHDRAWAL RATE COMPARISON RESULTS")
    print("=" * 120)

    # Format the dataframe for better display
    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    # Custom formatting for currency columns
    formatted_df = df.copy()
    currency_columns = ['Total Withdrawals ($)', 'Total Premiums ($)', 'Total Interest ($)', 'Final Portfolio ($)']

    for col in currency_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.2f}")

    # Format percentage columns
    percentage_columns = ['Withdrawal Rate (%)', 'Portfolio Return (%)', 'Gross Total Return (%)', 'Net Total Return (%)']
    for col in percentage_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}%")

    # Format years
    if 'Period (Years)' in formatted_df.columns:
        formatted_df['Period (Years)'] = formatted_df['Period (Years)'].apply(lambda x: f"{x:.1f}")

    print(formatted_df.to_string(index=False))

    print("\n" + "=" * 120)
    print("ANALYSIS SUMMARY")
    print("=" * 120)

    if len(results) > 1:
        # Find best performing scenarios
        best_net_return = max(results, key=lambda x: x['Net Total Return (%)'])
        best_gross_return = max(results, key=lambda x: x['Gross Total Return (%)'])
        max_withdrawals = max(results, key=lambda x: x['Total Withdrawals ($)'])
        highest_final = max(results, key=lambda x: x['Final Portfolio ($)'])
        lowest_interest = min(results, key=lambda x: x['Total Interest ($)'])

        print(f"Best Net Total Return (after interest): {best_net_return['Withdrawal Rate (%)']}% rate with {best_net_return['Net Total Return (%)']:.2f}% annually")
        print(f"Best Gross Total Return (before interest): {best_gross_return['Withdrawal Rate (%)']}% rate with {best_gross_return['Gross Total Return (%)']:.2f}% annually")
        print(f"Maximum Withdrawals: {max_withdrawals['Withdrawal Rate (%)']}% rate with ${max_withdrawals['Total Withdrawals ($)']:,.2f}")
        print(f"Highest Final Portfolio: {highest_final['Withdrawal Rate (%)']}% rate with ${highest_final['Final Portfolio ($)']:,.2f}")
        print(f"Lowest Interest Cost: {lowest_interest['Withdrawal Rate (%)']}% rate with ${lowest_interest['Total Interest ($)']:,.2f}")

        # Show impact of interest costs
        print(f"\nInterest Cost Impact on Returns:")
        for result in results:
            gross_return = result['Gross Total Return (%)']
            net_return = result['Net Total Return (%)']
            interest_impact = gross_return - net_return
            print(f"  {result['Withdrawal Rate (%)']}% rate: {gross_return:.2f}% gross → {net_return:.2f}% net (interest cost: {interest_impact:.2f}%)")

        # Calculate total value generated
        print(f"\nNet Total Value (Final Portfolio + Withdrawals - Interest):")
        for result in results:
            net_value = result['Final Portfolio ($)'] + result['Total Withdrawals ($)'] - result['Total Interest ($)']
            print(f"  {result['Withdrawal Rate (%)']}% rate: ${net_value:,.2f}")

    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()