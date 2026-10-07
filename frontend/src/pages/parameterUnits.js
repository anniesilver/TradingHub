// UI percentages are human-readable; configuration/API values retain their units.
// Monthly withdrawals already use percentage points and must not be divided by 100.
export const parameterUnits = {
  callCostBuffer: { label: 'Call Cost Buffer (%)', displayScale: 100 },
  coveredCallRatio: { label: 'Covered Call Ratio (%)', displayScale: 100 },
  dipBuyPercent: { label: 'Dip Buy (%)', displayScale: 100 },
  highVixDipBuyPercent: { label: 'High-VIX Buy %', displayScale: 100 },
  initialPositionPercent: { label: 'Initial Position %', displayScale: 100 },
  marginInterestRate: { label: 'Margin Interest Rate (%)', displayScale: 100 },
  minStrikeDistance: { label: 'Min Strike Distance (%)', displayScale: 100 },
  riskFreeRate: { label: 'Risk Free Rate (%)', displayScale: 100 },
  IV_ENTRY_THRESHOLD: { label: 'IV Entry Threshold (%)', displayScale: 100 },
  IV_EXIT_THRESHOLD: { label: 'IV Exit Threshold (%)', displayScale: 100 },
  INITIAL_POSITION_PERCENT: { label: 'Initial Position %', displayScale: 100 },
  SLIPPAGE_PERCENT: { label: 'Slippage %', displayScale: 100 },
  monthlyWithdrawalRate: { label: 'Monthly Withdrawal Rate (%)', displayScale: 1 },
  dipTrigger: { label: 'Dip Trigger (ratio)' },
  highVixDipTrigger: { label: 'High-VIX Dip Trigger (ratio)' },
  DEC_INDEX: { label: 'Add-Load Trigger (ratio)' },
  vixHighThreshold: { label: 'VIX High Threshold (normalized)' },
  vixDeleverageThreshold: { label: 'VIX Deleverage Threshold (normalized)' },
};

const displayScale = (name) => parameterUnits[name]?.displayScale ?? 1;

// Avoid exposing binary floating-point noise, e.g. 0.07 * 100 = 7.000000000000001.
const cleanNumber = (value) => Number(value.toPrecision(12));

export const toDisplayValue = (name, value) => {
  const scale = displayScale(name);
  if (scale === 1 || value === '' || value === null || value === undefined) return value;
  return cleanNumber(Number(value) * scale);
};

export const toStoredValue = (name, value) => {
  const scale = displayScale(name);
  if (scale === 1 || value === '' || value === null || value === undefined) return value;
  return cleanNumber(Number(value) / scale);
};

export const toDisplayInputProps = (name, inputProps) => {
  const result = { ...inputProps };
  ['min', 'max', 'step'].forEach((constraint) => {
    if (result[constraint] !== undefined && result[constraint] !== 'any') {
      result[constraint] = toDisplayValue(name, result[constraint]);
    }
  });
  return result;
};
