-- Migration: Add run_id to block_trades table
-- Purpose: Enable filtering trades by specific bot run sessions
-- This allows more granular analytics queries focused on individual bot runs

-- Add run_id column to block_trades table
ALTER TABLE block_trades
    ADD COLUMN IF NOT EXISTS run_id INTEGER;

-- Create index for efficient filtering by run_id
CREATE INDEX IF NOT EXISTS idx_block_trades_run_id ON block_trades(run_id);

-- Create composite index for bot_id + run_id queries (common filter pattern)
CREATE INDEX IF NOT EXISTS idx_block_trades_bot_run ON block_trades(bot_id, run_id);

-- Add comment to document the column
COMMENT ON COLUMN block_trades.run_id IS 'References bot_runs.id - identifies which bot run session created this trade';

-- Note: We don't add a foreign key constraint because:
-- 1. block_trades is in the analytics database
-- 2. bot_runs is in the credentials database
-- 3. Cross-database foreign keys are not supported in PostgreSQL