# IBKR Data Integration Plan for TradingHub

## Analysis Summary

**Current State:**
- TradingHub uses static CSV files (SPY-20Y.csv, VIX-20Y.csv) stored in strategy directories
- Data loading happens in `MarketData` class within each strategy module
- Date range errors occur when requesting data beyond CSV file coverage

**IBKR Module Analysis:**
- `loading_data.py` uses Interactive Brokers API (ibapi) to fetch live/historical data
- Connects to TWS/IB Gateway on localhost:7496
- Currently configured for VIX data (IND/CBOE) but easily adaptable for stocks
- Saves data as CSV files with 10-year history by default

## Integration Plan

### Phase 1: Create IBKR Data Service
1. **New Module**: `backend/services/ibkr_data_service.py`
   - Refactor `loading_data.py` into a reusable service class
   - Add error handling, logging, and configuration management
   - Support both stock (SPY) and index (VIX) data fetching
   - Implement connection pooling and retry logic

2. **Add Dependencies**:
   - Add `ibapi` to `requirements.txt`
   - Update environment configuration for IBKR connection settings

### Phase 2: Database Integration
1. **New Table**: `market_data` in PostgreSQL
   - Columns: symbol, date, open, high, low, close, volume
   - Indexes on symbol+date for fast queries
   - Automatic data deduplication

2. **Data Management**:
   - Cache fetched data in database (all IBKR data stored here)
   - Implement data freshness checks (update if > 1 day old)
   - Background data refresh service

### Phase 3: MarketData Class Enhancement
1. **DB-First Approach**:
   - Try database first for requested date range
   - Fall back to IBKR API for missing data
   - All IBKR fetched data automatically saved to database

2. **API Integration**:
   - New endpoint: `GET /api/market-data/refresh/{symbol}`
   - Trigger manual data updates from frontend
   - Status monitoring for data freshness

### Phase 4: Configuration & Monitoring
1. **Environment Variables**:
   - `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`
   - `AUTO_REFRESH_DATA` flag for background updates

2. **Frontend Integration**:
   - Data status indicator in dashboard
   - Manual refresh buttons
   - Error handling for IBKR connectivity issues

## Implementation Benefits
- **Solves current issue**: Live data updates eliminate date range errors
- **Scalable**: Easy to add new symbols (QQQ, TSLA, etc.)
- **Resilient**: DB → IBKR fallback (no CSV dependency)
- **Performance**: Database caching reduces API calls
- **User Control**: Manual refresh capability when needed

## Dependencies
- IBKR TWS/Gateway running on user's machine
- PostgreSQL database (already configured)
- `ibapi` Python package installation