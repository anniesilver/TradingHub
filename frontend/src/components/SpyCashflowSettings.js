import React from 'react';
import {
  Box, Button, Checkbox, FormControlLabel, Grid, IconButton, Paper, TextField, Tooltip, Typography,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

// SPY_POWER_CASHFLOW on the shared rules: settings built from the rules' own parameter list
// (algo_trading/shared/tradekit/rules/spy_power_cashflow.py, served by
// /api/strategies/SPY_POWER_CASHFLOW_RULES/params), the same names the paper bot uses.

const BACKTEST_FIELDS = [
  ['strike_step', 'Strike step ($)', 'Dollars between made-up strikes near the price (SPY lists every $1).', { min: 0.5, step: 0.5 }],
  ['slippage', 'Slippage ($/share)', 'Added to each purchase, taken off each sale.', { min: 0, step: 0.01 }],
  ['risk_free_rate', 'Risk-free rate', 'For Black-Scholes, e.g. 0.05 = 5%.', { min: 0, step: 0.005 }],
];

const label = name => name.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());

function Help({ text }) {
  if (!text) return null;
  return (
    <Tooltip title={text} arrow describeChild>
      <IconButton size="small" aria-label={`Help: ${text}`} sx={{ ml: 0.25 }}>
        <HelpOutlineIcon sx={{ fontSize: 16 }} />
      </IconButton>
    </Tooltip>
  );
}

export function initialSpyCashflowConfig(schema) {
  const cfg = {};
  schema.rules.forEach(p => { cfg[p.name] = p.default; });
  return { ...cfg, ...schema.backtest };
}

export default function SpyCashflowSettings({ schema, value, onChange }) {
  if (!schema || !value) {
    return <Grid item xs={12}><Typography variant="body2" color="text.secondary">Loading the rules' settings…</Typography></Grid>;
  }
  const set = (name, v) => onChange({ ...value, [name]: v });
  const number = (p, raw) => {
    if (raw === '') return '';
    const n = Number(raw);
    return Number.isNaN(n) ? raw : (p.type === 'int' ? Math.trunc(n) : n);
  };
  return (
    <>
      <Grid item xs={12}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mt: 1, mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>SPY Power Cashflow rules (same as the paper bot)</Typography>
          <Button size="small" variant="text" onClick={() => onChange(initialSpyCashflowConfig(schema))}>Rule defaults</Button>
        </Box>
      </Grid>
      {schema.rules.map(p => {
        if (p.type === 'bool') {
          return (
            <Grid item xs={12} sm={6} md={3} key={p.name}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FormControlLabel
                  control={<Checkbox name={`spy_${p.name}`} checked={!!value[p.name]} onChange={e => set(p.name, e.target.checked)} />}
                  label={label(p.name)}
                />
                <Help text={p.help} />
              </Box>
            </Grid>
          );
        }
        const numeric = p.type === 'int' || p.type === 'float';
        return (
          <Grid item xs={12} sm={3} md={1.5} key={p.name}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <TextField fullWidth size="small" label={label(p.name)} name={`spy_${p.name}`}
                type={numeric ? 'number' : 'text'} value={value[p.name] ?? ''}
                onChange={e => set(p.name, numeric ? number(p, e.target.value) : e.target.value)}
                inputProps={numeric ? { min: p.min ?? undefined, max: p.max ?? undefined, step: 'any' } : {}} />
              <Help text={p.help} />
            </Box>
          </Grid>
        );
      })}
      <Grid item xs={12}>
        <Typography variant="subtitle2" sx={{ mt: 1, mb: 1, fontWeight: 'bold' }}>Backtest settings</Typography>
      </Grid>
      {BACKTEST_FIELDS.map(([name, text, help, limits]) => (
        <Grid item xs={12} sm={3} md={1.5} key={name}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TextField fullWidth size="small" type="number" label={text} name={`spy_${name}`} value={value[name] ?? ''}
              onChange={e => set(name, e.target.value === '' ? '' : Number(e.target.value))} inputProps={limits} />
            <Help text={help} />
          </Box>
        </Grid>
      ))}
    </>
  );
}

const money = v => (v === null || v === undefined) ? '—'
  : `${v < 0 ? '-' : ''}$${Math.abs(Number(v)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

// Summary tiles of a SPY_POWER_CASHFLOW backtest on the shared rules
export function SpyCashflowResults({ summary }) {
  if (!summary) return null;
  const s = summary;
  const tiles = [
    ['Final value', money(s.final_value)],
    ['Withdrawn', money(s.withdrawn)],
    ['SPY buy & hold', money(s.benchmark_final_value)],
    ['Calls sold', s.calls_sold],
    ['Bought back / expired', `${s.calls_bought_back} / ${s.calls_expired}`],
    ['Assigned', s.calls_assigned],
    ['Dip buys', s.dip_buys],
    ['Deleverage sales', s.deleverage_sales],
    ['Net premiums', money((s.premiums || 0) - (s.buybacks || 0))],
    ['Margin interest', money(s.interest)],
    ['Dividends', money(s.dividends)],
    ['Max leverage', `${s.max_leverage_seen}x`],
  ];
  return (
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid item xs={12}>
        <Paper elevation={2} sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'text.primary' }}>
            SPY Power Cashflow summary (shared rules)
          </Typography>
          <Grid container spacing={2}>
            {tiles.map(([text, v]) => (
              <Grid item xs={6} sm={4} md={2} key={text}>
                <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="body2" color="text.secondary">{text}</Typography>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'text.primary' }}>{v ?? '—'}</Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Paper>
      </Grid>
    </Grid>
  );
}
