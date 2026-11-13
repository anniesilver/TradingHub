import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PaperTestHistory from './PaperTestHistory';
import { getPaperTestHistory } from '../services/simulationService';

jest.mock('../services/simulationService', () => ({ getPaperTestHistory: jest.fn() }));

test('lists running and legacy tests', async () => {
  getPaperTestHistory.mockResolvedValue({ sync_error: null, tests: [
    { strategy: 'options_martin', id: 'current-old-setup', label: 'old setup (before paper tests)', status: 'running',
      legacy: true, started: '2026-10-29T13:31:14+00:00', trade_count: 13, paper_realized: '598.20' },
  ] });
  render(<PaperTestHistory strategyId="OPTIONS_MARTIN" />);
  fireEvent.click(screen.getByRole('button', { name: 'Past tests' }));
  expect(await screen.findByText(/old setup/)).toBeInTheDocument();
  expect(screen.getByText('legacy')).toBeInTheDocument();
  expect(screen.getByText('$598')).toBeInTheDocument();
  expect(getPaperTestHistory).toHaveBeenCalledWith('OPTIONS_MARTIN');
});
