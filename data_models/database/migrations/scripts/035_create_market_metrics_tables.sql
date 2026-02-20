-- Migration 035: Create market metrics tables for Open Interest and Volume snapshots
-- These tables store OI and Volume data from the FundingMonitor for historical analysis

-- ==============================================================================
-- CREATE TABLE: broker_open_interest_snapshots
-- Stores open interest snapshots from exchange market data services
-- ==============================================================================
CREATE TABLE IF NOT EXISTS broker_open_interest_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    open_interest DOUBLE PRECISION NOT NULL,
    open_interest_value DOUBLE PRECISION,  -- USD value (if available)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_oi_snapshots_time
    ON broker_open_interest_snapshots(snapshot_time);

-- Index for exchange+symbol queries
CREATE INDEX IF NOT EXISTS idx_oi_snapshots_exchange_symbol
    ON broker_open_interest_snapshots(exchange, symbol);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_oi_snapshots_exchange_symbol_time
    ON broker_open_interest_snapshots(exchange, symbol, snapshot_time);

-- ==============================================================================
-- CREATE TABLE: broker_volume_snapshots
-- Stores 24-hour trading volume snapshots from exchange market data services
-- ==============================================================================
CREATE TABLE IF NOT EXISTS broker_volume_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    volume_24h DOUBLE PRECISION NOT NULL,  -- Volume in quote currency (USD/USDT)
    quote_volume_24h DOUBLE PRECISION,     -- Base currency volume (for reference)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_vol_snapshots_time
    ON broker_volume_snapshots(snapshot_time);

-- Index for exchange+symbol queries
CREATE INDEX IF NOT EXISTS idx_vol_snapshots_exchange_symbol
    ON broker_volume_snapshots(exchange, symbol);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_vol_snapshots_exchange_symbol_time
    ON broker_volume_snapshots(exchange, symbol, snapshot_time);

-- ==============================================================================
-- COMMENTS
-- ==============================================================================
COMMENT ON TABLE broker_open_interest_snapshots IS 'Open interest snapshots from FundingMonitor for market analysis';
COMMENT ON COLUMN broker_open_interest_snapshots.open_interest IS 'Open interest in contracts';
COMMENT ON COLUMN broker_open_interest_snapshots.open_interest_value IS 'USD value of open interest (if calculated)';

COMMENT ON TABLE broker_volume_snapshots IS '24-hour trading volume snapshots from FundingMonitor';
COMMENT ON COLUMN broker_volume_snapshots.volume_24h IS 'Volume in quote currency (USD/USDT)';
COMMENT ON COLUMN broker_volume_snapshots.quote_volume_24h IS 'Volume in base currency for reference';
