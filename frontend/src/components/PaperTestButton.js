import React, { useState } from 'react';
import {
  Alert, Box, Button, Checkbox, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControlLabel, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { cancelPaperTest, getPaperTest, startPaperTest } from '../services/simulationService';

// "Start paper test": run these exact settings on the trade-engine server's paper account.
// One test runs per strategy. If the strategy still holds positions, they are listed and
// must be closed (at the price available) before the new test starts.

const money = v => (v === null || v === undefined ? 'no price now'
  : `${v < 0 ? '-' : ''}$${Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`);

function Positions({ held }) {
  const total = held.every(p => p.value !== null && p.value !== undefined)
    ? held.reduce((sum, p) => sum + p.value, 0) : null;
  return (
    <Table size="small" sx={{ my: 1 }}>
      <TableHead><TableRow><TableCell>Position</TableCell><TableCell align="right">Value now</TableCell></TableRow></TableHead>
      <TableBody>
        {held.map(p => (
          <TableRow key={p.contract}>
            <TableCell>{p.qty > 0 ? '+' : ''}{p.qty} {p.contract}</TableCell>
            <TableCell align="right">{money(p.value)}</TableCell>
          </TableRow>
        ))}
        {held.length > 1 && <TableRow><TableCell><b>Total</b></TableCell><TableCell align="right"><b>{money(total)}</b></TableCell></TableRow>}
      </TableBody>
    </Table>
  );
}

function CurrentTest({ status }) {
  const t = status.test;
  const books = status.last_status?.books;
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="body2">
        <b>Running now:</b>{' '}
        {t ? `${t.label || t.id} since ${(t.started || '').slice(0, 10)} (${t.dry_run ? 'dry run' : 'paper orders'}, rules ${t.rules_commit?.slice(0, 7)})`
          : `the settings already on the server (${status.dry_run ? 'dry run' : 'paper orders'})`}
      </Typography>
      {books && <Typography variant="body2" color="text.secondary">
        Realized {money(books.realized)} after {books.trades} trades{books.unrealized !== null && books.unrealized !== undefined ? `, open ${money(books.unrealized)}` : ''}
      </Typography>}
    </Box>
  );
}

export default function PaperTestButton({ strategyId, config, disabled }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);
  const [dryRun, setDryRun] = useState(false);
  const [label, setLabel] = useState('');

  const errorOf = e => e.response?.data?.error || e.message;

  const openDialog = async () => {
    setOpen(true); setBusy(true); setError(null); setDone(null); setStatus(null);
    try {
      setStatus(await getPaperTest(strategyId));
    } catch (e) {
      setError(errorOf(e));
    } finally {
      setBusy(false);
    }
  };

  const start = async (closeOut) => {
    setBusy(true); setError(null);
    try {
      const out = await startPaperTest({ ...config, strategyId }, { dryRun, closeOut, label });
      if (out.needs_close_out) {
        setStatus(s => ({ ...s, held: out.held }));
        setError(out.message);
      } else {
        setDone(out);
      }
    } catch (e) {
      setError(errorOf(e));
    } finally {
      setBusy(false);
    }
  };

  const cancelWaiting = async () => {
    setBusy(true);
    try {
      await cancelPaperTest(strategyId);
      setStatus(await getPaperTest(strategyId));
    } catch (e) {
      setError(errorOf(e));
    } finally {
      setBusy(false);
    }
  };

  const held = status?.held || [];
  return (
    <>
      <Button variant="outlined" color="primary" onClick={openDialog} disabled={disabled}>Start paper test</Button>
      <Dialog open={open} onClose={() => !busy && setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Start a paper test</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Runs these exact settings on the server's paper account, with the algo_trading rules this backtest ran.
            It replaces the current test.
          </Typography>
          {busy && !status && <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, my: 2 }}><CircularProgress size={20} /> Asking the server…</Box>}
          {status && <CurrentTest status={status} />}
          {status?.waiting && <Alert severity="info" sx={{ my: 1 }} action={<Button size="small" onClick={cancelWaiting} disabled={busy}>Cancel it</Button>}>
            A new test ({status.waiting.label || status.waiting.id}) is already waiting for the close-out.
          </Alert>}
          {status && held.length > 0 && !done && (
            <Alert severity="warning" sx={{ my: 1 }}>
              It still holds positions. They must be closed before a new test starts:
              <Positions held={held} />
              Closing sells at the bid and buys back at the ask, starting from 09:35 New York time on a trading day.
            </Alert>
          )}
          {status && !done && (
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', mt: 1 }}>
              <TextField size="small" label="Name (optional)" value={label} onChange={e => setLabel(e.target.value)} />
              <FormControlLabel control={<Checkbox checked={dryRun} onChange={e => setDryRun(e.target.checked)} />}
                label="Dry run (no orders sent)" />
            </Box>
          )}
          {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
          {done && <Alert severity="success" sx={{ mt: 1 }}>{done.message}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={busy}>{done ? 'Close' : 'Cancel'}</Button>
          {status && !done && (held.length > 0
            ? <Button variant="contained" color="warning" onClick={() => start(true)} disabled={busy}>Close positions and start</Button>
            : <Button variant="contained" onClick={() => start(false)} disabled={busy}>Start paper test</Button>)}
        </DialogActions>
      </Dialog>
    </>
  );
}
