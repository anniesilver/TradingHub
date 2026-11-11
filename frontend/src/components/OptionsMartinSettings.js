import React from 'react';
import {
  Box, Button, Checkbox, FormControl, FormControlLabel, Grid, IconButton, InputLabel, MenuItem, Select,
  TextField, Tooltip, Typography,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

// OPTIONS_MARTIN settings, built from the rules' own parameter list
// (algo_trading/shared/tradekit/rules/options_martin.py, served by /api/strategies/OPTIONS_MARTIN/params),
// so every rule the paper bot has can be tuned here under the same name.

// Backtest-only settings (the live bot doesn't have these)
const BACKTEST_FIELDS = [
  ['strike_step', 'Strike step ($)', 'Dollars between made-up strikes near the price (TSLA lists every $2.50).', { min: 0.5, step: 0.5 }],
  ['price_iv_mult', 'Price IV multiplier', 'Options are priced at IV x this. Short-dated out-of-the-money calls trade well above the 30-day IV; the IV filter still sees plain IV.', { min: 0.1, max: 10, step: 0.1 }],
  ['slippage', 'Slippage ($/share)', 'Added to each purchase, taken off each sale.', { min: 0, step: 0.01 }],
  ['risk_free_rate', 'Risk-free rate', 'For Black-Scholes, e.g. 0.05 = 5%.', { min: 0, step: 0.005 }],
  ['cash', 'Starting cash (0 = round budget)', 'Cash the backtest starts with; 0 uses the round budget.', { min: 0, step: 100 }],
];
const FILL_MODES = [
  ['next_open', 'Next bar open'],
  ['close', 'Deciding bar close (optimistic)'],
  ['cautious', 'Next bar high/low (cautious)'],
];

function Help({ id, text }) {
  if (!text) return null;
  return (
    <Tooltip title={text} arrow describeChild>
      <IconButton size="small" aria-label={`Help: ${text}`} sx={{ ml: 0.25 }}>
        <HelpOutlineIcon sx={{ fontSize: 16 }} />
      </IconButton>
    </Tooltip>
  );
}

const label = name => name.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());

export function initialOptionsMartinConfig(schema) {
  const cfg = {};
  schema.rules.forEach(p => { cfg[p.name] = p.default; });
  Object.assign(cfg, schema.backtest, schema.presets?.paper_bot || {});
  return cfg;
}

export default function OptionsMartinSettings({ schema, value, onChange }) {
  if (!schema || !value) {
    return <Grid item xs={12}><Typography variant="body2" color="text.secondary">Loading the rules' settings…</Typography></Grid>;
  }
  const set = (name, v) => onChange({ ...value, [name]: v });
  const number = (p, raw) => {
    if (raw === '') return '';
    const n = Number(raw);
    return Number.isNaN(n) ? raw : (p.type === 'int' ? Math.trunc(n) : n);
  };
  const applyPreset = (preset) => {
    const base = initialOptionsMartinConfig({ ...schema, presets: {} });
    onChange(preset ? { ...base, ...schema.presets.paper_bot } : base);
  };

  return (
    <>
      <Grid item xs={12}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mt: 1, mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>Options Martingale rules (same as the paper bot)</Typography>
          <Button size="small" variant="outlined" onClick={() => applyPreset(true)}>Paper bot settings</Button>
          <Button size="small" variant="text" onClick={() => applyPreset(false)}>Rule defaults</Button>
        </Box>
      </Grid>
      {schema.rules.filter(p => p.name !== 'underlying').map(p => {  // the Symbol field above is the underlying
        const id = `om-${p.name}-help`;
        if (p.type === 'bool') {
          return (
            <Grid item xs={12} sm={6} md={3} key={p.name}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FormControlLabel
                  control={<Checkbox name={`om_${p.name}`} checked={!!value[p.name]} onChange={e => set(p.name, e.target.checked)} />}
                  label={label(p.name)}
                />
                <Help id={id} text={p.help} />
              </Box>
            </Grid>
          );
        }
        if (p.choices) {
          return (
            <Grid item xs={12} sm={3} md={1.5} key={p.name}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FormControl fullWidth size="small">
                  <InputLabel id={`om-${p.name}-label`}>{label(p.name)}</InputLabel>
                  <Select labelId={`om-${p.name}-label`} name={`om_${p.name}`} label={label(p.name)}
                    value={value[p.name] ?? ''} onChange={e => set(p.name, e.target.value)}>
                    {p.choices.map(c => <MenuItem key={String(c)} value={c}>{String(c)}</MenuItem>)}
                  </Select>
                </FormControl>
                <Help id={id} text={p.help} />
              </Box>
            </Grid>
          );
        }
        const numeric = p.type === 'int' || p.type === 'float';
        return (
          <Grid item xs={12} sm={3} md={1.5} key={p.name}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <TextField fullWidth size="small" label={label(p.name)} name={`om_${p.name}`}
                type={numeric ? 'number' : 'text'} value={value[p.name] ?? ''}
                onChange={e => set(p.name, numeric ? number(p, e.target.value) : e.target.value)}
                inputProps={numeric ? { min: p.min ?? undefined, max: p.max ?? undefined, step: p.type === 'int' ? 1 : 'any' } : {}} />
              <Help id={id} text={p.help} />
            </Box>
          </Grid>
        );
      })}

      <Grid item xs={12}>
        <Typography variant="subtitle2" sx={{ mt: 1, mb: 1, fontWeight: 'bold' }}>Backtest settings</Typography>
      </Grid>
      <Grid item xs={12} sm={3} md={1.5}>
        <FormControl fullWidth size="small">
          <InputLabel id="om-fill_mode-label">Fills</InputLabel>
          <Select labelId="om-fill_mode-label" name="om_fill_mode" label="Fills" value={value.fill_mode ?? 'next_open'}
            onChange={e => set('fill_mode', e.target.value)}>
            {FILL_MODES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
          </Select>
        </FormControl>
      </Grid>
      {BACKTEST_FIELDS.map(([name, text, help, limits]) => (
        <Grid item xs={12} sm={3} md={1.5} key={name}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TextField fullWidth size="small" type="number" label={text} name={`om_${name}`} value={value[name] ?? ''}
              onChange={e => set(name, e.target.value === '' ? '' : Number(e.target.value))} inputProps={limits} />
            <Help id={`om-${name}-help`} text={help} />
          </Box>
        </Grid>
      ))}
    </>
  );
}
