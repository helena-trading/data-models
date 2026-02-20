-- Migration: Fix block_trades schema to match code requirements
-- This migration ensures all required columns exist for block trade recording

-- First, rename 'symbol' column to 'contract' to match the model
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'block_trades' AND column_name = 'symbol'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'block_trades' AND column_name = 'contract'
    ) THEN
        ALTER TABLE block_trades RENAME COLUMN symbol TO contract;
        RAISE NOTICE 'Renamed symbol column to contract in block_trades';
    END IF;
END $$;

-- Add missing columns based on BlockTrade model
ALTER TABLE block_trades 
    ADD COLUMN IF NOT EXISTS size NUMERIC(20,8),
    ADD COLUMN IF NOT EXISTS spread_captured NUMERIC(20,8),
    ADD COLUMN IF NOT EXISTS total_fees NUMERIC(20,8),
    ADD COLUMN IF NOT EXISTS net_profit NUMERIC(20,8),
    ADD COLUMN IF NOT EXISTS lifecycle_state VARCHAR(50),
    ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER,
    ADD COLUMN IF NOT EXISTS route_id INTEGER;

-- Migrate data from old columns to new ones if needed
UPDATE block_trades 
SET 
    size = COALESCE(size, quantity),
    lifecycle_state = COALESCE(lifecycle_state, status)
WHERE size IS NULL OR lifecycle_state IS NULL;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_block_trades_lifecycle_state ON block_trades(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_block_trades_route_id ON block_trades(route_id);
CREATE INDEX IF NOT EXISTS idx_block_trades_execution_time ON block_trades(execution_time_ms);

-- Add comment to document the schema
COMMENT ON TABLE block_trades IS 'Records of executed arbitrage trades between exchanges';
COMMENT ON COLUMN block_trades.contract IS 'Trading pair/contract (e.g., BTC-PERP, ETH-USD)';
COMMENT ON COLUMN block_trades.size IS 'Trade size/quantity';
COMMENT ON COLUMN block_trades.spread_captured IS 'Profit from price difference';
COMMENT ON COLUMN block_trades.total_fees IS 'Total fees paid to exchanges';
COMMENT ON COLUMN block_trades.net_profit IS 'Net profit after fees';
COMMENT ON COLUMN block_trades.lifecycle_state IS 'Trade state (pending, completed, failed)';
COMMENT ON COLUMN block_trades.execution_time_ms IS 'Time taken to execute the trade in milliseconds';
COMMENT ON COLUMN block_trades.route_id IS 'ID of the route that executed this trade';