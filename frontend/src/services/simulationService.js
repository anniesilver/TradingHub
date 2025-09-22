import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8080/api';

// Configure axios defaults
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Add request interceptor for debugging
axios.interceptors.request.use(request => {
  console.log('Starting Request:', {
    url: request.url,
    method: request.method,
    data: request.data
  });
  return request;
});

// Add response interceptor for debugging
axios.interceptors.response.use(
  response => {
    console.log('Response:', {
      status: response.status,
      data: response.data
    });
    return response;
  },
  error => {
    console.error('Response Error:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status
    });
    return Promise.reject(error);
  }
);

/**
 * Fetches available trading strategies from the backend
 * @param {number} limit - Maximum number of strategies to return
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Array>} List of available strategies
 */
export const getSimulations = async (limit = 10, offset = 0) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/strategies`);
    console.log('Strategies response:', response.data);
    return response.data.strategies;
  } catch (error) {
    console.error('Error fetching simulations:', error.response || error);
    throw error;
  }
};

/**
 * Runs a trading strategy simulation with custom parameters
 * @param {Object} config - Simulation configuration
 * @param {string} config.strategyId - Strategy type (default: 'SPY_POWER_CASHFLOW')
 * @param {string} config.symbol - Trading symbol (default: 'SPY')
 * @param {string} config.startDate - Start date for simulation
 * @param {string} config.endDate - End date for simulation
 * @param {number} config.initialBalance - Initial balance (default: 10000.0)
 * @param {number} config.callCostBuffer - Buffer for call cost (default: 0.05)
 * @param {number} config.contractSize - Option contract size (default: 100)
 * @param {number} config.coveredCallRatio - Covered call ratio (default: 1.0)
 * @param {number} config.dipBuyPercent - Dip buy percentage (default: 0.4)
 * @param {number} config.dipTrigger - Dip trigger threshold (default: 0.92)
 * @param {number} config.initialPositionPercent - Initial position percentage (default: 0.6)
 * @param {number} config.marginInterestRate - Margin interest rate (default: 0.06)
 * @param {number} config.maxMarginRatio - Maximum leverage ratio (position_value/account_value) (default: 2)
 * @param {number} config.maxPositionSize - Maximum position size (default: 10000)
 * @param {number} config.minCommission - Minimum commission (default: 1.0)
 * @param {number} config.minStrikeDistance - Minimum strike distance (default: 0.015)
 * @param {number} config.minTradeSize - Minimum trade size (default: 1000)
 * @param {number} config.monthlyWithdrawal - Monthly withdrawal amount (default: 5000.0)
 * @param {number} config.optionCommission - Option commission (default: 0.65)
 * @param {number} config.riskFreeRate - Risk-free rate (default: 0.05)
 * @param {number} config.stockCommission - Stock commission (default: 0.01)
 * @param {number} config.volatilityScalingFactor - Volatility scaling factor (default: 0.15)
 * @returns {Promise<Object>} Simulation results
 */
export const runSimulation = async (config) => {
  try {
    if (!config) {
      throw new Error('No configuration provided');
    }

    const payload = {
      strategy_type: config.strategyId || 'SPY_POWER_CASHFLOW',
      config: {
        SYMBOL: config.symbol || 'SPY',       
        OPTION_TYPE: config.optionType || 'call',
        // Add all the new config parameters
        CALL_COST_BUFFER: config.callCostBuffer !== undefined ? config.callCostBuffer : 0.05,
        CONTRACT_SIZE: config.contractSize !== undefined ? config.contractSize : 100,
        COVERED_CALL_RATIO: config.coveredCallRatio !== undefined ? config.coveredCallRatio : 1.0,
        DIP_BUY_PERCENT: config.dipBuyPercent !== undefined ? config.dipBuyPercent : 0.4,
        DIP_TRIGGER: config.dipTrigger !== undefined ? config.dipTrigger : 0.92,
        INITIAL_POSITION_PERCENT: config.initialPositionPercent !== undefined ? config.initialPositionPercent : 0.6,
        MARGIN_INTEREST_RATE: config.marginInterestRate !== undefined ? config.marginInterestRate : 0.06,
        MAX_MARGIN_RATIO: config.maxMarginRatio !== undefined ? config.maxMarginRatio : 2,
        MAX_POSITION_SIZE: config.maxPositionSize !== undefined ? config.maxPositionSize : 10000,
        MIN_COMMISSION: config.minCommission !== undefined ? config.minCommission : 1.0,
        MIN_STRIKE_DISTANCE: config.minStrikeDistance !== undefined ? config.minStrikeDistance : 0.015,
        MIN_TRADE_SIZE: config.minTradeSize !== undefined ? config.minTradeSize : 1000,
        MONTHLY_WITHDRAWAL: config.monthlyWithdrawal !== undefined ? config.monthlyWithdrawal : 5000.0,
        OPTION_COMMISSION: config.optionCommission !== undefined ? config.optionCommission : 0.65,
        RISK_FREE_RATE: config.riskFreeRate !== undefined ? config.riskFreeRate : 0.05,
        STOCK_COMMISSION: config.stockCommission !== undefined ? config.stockCommission : 0.01,
        VOLATILITY_SCALING_FACTOR: config.volatilityScalingFactor !== undefined ? config.volatilityScalingFactor : 0.15,
      },
      // Ensure we're passing the correct date formats to the backend
      start_date: config.startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end_date: config.endDate || new Date().toISOString().split('T')[0]
    };
    
    console.log(`Using date range: ${payload.start_date} to ${payload.end_date}`);

    // Add initial balance with consistent naming
    if (config.initialBalance !== undefined && config.initialBalance !== null) {
      // Parse to ensure it's a proper number
      const balanceValue = parseFloat(config.initialBalance);
      if (!isNaN(balanceValue) && balanceValue > 0) {
        payload.initial_balance = balanceValue;
        // Also add to config for the backend strategy
        payload.config.INITIAL_CASH = balanceValue;
        console.log(`Setting initial_balance: ${balanceValue}`);
      } else {
        payload.initial_balance = 200000.0;
        payload.config.INITIAL_CASH = 200000.0;
        console.log(`Invalid initialBalance, using default: 200000.0`);
      }
    } else {
      payload.initial_balance = 200000.0;
      payload.config.INITIAL_CASH = 200000.0;
      console.log(`No initialBalance provided, using default: 200000.0`);
    }

    console.log('=== FRONTEND PARAMETER DEBUG ===');
    console.log('Original config object:', config);
    console.log('Monthly withdrawal from config:', config.monthlyWithdrawal);
    console.log('Full payload being sent:', JSON.stringify(payload, null, 2));
    console.log('=== END FRONTEND DEBUG ===');
    console.log('Sending simulation request:', payload);
    const response = await axios.post(`${API_BASE_URL}/simulate`, payload);
    
    if (!response.data) {
      throw new Error('No data received from simulation');
    }
    
    // Additional validation of the response data
    if (typeof response.data === 'object') {
      // Check if the data object has any entries
      const dataSize = Object.keys(response.data).length;
      console.log(`Response data contains ${dataSize} entries`);
      
      if (dataSize === 0) {
        throw new Error('Simulation returned empty data object');
      }
      
      // Check a few expected fields in the first entry
      const firstEntryKey = Object.keys(response.data)[0];
      if (firstEntryKey) {
        const firstEntry = response.data[firstEntryKey];
        console.log('First entry sample:', firstEntry);
        
        // Check for required fields
        const requiredFields = ['Portfolio_Value', 'spy_value', 'Margin_Ratio'];
        const missingFields = requiredFields.filter(field => !(field in firstEntry));
        
        if (missingFields.length > 0) {
          console.warn(`Missing expected fields in response data: ${missingFields.join(', ')}`);
        }
      }
    }
    
    console.log('Simulation response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error running simulation:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      config: config
    });
    throw error;
  }
}; 