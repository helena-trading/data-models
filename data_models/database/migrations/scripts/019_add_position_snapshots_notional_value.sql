-- Add notional_value column to position_snapshots table
-- Version: 017
-- Description: Add missing notional_value column that the code expects

-- Add notional_value column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'position_snapshots' 
        AND column_name = 'notional_value'
    ) THEN
        ALTER TABLE position_snapshots 
        ADD COLUMN notional_value DECIMAL(20, 8);
        
        RAISE NOTICE 'Added notional_value column to position_snapshots';
    ELSE
        RAISE NOTICE 'Column notional_value already exists in position_snapshots';
    END IF;
END $$;

-- Also ensure the contract column exists (from migration 016)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'position_snapshots' 
        AND column_name = 'symbol'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'position_snapshots' 
        AND column_name = 'contract'
    ) THEN
        ALTER TABLE position_snapshots RENAME COLUMN symbol TO contract;
        RAISE NOTICE 'Renamed symbol column to contract in position_snapshots';
    END IF;
END $$;

-- Update indexes if needed
DROP INDEX IF EXISTS idx_position_snapshots_exchange_symbol;
CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange_contract 
ON position_snapshots(exchange, contract);

-- Add comment to document the column
COMMENT ON COLUMN position_snapshots.notional_value IS 'Notional value of the position (size * mark_price)';