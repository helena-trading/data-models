-- Helena Bot PostgreSQL Schema (without TimescaleDB)
-- Version: 001
-- Description: Initial schema setup for local testing

-- 1. Order Executions (Main trading activity)
CREATE TABLE IF NOT EXISTS order_executions (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    order_id VARCHAR(100) NOT NULL,
    client_order_id VARCHAR(100),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8),
    quantity DECIMAL(20, 8),
    filled_quantity DECIMAL(20, 8),
    fee DECIMAL(20, 8),
    fee_currency VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    PRIMARY KEY (time, id)
);

-- 2. Market Data (Price and orderbook data)
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    bid_price DECIMAL(20, 8),
    ask_price DECIMAL(20, 8),
    bid_quantity DECIMAL(20, 8),
    ask_quantity DECIMAL(20, 8),
    mid_price DECIMAL(20, 8),
    spread DECIMAL(20, 8),
    timestamp BIGINT,
    PRIMARY KEY (time, id)
);

-- 3. Position Snapshots (Position tracking)
CREATE TABLE IF NOT EXISTS position_snapshots (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    position_size DECIMAL(20, 8),
    entry_price DECIMAL(20, 8),
    mark_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8),
    margin_used DECIMAL(20, 8),
    leverage INTEGER,
    liquidation_price DECIMAL(20, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, id)
);

-- 4. Account Balances (Balance tracking)
CREATE TABLE IF NOT EXISTS account_balances (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    currency VARCHAR(20) NOT NULL,
    free_balance DECIMAL(20, 8),
    locked_balance DECIMAL(20, 8),
    total_balance DECIMAL(20, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, id)
);

-- 5. Latency Metrics (Performance monitoring)
CREATE TABLE IF NOT EXISTS latency_metrics (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    latency_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    metadata JSONB,
    PRIMARY KEY (time, id)
);

-- 6. Block Trades (Arbitrage execution blocks)
CREATE TABLE IF NOT EXISTS block_trades (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id SERIAL,
    block_id VARCHAR(100) UNIQUE NOT NULL,
    maker_exchange VARCHAR(50) NOT NULL,
    taker_exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    maker_side VARCHAR(10) NOT NULL,
    taker_side VARCHAR(10) NOT NULL,
    maker_price DECIMAL(20, 8),
    taker_price DECIMAL(20, 8),
    quantity DECIMAL(20, 8),
    spread_percentage DECIMAL(10, 6),
    profit_estimate DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL,
    maker_order_id VARCHAR(100),
    taker_order_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB,
    PRIMARY KEY (time, id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_order_executions_exchange_symbol ON order_executions(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_order_executions_time ON order_executions(time DESC);
CREATE INDEX IF NOT EXISTS idx_order_executions_order_id ON order_executions(order_id);

CREATE INDEX IF NOT EXISTS idx_market_data_exchange_symbol ON market_data(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(time DESC);

CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange_symbol ON position_snapshots(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_time ON position_snapshots(time DESC);

CREATE INDEX IF NOT EXISTS idx_account_balances_exchange ON account_balances(exchange, currency);
CREATE INDEX IF NOT EXISTS idx_account_balances_time ON account_balances(time DESC);

CREATE INDEX IF NOT EXISTS idx_latency_metrics_exchange_operation ON latency_metrics(exchange, operation);
CREATE INDEX IF NOT EXISTS idx_latency_metrics_time ON latency_metrics(time DESC);

CREATE INDEX IF NOT EXISTS idx_block_trades_status ON block_trades(status);
CREATE INDEX IF NOT EXISTS idx_block_trades_time ON block_trades(time DESC);
CREATE INDEX IF NOT EXISTS idx_block_trades_block_id ON block_trades(block_id);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to order_executions
CREATE TRIGGER update_order_executions_updated_at BEFORE UPDATE
    ON order_executions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();