-- Fix latency_metrics table to match the model requirements
-- Version: 018
-- Description: Add missing columns to latency_metrics table

-- Add metric_type column
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS metric_type VARCHAR(50);

-- Add exchange_maker and exchange_taker columns
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS exchange_maker VARCHAR(50);
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS exchange_taker VARCHAR(50);

-- Add contract column
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS contract VARCHAR(50);

-- Add state_transitions column for storing JSON data
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS state_transitions JSONB;

-- Add route_id column
ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS route_id INTEGER;

-- Update the operation column to metric_type if needed (for existing data)
DO $$ 
BEGIN
    -- If we have data in operation column but not in metric_type, copy it over
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'latency_metrics' AND column_name = 'operation'
    ) THEN
        UPDATE latency_metrics 
        SET metric_type = operation 
        WHERE metric_type IS NULL AND operation IS NOT NULL;
        
        -- Map old operation values to new metric_type values
        UPDATE latency_metrics SET metric_type = 'orderbook' WHERE metric_type LIKE '%orderbook%';
        UPDATE latency_metrics SET metric_type = 'placement' WHERE metric_type LIKE '%place%' OR metric_type LIKE '%create%';
        UPDATE latency_metrics SET metric_type = 'cancellation' WHERE metric_type LIKE '%cancel%';
        UPDATE latency_metrics SET metric_type = 'cycle' WHERE metric_type LIKE '%cycle%' OR metric_type LIKE '%total%';
    END IF;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_latency_metrics_metric_type ON latency_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_latency_metrics_exchanges ON latency_metrics(exchange_maker, exchange_taker);
CREATE INDEX IF NOT EXISTS idx_latency_metrics_contract ON latency_metrics(contract);
CREATE INDEX IF NOT EXISTS idx_latency_metrics_route_id ON latency_metrics(route_id);

-- Add comments to document the schema
COMMENT ON COLUMN latency_metrics.metric_type IS 'Type of latency measurement: orderbook, placement, cancellation, cycle';
COMMENT ON COLUMN latency_metrics.exchange_maker IS 'Exchange where maker orders are placed';
COMMENT ON COLUMN latency_metrics.exchange_taker IS 'Exchange where taker orders are placed';
COMMENT ON COLUMN latency_metrics.contract IS 'Trading contract/pair';
COMMENT ON COLUMN latency_metrics.state_transitions IS 'JSON object containing timestamps for each state transition';
COMMENT ON COLUMN latency_metrics.route_id IS 'ID of the route that generated this metric';