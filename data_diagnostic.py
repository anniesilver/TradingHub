#!/usr/bin/env python3
"""
Data Diagnostic Tool
Diagnoses data availability issues for 2000-2009 period
Checks what data is actually being retrieved vs what should be available
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta

API_URL = 'http://127.0.0.1:8080/api/simulate'

def test_data_availability():
    """Test data availability for different periods"""
    test_periods = [
        # Test each year individually
        ('2000-01-01', '2000-12-31', '2000'),
        ('2001-01-01', '2001-12-31', '2001'),
        ('2002-01-01', '2002-12-31', '2002'),
        ('2003-01-01', '2003-12-31', '2003'),
        ('2004-01-01', '2004-12-31', '2004'),
        ('2005-01-01', '2005-12-31', '2005'),
        ('2006-01-01', '2006-12-31', '2006'),
        ('2007-01-01', '2007-12-31', '2007'),
        ('2008-01-01', '2008-12-31', '2008'),
        ('2009-01-01', '2009-12-31', '2009'),
        # Test full period
        ('2000-01-01', '2009-12-31', 'Full 2000-2009'),
        # Test recent period for comparison
        ('2020-01-01', '2020-12-31', '2020 (known working)')
    ]

    print("=" * 80)
    print("DATA AVAILABILITY DIAGNOSTIC")
    print("=" * 80)
    print("Testing data retrieval for different periods...")
    print()

    results = []

    for start_date, end_date, period_name in test_periods:
        print(f"Testing {period_name} ({start_date} to {end_date})...")

        payload = {
            "strategy_type": "SPY_POWER_CASHFLOW",
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": 200000,
            "config": {
                "SYMBOL": "SPY",
                "INITIAL_CASH": 200000,
                "MONTHLY_WITHDRAWAL_RATE": 1.0
            }
        }

        try:
            response = requests.post(API_URL, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()

                if data:
                    # Count data points
                    data_points = len(data)

                    # Get date range from actual data
                    dates = list(data.keys())
                    dates.sort()

                    if dates:
                        actual_start = dates[0]
                        actual_end = dates[-1]

                        # Calculate expected trading days (roughly 252 per year)
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        total_days = (end_dt - start_dt).days
                        expected_trading_days = int(total_days * (252/365))

                        coverage_percent = (data_points / expected_trading_days * 100) if expected_trading_days > 0 else 0

                        results.append({
                            'period': period_name,
                            'requested_start': start_date,
                            'requested_end': end_date,
                            'actual_start': actual_start,
                            'actual_end': actual_end,
                            'data_points': data_points,
                            'expected_days': expected_trading_days,
                            'coverage_percent': coverage_percent,
                            'status': 'SUCCESS'
                        })

                        print(f"  ✓ SUCCESS: {data_points} data points")
                        print(f"    Requested: {start_date} to {end_date}")
                        print(f"    Actual: {actual_start} to {actual_end}")
                        print(f"    Coverage: {coverage_percent:.1f}% of expected trading days")

                        # Check for data quality issues
                        sample_data = data[dates[0]]
                        initial_portfolio = sample_data.get('Portfolio_Value', 0)
                        if initial_portfolio <= 0:
                            print(f"    ⚠ WARNING: Initial portfolio is ${initial_portfolio}")
                    else:
                        print(f"  ✗ FAILED: No date data in response")
                        results.append({
                            'period': period_name,
                            'status': 'NO_DATES',
                            'data_points': 0,
                            'coverage_percent': 0
                        })
                else:
                    print(f"  ✗ FAILED: Empty response")
                    results.append({
                        'period': period_name,
                        'status': 'EMPTY_RESPONSE',
                        'data_points': 0,
                        'coverage_percent': 0
                    })
            else:
                print(f"  ✗ FAILED: HTTP {response.status_code}")
                results.append({
                    'period': period_name,
                    'status': f'HTTP_{response.status_code}',
                    'data_points': 0,
                    'coverage_percent': 0
                })

        except requests.exceptions.Timeout:
            print(f"  ✗ FAILED: Request timeout")
            results.append({
                'period': period_name,
                'status': 'TIMEOUT',
                'data_points': 0,
                'coverage_percent': 0
            })
        except Exception as e:
            print(f"  ✗ FAILED: {str(e)}")
            results.append({
                'period': period_name,
                'status': f'ERROR: {str(e)}',
                'data_points': 0,
                'coverage_percent': 0
            })

        print()

    return results

def analyze_results(results):
    """Analyze the diagnostic results"""
    print("=" * 80)
    print("DIAGNOSTIC ANALYSIS")
    print("=" * 80)

    successful_periods = [r for r in results if r['status'] == 'SUCCESS']
    failed_periods = [r for r in results if r['status'] != 'SUCCESS']

    print(f"Successful periods: {len(successful_periods)}")
    print(f"Failed periods: {len(failed_periods)}")
    print()

    if failed_periods:
        print("FAILED PERIODS:")
        for period in failed_periods:
            print(f"  • {period['period']}: {period['status']}")
        print()

    if successful_periods:
        print("DATA COVERAGE ANALYSIS:")
        for period in successful_periods:
            if 'coverage_percent' in period:
                status_icon = "✓" if period['coverage_percent'] > 80 else "⚠" if period['coverage_percent'] > 50 else "✗"
                print(f"  {status_icon} {period['period']}: {period['coverage_percent']:.1f}% coverage "
                      f"({period['data_points']} points)")
        print()

    # Identify the data gap
    print("DATA GAP ANALYSIS:")
    earliest_successful = None
    latest_successful = None

    for period in successful_periods:
        if 'actual_start' in period:
            period_start = period['actual_start']
            if earliest_successful is None or period_start < earliest_successful:
                earliest_successful = period_start
            if latest_successful is None or period_start > latest_successful:
                latest_successful = period_start

    if earliest_successful and latest_successful:
        print(f"  Earliest available data: {earliest_successful}")
        print(f"  Latest available data: {latest_successful}")

        # Check if 2000-2009 data is available
        early_2000s = [p for p in successful_periods if p['period'].startswith('200') and int(p['period'][:4]) <= 2005]
        if not early_2000s:
            print(f"  ✗ CRITICAL: No data available for early 2000s (dot-com crash period)")
        else:
            print(f"  ✓ Early 2000s data available: {len(early_2000s)} years")

    print()
    print("RECOMMENDATIONS:")
    if len(failed_periods) > len(successful_periods):
        print("  • Major data retrieval issues detected")
        print("  • Check TWS/IB Gateway connection and configuration")
        print("  • Verify database setup and data import process")
    elif not successful_periods or all(p.get('coverage_percent', 0) < 50 for p in successful_periods):
        print("  • Insufficient data coverage")
        print("  • May need to import historical data to database")
        print("  • Check IBKR data service configuration")
    else:
        print("  • Data retrieval appears functional")
        print("  • Focus on specific periods with low coverage")

def main():
    """Main diagnostic function"""
    print("Starting data diagnostic for 2000-2009 period...")
    print("This will test data availability year by year to identify gaps.")
    print()

    results = test_data_availability()
    analyze_results(results)

    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("Review the results above to identify data availability issues.")
    print("If specific years are missing, investigate:")
    print("1. TWS/IB Gateway connection")
    print("2. Database import process")
    print("3. Date range limitations in IBKR API")
    print("4. Historical data subscription requirements")

if __name__ == "__main__":
    main()