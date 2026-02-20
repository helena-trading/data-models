-- Migration: Create bot_parameters table for dynamic parameter management
-- Version: 002
-- Date: 2024-12-20

-- Create the bot_parameters table
CREATE TABLE IF NOT EXISTS bot_parameters (
    id SERIAL PRIMARY KEY,
    parameter_name VARCHAR(50) UNIQUE NOT NULL,
    parameter_value JSONB NOT NULL,
    parameter_type VARCHAR(20) NOT NULL CHECK (parameter_type IN ('float', 'int', 'bool', 'string')),
    min_value FLOAT,
    max_value FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    change_reason TEXT,
    previous_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_bot_parameters_name ON bot_parameters(parameter_name);
CREATE INDEX IF NOT EXISTS idx_bot_parameters_updated_at ON bot_parameters(updated_at);

-- Create update trigger to maintain updated_at
CREATE OR REPLACE FUNCTION update_bot_parameters_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bot_parameters_updated_at_trigger
    BEFORE UPDATE ON bot_parameters
    FOR EACH ROW
    EXECUTE FUNCTION update_bot_parameters_updated_at();

-- Create parameter history table for audit trail
CREATE TABLE IF NOT EXISTS bot_parameters_history (
    id SERIAL PRIMARY KEY,
    parameter_name VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bot_parameters_history_name ON bot_parameters_history(parameter_name);
CREATE INDEX IF NOT EXISTS idx_bot_parameters_history_changed_at ON bot_parameters_history(changed_at);

-- Create trigger to log parameter changes
CREATE OR REPLACE FUNCTION log_bot_parameter_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO bot_parameters_history (parameter_name, old_value, new_value, changed_by, change_reason)
    VALUES (NEW.parameter_name, OLD.parameter_value, NEW.parameter_value, NEW.updated_by, NEW.change_reason);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bot_parameters_history_trigger
    AFTER UPDATE ON bot_parameters
    FOR EACH ROW
    WHEN (OLD.parameter_value IS DISTINCT FROM NEW.parameter_value)
    EXECUTE FUNCTION log_bot_parameter_changes();

-- Insert default parameters
INSERT INTO bot_parameters (parameter_name, parameter_value, parameter_type, min_value, max_value, updated_by, change_reason)
VALUES 
    ('target_premium', '0.15', 'float', 0.01, 10.0, 'system', 'Initial setup'),
    ('target_discount', '0.15', 'float', 0.01, 10.0, 'system', 'Initial setup'),
    ('taker_spread', '0.05', 'float', 0.001, 1.0, 'system', 'Initial setup'),
    ('max_target_deviation', '0.01', 'float', 0.001, 0.1, 'system', 'Initial setup'),
    ('accepted_slippage', '0.5', 'float', 0.01, 5.0, 'system', 'Initial setup'),
    ('trade_amt_cap', '300.0', 'float', 10.0, 1000000.0, 'system', 'Initial setup'),
    ('trade_amt_floor', '300.0', 'float', 10.0, 1000000.0, 'system', 'Initial setup'),
    ('min_dist_maker', '100', 'float', 0.001, 10000.0, 'system', 'Initial setup'),
    ('wait_exec', '5000', 'int', 100, 60000, 'system', 'Initial setup'),
    ('taker_latency_timeout', '5000', 'int', 100, 60000, 'system', 'Initial setup'),
    ('maximum_amount_premium', '100000.0', 'float', 100.0, 10000000.0, 'system', 'Initial setup'),
    ('maximum_amount_discount', '100000.0', 'float', 100.0, 10000000.0, 'system', 'Initial setup')
ON CONFLICT (parameter_name) DO NOTHING;

-- Grant permissions (adjust based on your database users)
-- GRANT SELECT, INSERT, UPDATE ON bot_parameters TO helena_bot_user;
-- GRANT SELECT ON bot_parameters_history TO helena_bot_user;
-- GRANT USAGE, SELECT ON SEQUENCE bot_parameters_id_seq TO helena_bot_user;
-- GRANT USAGE, SELECT ON SEQUENCE bot_parameters_history_id_seq TO helena_bot_user;