import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PaperTestButton from './PaperTestButton';
import { getPaperTest, startPaperTest } from '../services/simulationService';

jest.mock('../services/simulationService', () => ({
  getPaperTest: jest.fn(), startPaperTest: jest.fn(), cancelPaperTest: jest.fn(),
}));

const config = { symbol: 'AMZN', budget: 30000, put_otm_pct: 0.07 };

test('holding positions: lists them and closes them before starting', async () => {
  getPaperTest.mockResolvedValue({
    dry_run: false, test: null, waiting: null, last_status: {},
    held: [{ contract: 'AMZN 245P 12-11', qty: -1, value: -180 }],
  });
  startPaperTest.mockResolvedValue({ ok: true, waiting: true, message: 'wheel will close AMZN 245P 12-11 ...' });
  render(<PaperTestButton strategyId="WHEEL" config={config} />);
  fireEvent.click(screen.getByRole('button', { name: 'Start paper test' }));
  expect(await screen.findByText('-1 AMZN 245P 12-11')).toBeInTheDocument();
  expect(screen.getByText('-$180')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Close positions and start' }));
  await waitFor(() => expect(startPaperTest).toHaveBeenCalledWith(
    { ...config, strategyId: 'WHEEL' }, { dryRun: false, closeOut: true, label: '' }));
  expect(await screen.findByText(/will close AMZN 245P/)).toBeInTheDocument();
});

test('flat: starts at once, dry run when ticked', async () => {
  getPaperTest.mockResolvedValue({ dry_run: true, test: null, waiting: null, last_status: {}, held: [] });
  startPaperTest.mockResolvedValue({ ok: true, waiting: false, message: 'New wheel test started' });
  render(<PaperTestButton strategyId="WHEEL" config={config} />);
  fireEvent.click(screen.getByRole('button', { name: 'Start paper test' }));
  fireEvent.click(await screen.findByLabelText('Dry run (no orders sent)'));
  const buttons = screen.getAllByRole('button', { name: 'Start paper test' });
  fireEvent.click(buttons[buttons.length - 1]);
  await waitFor(() => expect(startPaperTest).toHaveBeenLastCalledWith(
    { ...config, strategyId: 'WHEEL' }, { dryRun: true, closeOut: false, label: '' }));
  expect(await screen.findByText('New wheel test started')).toBeInTheDocument();
});
