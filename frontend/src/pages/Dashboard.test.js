import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ParameterField from '../components/ParameterField';
import Dashboard from './Dashboard';
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

test('explains different percentage units without changing submitted values', async () => {
  render(<Dashboard />);
  await screen.findByText('Backtest service unavailable');
  const position = screen.getByLabelText('Initial Position %');
  const withdrawal = screen.getByLabelText('Monthly Withdrawal Rate (%)');
  expect(position).toHaveAccessibleDescription(expect.stringContaining('0.6 = 60%'));
  expect(withdrawal).toHaveAccessibleDescription(expect.stringContaining('1.0 for 1%'));
  fireEvent.change(position, { target: { value: '0.7' } });
  fireEvent.change(withdrawal, { target: { value: '2' } });
  fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));
  await waitFor(() => expect(runSimulation).toHaveBeenLastCalledWith(expect.objectContaining({
    initialPositionPercent: 0.7,
    monthlyWithdrawalRate: 2,
    strategyId: 'SPY_POWER_CASHFLOW',
  })));
});

test('IV help stays available when its entry threshold is disabled', async () => {
  render(<Dashboard />);
  fireEvent.click(screen.getByText('Options Martingale'));
  await screen.findByText('Backtest service unavailable');
  fireEvent.click(screen.getByRole('checkbox', { name: 'Enable IV Entry Filter' }));
  const threshold = screen.getByLabelText('IV Entry Threshold');
  expect(threshold).toBeDisabled();
  expect(threshold).toHaveAccessibleDescription(expect.stringContaining('0.30 = 30%'));
  userEvent.click(screen.getByRole('button', { name: 'Help for IV Entry Threshold' }));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('0.30 = 30%');
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
