-- Migration: Fix block_trades status column
-- The status column is not used in the BlockTrade model (uses lifecycle_state instead)

-- Make status nullable since we use lifecycle_state
ALTER TABLE block_trades 
    ALTER COLUMN status DROP NOT NULL;

-- Add comment to explain
COMMENT ON COLUMN block_trades.status IS 'Legacy column - use lifecycle_state instead';