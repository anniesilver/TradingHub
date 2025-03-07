import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  Box,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { runSimulation } from '../services/simulationService';

const Root = styled('div')(({ theme }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
}));

const LoadingContainer = styled('div')({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '400px',
});

const ErrorContainer = styled('div')(({ theme }) => ({
  margin: theme.spacing(2),
}));

const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  margin: theme.spacing(1),
}));

const LogContainer = styled(Box)(({ theme }) => ({
  maxHeight: '300px',
  overflowY: 'auto',
  padding: theme.spacing(2),
  backgroundColor: theme.palette.grey[100],
  borderRadius: theme.shape.borderRadius,
}));

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    chartData: [],
    marginData: [],
    tradingLogs: []
  });
  const [config, setConfig] = useState({
    symbol: 'SPY',
    optionType: 'call',
    initialBalance: 10000,
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  });

  const handleConfigChange = (event) => {
    const { name, value } = event.target;
    let processedValue = value;
    
    if (['initialBalance'].includes(name)) {
      processedValue = parseFloat(value) || 0;
    }
    
    setConfig(prev => ({
      ...prev,
      [name]: processedValue
    }));
  };

  const processSimulationData = (results) => {
    try {
      // Parse the results if it's a string
      const parsedData = typeof results === 'string' ? JSON.parse(results) : results;
      
      // Convert the data into arrays for charts
      const processedData = Object.entries(parsedData).map(([date, values]) => {
        const tradingLog = values.Trading_Log || '';
        const hasBuy = tradingLog.toLowerCase().includes('buy');
        const hasSell = tradingLog.toLowerCase().includes('sell');
        
        return {
          date,
          Portfolio_Value: Number(values.Portfolio_Value) || 0,
          spy_value: Number(values.spy_value) || 0,
          Margin_Ratio: Number(values.Margin_Ratio) || 0,
          hasBuy,
          hasSell
        };
      }).sort((a, b) => new Date(a.date) - new Date(b.date));

      // Extract trading logs where actual trading happened
      const tradingLogs = Object.entries(parsedData)
        .filter(([_, values]) => values.Trading_Log && values.Trading_Log.includes('Executed'))
        .map(([date, values]) => ({
          date,
          log: values.Trading_Log
        }))
        .sort((a, b) => new Date(b.date) - new Date(a.date));

      setData({
        chartData: processedData,
        marginData: processedData,
        tradingLogs
      });
    } catch (error) {
      console.error('Error processing simulation data:', error);
      setError('Failed to process simulation data');
    }
  };

  const handleRunSimulation = async (event) => {
    if (event) {
      event.preventDefault();
    }
    try {
      setLoading(true);
      setError(null);
      
      const results = await runSimulation({
        ...config,
        strategyId: 'SPY_POWER_CASHFLOW'
      });
      
      processSimulationData(results);
    } catch (err) {
      console.error('Error in handleRunSimulation:', err);
      setError(err.response?.data?.error || err.message || 'Failed to run simulation');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleRunSimulation();
  }, []);

  if (loading) {
    return (
      <LoadingContainer>
        <CircularProgress />
      </LoadingContainer>
    );
  }

  if (error) {
    return (
      <ErrorContainer>
        <Alert severity="error">{error}</Alert>
      </ErrorContainer>
    );
  }

  return (
    <Root>
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          Trading Strategy Performance
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          Strategy: SPY Power Cashflow
        </Typography>
      </Box>

      {/* Configuration Form */}
      <Box component="form" mb={4}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Symbol"
              name="symbol"
              value={config.symbol}
              onChange={handleConfigChange}
              disabled
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Option Type</InputLabel>
              <Select
                name="optionType"
                value={config.optionType}
                onChange={handleConfigChange}
                label="Option Type"
              >
                <MenuItem value="call">Call</MenuItem>
                <MenuItem value="put">Put</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              type="number"
              label="Initial Balance"
              name="initialBalance"
              value={config.initialBalance}
              onChange={handleConfigChange}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              type="date"
              label="Start Date"
              name="startDate"
              value={config.startDate}
              onChange={handleConfigChange}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              type="date"
              label="End Date"
              name="endDate"
              value={config.endDate}
              onChange={handleConfigChange}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleRunSimulation}
            >
              RUN SIMULATION
            </Button>
          </Grid>
        </Grid>
      </Box>

      {/* Performance Charts */}
      <Grid container spacing={2}>
        {/* Strategy vs SPY Performance Chart */}
        <Grid item xs={12}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Strategy vs SPY Performance
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart
                  data={data.chartData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date"
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                  />
                  <Tooltip 
                    formatter={(value) => [`$${value.toLocaleString()}`, value === data.chartData[0]?.Portfolio_Value ? 'Strategy' : 'SPY']}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="Portfolio_Value" 
                    name="Strategy" 
                    stroke="#8884d8" 
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="spy_value" 
                    name="SPY Buy & Hold" 
                    stroke="#82ca9d" 
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </StyledCard>
        </Grid>

        {/* Margin Ratio Chart */}
        <Grid item xs={12}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Margin Ratio
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={data.marginData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date"
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    domain={[0, 1]}
                    tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                  />
                  <Tooltip 
                    formatter={(value) => [`${(value * 100).toFixed(2)}%`, 'Margin Ratio']}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="Margin_Ratio" 
                    name="Margin Ratio" 
                    stroke="#ff7300" 
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </StyledCard>
        </Grid>

        {/* Trading Logs */}
        <Grid item xs={12}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Trading Activity Log
              </Typography>
              <LogContainer>
                {data.tradingLogs.map(({ date, log }) => (
                  <Box key={date} mb={1}>
                    <Typography variant="subtitle2" color="primary">
                      {date}
                    </Typography>
                    <Typography variant="body2">
                      {log}
                    </Typography>
                  </Box>
                ))}
                {data.tradingLogs.length === 0 && (
                  <Typography variant="body2" color="textSecondary">
                    No trading activity in this period
                  </Typography>
                )}
              </LogContainer>
            </CardContent>
          </StyledCard>
        </Grid>
      </Grid>
    </Root>
  );
}

export default Dashboard; 