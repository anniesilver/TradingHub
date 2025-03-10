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
 * @param {string} config.buyTime - Time to buy (default: '9:35')
 * @param {string} config.sellTime - Time to sell (default: '15:45')
 * @param {number} config.stopLoss - Stop loss percentage (default: 0.50)
 * @param {number} config.takeProfit - Take profit percentage (default: 1.00)
 * @param {string} config.optionType - Option type (default: 'call')
 * @param {number} config.dteMin - Minimum days to expiration (default: 1)
 * @param {number} config.dteMax - Maximum days to expiration (default: 5)
 * @param {number} config.deltaMin - Minimum delta (default: 0.40)
 * @param {number} config.deltaMax - Maximum delta (default: 0.60)
 * @param {string} config.startDate - Start date for simulation
 * @param {string} config.endDate - End date for simulation
 * @param {number} config.initialBalance - Initial balance (default: 10000.0)
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
      },
      start_date: config.startDate,
      end_date: config.endDate
    };
    
    // Add initial balance with consistent naming
    if (config.initialBalance !== undefined && config.initialBalance !== null) {
      // Parse to ensure it's a proper number
      const balanceValue = parseFloat(config.initialBalance);
      if (!isNaN(balanceValue) && balanceValue > 0) {
        payload.initial_balance = balanceValue;
        console.log(`Setting initial_balance: ${balanceValue}`);
      } else {
        payload.initial_balance = 500000.0;
        console.log(`Invalid initialBalance, using default: 500000.0`);
      }
    } else {
      payload.initial_balance = 500000.0;
      console.log(`No initialBalance provided, using default: 500000.0`);
    }

    console.log('Sending simulation request:', payload);
    const response = await axios.post(`${API_BASE_URL}/simulate`, payload);
    
    if (!response.data) {
      throw new Error('No data received from simulation');
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