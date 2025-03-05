import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const getSimulationResults = async (simulationId) => {
  try {
    const response = await axios.get(`${API_URL}/api/simulations/${simulationId}/results`);
    return response.data;
  } catch (error) {
    console.error('Error fetching simulation results:', error);
    throw error;
  }
};

export const getSimulations = async (limit = 10, offset = 0) => {
  try {
    const response = await axios.get(`${API_URL}/api/simulations`, {
      params: { limit, offset }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching simulations:', error);
    throw error;
  }
};

export const runSimulation = async (config) => {
  try {
    const response = await axios.post(`${API_URL}/api/simulations`, config);
    return response.data;
  } catch (error) {
    console.error('Error running simulation:', error);
    throw error;
  }
}; 