import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ParameterField from '../components/ParameterField';
import Dashboard, { CustomTooltip } from './Dashboard';
import { runSimulation } from '../services/simulationService';

jest.mock('../services/simulationService', () => ({ runSimulation: jest.fn() }));

beforeEach(() => {
  // Exercise the form without a database, broker, or external strategy engine.
  runSimulation.mockRejectedValue(new Error('Backtest service unavailable'));
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
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
