import React, { useId, useState } from 'react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { chartColors } from './chartColors';
import ExpandableChart from './ExpandableChart';

const currency = value => `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const shortCurrency = value => Math.abs(value) >= 1000 ? `$${(value / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })}k` : currency(value);

export default function PerformanceChart({ data, strategyId, tooltip, sample = false }) {
  const id = useId();
  const [showValues, setShowValues] = useState(false);
  const last = data[data.length - 1];
  if (!data.length) return <p>No recorded performance data available.</p>;

  return (
    <ExpandableChart title={sample ? 'Sample performance chart' : 'Portfolio performance chart'} sample={sample}><figure className="performance-figure" aria-labelledby={`${id}-caption`}>
      <figcaption id={`${id}-caption`} className="chart-heading">
        <div><div className="eyebrow">{sample ? 'Illustrative strategy' : 'Strategy value'}</div><div className="chart-value">{currency(last.Portfolio_Value)}</div></div>
        <div><div className="eyebrow">{sample ? 'Illustrative benchmark' : 'SPY buy & hold'}</div><div className="chart-value chart-value-secondary">{currency(last.spy_value)}</div></div>
      </figcaption>
      <div className="chart-key"><span><i className="line-key" style={{ borderColor: chartColors.strategy }} />{sample ? 'Illustrative strategy' : 'Strategy'}</span><span><i className="line-key dashed" style={{ borderColor: chartColors.benchmark }} />{sample ? 'Illustrative benchmark' : 'SPY buy & hold'}</span></div>
      <div className="chart-canvas">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 20, left: 0, bottom: 12 }} accessibilityLayer>
            <CartesianGrid vertical={false} strokeDasharray="3 6" />
            <XAxis dataKey="date" interval="preserveStartEnd" minTickGap={48} height={42} tickMargin={12} axisLine={false} tickLine={false} tickFormatter={value => String(value).slice(0, 7)} />
            <YAxis domain={['auto', 'auto']} width={72} tickMargin={10} axisLine={false} tickLine={false} tickFormatter={shortCurrency} />
            <Tooltip content={tooltip} cursor={{ stroke: '#777777', strokeDasharray: '3 3' }} />
            <Line type="linear" dataKey="Portfolio_Value" name={sample ? 'Illustrative strategy' : 'Strategy'} stroke={chartColors.strategy} strokeWidth={2.5} isAnimationActive={false} activeDot={{ r: 4, stroke: '#141414', strokeWidth: 2 }} dot={strategyId === 'SPY500_LEADER' ? props => {
              if (!props.payload?.isSwapTransaction) return null;
              const initial = props.payload.Trading_Log?.startsWith('INITIAL BUY:');
              return initial
                ? <circle cx={props.cx} cy={props.cy} r={5} fill="#141414" stroke="#f5f5f5" strokeWidth={2} />
                : <path d={`M${props.cx} ${props.cy - 6} l6 6 -6 6 -6 -6 Z`} fill="#dddddd" stroke="#141414" />;
            } : false} />
            <Line type="linear" dataKey="spy_value" name={sample ? 'Illustrative benchmark' : 'SPY Buy & Hold'} stroke={chartColors.benchmark} strokeWidth={2} strokeDasharray="6 5" isAnimationActive={false} activeDot={{ r: 4 }} dot={props => props.payload?.isBuySharesTransaction ? <path d={`M${props.cx} ${props.cy - 7} l6 11 h-12 Z`} fill="#dddddd" stroke="#141414" /> : null} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-note">{data[0].date} — {last.date} · {data.length.toLocaleString()} recorded points · USD</p>
      <details className="chart-data" open={showValues}>
        <summary onClick={event => { event.preventDefault(); setShowValues(value => !value); }}>View chart values</summary>
        {showValues && (
          <div className="chart-table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">{sample ? 'Illustrative strategy' : 'Strategy'}</th>
                  <th scope="col">{sample ? 'Illustrative benchmark' : 'SPY buy & hold'}</th>
                </tr>
              </thead>
              <tbody>
                {data.map(row => (
                  <tr key={row.date}>
                    <th scope="row">{row.date}</th>
                    <td>{Number(row.Portfolio_Value).toLocaleString(undefined, { style: 'currency', currency: 'USD' })}</td>
                    <td>{Number(row.spy_value).toLocaleString(undefined, { style: 'currency', currency: 'USD' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>
    </figure></ExpandableChart>
  );
}
