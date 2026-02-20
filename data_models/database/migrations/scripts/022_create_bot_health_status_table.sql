-- Migration: Create bot_health_status table for real-time WebSocket health monitoring
-- This table stores periodic health reports from running bots

CREATE TABLE IF NOT EXISTS bot_health_status (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    -- Timestamp of health report
    reported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Overall WebSocket status
    websocket_status VARCHAR(50) NOT NULL CHECK (websocket_status IN ('healthy', 'connected', 'unhealthy', 'disconnected', 'error', 'failed', 'unknown')),
    
    -- WebSocket metrics
    reconnect_count INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    uptime_seconds INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Per-exchange health status (JSON)
    -- Format: {"binance": {"connected": true, "last_message": "2024-01-01T12:00:00Z", "latency_ms": 15}, ...}
    exchanges_health JSONB,
    
    -- Engine health metrics
    engine_status VARCHAR(50) DEFAULT 'healthy',
    last_tick TIMESTAMP WITH TIME ZONE,
    ticks_per_second NUMERIC(10,2),
    queued_orders INTEGER DEFAULT 0,
    
    -- Performance metrics (last period)
    orders_last_minute INTEGER DEFAULT 0,
    trades_last_minute INTEGER DEFAULT 0,
    errors_last_minute INTEGER DEFAULT 0,
    
    -- Latency metrics (milliseconds)
    tick_processing_latency_ms INTEGER,
    order_placement_latency_ms INTEGER,
    websocket_roundtrip_ms INTEGER,
    
    -- Indexes
    CONSTRAINT bot_health_status_bot_id_reported_at_key UNIQUE (bot_id, reported_at)
);

-- Create indexes for efficient queries
CREATE INDEX idx_bot_health_status_bot_id ON bot_health_status(bot_id);
CREATE INDEX idx_bot_health_status_reported_at ON bot_health_status(reported_at DESC);
CREATE INDEX idx_bot_health_status_bot_id_reported_at ON bot_health_status(bot_id, reported_at DESC);

-- Create index for finding unhealthy bots
CREATE INDEX idx_bot_health_status_websocket_status ON bot_health_status(websocket_status) 
WHERE websocket_status NOT IN ('healthy', 'connected');

-- Add comment
COMMENT ON TABLE bot_health_status IS 'Real-time health status reports from running bots';
COMMENT ON COLUMN bot_health_status.websocket_status IS 'Overall WebSocket connection status';
COMMENT ON COLUMN bot_health_status.exchanges_health IS 'Per-exchange health metrics in JSON format';
COMMENT ON COLUMN bot_health_status.engine_status IS 'Trading engine health status';

-- Create a function to automatically delete old health records (older than 24 hours)
CREATE OR REPLACE FUNCTION delete_old_bot_health_status()
RETURNS void AS $$
BEGIN
    DELETE FROM bot_health_status 
    WHERE reported_at < CURRENT_TIMESTAMP - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to limit records per bot (keep only last 100 records per bot)
CREATE OR REPLACE FUNCTION limit_bot_health_records()
RETURNS TRIGGER AS $$
BEGIN
    -- Keep only the most recent 100 records per bot
    DELETE FROM bot_health_status
    WHERE bot_id = NEW.bot_id
    AND id NOT IN (
        SELECT id FROM bot_health_status
        WHERE bot_id = NEW.bot_id
        ORDER BY reported_at DESC
        LIMIT 100
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_limit_bot_health_records
AFTER INSERT ON bot_health_status
FOR EACH ROW
EXECUTE FUNCTION limit_bot_health_records();