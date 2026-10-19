import React, { useId, useState } from 'react';
import { IconButton, Tooltip } from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { visuallyHidden } from '@mui/utils';

const finite = value => typeof value === 'number' && Number.isFinite(value);
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const currency = value => finite(value) ? money.format(value) : 'N/A';
const percent = value => finite(value) && finite(value * 100) ? `${(value * 100).toFixed(2)}%` : 'N/A';
const ratio = value => finite(value) ? value.toFixed(2) : 'N/A';

function MetricHelp({ label, children }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return <>
    <span id={id} style={visuallyHidden}>{children}</span>
    <Tooltip title={children} describeChild arrow open={open} onOpen={() => setOpen(true)} onClose={() => setOpen(false)}>
      <IconButton size="small" aria-label={`About ${label}`} aria-describedby={id}
        onClick={() => setOpen(value => !value)} onKeyDown={event => { if (event.key === 'Escape') setOpen(false); }}
        sx={{ width: 28, height: 28, color: 'text.secondary', '@media (pointer: coarse)': { width: 36, height: 36 } }}>
        <HelpOutlineIcon sx={{ fontSize: 15 }} />
      </IconButton>
    </Tooltip>
  </>;
}

function HeadlineMetric({ label, value, caption, help }) {
  return <div className="performance-metric">
    <dt><span>{label}</span><MetricHelp label={label}>{help}</MetricHelp></dt>
    <dd><span className="performance-metric-value">{value}</span><span className="performance-metric-caption">{caption}</span></dd>
  </div>;
}

function CashFlowGroup({ title, rows }) {
  const id = useId();
  return <section className="performance-cash-group" aria-labelledby={id}>
    <h4 id={id}>{title}</h4>
    <dl>{rows.map(([label, value, help]) => <div className="performance-cash-row" key={label}>
      <dt><span>{label}</span>{help && <MetricHelp label={label}>{help}</MetricHelp>}</dt>
      <dd>{currency(value)}</dd>
    </div>)}</dl>
  </section>;
}

// Presentation only: consume the completed run's metrics. Calculation methods
// and monetary aggregation remain in Annie's existing processing pipeline.
export default function PerformanceSummary({ data, resultContext, sample = false }) {
  const id = useId();
  const points = data.chartData ?? [];
  const first = points[0];
  const last = points[points.length - 1];
  const initial = resultContext?.config?.initialBalance;
  const final = last?.Portfolio_Value;
  const withdrawals = data.totalWithdrawAmount;
  const adjusted = finite(final) && finite(withdrawals) ? final + withdrawals : null;
  // The existing CAGR function falls back to zero for ineligible periods.
  // Display N/A for those cases, without altering the stored metric/formula.
  const cagrAvailable = points.length > 1 && finite(initial) && initial > 0 && finite(adjusted) && adjusted > 0 &&
    new Date(last.date) - new Date(first.date) > 86400000;
  const riskFree = finite(data.sharpeRiskFreeRate) ? data.sharpeRiskFreeRate : resultContext?.config?.riskFreeRate;
  const cagrHelp = 'Compound annualized growth rate using final balance plus total withdrawals. This existing adjustment does not account for the timing of each withdrawal.';
  const drawdownHelp = 'Observed decline from the recorded equity peak; withdrawals can affect this measure. This does not predict future risk.';
  const sharpeHelp = 'Annualized mean daily excess return divided by its sample standard deviation, times √252. Monthly withdrawals are added back so they are not counted as losses. N/A means there are insufficient valid returns or no return variability.';

  return <section className="performance-summary" aria-labelledby={`${id}-title`}>
    <div className="performance-summary-heading">
      <div><span className="eyebrow">Return · Risk · Cash flows</span><h3 id={`${id}-title`}>{sample ? 'Sample performance summary' : 'Performance summary'}</h3></div>
      <p>{sample ? 'Fictional example' : 'Historical backtest'} <span aria-hidden="true">·</span> USD</p>
    </div>
    {sample && <p className="chart-note">Fixed example statistics for layout testing only—not calculated from the chart or a simulation.</p>}
    <dl className="performance-headlines">
      <HeadlineMetric label="CAGR" value={cagrAvailable ? percent(data.annualizedReturn) : 'N/A'} caption="Withdrawal-adjusted · annualized" help={cagrHelp} />
      <HeadlineMetric label="Maximum drawdown (MDD)" value={points.length ? percent(data.maxDrawdown) : 'N/A'} caption="Largest recorded peak-to-trough decline" help={drawdownHelp} />
      <HeadlineMetric label="Sharpe ratio" value={ratio(data.sharpeRatio)} caption="Annualized · risk-adjusted" help={sharpeHelp} />
    </dl>
    <div className="performance-cash-flows">
      <CashFlowGroup title="Income" rows={[
        ['Premiums received', data.totalPremiumsReceived],
        ['Dividends received', data.totalDividendsReceived],
      ]} />
      <CashFlowGroup title="Costs & distributions" rows={[
        ['Interest paid', data.totalInterestPaid],
        ['ITM call closure costs', data.totalAssignedCost, 'Total in-the-money call closure cost, including buybacks and assignments.'],
        ['Withdrawals', withdrawals],
      ]} />
    </div>
    <details className="performance-details">
      <summary>Calculation details</summary>
      <div className="performance-methods">
        <section><h4>Recorded period</h4><p>{first?.date ?? 'N/A'} — {last?.date ?? 'N/A'}</p>
          <dl className="performance-balances">
            <div><dt>Initial Balance</dt><dd>{currency(initial)}</dd></div>
            <div><dt>Final Balance</dt><dd>{currency(final)}</dd></div>
            <div><dt>Total Withdrawals</dt><dd>{currency(withdrawals)}</dd></div>
            <div><dt>Adjusted final value</dt><dd>{currency(adjusted)}</dd></div>
          </dl>
        </section>
        <section><h4>CAGR & maximum drawdown</h4><p>{cagrHelp}</p><p>{drawdownHelp}</p></section>
        <section><h4>Sharpe ratio methodology</h4><p>{sharpeHelp}</p><p>Risk-free rate: {percent(riskFree)} per year (from this run’s strategy settings).</p></section>
      </div>
    </details>
  </section>;
}
