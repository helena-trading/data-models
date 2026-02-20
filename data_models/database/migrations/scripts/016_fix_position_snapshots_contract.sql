-- Fix position_snapshots table to use 'contract' instead of 'symbol'
-- Version: 016
-- Description: Rename symbol column to contract in position_snapshots table

-- Rename symbol column to contract if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'position_snapshots' AND column_name = 'symbol'
    ) THEN
        ALTER TABLE position_snapshots RENAME COLUMN symbol TO contract;
        RAISE NOTICE 'Renamed symbol column to contract in position_snapshots';
    END IF;
END $$;

-- Update any indexes that referenced symbol
DROP INDEX IF EXISTS idx_position_snapshots_exchange_symbol;
CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange_contract ON position_snapshots(exchange, contract);