import React, { useState } from 'react';
import { Box, Button, Paper, Tab, Tabs, Typography } from '@mui/material';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PerformanceChart from './PerformanceChart';
import PerformanceSummary from './PerformanceSummary';
import { chartColors } from './chartColors';
import ExpandableChart from './ExpandableChart';

// Fictional, fixed design-preview data. Never passed through the simulation
// adapter, used for performance statistics, or sent to the API.
export const SAMPLE_POINTS = [
  [100000, 100000, 20000], [102400, 101300, 21800], [101200, 100500, 19400],
  [104600, 102700, 23000], [103100, 102000, 21000], [107200, 104600, 25400],
  [108500, 105800, 24700], [106900, 104400, 21900], [110300, 107100, 27300],
  [112800, 109200, 28000], [111600, 108800, 26400], [115100, 111700, 31000],
].map(([Portfolio_Value, spy_value, Cash_Balance], index) => ({
  date: `2024-${String(index + 1).padStart(2, '0')}-01`, Portfolio_Value, spy_value, Cash_Balance,
  Margin_Ratio: [0.12, 0.15, 0.18, 0.14, 0.2, 0.16, 0.17, 0.23, 0.19, 0.15, 0.18, 0.13][index],
}));

// Explicit fictional display fixture. Not derived from monthly sample points,
// not processed by the backtest adapter, and never submitted to the API.
const SAMPLE_SUMMARY = {
  chartData: SAMPLE_POINTS,
  annualizedReturn: 0.157,
  maxDrawdown: -0.0315,
  sharpeRatio: 1.24,
  sharpeRiskFreeRate: 0.05,
  totalPremiumsReceived: 12345.67,
  totalDividendsReceived: 890.12,
  totalInterestPaid: 2345.67,
  totalAssignedCost: 1230,
  totalWithdrawAmount: 1000,
};
const SAMPLE_CONTEXT = { config: { initialBalance: 100000, riskFreeRate: 0.05 } };

function SampleTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="sample-tooltip">
      <strong>{label} · Sample only</strong>
      {payload.map(item => <div key={item.dataKey}>
        {item.name}: {item.dataKey === 'Margin_Ratio' ? `${(item.value * 100).toFixed(1)}%` : `$${item.value.toLocaleString()}`}
      </div>)}
    </div>
  );
}

export default function SampleChartPreview({ onClose, onTabChange }) {
  const [tab, setTab] = useState(0);
  const [direction, setDirection] = useState(1);
  return (
    <Paper className="sample-preview" component="section" aria-label="Sample chart preview" sx={{ mb: 3, overflow: 'hidden' }}>
      <div className="result-context">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6" component="h2">Sample chart preview · Testing only</Typography><Button onClick={onClose}>Close preview</Button>
        </Box>
        <Typography variant="body2" color="text.secondary">Fictional data for UI review only—not market prices, a backtest, or a forecast. Statistics are fixed examples, not calculated from the chart. Your simulation settings are unchanged.</Typography>
      </div>
      <Tabs value={tab} onChange={(_, value) => { onTabChange?.(value); setDirection(value > tab ? 1 : -1); setTab(value); }} aria-label="sample chart tabs" variant="scrollable" scrollButtons="auto">
        {['Performance', 'Margin', 'Cash'].map((label, index) => <Tab key={label} label={label} id={`sample-tab-${index}`} aria-controls={`sample-panel-${index}`} />)}
      </Tabs>
      <Box key={tab} id={`sample-panel-${tab}`} role="tabpanel" aria-labelledby={`sample-tab-${tab}`} className="result-panel" style={{ '--panel-offset': direction > 0 ? '24px' : '-24px' }} sx={{ p: { xs: 2, sm: 3 } }}>
        {tab === 0 ? <div className="performance-overview sample-overview">
          <PerformanceSummary data={SAMPLE_SUMMARY} resultContext={SAMPLE_CONTEXT} sample />
          <div className="portfolio-chart"><PerformanceChart data={SAMPLE_POINTS} sample tooltip={<SampleTooltip />} /></div>
        </div> : <ExpandableChart title={tab === 1 ? 'Sample margin chart' : 'Sample cash chart'} sample>
          <Typography variant="h6" gutterBottom>{tab === 1 ? 'Illustrative margin ratio' : 'Illustrative cash balance'}</Typography>
          <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><LineChart data={SAMPLE_POINTS} margin={{ top: 16, right: 20, left: 0, bottom: 12 }} accessibilityLayer>
            <CartesianGrid vertical={false} strokeDasharray="3 6" /><XAxis dataKey="date" interval="preserveStartEnd" minTickGap={48} height={42} axisLine={false} tickLine={false} tickMargin={12} tickFormatter={value => value.slice(0, 7)} />
            <YAxis width={72} axisLine={false} tickLine={false} domain={tab === 1 ? [0, 1] : ['auto', 'auto']} tickFormatter={value => tab === 1 ? `${Math.round(value * 100)}%` : `$${value / 1000}k`} />
            <Tooltip content={<SampleTooltip />} /><Line type="linear" dataKey={tab === 1 ? 'Margin_Ratio' : 'Cash_Balance'} name={tab === 1 ? 'Illustrative margin' : 'Illustrative cash'} stroke={tab === 1 ? chartColors.margin : chartColors.cash} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          </LineChart></ResponsiveContainer></div>
          <p className="chart-note">Fictional monthly values · January–December 2024</p>
        </ExpandableChart>}
      </Box>
    </Paper>
  );
}
