// Performance metrics derived from the daily backtest series.

export const TRADING_DAYS_PER_YEAR = 252;

const WITHDRAWAL_PATTERNS = [
  /Monthly withdrawal: \$([0-9,]+\.?[0-9]*)/,
  /\[WITHDRAWAL\].*\$([0-9,]+\.?[0-9]*)/,
];

// Returns the withdrawal amount recorded in one day's trading log, or 0.
export const extractWithdrawalAmount = (log) => {
  if (!log) return 0;
  for (const pattern of WITHDRAWAL_PATTERNS) {
    const match = log.match(pattern);
    if (match) {
      const amount = parseFloat(match[1].replace(/,/g, ''));
      return !isNaN(amount) && amount >= 0 ? amount : 0;
    }
  }
  return 0;
};

// Annualized Sharpe ratio from daily portfolio values.
// Withdrawals are cash leaving the account, not losses, so they are added back to
// that day's value before computing its return. The simulator records the withdrawal
// on the same row where Portfolio_Value drops.
// riskFreeRate is an annual fraction (0.05 = 5%); returns null when not computable.
export const computeSharpeRatio = (
  series,
  { riskFreeRate = 0, periodsPerYear = TRADING_DAYS_PER_YEAR } = {}
) => {
  if (!Array.isArray(series) || series.length < 3) return null;

  const dailyRiskFree = riskFreeRate / periodsPerYear;
  const excessReturns = [];
  for (let i = 1; i < series.length; i++) {
    const previous = Number(series[i - 1].Portfolio_Value);
    const current = Number(series[i].Portfolio_Value);
    if (!(previous > 0) || !isFinite(current)) continue;
    const withdrawal = extractWithdrawalAmount(series[i].Trading_Log);
    excessReturns.push((current + withdrawal) / previous - 1 - dailyRiskFree);
  }
  if (excessReturns.length < 2) return null;

  const mean = excessReturns.reduce((sum, r) => sum + r, 0) / excessReturns.length;
  const variance =
    excessReturns.reduce((sum, r) => sum + (r - mean) ** 2, 0) / (excessReturns.length - 1);
  const stdDev = Math.sqrt(variance);
  if (!(stdDev > 0)) return null;

  return (mean / stdDev) * Math.sqrt(periodsPerYear);
};
