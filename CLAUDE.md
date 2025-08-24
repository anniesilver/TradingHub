# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Environment Setup
- `make venv` - Create Python virtual environment and install dependencies
- `make tools` - Install development tools (linting, testing, etc.)
- `cd frontend && npm install` - Install frontend dependencies
- `python setup_ibkr_integration.py` - Set up IBKR data integration
- `python backend/init_market_data_db.py` - Initialize market data tables

### Backend Development
- `.\.venv\Scripts\python backend\simple_app.py` (Windows) - Start API server on port 8080
- `./.venv/bin/python backend/simple_app.py` (Linux/Mac) - Start API server on port 8080
- `make test` - Run Python unit tests with coverage reports
- `make lint` - Run static code analysis (flake8, pylint, mypy)
- `make format` - Format Python code with black and isort

### Frontend Development
- `cd frontend && npm start` - Start React development server (usually port 3000/3001)
- `cd frontend && npm run build` - Build production frontend
- `cd frontend && npm test` - Run React tests

### Database
- `createdb tradinghub` - Create PostgreSQL database
- Copy `backend/services/.env.example` to `backend/services/.env` and configure
- `python backend/init_all_db.py` - Create all database tables (users, products, strategies, market data)

### IBKR Data Integration
- `POST /api/market-data/refresh/<symbol>` - Refresh market data from IBKR
- `GET /api/market-data/status/<symbol>` - Check data availability and coverage
- `GET /api/market-data/test-connection` - Test IBKR TWS/Gateway connection
- Requires TWS or IB Gateway running with API enabled (port 7496/4002)

## Architecture Overview

TradingHub is a full-stack web application for trading strategy simulation and backtesting.

### Backend Structure
- **Flask API** (`backend/simple_app.py`) - Main API server with CORS enabled
- **Strategy Service** (`backend/services/strategy_service.py`) - Core trading strategy logic and simulation engine
- **Models** (`backend/models/`) - SQLAlchemy database models for users and products
- **Routes** (`backend/routes/`) - API route handlers for auth, accounts, and strategies
- **Database**: PostgreSQL with Flask-SQLAlchemy ORM

### Frontend Structure
- **React.js** application using Material-UI components
- **Services** (`frontend/src/services/`) - API communication layers
- **Pages** (`frontend/src/pages/`) - Dashboard and Login components
- **Charts**: Uses Recharts for performance visualization

### Key Integration Points
- Backend serves API on port 8080, frontend typically on port 3000/3001
- Authentication handled via Flask-JWT-Extended
- Strategy simulation endpoint: `POST /api/simulate`
- API test endpoint: `GET /api/test`
- Market data integration with IBKR API for live data updates
- Database-first approach with IBKR fallback for missing data

### Development Environment Requirements
- Python 3.8+ with virtual environment
- PostgreSQL database
- Node.js for frontend build tools
- Interactive Brokers TWS or IB Gateway (for live data)
- Environment variables in `backend/services/.env` for database and IBKR connection

### Code Quality Tools
- Black formatter with 120 character line length
- Pylint and Flake8 for linting
- MyPy for type checking
- Pytest for unit testing with coverage
- ESLint for React code (via react-scripts)