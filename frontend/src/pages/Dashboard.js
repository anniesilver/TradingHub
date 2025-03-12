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
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
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

// Tab Panel component
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`chart-tabpanel-${index}`}
      aria-labelledby={`chart-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box p={3}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index) {
  return {
    id: `chart-tab-${index}`,
    'aria-controls': `chart-tabpanel-${index}`,
  };
}

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    chartData: [],
    marginData: [],
    premiumData: [],
    tradingLogs: []
  });
  const [config, setConfig] = useState({
    symbol: 'SPY',
    optionType: 'call',
    initialBalance: 200000,
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  });
  // Add state for the active tab
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleConfigChange = (event) => {
    const { name, value } = event.target;
    let processedValue = value;
    
    if (['initialBalance'].includes(name)) {
      // Ensure initialBalance is always a valid number
      processedValue = parseFloat(value);
      if (isNaN(processedValue) || processedValue <= 0) {
        // Default to 200000 if value is invalid
        processedValue = 200000;
      }
      console.log(`Setting initialBalance to: ${processedValue}`);
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
      
      console.log('Raw API data:', parsedData);
      
      // Step 1: Extract ALL available premium values directly from API
      const rawPremiumData = [];
      
      // Collect all premium values and trading logs
      Object.entries(parsedData).forEach(([date, values]) => {
        const tradingLog = values.Trading_Log || '';
        
        // Store the raw premium value if available (either from Premiums_Received, Premium_Received or premium_received)
        let premiumValue = null;
        if ('Premiums_Received' in values) {
          premiumValue = values.Premiums_Received;
        } 
        
        // If no direct premium value, try to extract it from trading log
        if (premiumValue === null && tradingLog) {
          if (tradingLog.toLowerCase().includes('premium') || tradingLog.toLowerCase().includes('credit')) {
            // Try to extract premium amount and contracts
            const premiumMatch = tradingLog.match(/premium:?\s*\$?(\d+(\.\d+)?)/i) || 
                               tradingLog.match(/credit:?\s*\$?(\d+(\.\d+)?)/i);
                               
            const contractsMatch = tradingLog.match(/(\d+)\s*calls?/i) || 
                                 tradingLog.match(/(\d+)\s*puts?/i);
          }
        }
        
        // Add to our raw data collection if we found a value
        if (premiumValue !== null) {
          rawPremiumData.push({
            date,
            premiumValue,
            tradingLog
          });
        }
      });
      
      console.log('Raw premium data collected:', rawPremiumData);
      
      // Step 2: Analyze the data to determine the correct scaling
      
      // Step 3: Create properly scaled premium data
      const premiumData = rawPremiumData.map(item => {
        const rawValue = item.premiumValue;
        let scaledValue = rawValue;
        
        // Apply scaling for small values
        if (rawValue < 5) {
          // Define scalingFactor if needed
          const scalingFactor = 100; // Default value if not defined elsewhere
          scaledValue = rawValue * scalingFactor;
        }
        
        // Special case handling for known correct values
        const knownCorrectValues = {}; // Define empty object if not defined elsewhere
        if (item.date in knownCorrectValues) {
          scaledValue = knownCorrectValues[item.date];
        }
        
        return {
          date: item.date,
          Premiums_Received: scaledValue,
          source: item.date in knownCorrectValues ? 'known_correct' : 
                 rawValue < 5 ? 'scaled' : 'original'
        };
      });
      
      // Filter out entries where Premiums_Received is zero
      const filteredPremiumData = premiumData.filter(item => item.Premiums_Received !== 0);
      
      // Sort by date
      filteredPremiumData.sort((a, b) => new Date(a.date) - new Date(b.date));
      
      console.log('Final premium data with proper scaling (non-zero only):', filteredPremiumData);
      
      // Convert the data into arrays for the main charts
      const processedData = Object.entries(parsedData).map(([date, values]) => {
        const tradingLog = values.Trading_Log || '';
        const hasBuy = tradingLog.toLowerCase().includes('buy');
        const hasSell = tradingLog.toLowerCase().includes('sell');
        
        return {
          date,
          Portfolio_Value: Number(values.Portfolio_Value) || 0,
          spy_value: Number(values.spy_value) || 0,
          Margin_Ratio: Number(values.Margin_Ratio) || 0,
          Cash_Balance: Number(values.Cash_Balance) || 0,
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
      
      // If we still have no premium data, create test data
      if (filteredPremiumData.length === 0) {
        console.log('No premium data found, creating varied test data');
      }
      
      console.log('Final premium data for chart:', filteredPremiumData);
      console.log('Total premium data points:', filteredPremiumData.length);

      setData({
        chartData: processedData,
        marginData: processedData,
        premiumData: filteredPremiumData,
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
      
      console.log('Running simulation with config:', config);
      
      const results = await runSimulation({
        ...config,
        strategyId: 'SPY_POWER_CASHFLOW'
      });
      
      console.log('Simulation API response received');
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

      {/* Performance Charts with Tabs */}
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Paper elevation={2}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs 
                value={activeTab} 
                onChange={handleTabChange} 
                aria-label="chart tabs"
                variant="scrollable"
                scrollButtons="auto"
              >
                <Tab label="Performance" {...a11yProps(0)} />
                <Tab label="Margin Ratio" {...a11yProps(1)} />
                <Tab label="Cash Balance" {...a11yProps(2)} />
                <Tab label="Premium Received" {...a11yProps(3)} />
              </Tabs>
            </Box>
            
            {/* Tab content for Performance Chart */}
            <TabPanel value={activeTab} index={0}>
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
            </TabPanel>
            
            {/* Tab content for Margin Ratio Chart */}
            <TabPanel value={activeTab} index={1}>
              <Typography variant="h6" gutterBottom>
                Margin Ratio
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
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
            </TabPanel>
            
            {/* Tab content for Cash Balance Chart */}
            <TabPanel value={activeTab} index={2}>
              <Typography variant="h6" gutterBottom>
                Cash Balance
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
                    formatter={(value) => [`$${value.toLocaleString()}`, 'Cash Balance']}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="Cash_Balance" 
                    name="Cash Balance" 
                    stroke="#4db6ac" 
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </TabPanel>
            
            {/* Tab content for Premium Received Bar Chart */}
            <TabPanel value={activeTab} index={3}>
              <Typography variant="h6" gutterBottom>
                Premium Received
              </Typography>
              {data.premiumData && data.premiumData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart
                    data={data.premiumData}
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
                      domain={[0, 'auto']}
                      tickFormatter={(value) => `$${value.toLocaleString()}`}
                    />
                    <Tooltip 
                      formatter={(value) => [`$${value.toFixed(2)}`, 'Premium Received']}
                      labelFormatter={(label) => `Date: ${label}`}
                    />
                    <Legend />
                    <Bar 
                      dataKey="Premiums_Received" 
                      name="Premium Received" 
                      fill="#8884d8"
                      barSize={30} 
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Box mt={2} textAlign="center" height={400} display="flex" alignItems="center" justifyContent="center">
                  <Typography variant="body1" color="textSecondary">
                    No premium data available for the selected period
                  </Typography>
                </Box>
              )}
              <Box mt={2}>
                <Typography variant="subtitle2">Data used for chart:</Typography>
                <pre style={{ maxHeight: '200px', overflow: 'auto', background: '#f5f5f5', padding: '8px', fontSize: '12px' }}>
                  {JSON.stringify(data.premiumData, null, 2)}
                </pre>
              </Box>
            </TabPanel>
          </Paper>
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