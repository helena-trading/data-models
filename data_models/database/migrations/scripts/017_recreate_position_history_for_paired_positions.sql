-- Recreate position_history table for paired position tracking
-- Version: 017
-- Description: Recreate position_history to track paired maker/taker positions

-- First, backup existing data if any
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'position_history') THEN
        -- Create backup table
        CREATE TABLE IF NOT EXISTS position_history_backup AS SELECT * FROM position_history;
        RAISE NOTICE 'Created backup of existing position_history table';
        
        -- Drop existing views that depend on position_history
        DROP VIEW IF EXISTS current_positions CASCADE;
        DROP VIEW IF EXISTS position_pnl_summary CASCADE;
        DROP FUNCTION IF EXISTS calculate_position_metrics CASCADE;
        
        -- Drop the existing table
        DROP TABLE position_history CASCADE;
        RAISE NOTICE 'Dropped existing position_history table';
    END IF;
END $$;

-- Create new position_history table for paired positions
CREATE TABLE position_history (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    maker_exchange VARCHAR(50) NOT NULL,
    taker_exchange VARCHAR(50) NOT NULL,
    contract VARCHAR(50) NOT NULL,
    maker_position DECIMAL(20, 8) NOT NULL,
    taker_position DECIMAL(20, 8) NOT NULL,
    exposure DECIMAL(20, 8) NOT NULL, -- Absolute value of sum of positions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_position_history_time ON position_history (time DESC);
CREATE INDEX idx_position_history_contract ON position_history (contract, time DESC);
CREATE INDEX idx_position_history_exchanges ON position_history (maker_exchange, taker_exchange, time DESC);
CREATE INDEX idx_position_history_exposure ON position_history (exposure) WHERE exposure > 0;

-- Add comments to document the schema
COMMENT ON TABLE position_history IS 'Tracks paired positions on maker and taker exchanges during trade execution';
COMMENT ON COLUMN position_history.maker_exchange IS 'Exchange where maker orders are placed';
COMMENT ON COLUMN position_history.taker_exchange IS 'Exchange where taker orders are placed';
COMMENT ON COLUMN position_history.contract IS 'Trading contract/pair';
COMMENT ON COLUMN position_history.maker_position IS 'Position size on maker exchange';
COMMENT ON COLUMN position_history.taker_position IS 'Position size on taker exchange';
COMMENT ON COLUMN position_history.exposure IS 'Absolute value of net position across both exchanges';