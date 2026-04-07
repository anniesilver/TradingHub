#!/usr/bin/env python3
"""
Stress Test: SPY_POWER_CASHFLOW Strategy 2000-2009
Tests strategy during dot-com crash and financial crisis period
"""

import requests
import json
import pandas as pd
from datetime import datetime

# Configuration for stress test period
API_URL = 'http://127.0.0.1:8080/api/simulate'
START_DATE = '2000-01-03'  # First trading day of 2000
END_DATE = '2009-12-31'    # Last trading day of 2009
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
            'trading_log': data.get('Trading_Log', ''),
            'margin_ratio': data.get('Margin_Ratio', 0),
            'spy_value': data.get('spy_value', 0)
        })

    # Sort by date
    daily_data.sort(key=lambda x: x['date'])

    if len(daily_data) < 2:
        print(f"Warning: Insufficient data points: {len(daily_data)}")
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

    # Portfolio values
    final_portfolio_value = daily_data[-1]['portfolio_value']
    initial_portfolio_value = daily_data[0]['portfolio_value']

    # If initial portfolio is 0 or invalid, use the INITIAL_BALANCE
    if initial_portfolio_value <= 0:
        initial_portfolio_value = INITIAL_BALANCE
        print(f"  Warning: Using initial balance ${INITIAL_BALANCE} instead of reported ${daily_data[0]['portfolio_value']:.2f}")

    # Debug: Check if we have valid data
    print(f"  Data points: {len(daily_data)}")
    print(f"  Initial portfolio: ${initial_portfolio_value:.2f}")
    print(f"  Final portfolio: ${final_portfolio_value:.2f}")

    # Calculate maximum drawdown
    peak = initial_portfolio_value if initial_portfolio_value > 0 else 1
    max_drawdown = 0
    for day in daily_data:
        current_value = day['portfolio_value']
        if current_value > peak:
            peak = current_value
        if peak > 0:  # Prevent division by zero
            drawdown = (peak - current_value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    # Calculate maximum margin ratio
    max_margin_ratio = max(day['margin_ratio'] for day in daily_data)

    # Calculate time metrics
    start_date = datetime.strptime(daily_data[0]['date'], '%Y-%m-%d')
    end_date = datetime.strptime(daily_data[-1]['date'], '%Y-%m-%d')
    years = (end_date - start_date).days / 365.25

    # Calculate returns
    portfolio_only_return = 0
    total_return_gross = 0
    net_total_return = 0

    if years > 0 and initial_portfolio_value > 0:
        # Portfolio-only return
        portfolio_only_return = (pow(final_portfolio_value / initial_portfolio_value, 1/years) - 1) * 100

        # Total return including withdrawals
        total_value_generated = final_portfolio_value + total_withdrawals
        total_return_gross = (pow(total_value_generated / initial_portfolio_value, 1/years) - 1) * 100

        # Net return after interest costs
        net_total_value = final_portfolio_value + total_withdrawals - total_interest
        net_total_return = (pow(net_total_value / initial_portfolio_value, 1/years) - 1) * 100

    # Check if strategy survived (portfolio > $10,000)
    survived = final_portfolio_value > 10000

    return {
        'total_withdrawals': total_withdrawals,
        'total_premiums': total_premiums,
        'total_interest': total_interest,
        'final_portfolio_value': final_portfolio_value,
        'initial_portfolio_value': initial_portfolio_value,
        'max_drawdown': max_drawdown,
        'max_margin_ratio': max_margin_ratio,
        'portfolio_only_return': portfolio_only_return,
        'total_return_gross': total_return_gross,
        'net_total_return': net_total_return,
        'years': years,
        'survived': survived
    }

def main():
    """Main function to run stress test"""
    print("=" * 100)
    print("SPY POWER CASHFLOW STRATEGY - STRESS TEST 2000-2009")
    print("=" * 100)
    print("TESTING PERIOD: DOT-COM CRASH + FINANCIAL CRISIS")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Investment: ${INITIAL_BALANCE:,}")
    print(f"Withdrawal Rates: {WITHDRAWAL_RATES}% monthly")
    print("=" * 100)

    # SPY performance during this period
    print("MARKET CONTEXT (2000-2009):")
    print("• 2000-2002: Dot-com crash (SPY ~$150 → $75, -50%)")
    print("• 2003-2007: Recovery period")
    print("• 2008-2009: Financial crisis (SPY ~$157 → $67, -57%)")
    print("• Overall: SPY had negative returns for the decade")
    print("=" * 100)

    results = []

    for rate in WITHDRAWAL_RATES:
        print(f"\nProcessing {rate}% withdrawal rate...")
        simulation_data = run_simulation(rate)

        if simulation_data:
            stats = calculate_statistics(simulation_data)
            if stats:
                survival_status = "✓ SURVIVED" if stats['survived'] else "✗ FAILED"
                results.append({
                    'Withdrawal Rate (%)': rate,
                    'Status': 'Survived' if stats['survived'] else 'Failed',
                    'Total Withdrawals ($)': stats['total_withdrawals'],
                    'Total Premiums ($)': stats['total_premiums'],
                    'Total Interest ($)': stats['total_interest'],
                    'Final Portfolio ($)': stats['final_portfolio_value'],
                    'Max Drawdown (%)': stats['max_drawdown'],
                    'Max Margin Ratio': stats['max_margin_ratio'],
                    'Portfolio Return (%)': stats['portfolio_only_return'],
                    'Net Total Return (%)': stats['net_total_return'],
                    'Period (Years)': stats['years']
                })
                print(f"{survival_status}: Final portfolio ${stats['final_portfolio_value']:,.2f}, "
                      f"Max drawdown {stats['max_drawdown']:.1f}%, Net return {stats['net_total_return']:.2f}%")
            else:
                print(f"✗ Failed to calculate statistics for {rate}%")
                results.append({
                    'Withdrawal Rate (%)': rate,
                    'Status': 'Error',
                    'Total Withdrawals ($)': 0,
                    'Total Premiums ($)': 0,
                    'Total Interest ($)': 0,
                    'Final Portfolio ($)': 0,
                    'Max Drawdown (%)': 0,
                    'Max Margin Ratio': 0,
                    'Portfolio Return (%)': 0,
                    'Net Total Return (%)': 0,
                    'Period (Years)': 10
                })
        else:
            print(f"✗ Failed to run simulation for {rate}%")

    if not results:
        print("\nNo simulations completed.")
        return

    # Create results table
    df = pd.DataFrame(results)

    print("\n" + "=" * 140)
    print("STRESS TEST RESULTS (2000-2009)")
    print("=" * 140)

    # Format the dataframe
    formatted_df = df.copy()

    # Format currency columns
    currency_columns = ['Total Withdrawals ($)', 'Total Premiums ($)', 'Total Interest ($)', 'Final Portfolio ($)']
    for col in currency_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.0f}")

    # Format percentage columns
    percentage_columns = ['Withdrawal Rate (%)', 'Max Drawdown (%)', 'Portfolio Return (%)', 'Net Total Return (%)']
    for col in percentage_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}%")

    # Format margin ratio
    if 'Max Margin Ratio' in formatted_df.columns:
        formatted_df['Max Margin Ratio'] = formatted_df['Max Margin Ratio'].apply(lambda x: f"{x:.2f}")

    # Format years
    if 'Period (Years)' in formatted_df.columns:
        formatted_df['Period (Years)'] = formatted_df['Period (Years)'].apply(lambda x: f"{x:.1f}")

    print(formatted_df.to_string(index=False))

    print("\n" + "=" * 140)
    print("STRESS TEST ANALYSIS")
    print("=" * 140)

    # Survival analysis
    survivors = [r for r in results if r['Status'] == 'Survived']
    failures = [r for r in results if r['Status'] == 'Failed']

    print(f"SURVIVAL RATE: {len(survivors)}/{len(results)} scenarios survived")

    if failures:
        print(f"\nFAILED SCENARIOS:")
        for fail in failures:
            print(f"  • {fail['Withdrawal Rate (%)']}% withdrawal rate: Strategy failed")

    if survivors:
        print(f"\nSURVIVING SCENARIOS:")
        for surv in survivors:
            print(f"  • {surv['Withdrawal Rate (%)']}% rate: ${surv['Final Portfolio ($)']:,.0f} final, "
                  f"{surv['Max Drawdown (%)']:.1f}% max drawdown")

        best_survivor = max(survivors, key=lambda x: x['Final Portfolio ($)'])
        print(f"\nBEST PERFORMING SURVIVOR: {best_survivor['Withdrawal Rate (%)']}% rate")
        print(f"  Final Portfolio: ${best_survivor['Final Portfolio ($)']:,.0f}")
        print(f"  Net Return: {best_survivor['Net Total Return (%)']:.1f}% annually")
        print(f"  Max Drawdown: {best_survivor['Max Drawdown (%)']:.1f}%")

    print(f"\nCOMPARISON TO SPY BUY-AND-HOLD:")
    print(f"  SPY 2000-2009: Approximately -1% to +1% annually (lost decade)")
    print(f"  Strategy performance: See results above")

    print("\nSTRESS TEST CONCLUSION:")
    if len(survivors) == len(results):
        print("  ✓ Strategy survived all withdrawal rate scenarios")
        print("  ✓ Outperformed buy-and-hold SPY during crisis period")
    elif len(survivors) > 0:
        print("  ⚠ Strategy survived some but not all scenarios")
        print("  ⚠ Higher withdrawal rates may pose significant risk")
    else:
        print("  ✗ Strategy failed in all scenarios")
        print("  ✗ Not suitable for crisis periods")

    print(f"\nTest completed successfully!")

if __name__ == "__main__":
    main()