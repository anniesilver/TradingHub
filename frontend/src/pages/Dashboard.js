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
import { getSimulationResults, getSimulations, runSimulation } from '../services/simulationService';

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
}));

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    strategy: null,
    results: null,
  });
  const [config, setConfig] = useState({
    symbol: 'SPY',
    optionType: 'call',
    buyTime: '9:35',
    sellTime: '15:45',
    stopLoss: 0.50,
    takeProfit: 1.00,
    dteMin: 1,
    dteMax: 5,
    deltaMin: 0.40,
    deltaMax: 0.60,
    initialBalance: 10000.0,
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  });

  const handleConfigChange = (event) => {
    event.preventDefault(); // Prevent form submission
    const { name, value } = event.target;
    setConfig(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRunSimulation = async (event) => {
    if (event) {
      event.preventDefault(); // Prevent form submission
    }
    try {
      setLoading(true);
      setError(null);
      console.log("Running simulation with config:", config);
      
      const results = await runSimulation({
        ...config,
        strategyId: data.strategy?.id || 'SPY_POWER_CASHFLOW'
      });
      console.log("Received simulation results:", results);
      
      setData(prev => ({
        ...prev,
        results
      }));
    } catch (err) {
      console.error('Error in handleRunSimulation:', err);
      setError(err.response?.data?.error || err.message || 'Failed to run simulation');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log("Fetching initial data...");
        
        // Get the default strategy
        const defaultStrategy = {
          id: 'SPY_POWER_CASHFLOW',
          name: 'SPY Power Cashflow'
        };
        
        console.log("Using default strategy:", defaultStrategy);
        
        // Run initial simulation with default config
        const results = await runSimulation({
          ...config,
          strategyId: defaultStrategy.id
        });
        
        if (!results) {
          throw new Error('No simulation results received');
        }
        
        console.log("Received simulation results:", results);
        
        setData({
          strategy: defaultStrategy,
          results: results
        });
      } catch (err) {
        console.error('Error in fetchInitialData:', err);
        const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch data';
        console.error('Detailed error:', errorMessage);
        setError(errorMessage);
        // Set empty results to prevent infinite loading
        setData({
          strategy: null,
          results: {}
        });
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, []); // Only run once on component mount

  const prepareChartData = () => {
    if (!data.results) return [];
    return Object.entries(data.results).map(([date, dayData]) => ({
      date,
      balance: dayData.balance,
      profitLoss: dayData.profit_loss,
      trades: dayData.trades_count,
    }));
  };

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

  const chartData = prepareChartData();
  const lastData = chartData[chartData.length - 1] || {};
  const firstData = chartData[0] || {};
  const totalReturn = lastData.balance - firstData.balance;
  const percentReturn = ((totalReturn / firstData.balance) * 100).toFixed(2);

  return (
    <Root>
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          Trading Strategy Performance
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          Strategy: {data.strategy?.name || 'Unknown'}
        </Typography>
      </Box>

      {/* Configuration Form */}
      <form onSubmit={handleRunSimulation}>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12}>
            <StyledCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Strategy Configuration
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Symbol"
                      name="symbol"
                      value={config.symbol}
                      onChange={handleConfigChange}
                    />
                  </Grid>
                  <Grid item xs={12} md={3}>
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
                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Initial Balance"
                      name="initialBalance"
                      value={config.initialBalance}
                      onChange={handleConfigChange}
                    />
                  </Grid>
                  <Grid item xs={12} md={3}>
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
                  <Grid item xs={12} md={3}>
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
                </Grid>
                <Box mt={2} display="flex" justifyContent="flex-end">
                  <Button
                    variant="contained"
                    color="primary"
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? 'Running...' : 'Run Simulation'}
                  </Button>
                </Box>
              </CardContent>
            </StyledCard>
          </Grid>
        </Grid>
      </form>

      {/* Results Section */}
      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid item xs={12} md={4}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Balance
              </Typography>
              <Typography variant="h4">
                ${lastData.balance?.toFixed(2) || '0.00'}
              </Typography>
            </CardContent>
          </StyledCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Total Return
              </Typography>
              <Typography variant="h4" color={totalReturn >= 0 ? 'success.main' : 'error.main'}>
                ${totalReturn?.toFixed(2) || '0.00'} ({percentReturn}%)
              </Typography>
            </CardContent>
          </StyledCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Total Trades
              </Typography>
              <Typography variant="h4">
                {chartData.reduce((sum, day) => sum + day.trades, 0)}
              </Typography>
            </CardContent>
          </StyledCard>
        </Grid>

        {/* Balance Chart */}
        <Grid item xs={12}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Account Balance History
              </Typography>
              <Box height={400}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="balance"
                      stroke="#2196f3"
                      name="Balance"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </StyledCard>
        </Grid>

        {/* Profit/Loss Chart */}
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Daily Profit/Loss
              </Typography>
              <Box height={300}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="profitLoss"
                      stroke="#4caf50"
                      name="Profit/Loss"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </StyledCard>
        </Grid>

        {/* Trades Chart */}
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Daily Trading Activity
              </Typography>
              <Box height={300}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="trades"
                      stroke="#ff9800"
                      name="Number of Trades"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </StyledCard>
        </Grid>
      </Grid>
    </Root>
  );
}

export default Dashboard; 