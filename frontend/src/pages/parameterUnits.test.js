import { parameterUnits, toDisplayValue, toStoredValue, toDisplayInputProps } from './parameterUnits';

test.each([
  ['callCostBuffer', 0.05, 5],
  ['coveredCallRatio', 1, 100],
  ['dipBuyPercent', 0.4, 40],
  ['highVixDipBuyPercent', 0.15, 15],
  ['initialPositionPercent', 0.6, 60],
  ['marginInterestRate', 0.06, 6],
  ['minStrikeDistance', 0.015, 1.5],
  ['riskFreeRate', 0.05, 5],
  ['IV_ENTRY_THRESHOLD', 0.3, 30],
  ['IV_EXIT_THRESHOLD', 0.5, 50],
  ['INITIAL_POSITION_PERCENT', 0.6, 60],
  ['SLIPPAGE_PERCENT', 0.001, 0.1],
])('%s converts percentages in both directions', (name, stored, displayed) => {
  expect(toDisplayValue(name, stored)).toBe(displayed);
  expect(toStoredValue(name, displayed)).toBe(stored);
  expect(toDisplayValue(name, 0)).toBe(0);
  expect(toStoredValue(name, 0)).toBe(0);
});

test.each([
  ['monthlyWithdrawalRate', 1],
  ['dipTrigger', 0.92],
  ['highVixDipTrigger', 0.8],
  ['DEC_INDEX', 0.6],
  ['INC_INDEX', 2],
  ['vixHighThreshold', 0.25],
  ['vixDeleverageThreshold', 0.25],
  ['maxMarginRatio', 2],
  ['volatilityScalingFactor', 0.15],
  ['initialBalance', 200000],
])('%s retains its existing units', (name, value) => {
  expect(toDisplayValue(name, value)).toBe(value);
  expect(toStoredValue(name, value)).toBe(value);
});

test('every scaled field is explicitly labelled as a percentage', () => {
  Object.values(parameterUnits).filter((unit) => unit.displayScale === 100).forEach((unit) => {
    expect(unit.label).toContain('%');
  });
});

test('converts numeric constraints to the same units as the input', () => {
  expect(toDisplayInputProps('SLIPPAGE_PERCENT', { min: 0, max: 0.01, step: 0.0001 })).toEqual({
    min: 0, max: 1, step: 0.01,
  });
  expect(toDisplayInputProps('monthlyWithdrawalRate', { min: 0, max: 10, step: 0.1 })).toEqual({
    min: 0, max: 10, step: 0.1,
  });
  expect(toDisplayInputProps('dipBuyPercent', { step: 'any', 'aria-describedby': 'help' })).toEqual({
    step: 'any', 'aria-describedby': 'help',
  });
});

test('avoids floating-point display noise and preserves empty values', () => {
  expect(toDisplayValue('dipBuyPercent', 0.07)).toBe(7);
  expect(toStoredValue('SLIPPAGE_PERCENT', 0.07)).toBe(0.0007);
  ['', null, undefined].forEach((value) => {
    expect(toDisplayValue('dipBuyPercent', value)).toBe(value);
    expect(toStoredValue('dipBuyPercent', value)).toBe(value);
  });
});
