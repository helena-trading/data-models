-- Fix latency_metrics table columns to match code expectations
-- Version: 018
-- Description: Update latency_metrics to have exchange_maker and exchange_taker columns

-- First, check if we need to split the exchange column into maker/taker
DO $$ 
BEGIN
    -- Add exchange_maker column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'exchange_maker'
    ) THEN
        ALTER TABLE latency_metrics 
        ADD COLUMN exchange_maker VARCHAR(50);
        
        RAISE NOTICE 'Added exchange_maker column to latency_metrics';
    END IF;

    -- Add exchange_taker column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'exchange_taker'
    ) THEN
        ALTER TABLE latency_metrics 
        ADD COLUMN exchange_taker VARCHAR(50);
        
        RAISE NOTICE 'Added exchange_taker column to latency_metrics';
    END IF;

    -- Add contract column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'contract'
    ) THEN
        ALTER TABLE latency_metrics 
        ADD COLUMN contract VARCHAR(50);
        
        RAISE NOTICE 'Added contract column to latency_metrics';
    END IF;

    -- Add state_transitions column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'state_transitions'
    ) THEN
        ALTER TABLE latency_metrics 
        ADD COLUMN state_transitions JSONB;
        
        RAISE NOTICE 'Added state_transitions column to latency_metrics';
    END IF;

    -- Add route_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'route_id'
    ) THEN
        ALTER TABLE latency_metrics 
        ADD COLUMN route_id INTEGER;
        
        RAISE NOTICE 'Added route_id column to latency_metrics';
    END IF;

    -- If there's an old 'exchange' column, migrate data and drop it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'exchange'
    ) THEN
        -- Copy exchange data to exchange_maker if not already populated
        UPDATE latency_metrics 
        SET exchange_maker = exchange 
        WHERE exchange_maker IS NULL AND exchange IS NOT NULL;
        
        -- Drop the old column
        ALTER TABLE latency_metrics DROP COLUMN exchange;
        
        RAISE NOTICE 'Migrated and dropped old exchange column from latency_metrics';
    END IF;

    -- If there's an old 'operation' column, drop it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' 
        AND column_name = 'operation'
    ) THEN
        ALTER TABLE latency_metrics DROP COLUMN operation;
        RAISE NOTICE 'Dropped old operation column from latency_metrics';
    END IF;
END $$;

-- Update indexes
DROP INDEX IF EXISTS idx_latency_metrics_exchange_operation;
CREATE INDEX IF NOT EXISTS idx_latency_metrics_exchanges 
ON latency_metrics(exchange_maker, exchange_taker);
CREATE INDEX IF NOT EXISTS idx_latency_metrics_metric_type 
ON latency_metrics(metric_type);

-- Add comments to document the columns
COMMENT ON COLUMN latency_metrics.exchange_maker IS 'Exchange where maker order is placed';
COMMENT ON COLUMN latency_metrics.exchange_taker IS 'Exchange where taker order is placed';
COMMENT ON COLUMN latency_metrics.state_transitions IS 'Detailed timing of state transitions';
COMMENT ON COLUMN latency_metrics.route_id IS 'Route identifier for multi-route strategies';