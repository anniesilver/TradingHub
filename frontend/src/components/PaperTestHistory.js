import React, { useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material';
import { getPaperTestHistory } from '../services/simulationService';

// "Past tests": every paper test of this strategy so far (TradingHub's copy of the server's
// history, refreshed from the server when opened). Legacy = runs from before the
// Start paper test button, with the settings they used at the end.

const money = v => (v === null || v === undefined ? '' : `${Number(v) < 0 ? '-' : ''}$${Math.abs(Number(v))
  .toLocaleString(undefined, { maximumFractionDigits: 0 })}`);
const day = t => (t ? String(t).slice(0, 10) : '');

export default function PaperTestHistory({ strategyId }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const openDialog = async () => {
    setOpen(true); setBusy(true); setError(null);
    try {
      setData(await getPaperTestHistory(strategyId));
    } catch (e) {
      setError(e.response?.data?.error || e.message);
    } finally {
      setBusy(false);
    }
  };

  const tests = data?.tests || [];
  return (
    <>
      <Button variant="text" onClick={openDialog}>Past tests</Button>
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Paper tests so far</DialogTitle>
        <DialogContent>
          {busy && <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, my: 2 }}><CircularProgress size={20} /> Loading…</Box>}
          {data?.sync_error && <Alert severity="warning" sx={{ mb: 1 }}>Couldn't reach the server, showing the last copy: {data.sync_error}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          {data && !tests.length && <Typography variant="body2">No tests yet.</Typography>}
          {tests.length > 0 && (
            <Table size="small">
              <TableHead><TableRow>
                <TableCell>Test</TableCell><TableCell>Dates</TableCell><TableCell align="right">Trades</TableCell>
                <TableCell align="right">Paper P&amp;L (realized)</TableCell><TableCell>Rules</TableCell>
              </TableRow></TableHead>
              <TableBody>
                {tests.map(t => (
                  <TableRow key={`${t.strategy}/${t.id}`}>
                    <TableCell>
                      {t.label || t.id}{' '}
                      {t.status === 'running' && <Chip size="small" color="success" label="running" />}{' '}
                      {t.legacy && <Chip size="small" label="legacy" />}{' '}
                      {t.dry_run && <Chip size="small" label="dry run" />}
                    </TableCell>
                    <TableCell>{day(t.started)} – {t.status === 'running' ? 'now' : day(t.ended)}</TableCell>
                    <TableCell align="right">{t.trade_count}</TableCell>
                    <TableCell align="right">{money(t.paper_realized)}</TableCell>
                    <TableCell>{t.rules_commit ? t.rules_commit.slice(0, 7) : ''}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>Close</Button></DialogActions>
      </Dialog>
    </>
  );
}
