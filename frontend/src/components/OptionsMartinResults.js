import React from 'react';
import { Box, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';

const money = v => (v === null || v === undefined) ? '—'
  : `${v < 0 ? '-' : ''}$${Math.abs(Number(v)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

// Summary tiles and the list of rounds of an OPTIONS_MARTIN backtest (tradekit OptionsMartinRun)
export default function OptionsMartinResults({ summary, rounds, notes }) {
  if (!summary) return null;
  const s = summary;
  const n = notes || {};
  const exits = Object.entries(s.exits || {}).map(([k, v]) => `${k.toLowerCase()} ${v}`).join(', ') || '—';
  const tiles = [
    ['Rounds', s.rounds],
    ['Wins / losses', `${s.wins} / ${s.losses}`],
    ['Win rate', `${Math.round((s.win_rate || 0) * 100)}%`],
    ['Total P&L', money(s.total_pnl)],
    ['Best round', money(s.best_round)],
    ['Worst round', money(s.worst_round)],
    ['Avg round cost', money(s.avg_cost)],
    ['Max round cost', money(s.max_round_cost)],
    ['Avg buys per round', (s.avg_loads || 0).toFixed(1)],
    ['Exits', exits],
    ['Commissions', money(s.commissions)],
    ['Max drawdown', money(s.max_drawdown)],
  ];
  return (
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid item xs={12}>
        <Paper elevation={2} sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'text.primary' }}>
            Options Martingale summary · {s.underlying}
          </Typography>
          <Grid container spacing={2}>
            {tiles.map(([label, value]) => (
              <Grid item xs={6} sm={4} md={2} key={label}>
                <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="body2" color="text.secondary">{label}</Typography>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'text.primary', wordBreak: 'break-word' }}>{value}</Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
          {rounds && rounds.length > 0 && (
            <TableContainer sx={{ mt: 2, maxHeight: 420 }}>
              <Table size="small" stickyHeader aria-label="Rounds">
                <TableHead>
                  <TableRow>
                    {['Start', 'End', 'Contract', 'Buys', 'Contracts', 'Cost', 'Exit', 'P&L'].map(h => <TableCell key={h}>{h}</TableCell>)}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rounds.map(r => (
                    <TableRow key={r.start}>
                      <TableCell>{r.start}</TableCell>
                      <TableCell>{r.end || '—'}</TableCell>
                      <TableCell>{r.contract}</TableCell>
                      <TableCell>{r.loads}</TableCell>
                      <TableCell>{r.contracts}</TableCell>
                      <TableCell>{money(r.cost)}</TableCell>
                      <TableCell>{r.exit}</TableCell>
                      <TableCell sx={{ color: r.pnl > 0 ? 'success.main' : r.pnl < 0 ? 'error.main' : undefined }}>{money(r.pnl)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
            Option prices are modeled, not real quotes: {n.pricing || 'Black-Scholes'}, priced at IV x {n.price_iv_mult ?? 1}.
            Volatility: {n.iv_name || '—'} ({n.bars_with_iv ?? '?'} of {n.bars ?? '?'} bars had IV; the rest use the last one).
            Strike step ${n.strike_step}, slippage ${n.slippage}/share, fills: {n.fill_mode}.
            Decides after every completed bar and rolls like the paper bot.
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  );
}
