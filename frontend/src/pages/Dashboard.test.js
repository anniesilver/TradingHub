import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ParameterField from '../components/ParameterField';
import Dashboard, { CustomTooltip } from './Dashboard';
import App from '../App';
import { createWorkspaceTheme } from '../theme';
import { chartColors } from '../components/chartColors';
import { runSimulation } from '../services/simulationService';
import { computeSharpeRatio } from './performanceMetrics';

jest.mock('../services/simulationService', () => ({ runSimulation: jest.fn() }));

const originalResizeObserver = global.ResizeObserver;
test('configured starting capital preserves cents without requesting another simulation', async () => {
  render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const calls = runSimulation.mock.calls.length;
  fireEvent.change(screen.getByLabelText('Initial Balance'), { target: { value: '200000.50' } });
  expect(screen.getByText('$200,000.50 USD')).toBeInTheDocument();
  expect(runSimulation).toHaveBeenCalledTimes(calls);
});

test('compact strategy navigation closes with Escape or a selection and returns focus', async () => {
  render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const menu = screen.getByRole('button', { name: 'Toggle strategy navigation' });
  const calls = runSimulation.mock.calls.length;
  fireEvent.click(menu);
  expect(menu).toHaveAttribute('aria-expanded', 'true');
  screen.getByRole('button', { name: 'SPY Enhanced Cashflow' }).focus();
  fireEvent.keyDown(document.activeElement, { key: 'Escape' });
  expect(menu).toHaveAttribute('aria-expanded', 'false');
  expect(menu).toHaveFocus();
  expect(runSimulation).toHaveBeenCalledTimes(calls);
  fireEvent.click(menu);
  fireEvent.click(screen.getByRole('button', { name: 'SPY Power Cashflow' }));
  expect(menu).toHaveAttribute('aria-expanded', 'false');
  expect(menu).toHaveFocus();
  expect(runSimulation).toHaveBeenCalledTimes(calls);
  fireEvent.click(menu);
  fireEvent.click(screen.getByRole('button', { name: 'SPY Enhanced Cashflow' }));
  await screen.findByText('Backtest service unavailable');
  expect(menu).toHaveAttribute('aria-expanded', 'false');
  expect(menu).toHaveFocus();
  expect(screen.getByRole('button', { name: 'SPY Enhanced Cashflow' })).toHaveAttribute('aria-current', 'page');
});

test('only Power Cashflow hides its unused fields, without losing their values', async () => {
  render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const labels = ['Option Type', 'Max Position Size', 'Min Trade Size'];
  labels.forEach(label => expect(screen.queryByLabelText(label)).not.toBeInTheDocument());
  for (const strategy of ['SPY Enhanced Cashflow', 'Options Martingale', 'S&P 500 Leader']) {
    fireEvent.click(screen.getByRole('button', { name: strategy }));
    await screen.findByText('Backtest service unavailable');
    labels.forEach(label => expect(screen.getByLabelText(label)).toBeInTheDocument());
  }
  fireEvent.change(screen.getByLabelText('Max Position Size'), { target: { value: '12000' } });
  fireEvent.change(screen.getByLabelText('Min Trade Size'), { target: { value: '2400' } });
  fireEvent.mouseDown(screen.getByLabelText('Option Type'));
  fireEvent.click(screen.getByRole('option', { name: 'Put' }));
  fireEvent.click(screen.getByRole('button', { name: 'SPY Power Cashflow' }));
  await screen.findByText('Backtest service unavailable');
  labels.forEach(label => expect(screen.queryByLabelText(label)).not.toBeInTheDocument());
  expect(runSimulation.mock.calls.at(-1)[0]).toEqual(expect.objectContaining({
    maxPositionSize: 12000, minTradeSize: 2400, optionType: 'put',
  }));
  fireEvent.click(screen.getByRole('button', { name: 'SPY Enhanced Cashflow' }));
  await screen.findByText('Backtest service unavailable');
  expect(screen.getByLabelText('Max Position Size')).toHaveValue(12000);
  expect(screen.getByLabelText('Min Trade Size')).toHaveValue(2400);
  expect(screen.getByLabelText('Option Type')).toHaveTextContent('Put');
});

test('strategy navigation and header occupy separate in-flow grid cells', async () => {
  const { container } = render(<App />);
  await screen.findByText('Backtest service unavailable');
  const rail = screen.getByRole('navigation', { name: 'Trading strategies' });
  const main = screen.getByRole('main');
  expect(rail.parentElement).toBe(main.parentElement);
  expect(rail.parentElement).toHaveStyle({ display: 'grid', gridTemplateColumns: '232px minmax(0, 1fr)' });
  expect(rail).toHaveStyle({ position: 'relative' });
  expect(main).toHaveAttribute('id', 'analysis-workspace');
  expect(within(main).getByLabelText('Configured scenario')).toHaveTextContent('SPY');
  expect(container.querySelector('.MuiDrawer-paper')).toBeNull();
  expect(within(rail).getByRole('button', { name: 'SPY Power Cashflow' })).toHaveAttribute('aria-current', 'page');
  expect(within(main).getByRole('heading', { name: 'SPY Power Cashflow' })).toBeVisible();
  const run = screen.getByRole('button', { name: 'Run simulation' });
  expect(run.closest('.form-actions').firstElementChild).toBe(run);
  expect(run.closest('.MuiGrid-container').firstElementChild).toBe(run.closest('.primary-run-action'));
});

test('the reference palette supports glass/solid and light/dark without rerunning or resetting the scenario', async () => {
  const { container } = render(<App />);
  await screen.findByText('Backtest service unavailable');
  fireEvent.change(screen.getByLabelText('Initial Balance'), { target: { value: '456000' } });
  const calls = runSimulation.mock.calls.length;
  const app = container.querySelector('.app');
  expect(app.style.getPropertyValue('--workspace-accent')).toBe('#052659');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Solid surfaces' }));
  expect(container.querySelector('.workspace-wave-backdrop')).toBeNull();
  expect(app.style.getPropertyValue('--workspace-accent')).toBe('#052659');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Light mode' }));
  expect(app.style.getPropertyValue('--workspace-bg')).toBe('#021024');
  expect(app.style.getPropertyValue('--chart-surface')).toBe('#071A32');
  expect(app.style.getPropertyValue('--workspace-accent')).toBe('#C1E8FF');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Solid surfaces' }));
  expect(container.querySelector('.workspace-wave-backdrop')).toBeInTheDocument();
  expect(app.style.getPropertyValue('--workspace-accent')).toBe('#C1E8FF');
  expect(screen.getByLabelText('Initial Balance')).toHaveValue(456000);
  expect(runSimulation).toHaveBeenCalledTimes(calls);
});
// Deterministic backtest fixture; never used by the production API or preview.
const summaryRun = {
  '2026-09-11': { Portfolio_Value: 200000, spy_value: 200000, Cash_Balance: 10000, Margin_Ratio: 0.1, Premiums_Received: 0, Interest_Paid: 0, Dividends_Received: 0, Trading_Log: 'Buy: 10 shares at $100.00' },
  '2026-09-14': { Portfolio_Value: 202000, spy_value: 201000, Cash_Balance: 10200, Margin_Ratio: 0.1, Premiums_Received: 200, Interest_Paid: 10, Dividends_Received: 50, Trading_Log: 'Wrote 1 call premium $200.00' },
  '2026-09-15': { Portfolio_Value: 198000, spy_value: 199000, Cash_Balance: 9700, Margin_Ratio: 0.2, Premiums_Received: 0, Interest_Paid: 20, Dividends_Received: 0, Trading_Log: 'Bought back call at a cost of $500.00' },
  '2026-10-09': { Portfolio_Value: 204000, spy_value: 202000, Cash_Balance: 9000, Margin_Ratio: 0.1, Premiums_Received: 300, Interest_Paid: 30, Dividends_Received: 0, Trading_Log: 'Monthly withdrawal: $1,000.00' },
};

test.each(['SPY Power Cashflow', 'SPY Enhanced Cashflow', 'Options Martingale', 'S&P 500 Leader'])(
  'shows all eight metrics in Performance, retains Premium context, and keeps Logs transactional for %s', async strategy => {
    const leader = strategy === 'S&P 500 Leader';
    const response = leader ? Object.fromEntries(Object.entries(summaryRun).map(([date, row], index) => [date, {
      ...row, Premiums_Received: 0, Interest_Paid: 0,
      Trading_Log: index === 0 ? 'INITIAL BUY: 10 shares at $100.00' : index === 3 ? 'SWAP: Rebalanced portfolio' : '',
      isSwapTransaction: index === 0 || index === 3,
    }])) : summaryRun;
    runSimulation.mockResolvedValue(response);
    render(<Dashboard />);
    if (strategy !== 'SPY Power Cashflow') fireEvent.click(screen.getByRole('button', { name: strategy }));
    const summary = await screen.findByRole('region', { name: 'Performance summary' });
    const row = name => within(summary).getByText(name).closest('.performance-cash-row');
    expect(summary.querySelectorAll('.performance-cash-row.performance-metric')).toHaveLength(5);
    expect(row('Premiums received').querySelector('dt')).toHaveTextContent('Premiums received');
    expect(row('Premiums received').querySelector('dd .performance-metric-value')).toBeInTheDocument();
    expect(within(summary).getByText('CAGR')).toBeInTheDocument();
    expect(within(summary).getByText('Maximum drawdown (MDD)')).toBeInTheDocument();
    const sharpe = computeSharpeRatio(Object.values(response), { riskFreeRate: 0.05 });
    expect(within(summary).getByText('Sharpe ratio').closest('.performance-metric')).toHaveTextContent(sharpe.toFixed(2));
    expect(row('Premiums received')).toHaveTextContent(leader ? '$0.00' : '$500.00');
    expect(row('Dividends received')).toHaveTextContent('$50.00');
    expect(row('Interest paid')).toHaveTextContent(leader ? '$0.00' : '$60.00');
    expect(row('ITM call closure costs')).toHaveTextContent(leader ? '$0.00' : '$500.00');
    expect(row('Withdrawals')).toHaveTextContent(leader ? '$0.00' : '$1,000.00');
    const calls = runSimulation.mock.calls.length;
    fireEvent.click(screen.getByRole('tab', { name: 'Trading Logs' }));
    expect(screen.queryByRole('region', { name: 'Performance summary' })).not.toBeInTheDocument();
    expect(screen.queryByText('CAGR')).not.toBeInTheDocument();
    expect(screen.queryByText(/Total premiums received during test period/)).not.toBeInTheDocument();
    expect(screen.getByText(leader ? 'Transaction Date: 2026-09-11' : 'Transaction Date: 2026-09-15')).toBeInTheDocument();
    expect(screen.getByText(leader ? 'SWAP: Rebalanced portfolio' : 'Bought back call at a cost of $500.00')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Premium & Interest' }));
    if (leader) {
      expect(screen.queryByText(/Total premiums received:/)).not.toBeInTheDocument();
    } else {
      expect(screen.getByText('Total premiums received: $500.00')).toBeInTheDocument();
      expect(screen.getByText('Total interest paid: $60.00')).toBeInTheDocument();
    }
    fireEvent.click(screen.getByRole('tab', { name: 'Performance' }));
    expect(screen.getByRole('region', { name: 'Performance summary' })).toBeInTheDocument();
    expect(runSimulation).toHaveBeenCalledTimes(calls);
  }
);

test('the summary retains this run’s risk-free rate after editing the next scenario', async () => {
  runSimulation.mockResolvedValue(summaryRun);
  render(<Dashboard />);
  const summary = await screen.findByRole('region', { name: 'Performance summary' });
  const before = summary.textContent;
  fireEvent.change(screen.getByLabelText('Risk Free Rate (%)'), { target: { value: '12' } });
  expect(summary.textContent).toBe(before);
  expect(within(summary).getByText(/Risk-free rate: 5.00% per year/)).toBeInTheDocument();
  const details = within(summary).getByText('Calculation details').closest('details');
  fireEvent.click(within(details).getByText('Calculation details'));
  expect(within(details).getByText('Recorded period')).toBeInTheDocument();
  expect(within(details).getByText('Adjusted final value')).toBeInTheDocument();
  expect(details).not.toHaveTextContent('Compound annualized growth rate');
  expect(details).not.toHaveTextContent('Observed decline');
  expect(details).not.toHaveTextContent('Annualized mean daily excess return');
  expect(within(summary).getByRole('button', { name: 'About Sharpe ratio' })).toHaveAccessibleDescription(/Risk-free rate: 5.00% per year/);
  expect(screen.getByText('Settings have changed. Rerun to update these results.')).toBeInTheDocument();
});
test('light is the default and theme switching preserves parameters without requesting a simulation', async () => {
  const { container } = render(<App />);
  await screen.findByText('Backtest service unavailable');
  expect(container.querySelector('.app')).toHaveAttribute('data-theme', 'light');
  expect(screen.getByRole('checkbox', { name: 'Light mode' })).toBeChecked();
  expect(createWorkspaceTheme().palette.mode).toBe('light');
  fireEvent.change(screen.getByLabelText('Initial Balance'), { target: { value: '321000' } });
  const calls = runSimulation.mock.calls.length;
  fireEvent.click(screen.getByRole('checkbox', { name: 'Light mode' }));
  expect(container.querySelector('.app')).toHaveAttribute('data-theme', 'dark');
  expect(screen.getByLabelText('Initial Balance')).toHaveValue(321000);
  expect(runSimulation).toHaveBeenCalledTimes(calls);
  expect(createWorkspaceTheme('light').palette.mode).toBe('light');
  expect(createWorkspaceTheme('light').shape.borderRadius).toBe(12);
  fireEvent.click(screen.getByRole('checkbox', { name: 'Light mode' }));
  expect(container.querySelector('.app')).toHaveAttribute('data-theme', 'light');
});

test('sample tabs morph distinct contours without a fullscreen navigation wave', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Show sample chart' }));
  const first = screen.getByTestId('background-contour').getAttribute('d');
  fireEvent.click(screen.getByRole('tab', { name: 'Margin', exact: true }));
  expect(screen.getByTestId('background-contour').getAttribute('d')).not.toBe(first);
  expect(container.querySelector('.workspace-wave-backdrop')).toHaveAttribute('data-scene', '1');
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Cash', exact: true }));
  expect(container.querySelector('.workspace-wave-backdrop')).toHaveAttribute('data-scene', '2');
  fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
  expect(container.querySelector('.workspace-wave-backdrop')).toHaveAttribute('data-scene', '0');
});
beforeAll(() => {
  // jsdom has no layout observer. These tests verify result labels/state,
  // not chart geometry; browser validation is separate.
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});
afterAll(() => {
  if (originalResizeObserver) global.ResizeObserver = originalResizeObserver;
  else delete global.ResizeObserver;
});

test('labels the historical workspace and exposes session-only accessibility preferences', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  expect(screen.getByRole('heading', { level: 1, name: 'SPY Power Cashflow' })).toBeInTheDocument();
  expect(within(screen.getByRole('main')).getByText('Historical research')).toBeInTheDocument();
  expect(screen.getByRole('navigation', { name: 'Trading strategies' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^SPY Power Cashflow/ })).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to analysis' })).toHaveAttribute('href', '#analysis-workspace');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Solid surfaces' }));
  fireEvent.click(screen.getByRole('checkbox', { name: 'Reduce motion' }));
  expect(container.querySelector('.workspace')).toHaveAttribute('data-solid', 'true');
  expect(container.querySelector('.workspace')).toHaveAttribute('data-motion', 'reduced');
});

test('successful results keep their run context when configuration changes', async () => {
  // Test-only historical fixture, never substituted for market data in the app.
  runSimulation.mockResolvedValue({
    '2026-09-11': { Portfolio_Value: 200000, spy_value: 200000, Cash_Balance: 20000, Margin_Ratio: 0.1, Trading_Log: '' },
    '2026-10-09': { Portfolio_Value: 201000, spy_value: 200500, Cash_Balance: 21000, Margin_Ratio: 0.1, Trading_Log: '' },
  });
  const { container } = render(<Dashboard />);
  await screen.findByRole('heading', { name: 'Historical simulation results' });
  expect(screen.getByText(/Market-data freshness, session and source time zone are not supplied/)).toBeInTheDocument();
  const context = container.querySelector('[aria-label="Result context"]');
  const originalContext = context.textContent;
  fireEvent.change(screen.getByLabelText('Initial Balance'), { target: { value: '300000' } });
  expect(screen.getByText('Settings have changed. Rerun to update these results.')).toBeInTheDocument();
  expect(context.textContent).toContain(originalContext);
  const summary = screen.getByRole('region', { name: 'Performance summary' });
  expect(within(summary).getByText('$200,000.00')).toBeInTheDocument();
  expect(within(summary).queryByText('$300,000.00')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Trading Logs' }));
  expect(screen.queryByRole('region', { name: 'Performance summary' })).not.toBeInTheDocument();
});

test('glass is the default and solid surfaces is the only material override', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const firstInputs = runSimulation.mock.calls[0][0];
  expect(screen.queryByRole('checkbox', { name: 'Glass mode' })).not.toBeInTheDocument();
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  expect(container.querySelector('.workspace')).toHaveAttribute('data-glass', 'true');
  expect(container.querySelector('.workspace-wave-backdrop')).toHaveAttribute('aria-hidden', 'true');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Solid surfaces' }));
  expect(container.querySelector('.workspace')).toHaveAttribute('data-glass', 'false');
  expect(container.querySelector('.workspace-wave-backdrop')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Solid surfaces' }));
  expect(container.querySelector('.workspace')).toHaveAttribute('data-glass', 'true');
  expect(screen.getByRole('checkbox', { name: 'Solid surfaces' })).not.toBeChecked();
  const previousWipe = screen.queryByTestId('simulation-transition');
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  expect(screen.getByTestId('simulation-transition')).not.toBe(previousWipe);
  await screen.findByText('Backtest service unavailable');
  expect(runSimulation).toHaveBeenLastCalledWith(firstInputs);
});

beforeEach(() => {
  // Exercise the form without a database, broker, or external strategy engine.
  runSimulation.mockRejectedValue(new Error('Backtest service unavailable'));
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

test('sample preview is explicit, isolated from the API, and slides in both directions', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const callsBeforePreview = runSimulation.mock.calls.length;
  const originalBalance = screen.getByLabelText('Initial Balance').value;
  fireEvent.click(screen.getByRole('button', { name: 'Show sample chart' }));
  expect(screen.getByRole('region', { name: 'Sample chart preview' })).toBeInTheDocument();
  expect(screen.getByText(/Fictional data for UI review only/)).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Sample chart preview · Testing only' })).toBeInTheDocument();
  expect(container.querySelector('main').lastElementChild).toBe(container.querySelector('.testing-tools'));
  expect(chartColors.strategy).toContain('--chart-strategy');
  expect(chartColors.benchmark).toContain('--chart-benchmark');
  expect(screen.getByText('$115,100')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Cash' }));
  expect(screen.getByRole('tabpanel')).toHaveStyle({ '--panel-offset': '24px' });
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  expect(screen.getByText('Illustrative cash balance')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Performance' }));
  expect(screen.getByRole('tabpanel')).toHaveStyle({ '--panel-offset': '-24px' });
  expect(runSimulation).toHaveBeenCalledTimes(callsBeforePreview);
  expect(screen.getByLabelText('Initial Balance')).toHaveValue(Number(originalBalance));
  expect(container.querySelector('.analysis-results')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
  expect(screen.queryByRole('region', { name: 'Sample chart preview' })).not.toBeInTheDocument();
});

test('strategy descriptions remain available in an initially collapsed guide', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const guide = screen.getByText('Strategy guide').closest('details');
  expect(guide).not.toHaveAttribute('open');
  expect(guide).toHaveTextContent('Original covered call strategy with leveraged positions');
  expect(container.querySelector('nav .MuiListItemText-secondary')).not.toBeInTheDocument();
});

test('only explicit runs launch a fullscreen wave; navigation cancels it', async () => {
  render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Options Martingale' }));
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  await screen.findByText('Backtest service unavailable');
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  expect(screen.getByTestId('simulation-transition')).toBeInTheDocument();
  await screen.findByText('Backtest service unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Show sample chart' }));
  fireEvent.click(screen.getByRole('tab', { name: 'Cash' }));
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
});

afterEach(() => {
  jest.restoreAllMocks();
  jest.clearAllMocks();
});

test.each([
  'SPY Power Cashflow',
  'SPY Enhanced Cashflow',
  'Options Martingale',
  'S&P 500 Leader',
])('every parameter has compact, associated help for %s', async (strategy) => {
  const { container } = render(<Dashboard />);
  if (strategy !== 'SPY Power Cashflow') {
    fireEvent.click(screen.getByText(strategy));
  }
  await screen.findByText('Backtest service unavailable');

  fireEvent.click(screen.getByText('Advanced strategy parameters'));
  // MUI Select renders a visible control plus an aria-hidden internal input.
  const inputs = container.querySelectorAll(
    'form input:not([aria-hidden="true"]), form [role="combobox"], form [role="button"][aria-haspopup="listbox"]'
  );
  expect(inputs.length).toBeGreaterThan(20);
  expect(screen.getAllByRole('button', { name: /^Help for / })).toHaveLength(inputs.length);
  expect(container.querySelector('.MuiFormHelperText-root')).toBeNull();
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  inputs.forEach((input) => {
    const descriptionIds = input.getAttribute('aria-describedby');
    expect(descriptionIds).toBeTruthy();
    descriptionIds.split(' ').forEach((id) => {
      const help = document.getElementById(id);
      expect(help).toBeInTheDocument();
      expect(help).toHaveStyle({ position: 'absolute', overflow: 'hidden' });
      expect(help.textContent.trim().length).toBeGreaterThan(10);
    });
  });
});

test('shows human percentages while preserving the original API defaults', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');

  const percentages = {
    callCostBuffer: [5, 0.05],
    coveredCallRatio: [100, 1],
    dipBuyPercent: [40, 0.4],
    highVixDipBuyPercent: [15, 0.15],
    initialPositionPercent: [60, 0.6],
    marginInterestRate: [6, 0.06],
    minStrikeDistance: [1.5, 0.015],
    riskFreeRate: [5, 0.05],
    // This API field already uses percentage points, not a fraction.
    monthlyWithdrawalRate: [1, 1],
  };
  Object.entries(percentages).forEach(([name, [displayValue]]) => {
    const input = container.querySelector(`input[name="${name}"]`);
    expect(input).toHaveValue(displayValue);
    expect(input.labels[0]).toHaveTextContent('%');
  });
  expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining(
    Object.fromEntries(Object.entries(percentages).map(([name, [, apiValue]]) => [name, apiValue]))
  ));
});

test('converts edited percentages to API fractions exactly once', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');

  const percentages = {
    callCostBuffer: [2, 0.02],
    coveredCallRatio: [50, 0.5],
    dipBuyPercent: [25, 0.25],
    highVixDipBuyPercent: [20, 0.2],
    initialPositionPercent: [70, 0.7],
    marginInterestRate: [7.5, 0.075],
    minStrikeDistance: [2.5, 0.025],
    riskFreeRate: [4, 0.04],
    monthlyWithdrawalRate: [2, 2],
  };
  Object.entries(percentages).forEach(([name, [displayValue]]) => {
    const input = container.querySelector(`input[name="${name}"]`);
    fireEvent.change(input, { target: { value: String(displayValue) } });
    expect(input).toHaveValue(displayValue);
  });
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    ...Object.fromEntries(Object.entries(percentages).map(([name, [, apiValue]]) => [name, apiValue])),
    strategyId: 'SPY_POWER_CASHFLOW',
  })));
});

test.each([[0, 0], [100, 1]])('accepts a dip allocation of %s percent as API value %s', async (displayValue, apiValue) => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const allocation = container.querySelector('input[name="dipBuyPercent"]');
  expect(allocation).toHaveAttribute('min', '0');
  expect(allocation).toHaveAttribute('max', '100');
  expect(allocation).toHaveAttribute('step', '1');
  fireEvent.change(allocation, { target: { value: String(displayValue) } });
  expect(allocation).toHaveValue(displayValue);
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    dipBuyPercent: apiValue,
  })));
});

test('does not percentage-scale price ratios, normalized VIX, leverage, multipliers, or dollars', async () => {
  const { container } = render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const rawDefaults = {
    dipTrigger: 0.92,
    highVixDipTrigger: 0.8,
    vixHighThreshold: 0.25,
    vixDeleverageThreshold: 0.25,
    vixDeleverageTargetRatio: 1.5,
    maxMarginRatio: 2,
    volatilityScalingFactor: 0.15,
    initialBalance: 200000,
    minCommission: 1,
    optionCommission: 0.65,
    stockCommission: 0.01,
  };
  Object.entries(rawDefaults).forEach(([name, value]) => {
    expect(container.querySelector(`input[name="${name}"]`)).toHaveValue(value);
  });
  fireEvent.change(container.querySelector('input[name="dipTrigger"]'), { target: { value: '0.9' } });
  fireEvent.change(container.querySelector('input[name="vixHighThreshold"]'), { target: { value: '0.3' } });
  fireEvent.change(container.querySelector('input[name="maxMarginRatio"]'), { target: { value: '2.5' } });
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    ...rawDefaults,
    dipTrigger: 0.9,
    vixHighThreshold: 0.3,
    maxMarginRatio: 2.5,
  })));
});

test('shows IV thresholds in percent and submits decimal fractions', async () => {
  const { container } = render(<Dashboard />);
  fireEvent.click(screen.getByText('Options Martingale'));
  await screen.findByText('Backtest service unavailable');
  const entry = container.querySelector('input[name="IV_ENTRY_THRESHOLD"]');
  const exit = container.querySelector('input[name="IV_EXIT_THRESHOLD"]');
  expect(entry).toHaveValue(30);
  expect(exit).toHaveValue(50);
  expect(entry.labels[0]).toHaveTextContent('%');
  expect(exit.labels[0]).toHaveTextContent('%');
  expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    IV_ENTRY_THRESHOLD: 0.3,
    IV_EXIT_THRESHOLD: 0.5,
    INC_INDEX: 2,
    DEC_INDEX: 0.6,
  }));
  fireEvent.change(entry, { target: { value: '35' } });
  fireEvent.change(exit, { target: { value: '55' } });
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    IV_ENTRY_THRESHOLD: 0.35,
    IV_EXIT_THRESHOLD: 0.55,
    strategyId: 'OPTIONS_MARTIN',
  })));
});

test('shows leader allocation and fractional slippage in percent', async () => {
  const { container } = render(<Dashboard />);
  fireEvent.click(screen.getByText('S&P 500 Leader'));
  await screen.findByText('Backtest service unavailable');
  const position = container.querySelector('input[name="INITIAL_POSITION_PERCENT"]');
  const slippage = container.querySelector('input[name="SLIPPAGE_PERCENT"]');
  expect(position).toHaveValue(60);
  expect(slippage).toHaveValue(0.1);
  expect(slippage).toHaveAttribute('max', '1');
  expect(slippage).toHaveAttribute('step', '0.01');
  expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    INITIAL_POSITION_PERCENT: 0.6,
    SLIPPAGE_PERCENT: 0.001,
  }));
  fireEvent.change(position, { target: { value: '75' } });
  fireEvent.change(slippage, { target: { value: '0.2' } });
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    INITIAL_POSITION_PERCENT: 0.75,
    SLIPPAGE_PERCENT: 0.002,
    strategyId: 'SPY500_LEADER',
  })));
});

test('formats a margin ratio as a percentage without changing currency series', () => {
  render(<CustomTooltip
    active
    label="2026-10-03"
    payload={[
      { dataKey: 'Margin_Ratio', value: 0.4, payload: {} },
      { dataKey: 'Portfolio_Value', value: 40, payload: {} },
    ]}
  />);
  expect(screen.getByText('Margin Ratio: 40.00%')).toBeInTheDocument();
  expect(screen.getByText('Strategy: $40.00')).toBeInTheDocument();
  expect(screen.queryByText('Margin Ratio: $0.40')).not.toBeInTheDocument();
});

test('IV help stays available when its entry threshold is disabled', async () => {
  render(<Dashboard />);
  fireEvent.click(screen.getByText('Options Martingale'));
  await screen.findByText('Backtest service unavailable');
  fireEvent.click(screen.getByText('Advanced strategy parameters'));
  fireEvent.click(screen.getByRole('checkbox', { name: 'Enable IV Entry Filter' }));
  const threshold = screen.getByLabelText(/^IV Entry Threshold/);
  expect(threshold).toBeDisabled();
  expect(threshold).toHaveAccessibleDescription(expect.stringContaining('30%'));
  userEvent.click(screen.getByRole('button', { name: /^Help for IV Entry Threshold/ }));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('30%');
});

test('hover reveals help and leaving hides it', async () => {
  render(<ParameterField name="dipTrigger" label="Dip Trigger"><input /></ParameterField>);
  const helpButton = screen.getByRole('button', { name: 'Help for Dip Trigger' });
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  fireEvent.mouseOver(helpButton);
  expect(await screen.findByRole('tooltip')).toHaveTextContent('0.92 = an 8% drop');
  fireEvent.mouseLeave(helpButton);
  await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
});

test('keyboard focus reveals help and Escape dismisses it', async () => {
  render(<ParameterField name="monthlyWithdrawalRate" label="Monthly Withdrawal Rate (%)"><span>Rate</span></ParameterField>);
  userEvent.tab();
  expect(screen.getByRole('button', { name: 'Help for Monthly Withdrawal Rate (%)' })).toHaveFocus();
  expect(await screen.findByRole('tooltip')).toHaveTextContent('1.0 for 1%');
  userEvent.keyboard('{Escape}');
  await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
});


test('advanced parameters are opt-in and retain edits without running a simulation', async () => {
  const { container } = render(<App />);
  await screen.findByText('Backtest service unavailable');
  const panel = container.querySelector('.advanced-settings');
  expect(panel).not.toHaveAttribute('open');
  const calls = runSimulation.mock.calls.length;
  fireEvent.click(screen.getByText('Advanced strategy parameters'));
  expect(panel).toHaveAttribute('open');
  fireEvent.change(screen.getByLabelText('Contract Size'), { target: { value: '125' } });
  fireEvent.click(screen.getByText('Advanced strategy parameters'));
  expect(panel).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText('Advanced strategy parameters'));
  expect(screen.getByLabelText('Contract Size')).toHaveValue(125);
  expect(runSimulation).toHaveBeenCalledTimes(calls);
});

test('unavailable results keep an honest empty overview instead of invented values', async () => {
  render(<App />);
  await screen.findByText('Backtest service unavailable');
  const overview = screen.getByRole('region', { name: 'Simulation overview' });
  expect(within(overview).getAllByText('No completed run')).toHaveLength(3);
  expect(within(overview).getByRole('button', { name: 'Show sample chart' })).toBeVisible();
  expect(screen.queryByText('15.70%')).not.toBeInTheDocument();
});


test('sample chart expansion preserves the scenario and table, supports Escape, and restores focus', async () => {
  render(<App />);
  await screen.findByText('Backtest service unavailable');
  fireEvent.change(screen.getByLabelText('Initial Balance'), { target: { value: '212345.67' } });
  fireEvent.click(screen.getByRole('checkbox', { name: 'Light mode' }));
  fireEvent.click(screen.getByRole('button', { name: 'Show sample chart' }));
  fireEvent.click(screen.getByText('View chart values'));
  const calls = runSimulation.mock.calls.length;
  const expand = screen.getByRole('button', { name: 'Expand Sample performance chart' });
  userEvent.click(expand);
  const dialog = await screen.findByRole('dialog', { name: 'Sample performance chart' });
  expect(dialog).toHaveTextContent('Fictional sample · UI testing only');
  expect(within(dialog).getByRole('button', { name: 'Close chart' })).toHaveFocus();
  expect(dialog.closest('.expanded-chart-dialog').style.getPropertyValue('--chart-surface')).toBe('#071A32');
  expect(within(dialog).getByRole('table')).toHaveTextContent('2024-12-01');
  expect(within(dialog).getByText('$115,100')).toBeInTheDocument();
  userEvent.keyboard('{Escape}');
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(expand).toHaveFocus();
  expect(screen.getByLabelText('Initial Balance')).toHaveValue(212345.67);
  expect(screen.getByRole('table')).toHaveTextContent('2024-12-01');
  expect(runSimulation).toHaveBeenCalledTimes(calls);
  for (const [tab, title] of [['Margin', 'Sample margin chart'], ['Cash', 'Sample cash chart']]) {
    fireEvent.click(screen.getByRole('tab', { name: tab }));
    userEvent.click(screen.getByRole('button', { name: `Expand ${title}` }));
    expect(await screen.findByRole('dialog', { name: title })).toHaveTextContent('Fictional sample');
    userEvent.click(screen.getByRole('button', { name: 'Close chart' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  }
  expect(runSimulation).toHaveBeenCalledTimes(calls);
}, 15000);

test('completed-run charts expand without recalculating or replacing run context', async () => {
  runSimulation.mockResolvedValue(summaryRun);
  render(<App />);
  await screen.findByRole('heading', { name: 'Historical simulation results' });
  const calls = runSimulation.mock.calls.length;
  for (const [tab, title] of [['Performance', 'Portfolio performance chart'], ['Margin Ratio', 'Margin ratio chart'], ['Cash Balance', 'Cash balance chart'], ['Premium & Interest', 'Premium and interest chart']]) {
    fireEvent.click(screen.getByRole('tab', { name: tab }));
    userEvent.click(screen.getByRole('button', { name: `Expand ${title}` }));
    const dialog = await screen.findByRole('dialog', { name: title });
    expect(dialog).toHaveTextContent('Historical simulation · Completed-run values');
    expect(dialog).not.toHaveTextContent('Fictional sample');
    userEvent.click(within(dialog).getByRole('button', { name: 'Close chart' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Historical simulation results' })).toBeInTheDocument();
  }
  expect(runSimulation).toHaveBeenCalledTimes(calls);
}, 15000);
