-- Helena Bot Position History Table (without TimescaleDB)
-- Version: 004
-- Description: Add position history table for tracking position changes over time

-- Create position_history table
CREATE TABLE IF NOT EXISTS position_history (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG, SHORT, NEUTRAL
    position_size DECIMAL(20, 8) NOT NULL,
    entry_price DECIMAL(20, 8),
    mark_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8),
    margin_used DECIMAL(20, 8),
    leverage INTEGER,
    liquidation_price DECIMAL(20, 8),
    event_type VARCHAR(50), -- OPEN, CLOSE, UPDATE, LIQUIDATION
    event_reason TEXT, -- Reason for the position change
    metadata JSONB -- Additional data like order IDs, fees, etc.
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_position_history_exchange_symbol ON position_history (exchange, symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_position_history_time ON position_history (time DESC);
CREATE INDEX IF NOT EXISTS idx_position_history_event_type ON position_history (event_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_position_history_side ON position_history (side, time DESC);

-- Create a view for current positions (latest entry per exchange/symbol)
CREATE OR REPLACE VIEW current_positions AS
WITH latest_positions AS (
    SELECT DISTINCT ON (exchange, symbol)
        *
    FROM position_history
    WHERE position_size != 0
    ORDER BY exchange, symbol, time DESC
)
SELECT * FROM latest_positions;

-- Create a view for position PnL summary
CREATE OR REPLACE VIEW position_pnl_summary AS
SELECT 
    exchange,
    symbol,
    SUM(CASE WHEN event_type = 'CLOSE' THEN realized_pnl ELSE 0 END) as total_realized_pnl,
    SUM(CASE WHEN event_type = 'CLOSE' THEN 1 ELSE 0 END) as closed_positions,
    AVG(CASE WHEN event_type = 'CLOSE' THEN realized_pnl ELSE NULL END) as avg_pnl_per_trade,
    MAX(time) as last_activity
FROM position_history
GROUP BY exchange, symbol;

-- Function to calculate position metrics
CREATE OR REPLACE FUNCTION calculate_position_metrics(
    p_exchange VARCHAR,
    p_symbol VARCHAR,
    p_start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    p_end_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    total_volume DECIMAL,
    total_trades INTEGER,
    win_rate DECIMAL,
    avg_holding_time INTERVAL,
    total_pnl DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUM(ABS(position_size * entry_price)) as total_volume,
        COUNT(DISTINCT CASE WHEN event_type = 'CLOSE' THEN metadata->>'order_id' END)::INTEGER as total_trades,
        (COUNT(CASE WHEN event_type = 'CLOSE' AND realized_pnl > 0 THEN 1 END)::DECIMAL / 
         NULLIF(COUNT(CASE WHEN event_type = 'CLOSE' THEN 1 END), 0))::DECIMAL as win_rate,
        AVG(CASE 
            WHEN event_type = 'CLOSE' AND metadata->>'open_time' IS NOT NULL 
            THEN time - (metadata->>'open_time')::TIMESTAMPTZ 
            ELSE NULL 
        END) as avg_holding_time,
        SUM(CASE WHEN event_type = 'CLOSE' THEN realized_pnl ELSE 0 END)::DECIMAL as total_pnl
    FROM position_history
    WHERE exchange = p_exchange
    AND symbol = p_symbol
    AND time BETWEEN p_start_time AND p_end_time;
END;
$$ LANGUAGE plpgsql;