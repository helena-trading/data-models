-- Migration: Rename trade_amt/trade_min_amt to trade_amt_cap/trade_amt_floor
-- Version: 015
-- Date: 2025-01-11
-- Description: Renames trading amount parameters for clarity with dynamic sizing feature

-- Rename trade_amt -> trade_amt_cap
UPDATE bot_parameters
SET parameter_name = 'trade_amt_cap'
WHERE parameter_name = 'trade_amt';

-- Rename trade_min_amt -> trade_amt_floor
UPDATE bot_parameters
SET parameter_name = 'trade_amt_floor'
WHERE parameter_name = 'trade_min_amt';

-- Log the migration in history
INSERT INTO bot_parameters_history (parameter_name, old_value, new_value, changed_by, change_reason)
VALUES
    ('trade_amt_cap', NULL, '"renamed from trade_amt"', 'migration', 'Parameter rename for dynamic sizing clarity'),
    ('trade_amt_floor', NULL, '"renamed from trade_min_amt"', 'migration', 'Parameter rename for dynamic sizing clarity');
