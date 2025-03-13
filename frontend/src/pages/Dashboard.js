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

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  
  return (
    <div style={{ 
      backgroundColor: 'rgba(255, 255, 255, 0.95)', 
      padding: '8px 12px', 
      border: '1px solid #ccc',
      borderRadius: '4px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{label}</p>
      {payload.map((entry, index) => {
        // Determine the label based on the dataKey
        const seriesName = entry.dataKey === "Portfolio_Value" ? "Strategy" : 
                         entry.dataKey === "spy_value" ? "SPY Buy & Hold" :
                         entry.dataKey === "Margin_Ratio" ? "Margin Ratio" :
                         entry.dataKey === "Cash_Balance" ? "Cash Balance" :
                         entry.dataKey === "Premiums_Received" ? "Premium Received" :
                         entry.name;
                         
        return (
          <p key={index} style={{ margin: '5px 0', color: entry.color }}>
            {seriesName}: ${Number(entry.value).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            })}
          </p>
        );
      })}
    </div>
  );
};

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    chartData: [],
    marginData: [],
    premiumData: [],
    tradingLogs: [],
    firstMonthRawData: {}
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
      
      // Extract raw data for February 2017 (the first month)
      const feb2017Data = {};
      Object.entries(parsedData)
        .filter(([date, _]) => date.startsWith('2017-02'))
        .forEach(([date, values]) => {
          feb2017Data[date] = {
            Trading_Log: values.Trading_Log || '',
            Portfolio_Value: values.Portfolio_Value,
            Cash_Balance: values.Cash_Balance,
            Margin_Ratio: values.Margin_Ratio,
            Premiums_Received: values.Premiums_Received || 0,
            spy_value: values.spy_value
          };
        });
      
      console.log('February 2017 data:', feb2017Data);
      
      // Specifically log Feb 17 and Feb 28 trading logs
      console.log('2017-02-17 trading log:', feb2017Data['2017-02-17'] ? feb2017Data['2017-02-17'].Trading_Log : 'Not found');
      console.log('2017-02-28 trading log:', feb2017Data['2017-02-28'] ? feb2017Data['2017-02-28'].Trading_Log : 'Not found');
      
      // Extract the first month data with non-empty Trading_Log
      const firstMonthWithTrading = extractFirstMonthWithTrading(parsedData);
      console.log('First month data with non-empty logs:', firstMonthWithTrading);
      
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
        .filter(([date, values]) => {
          // First, check if there's any log content
          if (!values.Trading_Log || values.Trading_Log.trim() === '') {
            return false;
          }
          
          // Log data from 2017-02-17 and 2017-02-28 should be included
          // Those are the first and last days of February 2017
          if (date === '2017-02-17' || date === '2017-02-28') {
            console.log(`Including special trading log for date ${date}:`, values.Trading_Log);
            return true;
          }
          
          const log = values.Trading_Log.toLowerCase();
          
          // Less restrictive filter that allows different phrase patterns
          const isActualTradeActivity = (
            // Options activity keywords - more flexible patterns
            log.includes('sell') || 
            log.includes('buy') ||
            log.includes('write') ||
            log.includes('close') ||
            log.includes('call') || 
            log.includes('put') ||
            log.includes('option') ||
            log.includes('contract') ||
            // Share activity keywords
            log.includes('share') ||
            // Premium/credit received indicators
            log.includes('premium') ||
            log.includes('credit') ||
            // Explicit execution indicators
            log.includes('executed') ||
            log.includes('transaction') ||
            // Look for dollar amounts which often indicate trades
            log.includes('$') ||
            // Look for dates, which often appear in trade logs with expiration dates
            log.match(/\d{4}-\d{2}/) ||
            log.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}/i)
          );
          
          return isActualTradeActivity;
        })
        .map(([date, values]) => {
          const log = values.Trading_Log;
          
          // Parse the trading log to determine trade type and extract key information
          let tradeType = "UNKNOWN";
          let expiryDate = null;
          let action = null;
          let contracts = null;
          let premium = null;
          let tradeDetails = null;
          
          // Identify trade type and action
          if (log.toLowerCase().includes('sell') || log.toLowerCase().includes('write')) {
            if (log.toLowerCase().includes('call') || log.toLowerCase().includes('put')) {
              action = "SELL/WRITE";
              tradeType = "OPTION_WRITE";
            } else if (log.toLowerCase().includes('share')) {
              action = "SELL";
              tradeType = "SHARE_SELL";
            }
          } else if (log.toLowerCase().includes('buy') || log.toLowerCase().includes('close')) {
            if (log.toLowerCase().includes('call') || log.toLowerCase().includes('put')) {
              action = "BUY/CLOSE";
              tradeType = "OPTION_CLOSE";
            } else if (log.toLowerCase().includes('share')) {
              action = "BUY";
              tradeType = "SHARE_BUY";
              // Special case for 2018 dip buying
              if (date.startsWith('2018-02')) {
                tradeDetails = "Market Dip Purchase";
              }
            }
          }
          
          // Extract option type (call/put)
          let optionType = null;
          if (log.toLowerCase().includes('call')) {
            optionType = 'CALL';
          } else if (log.toLowerCase().includes('put')) {
            optionType = 'PUT';
          }
          
          // Extract expiry date with more patterns
          // Look for YYYY-MM patterns (like 2023-01)
          const yearMonthPattern = /\b(20\d{2})[/-](\d{2})\b/;
          // Look for month names with year (like Jan 2023)
          const monthNamePattern = /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b/i;
          
          let expiryMatch = log.match(yearMonthPattern);
          if (expiryMatch) {
            expiryDate = `${expiryMatch[1]}-${expiryMatch[2]}`;
          } else {
            expiryMatch = log.match(monthNamePattern);
            if (expiryMatch) {
              // Convert month name to number
              const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
              const monthIndex = monthNames.findIndex(m => expiryMatch[1].toLowerCase().startsWith(m)) + 1;
              expiryDate = `${expiryMatch[2]}-${monthIndex.toString().padStart(2, '0')}`;
            }
          }
          
          // Extract number of contracts or shares with improved patterns
          const quantityPatterns = [
            /\b(\d+)\s*(?:call|put|contract|option)/i,    // For options
            /\b(\d+)\s*(?:share)/i,                       // For shares
            /(?:sell|buy|write|close)\s+(\d+)/i           // Generic sell/buy count
          ];
          
          for (const pattern of quantityPatterns) {
            const match = log.match(pattern);
            if (match) {
              contracts = match[1];
              break;
            }
          }
          
          // Extract premium amount with improved patterns
          const premiumPatterns = [
            /premium:?\s*\$?(\d+(?:\.\d+)?)/i,
            /credit:?\s*\$?(\d+(?:\.\d+)?)/i,
            /\$(\d+(?:\.\d+)?)\s*(?:premium|credit)/i,
            /(?:receive|collect|for)\s*\$(\d+(?:\.\d+)?)/i
          ];
          
          for (const pattern of premiumPatterns) {
            const match = log.match(pattern);
            if (match) {
              premium = match[1];
              break;
            }
          }
          
          // Determine if date is likely first or last business day of month
          const logDate = new Date(date);
          const dayOfMonth = logDate.getDate();
          const lastDayOfMonth = new Date(logDate.getFullYear(), logDate.getMonth() + 1, 0).getDate();
          
          let datePosition = "MID_MONTH";
          let dateDescription = "";
          
          if (dayOfMonth <= 3) {
            datePosition = "FIRST_DAYS";
            dateDescription = "First trading days of month";
          } else if (dayOfMonth >= lastDayOfMonth - 2) {
            datePosition = "LAST_DAYS";
            dateDescription = "Last trading days of month";
          } else if (date.startsWith('2018-02')) {
            // Special case for 2018-02 market dip
            dateDescription = "Market dip opportunity";
          }
          
          return {
            date,
            log,
            tradeType,
            optionType,
            expiryDate,
            action,
            contracts,
            premium,
            datePosition,
            dateDescription,
            tradeDetails
          };
        })
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
        tradingLogs,
        firstMonthRawData: feb2017Data
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

  // Helper function to extract first month with trading activity
  const extractFirstMonthWithTrading = (data) => {
    // Convert data to array of [date, values] pairs and sort by date
    const sortedEntries = Object.entries(data)
      .sort((a, b) => new Date(a[0]) - new Date(b[0]));
    
    // Find entries with non-empty Trading_Log
    const entriesWithLogs = sortedEntries.filter(
      ([_, values]) => values.Trading_Log && values.Trading_Log.trim() !== ''
    );
    
    if (entriesWithLogs.length === 0) {
      return [];
    }
    
    // Get the first entry with a log
    const firstEntry = entriesWithLogs[0];
    const firstDate = new Date(firstEntry[0]);
    const firstMonth = firstDate.getMonth();
    const firstYear = firstDate.getFullYear();
    
    // Find all entries from the same month as the first entry
    const firstMonthEntries = sortedEntries.filter(([date, _]) => {
      const entryDate = new Date(date);
      return entryDate.getMonth() === firstMonth && 
             entryDate.getFullYear() === firstYear;
    });
    
    return firstMonthEntries;
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
              <ResponsiveContainer width="100%" height={600}>
                <LineChart
                  data={data.chartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
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
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    verticalAlign="top"
                    height={36}
                    wrapperStyle={{paddingBottom: '10px'}}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="Portfolio_Value" 
                    name="Strategy" 
                    stroke="#82ca9d" 
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="spy_value" 
                    name="SPY Buy & Hold" 
                    stroke="#8884d8" 
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
              <ResponsiveContainer width="100%" height={600}>
                <LineChart
                  data={data.marginData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
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
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    verticalAlign="top"
                    height={36}
                    wrapperStyle={{paddingBottom: '10px'}}
                  />
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
              <ResponsiveContainer width="100%" height={600}>
                <LineChart
                  data={data.chartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
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
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    verticalAlign="top"
                    height={36}
                    wrapperStyle={{paddingBottom: '10px'}}
                  />
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
                <ResponsiveContainer width="100%" height={600}>
                  <BarChart
                    data={data.premiumData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
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
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                      verticalAlign="top"
                      height={36}
                      wrapperStyle={{paddingBottom: '10px'}}
                    />
                    <Bar 
                      dataKey="Premiums_Received" 
                      name="Premium Received" 
                      fill="#8884d8"
                      barSize={30} 
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Box mt={2} textAlign="center" height={600} display="flex" alignItems="center" justifyContent="center">
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
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Options are typically written on the first business day of each month and closed on the last business day.
                {data.tradingLogs.some(log => log.date.startsWith('2018-02') && log.tradeType === "SHARE_BUY") && 
                  " Market dip buying occurred in February 2018."}
              </Typography>
              <LogContainer>
                {data.tradingLogs.map(({ date, log, tradeType, optionType, expiryDate, action, contracts, premium, datePosition, dateDescription, tradeDetails }) => (
                  <Box 
                    key={date} 
                    mb={2} 
                    p={1.5} 
                    border={1} 
                    borderRadius={1} 
                    borderColor={
                      tradeType === "OPTION_WRITE" ? "success.light" : 
                      tradeType === "OPTION_CLOSE" ? "error.light" :
                      tradeType === "SHARE_BUY" ? "info.light" :
                      tradeType === "SHARE_SELL" ? "warning.light" :
                      "grey.300"
                    }
                    sx={{
                      background: datePosition === "FIRST_DAYS" ? "rgba(232, 245, 233, 0.2)" :
                                datePosition === "LAST_DAYS" ? "rgba(255, 235, 238, 0.2)" :
                                date.startsWith('2018-02') ? "rgba(227, 242, 253, 0.2)" :
                                "transparent"
                    }}
                  >
                    <Typography variant="subtitle2" color="primary" fontWeight="bold">
                      Transaction Date: {date} {dateDescription && `(${dateDescription})`}
                    </Typography>
                    
                    {expiryDate && (
                      <Typography variant="body2" color="error" sx={{ mt: 0.5 }}>
                        Option Expiry: {expiryDate} {optionType && `(${optionType})`}
                      </Typography>
                    )}
                    
                    {action && (
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        <strong>Action:</strong> {action}
                        {tradeType === "OPTION_WRITE" && datePosition === "FIRST_DAYS" && " (Monthly option writing)"}
                        {tradeType === "OPTION_CLOSE" && datePosition === "LAST_DAYS" && " (Monthly option closing)"}
                        {tradeDetails && ` - ${tradeDetails}`}
                      </Typography>
                    )}
                    
                    {contracts && (
                      <Typography variant="body2">
                        <strong>{tradeType.includes("SHARE") ? "Shares:" : "Contracts:"}</strong> {contracts}
                      </Typography>
                    )}
                    
                    {premium && (
                      <Typography variant="body2">
                        <strong>{tradeType === "OPTION_WRITE" ? "Premium Received:" : "Cost:"}</strong> ${premium}
                      </Typography>
                    )}
                    
                    <Typography variant="body2" color="textSecondary" sx={{ mt: 1, fontSize: '0.875rem' }}>
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