-- Helena Bot Error Logs Enhancement
-- Version: 040
-- Description: Add bot_id and run_id columns to error_logs for better querying

-- Add bot_id and run_id columns to error_logs table
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS bot_id INTEGER;
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS run_id INTEGER;

-- Create indexes for efficient querying by bot_id and run_id
CREATE INDEX IF NOT EXISTS idx_error_logs_bot_id_time ON error_logs (bot_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_run_id_time ON error_logs (run_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_bot_run ON error_logs (bot_id, run_id, time DESC);

-- Update the recent_unresolved_errors view to include bot_id and run_id
DROP VIEW IF EXISTS recent_unresolved_errors;
CREATE VIEW recent_unresolved_errors AS
SELECT
    time,
    level,
    exchange,
    component,
    error_type,
    message,
    context->>'order_id' as order_id,
    context->>'contract' as contract,
    bot_id,
    run_id
FROM error_logs
WHERE resolved = FALSE
AND time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC;
