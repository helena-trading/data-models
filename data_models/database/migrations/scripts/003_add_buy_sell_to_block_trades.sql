-- Add buy/sell columns to block_trades table
-- Version: 003
-- Description: Add proper buy/sell tracking to distinguish from maker/taker

-- Add buy/sell columns
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS buy_exchange VARCHAR(50);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS sell_exchange VARCHAR(50);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS buy_price NUMERIC(20,8);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS sell_price NUMERIC(20,8);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS order_type VARCHAR(20);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS slippage_pct NUMERIC(10,4);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_block_trades_buy_sell_exchanges ON block_trades (buy_exchange, sell_exchange, time DESC);

-- Clean existing data as requested (all current data is test data)
TRUNCATE TABLE block_trades;

-- Also clean other related tables since we're resetting test data
TRUNCATE TABLE order_executions CASCADE;
TRUNCATE TABLE latency_metrics CASCADE;
TRUNCATE TABLE position_snapshots CASCADE;
TRUNCATE TABLE market_data CASCADE;
TRUNCATE TABLE account_balances CASCADE;