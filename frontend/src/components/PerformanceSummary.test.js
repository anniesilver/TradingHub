import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import PerformanceSummary from './PerformanceSummary';

const context = { config: { initialBalance: 100000, riskFreeRate: 0.04 } };
const fixture = {
  chartData: [
    { date: '2025-01-01', Portfolio_Value: 100000 },
    { date: '2025-07-01', Portfolio_Value: 95000 },
    { date: '2026-01-01', Portfolio_Value: 110000 },
  ],
  annualizedReturn: 0.125,
  maxDrawdown: -0.05,
  sharpeRatio: 1.27,
  sharpeRiskFreeRate: 0.05,
  totalPremiumsReceived: 12345.67,
  totalDividendsReceived: 100,
  totalInterestPaid: 250.5,
  totalAssignedCost: 1200,
  totalWithdrawAmount: 2500,
};
const metric = name => screen.getByText(name).closest('.performance-metric, .performance-cash-row');

test('organizes all eight existing metrics with explicit units and methodology', () => {
  render(<PerformanceSummary data={fixture} resultContext={context} />);
  expect(screen.getByRole('region', { name: 'Performance summary' })).toBeInTheDocument();
  expect(metric('CAGR')).toHaveTextContent('12.50%');
  expect(metric('Maximum drawdown (MDD)')).toHaveTextContent('-5.00%');
  expect(metric('Sharpe ratio')).toHaveTextContent('1.27');
  expect(metric('Sharpe ratio')).not.toHaveTextContent('1.27%');
  expect(metric('Premiums received')).toHaveTextContent('$12,345.67');
  expect(metric('Dividends received')).toHaveTextContent('$100.00');
  expect(metric('Interest paid')).toHaveTextContent('$250.50');
  expect(metric('ITM call closure costs')).toHaveTextContent('$1,200.00');
  expect(metric('Withdrawals')).toHaveTextContent('$2,500.00');
  const details = screen.getByText('Calculation details').closest('details');
  expect(details).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText('Calculation details'));
  expect(details).toHaveAttribute('open');
  expect(details).toHaveTextContent('2025-01-01 — 2026-01-01');
  expect(details).toHaveTextContent('Risk-free rate: 5.00% per year');
  expect(details).toHaveTextContent('$112,500.00');
  expect(details).toHaveTextContent('sample standard deviation');
  expect(details).toHaveTextContent('withdrawals can affect this measure');
});

test('keeps legitimate zero totals and signed metrics visible', () => {
  render(<PerformanceSummary data={{ ...fixture, annualizedReturn: -0.07, sharpeRatio: -0.42, maxDrawdown: 0,
    totalPremiumsReceived: 0, totalDividendsReceived: 0, totalInterestPaid: 0, totalAssignedCost: 0, totalWithdrawAmount: 0 }} resultContext={context} />);
  expect(metric('CAGR')).toHaveTextContent('-7.00%');
  expect(metric('Sharpe ratio')).toHaveTextContent('-0.42');
  expect(metric('Maximum drawdown (MDD)')).toHaveTextContent('0.00%');
  ['Premiums received', 'Dividends received', 'Interest paid', 'ITM call closure costs', 'Withdrawals'].forEach(name => expect(metric(name)).toHaveTextContent('$0.00'));
});

test.each([null, undefined, NaN, Infinity, -Infinity])('shows N/A for unavailable/non-finite inputs: %s', value => {
  const { container } = render(<PerformanceSummary data={{ ...fixture, annualizedReturn: value, sharpeRatio: value,
    maxDrawdown: value, totalPremiumsReceived: value }} resultContext={context} />);
  ['CAGR', 'Maximum drawdown (MDD)', 'Sharpe ratio', 'Premiums received'].forEach(name => expect(metric(name)).toHaveTextContent('N/A'));
  expect(container).not.toHaveTextContent('NaN');
  expect(container).not.toHaveTextContent('Infinity');
});

test('uses full currency precision for large monetary values', () => {
  render(<PerformanceSummary data={{ ...fixture, totalPremiumsReceived: 1234567890123.45 }} resultContext={context} />);
  expect(metric('Premiums received')).toHaveTextContent('$1,234,567,890,123.45');
});

test.each([[], [{ date: '2026-01-01', Portfolio_Value: 100000 }], [
  { date: '2026-01-01', Portfolio_Value: 100000 }, { date: '2026-01-02', Portfolio_Value: 101000 },
]].map(points => [points]))('does not present the existing insufficient-period CAGR fallback as an earned zero', points => {
  render(<PerformanceSummary data={{ ...fixture, chartData: points, annualizedReturn: 0, sharpeRatio: null }} resultContext={context} />);
  expect(metric('CAGR')).toHaveTextContent('N/A');
  expect(metric('Sharpe ratio')).toHaveTextContent('N/A');
});

test('uses N/A instead of invented balances when run metadata is absent', () => {
  render(<PerformanceSummary data={{ chartData: [], sharpeRatio: null }} />);
  const details = screen.getByText('Calculation details').closest('details');
  expect(within(details).getAllByText('N/A').length).toBeGreaterThanOrEqual(4);
  expect(details).not.toHaveTextContent('$0.00');
});

test('metric help is available by keyboard, Escape, and click', async () => {
  render(<PerformanceSummary data={fixture} resultContext={context} />);
  const help = screen.getByRole('button', { name: 'About CAGR' });
  userEvent.tab();
  expect(help).toHaveFocus();
  expect(await screen.findByRole('tooltip')).toHaveTextContent('timing of each withdrawal');
  userEvent.keyboard('{Escape}');
  await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'About ITM call closure costs' }));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('buybacks and assignments');
});

test('fictional review statistics are explicitly separate from backtest results', () => {
  render(<PerformanceSummary data={fixture} resultContext={context} sample />);
  expect(screen.getByRole('region', { name: 'Sample performance summary' })).toBeInTheDocument();
  expect(screen.getByText(/not calculated from the chart or a simulation/)).toBeInTheDocument();
});
