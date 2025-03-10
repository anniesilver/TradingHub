# TradingHub

TradingHub is a web-based platform for running trading strategy simulations, visualizing performance metrics, and analyzing trading results. It provides a simple interface for backtesting trading strategies across different time periods.

![TradingHub Screenshot](https://placeholder-for-screenshot.png)

## Features

- **Strategy Simulation**: Backtest trading strategies over custom date ranges
- **Performance Visualization**: View account balance charts and key performance metrics
- **Strategy Configuration**: Customize strategy parameters like symbols, option types, and risk management settings
- **Database Storage**: Save simulation results for later review and comparison
- **API Access**: RESTful API for programmatic access to simulation capabilities

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: React.js, Bootstrap, Chart.js
- **API**: RESTful JSON API

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- pip (Python package manager)
- Node.js and npm (for frontend)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TradingHub.git
   cd TradingHub
   ```

2. **Install Python dependencies**
   ```bash
   make venv
   ```
   
   Alternatively, you can set up the virtual environment manually:
   ```bash
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\pip install -r requirements.txt
   # On Linux/Mac:
   ./.venv/bin/pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Set up the database**
   ```bash
   # Create a PostgreSQL database
   createdb tradinghub
   ```

5. **Configure environment variables**
   ```bash
   # Create .env file in backend/services directory
   echo "DB_NAME=tradinghub" > backend/services/.env
   echo "DB_USER=postgres" >> backend/services/.env
   echo "DB_PASSWORD=your_password" >> backend/services/.env
   echo "DB_HOST=localhost" >> backend/services/.env
   echo "DB_PORT=5432" >> backend/services/.env
   ```

## Running the Application

### Starting the Backend Server

1. **Start the API server**
   ```bash
   # On Windows:
   .\.venv\Scripts\python backend\simple_app.py
   
   # On Linux/Mac:
   ./.venv/bin/python backend/simple_app.py
   ```
   
   The backend server will run on http://127.0.0.1:8080

### Starting the Frontend Server

2. **Start the React frontend**
   ```bash
   cd frontend
   npm start
   ```
   
   The frontend will be available at http://localhost:3000 or http://localhost:3001

### Accessing the Application

- **Frontend:** http://localhost:3000 (or http://localhost:3001)
- **API Endpoints:**
  - API Test: http://localhost:8080/api/test
  - Strategies List: http://localhost:8080/api/strategies
  - Simulation Endpoint: http://localhost:8080/api/simulate (POST)

## Troubleshooting

- **Dependency Issues:** If you encounter the scipy/numpy version mismatch error, try upgrading scipy to match your numpy version:
  ```bash
  ./.venv/Scripts/pip install scipy==1.15.2
  ```

- **'Config' object has no attribute 'SYMBOL' Error:** This error occurs when the strategy configuration does not have the required SYMBOL attribute. The backend code automatically applies the SYMBOL attribute from the frontend configuration, or falls back to 'SPY' as a default value if not provided.

- **Port Conflicts:** If port 8080 or 3000 is already in use, check running processes and terminate any conflicting services.

## Project Structure 
