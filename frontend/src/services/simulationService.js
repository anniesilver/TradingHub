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

export const getSimulationResults = async (strategyId) => {
  try {
    // Get current date and 30 days ago for a reasonable default range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    const payload = {
      strategy_type: strategyId,
      config: {
        SYMBOL: 'SPY',
        BUY_TIME: '9:35',
        SELL_TIME: '15:45',
        STOP_LOSS_PCT: 0.50,
        TAKE_PROFIT_PCT: 1.00,
        OPTION_TYPE: 'call',
        DTE_MIN: 1,
        DTE_MAX: 5,
        DELTA_MIN: 0.40,
        DELTA_MAX: 0.60,
      },
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
      initial_balance: 10000.0
    };

    console.log('Sending simulation request:', payload);
    const response = await axios.post(`${API_BASE_URL}/simulate`, payload);
    
    if (!response.data) {
      throw new Error('No data received from simulation');
    }
    
    console.log('Simulation response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching simulation results:', error.response || error);
    throw error;
  }
};

export const runSimulation = async (config) => {
  try {
    if (!config) {
      throw new Error('No configuration provided');
    }

    const payload = {
      strategy_type: config.strategyId || 'SPY_POWER_CASHFLOW',
      config: {
        SYMBOL: config.symbol || 'SPY',
        BUY_TIME: config.buyTime || '9:35',
        SELL_TIME: config.sellTime || '15:45',
        STOP_LOSS_PCT: config.stopLoss || 0.50,
        TAKE_PROFIT_PCT: config.takeProfit || 1.00,
        OPTION_TYPE: config.optionType || 'call',
        DTE_MIN: config.dteMin || 1,
        DTE_MAX: config.dteMax || 5,
        DELTA_MIN: config.deltaMin || 0.40,
        DELTA_MAX: config.deltaMax || 0.60,
      },
      start_date: config.startDate,
      end_date: config.endDate,
      initial_balance: config.initialBalance || 10000.0
    };

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