import React from 'react';
import {
  Box, Button, Checkbox, FormControlLabel, Grid, IconButton, Paper, TextField, Tooltip, Typography,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

// SPY_POWER_CASHFLOW on the shared rules: settings built from the rules' own parameter list
// (algo_trading/shared/tradekit/rules/spy_power_cashflow.py, served by
// /api/strategies/SPY_POWER_CASHFLOW_RULES/params), the same names the paper bot uses.

const BACKTEST_FIELDS = [
  ['short_iv_mult', 'Short call IV (x VIX)', "The calls are priced at VIX x this. Out-of-the-money SPY calls trade near SPY's own IV, about 0.8 x VIX. 1 = the old pricing at VIX.", { min: 0.1, step: 0.05 }],
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

// The dip-buy ladders (Annie 2026-11-21), shown as two small tables in percent instead of
// eight loose fractions. Each cell edits one rule parameter; the rules keep their own units.
const LADDER_KEYS = ['vix_high_threshold', 'extreme_vix', 'dip_trigger', 'high_vix_dip_trigger', 'extreme_vix_dip_trigger',
  'dip_buy_pct', 'dip_depth_mid', 'dip_buy_pct_mid', 'dip_depth_deep', 'dip_buy_pct_deep'];
const CAP_KEY = 'dip_buy_within_vix_limit';
const tidy = x => Number(x.toFixed(6));
// Percent shown <-> rule value: a fraction (x100), or a trigger (1 - drop%)
const AS_PCT = { toShow: v => tidy(v * 100), toRule: n => tidy(n / 100) };
const AS_DROP = { toShow: v => tidy((1 - v) * 100), toRule: n => tidy(1 - n / 100) };

export function hasDipLadder(schema) {
  const names = new Set((schema?.rules || []).map(p => p.name));
  return LADDER_KEYS.every(k => names.has(k));
}

function PctBox({ name, conv, value, onSet, prefix, help, ariaLabel }) {
  const v = value[name];
  const shown = (v === '' || v === null || v === undefined || Number.isNaN(Number(v))) ? '' : conv.toShow(Number(v));
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center' }}>
      <TextField size="small" type="number" name={`${prefix}_${name}`} value={shown}
        inputProps={{ step: 'any', min: 0, max: 100, 'aria-label': ariaLabel, style: { width: 56, textAlign: 'right' } }}
        onChange={e => onSet(name, e.target.value === '' ? '' : conv.toRule(Number(e.target.value)))} />
      <Typography variant="body2" sx={{ ml: 0.5 }}>%</Typography>
      <Help text={help} />
    </Box>
  );
}

function VixBox({ name, value, onSet, prefix, help, ariaLabel }) {
  const v = value[name];
  const shown = (v === '' || v === null || v === undefined) ? '' : tidy(Number(v) * 100);
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center' }}>
      <TextField size="small" type="number" name={`${prefix}_${name}`} value={shown}
        inputProps={{ step: 'any', min: 0, 'aria-label': ariaLabel, style: { width: 48, textAlign: 'right' } }}
        onChange={e => onSet(name, e.target.value === '' ? '' : tidy(Number(e.target.value) / 100))} />
      <Help text={help} />
    </Box>
  );
}

function DipLadder({ schema, value, set, prefix }) {
  const help = Object.fromEntries(schema.rules.map(p => [p.name, p.help]));
  const cap = schema.rules.find(p => p.name === CAP_KEY);
  const cell = { py: 0.5, pr: 2, verticalAlign: 'middle' };
  const head = { ...cell, fontWeight: 'bold', color: 'text.secondary', fontSize: 13, textAlign: 'left' };
  const props = { value, onSet: set, prefix };
  return (
    <Grid item xs={12}>
      <Paper variant="outlined" sx={{ p: 1.5, mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>Dip ladder</Typography>
        <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          <Box component="table" sx={{ borderCollapse: 'collapse' }} aria-label="When to buy">
            <caption style={{ captionSide: 'top', textAlign: 'left', fontSize: 13, paddingBottom: 4 }}>
              <b>When to buy</b>: a drop from the high since the last buy, by VIX
            </caption>
            <thead><tr><Box component="th" sx={head}>VIX</Box><Box component="th" sx={head}>Buy at a drop of</Box></tr></thead>
            <tbody>
              <tr>
                <Box component="td" sx={cell}>below {value.vix_high_threshold === '' ? '…' : tidy(Number(value.vix_high_threshold) * 100)}</Box>
                <Box component="td" sx={cell}><PctBox name="dip_trigger" conv={AS_DROP} help={help.dip_trigger} ariaLabel="Dip trigger, normal VIX (% drop)" {...props} /></Box>
              </tr>
              <tr>
                <Box component="td" sx={cell}>
                  <VixBox name="vix_high_threshold" help={help.vix_high_threshold} ariaLabel="High VIX from" {...props} /> to {value.extreme_vix === '' ? '…' : tidy(Number(value.extreme_vix) * 100)}
                </Box>
                <Box component="td" sx={cell}><PctBox name="high_vix_dip_trigger" conv={AS_DROP} help={help.high_vix_dip_trigger} ariaLabel="Dip trigger, high VIX (% drop)" {...props} /></Box>
              </tr>
              <tr>
                <Box component="td" sx={cell}>
                  <VixBox name="extreme_vix" ariaLabel="Extreme VIX from"
                    help={`${help.extreme_vix || ''} Also where the leverage limit drops to Extreme vix target.`} {...props} /> and up
                </Box>
                <Box component="td" sx={cell}><PctBox name="extreme_vix_dip_trigger" conv={AS_DROP} help={help.extreme_vix_dip_trigger} ariaLabel="Dip trigger, extreme VIX (% drop)" {...props} /></Box>
              </tr>
            </tbody>
          </Box>
          <Box component="table" sx={{ borderCollapse: 'collapse' }} aria-label="How much to buy">
            <caption style={{ captionSide: 'top', textAlign: 'left', fontSize: 13, paddingBottom: 4 }}>
              <b>How much to buy</b>: by how far the price is below the peak (highest price seen)
            </caption>
            <thead><tr><Box component="th" sx={head}>Below the peak</Box><Box component="th" sx={head}>Spend of buying power</Box></tr></thead>
            <tbody>
              <tr>
                <Box component="td" sx={cell}>any dip</Box>
                <Box component="td" sx={cell}><PctBox name="dip_buy_pct" conv={AS_PCT} help={help.dip_buy_pct} ariaLabel="Dip buy size, shallow (%)" {...props} /></Box>
              </tr>
              <tr>
                <Box component="td" sx={cell}>from <PctBox name="dip_depth_mid" conv={AS_PCT} help={help.dip_depth_mid} ariaLabel="Mid depth below the peak (%)" {...props} /></Box>
                <Box component="td" sx={cell}><PctBox name="dip_buy_pct_mid" conv={AS_PCT} help={help.dip_buy_pct_mid} ariaLabel="Dip buy size, mid (%)" {...props} /></Box>
              </tr>
              <tr>
                <Box component="td" sx={cell}>from <PctBox name="dip_depth_deep" conv={AS_PCT} help={help.dip_depth_deep} ariaLabel="Deep depth below the peak (%)" {...props} /></Box>
                <Box component="td" sx={cell}><PctBox name="dip_buy_pct_deep" conv={AS_PCT} help={help.dip_buy_pct_deep} ariaLabel="Dip buy size, deep (%)" {...props} /></Box>
              </tr>
            </tbody>
          </Box>
        </Box>
        {cap && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <FormControlLabel
              control={<Checkbox name={`${prefix}_${CAP_KEY}`} checked={!!value[CAP_KEY]} onChange={e => set(CAP_KEY, e.target.checked)} />}
              label="Cap each buy at today's leverage limit (2x; Vix deleverage target at high VIX, Extreme vix target at extreme VIX)"
            />
            <Help text={cap.help} />
          </Box>
        )}
      </Paper>
    </Grid>
  );
}

export function initialSpyCashflowConfig(schema) {
  const cfg = {};
  schema.rules.forEach(p => { cfg[p.name] = p.default; });
  return { ...cfg, ...schema.backtest };
}

// POOR_COVERED_CALL's backtest-only settings (tradekit.backtests.POOR_COVERED_CALL_DEFAULTS)
export const PCC_BACKTEST_FIELDS = [
  // Blank = auto from the ticker: SPY 0.8 x VIX, $0.40 / $0.05, 1.3%, 0.17; another stock 1.0 x its own IV,
  // slippage 0.2% / 0.05% of its price, its own dividend yield, its median IV
  ['short_iv_mult', 'Short call IV (x VIX or own IV)', "The monthly calls are priced at the 30-day IV x this: VIX for SPY, the stock's own IV otherwise. Blank = auto: 0.8 for SPY (its calls trade near SPY's own IV, about 0.8 x VIX), 1.0 for a stock.", { min: 0.1, step: 0.05 }],
  ['long_slippage', 'Long call slippage ($/share)', "Half the year-out call's bid/ask spread, paid on each purchase and sale. Blank = auto: $0.40 for SPY, 0.2% of the price for a stock.", { min: 0, step: 0.05 }],
  ['short_slippage', 'Short call slippage ($/share)', "Half the monthly call's spread. Blank = auto: $0.05 for SPY, 0.05% of the price (at least $0.05) for a stock.", { min: 0, step: 0.01 }],
  ['risk_free_rate', 'Risk-free rate', "For Black-Scholes, e.g. 0.04 = 4%. Blank = the 3-month T-bill rate of each day (near 0% in 2009-2015 and 2020-2021): the interest cost built into a call's price.", { min: 0, step: 0.005 }],
  ['cash_rate', 'Cash interest rate', 'What the idle cash earns a year, as if parked in a T-bill ETF like SGOV. Blank = the 3-month T-bill rate of each day minus the fee below; 0 = no interest.', { min: 0, step: 0.005 }],
  ['cash_rate_fee', 'Cash interest fee', "Taken off the T-bill rate: 0.0009 = SGOV's 0.09% fee. Use about 0.005 for IB's own cash rate.", { min: 0, step: 0.0005 }],
  ['cash_reserve_pct', 'Cash reserve', "This share of equity stays plain cash and earns nothing; the rest earns the cash interest rate (in the paper bot: sits in SGOV). 0.05 = 5%.", { min: 0, max: 1, step: 0.01 }],
  ['park_cash', 'Paper bot: park spare cash in SGOV', "The paper test buys SGOV with the cash above the reserve once a day at 15:50 and sells it when a buyback or roll needs the money. Off: the cash stays at IB.", { type: 'bool' }],
  ['dividend_yield', 'Dividend yield', "For Black-Scholes. Blank = auto: 1.3% for SPY, the stock's own dividends a year / its average price.", { min: 0, step: 0.001 }],
  ['long_iv_base', 'Long IV base', "Year-out IV = base + damp x (30-day IV - base). Blank = auto: 0.17 for SPY, the stock's median IV over the run.", { min: 0, step: 0.01 }],
  ['long_iv_damp', 'Long IV damp', 'How much of a 30-day IV move the year-out IV follows (0.35 = 35%).', { min: 0, step: 0.05 }],
];

// SPY Power Cashflow's rules in labelled boxes, in plain units. [name, label, unit]:
// unit 'pct' shows x100 (0.25 -> 25 %), 'drop' shows the drop (0.92 -> 8 % below), 'vix' shows
// VIX points (0.25 -> 25), anything else is the value as stored. Settings not listed here
// still show, under "Other settings", so a new rule parameter never goes missing.
export const SPY_GROUPS = [
  { title: 'Money', fields: [
    ['budget', 'Budget', '$'], ['initial_position_pct', 'First buy (% of budget)', 'pct'],
    ['monthly_withdrawal_pct', 'Monthly withdrawal (%)', ''], ['margin_interest_rate', 'Margin interest (% a year)', 'pct'],
    ['stock_commission', 'Stock commission ($/share)', ''], ['min_commission', 'Min commission ($/order)', ''],
  ] },
  { title: 'Leverage', fields: [
    ['max_leverage', 'Max leverage (x)', ''],
    ['vix_deleverage_threshold', 'Deleverage from VIX', 'vix'], ['vix_deleverage_target', 'Leverage at high VIX (x)', ''],
    ['extreme_vix_target', 'Leverage at extreme VIX (x)', ''],   // "Extreme VIX from" is in the Dip ladder
    ['min_keep_pct', 'Always keep (% of shares)', 'pct'], ['equity_counts_calls', 'Equity counts the short calls', ''],
  ] },
  { ladder: true },   // the Dip ladder box (when to buy, how much), when the rules have it
  { title: 'Covered calls', fields: [
    ['min_strike_distance', 'Strike at least (% above)', 'pct'], ['volatility_scaling', 'or VIX x this', ''],
    ['strike_rounding', 'Strike rounding ($)', ''], ['min_premium', 'Min premium ($/share)', ''],
    ['covered_call_ratio', 'Calls per 100 shares', ''], ['month_end_buyback_buffer', 'Month-end buyback buffer (%)', 'pct'],
    ['rebuy_after_assignment', 'Rebuy shares after assignment', ''],
  ] },
];

const round6 = x => Math.round(x * 1e6) / 1e6;
const toShown = (unit, v) => {
  if (v === '' || v === null || v === undefined || typeof v !== 'number') return v ?? '';
  if (unit === 'pct' || unit === 'vix') return round6(v * 100);
  if (unit === 'drop') return round6((1 - v) * 100);
  return v;
};
const fromShown = (unit, n) => {
  if (unit === 'pct' || unit === 'vix') return round6(n / 100);
  if (unit === 'drop') return round6(1 - n / 100);
  return n;
};

export default function SpyCashflowSettings({ schema, value, onChange, title = 'SPY Power Cashflow rules (same as the paper bot)',
  backtestFields = BACKTEST_FIELDS, prefix = 'spy', groups = null }) {
  if (!schema || !value) {
    return <Grid item xs={12}><Typography variant="body2" color="text.secondary">Loading the rules' settings…</Typography></Grid>;
  }
  const set = (name, v) => onChange({ ...value, [name]: v });
  const number = (p, raw) => {
    if (raw === '') return '';
    const n = Number(raw);
    return Number.isNaN(n) ? raw : (p.type === 'int' ? Math.trunc(n) : n);
  };
  const ladder = hasDipLadder(schema);
  const inLadder = new Set(ladder ? [...LADDER_KEYS, CAP_KEY] : []);
  // shown in a box or the ladder: everything else goes under "Other settings"
  const grouped = new Set([...inLadder, ...(groups || []).flatMap(g => (g.fields || []).map(([n]) => n))]);
  return (
    <>
      <Grid item xs={12}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mt: 1, mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>{title}</Typography>
          <Button size="small" variant="text" onClick={() => onChange(initialSpyCashflowConfig(schema))}>Rule defaults</Button>
        </Box>
      </Grid>
      {!groups && ladder && <DipLadder schema={schema} value={value} set={set} prefix={prefix} />}
      {groups && groups.map(g => {
        if (g.ladder) return ladder ? <DipLadder key="dip-ladder" schema={schema} value={value} set={set} prefix={prefix} /> : null;
        const byName = Object.fromEntries(schema.rules.map(p => [p.name, p]));
        const fields = g.fields.filter(([name]) => byName[name]);
        if (!fields.length) return null;
        return (
          <Grid item xs={12} key={g.title}>
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>{g.title}</Typography>
              <Grid container spacing={1.5}>
                {fields.map(([name, text, unit]) => {
                  const p = byName[name];
                  if (p.type === 'bool') {
                    return (
                      <Grid item xs={12} sm={6} md={3} key={name}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <FormControlLabel label={text}
                            control={<Checkbox name={`${prefix}_${name}`} checked={!!value[name]} onChange={e => set(name, e.target.checked)} />} />
                          <Help text={p.help} />
                        </Box>
                      </Grid>
                    );
                  }
                  return (
                    <Grid item xs={12} sm={4} md={2} key={name}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <TextField fullWidth size="small" type="number" label={text} name={`${prefix}_${name}`}
                          value={toShown(unit, value[name])} InputLabelProps={{ shrink: true }}
                          onChange={e => {
                            const raw = e.target.value;
                            if (raw === '' || Number.isNaN(Number(raw))) { set(name, raw); return; }
                            set(name, number(p, fromShown(unit, Number(raw))));
                          }}
                          inputProps={{ step: 'any' }} />
                        <Help text={p.help} />
                      </Box>
                    </Grid>
                  );
                })}
              </Grid>
              {g.note && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>{g.note}</Typography>}
            </Paper>
          </Grid>
        );
      })}
      {groups && schema.rules.some(p => !grouped.has(p.name)) && (
        <Grid item xs={12}><Typography variant="body2" sx={{ fontWeight: 'bold' }}>Other settings</Typography></Grid>
      )}
      {schema.rules.filter(p => !grouped.has(p.name)).map(p => {
        if (p.type === 'bool') {
          return (
            <Grid item xs={12} sm={6} md={3} key={p.name}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FormControlLabel
                  control={<Checkbox name={`${prefix}_${p.name}`} checked={!!value[p.name]} onChange={e => set(p.name, e.target.checked)} />}
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
              <TextField fullWidth size="small" label={label(p.name)} name={`${prefix}_${p.name}`}
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
      {backtestFields.map(([name, text, help, limits]) => limits?.type === 'bool' ? (
        <Grid item xs={12} sm={6} md={3} key={name}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControlLabel
              control={<Checkbox name={`${prefix}_${name}`} checked={!!value[name]} onChange={e => set(name, e.target.checked)} />}
              label={text}
            />
            <Help text={help} />
          </Box>
        </Grid>
      ) : (
        <Grid item xs={12} sm={3} md={1.5} key={name}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TextField fullWidth size="small" type="number" label={text} name={`${prefix}_${name}`} value={value[name] ?? ''}
              placeholder="auto" InputLabelProps={{ shrink: true }}
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

const pct = v => (v === null || v === undefined) ? '—' : `${v}%`;

// Summary tiles of a POOR_COVERED_CALL backtest
export function PoorCoveredCallResults({ summary }) {
  if (!summary) return null;
  const s = summary;
  const tiles = [
    ['Final value', money(s.final_value)],
    ['Per year', pct(s.cagr)],
    ['Worst drawdown', pct(s.max_drawdown_pct)],
    [`${s.underlying || 'SPY'} buy & hold`, money(s.benchmark_final_value)],
    ['Long call only (same rolls)', money(s.long_only_final_value)],
    ['Cash interest earned', money(s.cash_interest)],
    ['Calls sold', s.calls_sold],
    ['Harvests', s.harvests],
    ['Month-end buybacks', s.month_end_buybacks],
    ['Expired', s.calls_expired],
    ['Dividend buybacks', s.dividend_buybacks],
    ['Long call rolls', s.rolls],
    ['Net premiums', money((s.premiums || 0) - (s.buybacks || 0))],
    ['Long call P&L (rolls)', money(s.long_pnl)],
  ];
  return (
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid item xs={12}>
        <Paper elevation={2} sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'text.primary' }}>
            Poor Covered Call summary (shared rules)
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
          {s.long && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              At the end: long {s.long_qty} {s.long}{s.short ? `, short ${s.short_qty} ${s.short}` : ', no short call'}
            </Typography>
          )}
        </Paper>
      </Grid>
    </Grid>
  );
}
