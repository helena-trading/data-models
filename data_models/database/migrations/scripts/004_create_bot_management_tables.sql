-- Migration: Create bot management tables
-- Description: Tables for managing multiple bot instances with configuration and history

-- Bot configurations table
CREATE TABLE IF NOT EXISTS bots (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped' CHECK (status IN ('stopped', 'starting', 'running', 'stopping', 'error')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_started_at TIMESTAMP WITH TIME ZONE,
    last_stopped_at TIMESTAMP WITH TIME ZONE,
    pid INTEGER,
    container_id VARCHAR(100),
    error_message TEXT
);

-- Bot execution history
CREATE TABLE IF NOT EXISTS bot_runs (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER REFERENCES bots(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP WITH TIME ZONE,
    stop_reason VARCHAR(100),
    total_orders INTEGER DEFAULT 0,
    total_pnl DECIMAL(20,8) DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    config_snapshot JSONB -- Store config at time of run
);

-- Bot activity logs (for recent activity)
CREATE TABLE IF NOT EXISTS bot_activity_logs (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER REFERENCES bots(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES bot_runs(id) ON DELETE CASCADE,
    level VARCHAR(20) CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_bots_status ON bots(status);
CREATE INDEX idx_bots_updated_at ON bots(updated_at);
CREATE INDEX idx_bot_runs_bot_id ON bot_runs(bot_id);
CREATE INDEX idx_bot_runs_started_at ON bot_runs(started_at);
CREATE INDEX idx_bot_activity_logs_bot_id_created ON bot_activity_logs(bot_id, created_at);
CREATE INDEX idx_bot_activity_logs_run_id ON bot_activity_logs(run_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_bots_updated_at BEFORE UPDATE ON bots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE bots IS 'Bot configurations and current status';
COMMENT ON TABLE bot_runs IS 'Historical record of bot executions';
COMMENT ON TABLE bot_activity_logs IS 'Recent activity logs for each bot';

COMMENT ON COLUMN bots.config IS 'JSON configuration including contracts, exchanges, parameters';
COMMENT ON COLUMN bots.status IS 'Current bot status: stopped, starting, running, stopping, error';
COMMENT ON COLUMN bot_runs.config_snapshot IS 'Configuration at the time the bot was started';