import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import SpyCashflowSettings, { initialSpyCashflowConfig, hasDipLadder, SPY_GROUPS } from './SpyCashflowSettings';

const p = (name, def, type = 'float') => ({ name, type, default: def, min: 0, max: 4, choices: null, help: `help for ${name}` });

// The defaults of algo_trading's rules after #33 (Annie 2026-11-21)
const schema = {
  rules: [
    p('budget', 500000), p('max_leverage', 2.0),
    p('dip_trigger', 0.92), p('vix_high_threshold', 0.25), p('high_vix_dip_trigger', 0.90),
    p('extreme_vix_dip_trigger', 0.85), p('dip_buy_pct', 0.25), p('dip_depth_mid', 0.16), p('dip_buy_pct_mid', 0.40),
    p('dip_depth_deep', 0.24), p('dip_buy_pct_deep', 0.60), p('dip_buy_within_vix_limit', true, 'bool'),
    p('vix_deleverage_target', 1.5), p('extreme_vix', 0.40), p('extreme_vix_target', 1.25),
  ],
  backtest: { strike_step: 1.0 },
};

const box = label => screen.getByLabelText(label);

test('shows the dip ladders in percent', () => {
  render(<SpyCashflowSettings schema={schema} value={initialSpyCashflowConfig(schema)} onChange={() => {}} />);
  expect(screen.getByText('Dip ladder')).toBeInTheDocument();
  expect(box('Dip trigger, normal VIX (% drop)')).toHaveValue(8);
  expect(box('Dip trigger, high VIX (% drop)')).toHaveValue(10);
  expect(box('Dip trigger, extreme VIX (% drop)')).toHaveValue(15);
  expect(box('High VIX from')).toHaveValue(25);
  expect(box('Extreme VIX from')).toHaveValue(40);
  expect(box('Dip buy size, shallow (%)')).toHaveValue(25);
  expect(box('Mid depth below the peak (%)')).toHaveValue(16);
  expect(box('Dip buy size, mid (%)')).toHaveValue(40);
  expect(box('Deep depth below the peak (%)')).toHaveValue(24);
  expect(box('Dip buy size, deep (%)')).toHaveValue(60);
  expect(screen.getByLabelText(/Cap each buy at today's leverage limit/)).toBeChecked();
});

test('each ladder field appears once, not also in the plain grid', () => {
  const { container } = render(<SpyCashflowSettings schema={schema} value={initialSpyCashflowConfig(schema)} onChange={() => {}} />);
  ['dip_trigger', 'extreme_vix', 'dip_buy_pct_deep', 'dip_buy_within_vix_limit'].forEach(name => {
    expect(container.querySelectorAll(`input[name="spy_${name}"]`)).toHaveLength(1);
  });
  expect(container.querySelector('input[name="spy_max_leverage"]')).toHaveValue(2);
});

test('editing a percent stores the rule value', () => {
  const onChange = jest.fn();
  const value = initialSpyCashflowConfig(schema);
  render(<SpyCashflowSettings schema={schema} value={value} onChange={onChange} />);
  fireEvent.change(box('Dip trigger, normal VIX (% drop)'), { target: { value: '12' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...value, dip_trigger: 0.88 });
  fireEvent.change(box('Dip buy size, deep (%)'), { target: { value: '70' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...value, dip_buy_pct_deep: 0.7 });
  fireEvent.change(box('High VIX from'), { target: { value: '30' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...value, vix_high_threshold: 0.3 });
});

test('without the ladder parameters (older rules) every field stays in the plain grid', () => {
  const old = { rules: [p('dip_trigger', 0.92), p('high_vix_dip_trigger', 0.8), p('high_vix_dip_buy_pct', 0.15)], backtest: {} };
  expect(hasDipLadder(old)).toBe(false);
  const { container } = render(<SpyCashflowSettings schema={old} value={initialSpyCashflowConfig(old)} onChange={() => {}} />);
  expect(screen.queryByText('Dip ladder')).not.toBeInTheDocument();
  expect(container.querySelector('input[name="spy_dip_trigger"]')).toHaveValue(0.92);
});

test('with groups: labelled boxes, the ladder in its place, unknown settings under Other settings', () => {
  const s = { ...schema, rules: [...schema.rules, p('monthly_withdrawal_pct', 0.6), p('brand_new_setting', 3)] };
  const onChange = jest.fn();
  const value = initialSpyCashflowConfig(s);
  const { container } = render(<SpyCashflowSettings schema={s} value={value} onChange={onChange} groups={SPY_GROUPS} />);
  expect(screen.getByText('Money')).toBeInTheDocument();
  expect(screen.getByText('Dip ladder')).toBeInTheDocument();
  expect(screen.getByLabelText('Max leverage (x)')).toHaveValue(2);
  expect(screen.getByLabelText('Leverage at extreme VIX (x)')).toHaveValue(1.25);
  expect(box('Dip trigger, high VIX (% drop)')).toHaveValue(10);
  ['dip_trigger', 'extreme_vix', 'max_leverage', 'budget'].forEach(name => {
    expect(container.querySelectorAll(`input[name="spy_${name}"]`)).toHaveLength(1);
  });
  expect(screen.getByText('Other settings')).toBeInTheDocument();
  expect(screen.getByLabelText('Brand new setting')).toHaveValue(3);
  fireEvent.change(screen.getByLabelText('Max leverage (x)'), { target: { value: '1.8' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...value, max_leverage: 1.8 });
});
