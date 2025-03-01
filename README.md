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
- **Frontend**: HTML, JavaScript, Bootstrap, Chart.js
- **API**: RESTful JSON API

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TradingHub.git
   cd TradingHub
   ```

2. **Install Python dependencies**
   ```bash
   pip install flask flask-cors psycopg2-binary python-dotenv
   ```

3. **Set up the database**
   ```bash
   # Create a PostgreSQL database
   createdb tradinghub
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file in backend/services directory
   echo "DB_NAME=tradinghub" > backend/services/.env
   echo "DB_USER=postgres" >> backend/services/.env
   echo "DB_PASSWORD=your_password" >> backend/services/.env
   echo "DB_HOST=localhost" >> backend/services/.env
   echo "DB_PORT=5432" >> backend/services/.env
   ```

## Running the Application

1. **Start the API server**
   ```bash
   python backend/simple_app.py
   ```

2. **Start the frontend server**
   ```bash
   python backend/serve_static.py
   ```

3. **Access the application**
   - Frontend: http://localhost:8080
   - API: http://localhost:5000

## Project Structure 