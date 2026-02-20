-- Helena Bot Error Logs Table (without TimescaleDB)
-- Version: 003
-- Description: Add error logging table for monitoring bot errors

-- Create error_logs table
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL, -- ERROR, CRITICAL, WARNING
    exchange VARCHAR(50), -- Exchange where error occurred (if applicable)
    component VARCHAR(100) NOT NULL, -- Component/module that generated the error
    error_type VARCHAR(100), -- Type/class of error
    message TEXT NOT NULL, -- Error message
    traceback TEXT, -- Full traceback if available
    context JSONB, -- Additional context data
    route_id INTEGER, -- Associated route ID if applicable
    order_id BIGINT, -- Associated order ID if applicable
    resolved BOOLEAN DEFAULT FALSE, -- Whether the error has been resolved
    resolution_notes TEXT -- Notes about how the error was resolved
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_error_logs_level_time ON error_logs (level, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_exchange_time ON error_logs (exchange, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_component_time ON error_logs (component, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs (error_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_unresolved ON error_logs (time DESC) WHERE resolved = FALSE;

-- Create a view for recent unresolved errors
CREATE OR REPLACE VIEW recent_unresolved_errors AS
SELECT 
    time,
    level,
    exchange,
    component,
    error_type,
    message,
    context->>'order_id' as order_id,
    context->>'contract' as contract
FROM error_logs
WHERE resolved = FALSE
AND time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC;