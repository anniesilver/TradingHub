import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Grid } from '@mui/material';
import '@testing-library/jest-dom';
import SpyCashflowSettings, { SPY_GROUPS } from './SpyCashflowSettings';

const P = (name, def, type = 'float') => ({ name, type, default: def, min: null, max: null, choices: null, help: name });
const schema = {
  rules: [P('budget', 500000), P('dip_trigger', 0.92), P('high_vix_dip_trigger', 0.9), P('dip_buy_pct', 0.25),
    P('vix_high_threshold', 0.25), P('dip_buy_within_vix_limit', true, 'bool'), P('brand_new_setting', 3)],
  backtest: { strike_step: 1 },
};

function setup(value) {
  const onChange = jest.fn();
  render(<Grid container><SpyCashflowSettings schema={schema} value={value} onChange={onChange} groups={SPY_GROUPS} /></Grid>);
  return onChange;
}

test('dip ladder shows drops and sizes in percent and stores fractions', () => {
  const value = { budget: 500000, dip_trigger: 0.92, high_vix_dip_trigger: 0.9, dip_buy_pct: 0.25,
    vix_high_threshold: 0.25, dip_buy_within_vix_limit: true, brand_new_setting: 3, strike_step: 1 };
  const onChange = setup(value);
  expect(screen.getByLabelText('Normal VIX: drop (%)')).toHaveValue(8);
  expect(screen.getByLabelText('High VIX: drop (%)')).toHaveValue(10);
  expect(screen.getByLabelText('High VIX from (VIX)')).toHaveValue(25);
  expect(screen.getByLabelText('Near the peak: spend (% of buying power)')).toHaveValue(25);
  fireEvent.change(screen.getByLabelText('High VIX: drop (%)'), { target: { value: '12' } });
  expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ high_vix_dip_trigger: 0.88 }));
  fireEvent.change(screen.getByLabelText('Near the peak: spend (% of buying power)'), { target: { value: '30' } });
  expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ dip_buy_pct: 0.3 }));
  // a setting no group lists still shows
  expect(screen.getByText('Other settings')).toBeInTheDocument();
  expect(screen.getByLabelText('Brand new setting')).toHaveValue(3);
});
