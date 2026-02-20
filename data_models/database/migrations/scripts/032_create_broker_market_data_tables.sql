-- Create broker market data snapshot tables for historical analytics
-- These tables store periodic snapshots from broker's funding rate and mark price caches
--
-- Tables:
-- 1. broker_funding_rate_snapshots - Funding rate data from exchange WebSocket streams
-- 2. broker_mark_price_snapshots - Mark price data from exchange WebSocket streams
--
-- Note: These tables use "broker_" prefix to distinguish from Loris API data tables

-- ============================================================================
-- FUNDING RATE SNAPSHOTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS broker_funding_rate_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,  -- Internal format: BTC_USDT
    rate DOUBLE PRECISION NOT NULL,  -- Funding rate (e.g., 0.0001 for 0.01%)
    next_funding_time TIMESTAMP WITH TIME ZONE,
    interval_hours INTEGER NOT NULL DEFAULT 8
);

-- Create indexes for efficient queries
-- Primary query pattern: by time range + exchange + symbol
CREATE INDEX IF NOT EXISTS idx_broker_funding_snapshots_time
    ON broker_funding_rate_snapshots(snapshot_time);

CREATE INDEX IF NOT EXISTS idx_broker_funding_snapshots_exchange_symbol
    ON broker_funding_rate_snapshots(exchange, symbol);

CREATE INDEX IF NOT EXISTS idx_broker_funding_snapshots_time_exchange
    ON broker_funding_rate_snapshots(snapshot_time, exchange);

-- Composite index for common query pattern: specific symbol over time
CREATE INDEX IF NOT EXISTS idx_broker_funding_snapshots_symbol_time
    ON broker_funding_rate_snapshots(symbol, snapshot_time);

-- ============================================================================
-- MARK PRICE SNAPSHOTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS broker_mark_price_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,  -- Internal format: BTC_USDT
    mark_price DOUBLE PRECISION NOT NULL,
    index_price DOUBLE PRECISION NOT NULL,
    estimated_settle_price DOUBLE PRECISION  -- Can be NULL
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_broker_mark_snapshots_time
    ON broker_mark_price_snapshots(snapshot_time);

CREATE INDEX IF NOT EXISTS idx_broker_mark_snapshots_exchange_symbol
    ON broker_mark_price_snapshots(exchange, symbol);

CREATE INDEX IF NOT EXISTS idx_broker_mark_snapshots_time_exchange
    ON broker_mark_price_snapshots(snapshot_time, exchange);

-- Composite index for common query pattern: specific symbol over time
CREATE INDEX IF NOT EXISTS idx_broker_mark_snapshots_symbol_time
    ON broker_mark_price_snapshots(symbol, snapshot_time);
