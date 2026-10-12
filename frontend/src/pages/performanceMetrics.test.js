import { computeSharpeRatio, extractWithdrawalAmount } from './performanceMetrics';

const day = (Portfolio_Value, Trading_Log = '') => ({ Portfolio_Value, Trading_Log });

test('extracts withdrawal amounts from trading logs', () => {
  expect(extractWithdrawalAmount('Monthly withdrawal: $2,000.50 (1.0% of $200,050.00)')).toBe(2000.5);
  expect(extractWithdrawalAmount('Bought 10 shares')).toBe(0);
  expect(extractWithdrawalAmount(undefined)).toBe(0);
});

test('matches a hand-computed annualized Sharpe ratio', () => {
  // Daily returns: +1%, -1%, +2%  -> mean 0.006667, sample stdev 0.015275
  const series = [day(100), day(101), day(99.99), day(101.9898)];
  const expected = (0.02 / 3 / 0.015275252316519466) * Math.sqrt(252);
  expect(computeSharpeRatio(series)).toBeCloseTo(expected, 6);
});

test('adds withdrawals back so they do not count as losses', () => {
  const withoutWithdrawal = [day(100), day(101), day(99.99), day(101.9898)];
  // Same daily returns, but $1 leaves the account on day 3.
  const withWithdrawal = [
    day(100),
    day(101),
    day(98.99, 'Monthly withdrawal: $1.00 (1.0% of $99.99)'),
    day(100.9698),
  ];
  expect(computeSharpeRatio(withWithdrawal)).toBeCloseTo(computeSharpeRatio(withoutWithdrawal), 6);
});

test('subtracts the risk-free rate', () => {
  const series = [day(100), day(101), day(99.99), day(101.9898)];
  expect(computeSharpeRatio(series, { riskFreeRate: 0.05 })).toBeLessThan(computeSharpeRatio(series));
});

test('returns null when there is not enough data or no volatility', () => {
  expect(computeSharpeRatio([])).toBeNull();
  expect(computeSharpeRatio([day(100), day(101)])).toBeNull();
  expect(computeSharpeRatio([day(100), day(100), day(100)])).toBeNull();
});
