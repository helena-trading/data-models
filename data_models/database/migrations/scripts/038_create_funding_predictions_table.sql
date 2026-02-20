-- Migration 038: Create funding predictions table for model validation
-- Tracks funding rate predictions vs actual outcomes to validate
-- the uncertainty-aware pricing model and calibrate parameters.

-- ==============================================================================
-- CREATE TABLE: funding_predictions
-- Stores funding predictions at trade entry and actual outcomes after close
-- ==============================================================================
CREATE TABLE IF NOT EXISTS funding_predictions (
    id SERIAL PRIMARY KEY,

    -- When the prediction was made
    prediction_time TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Identifiers
    exchange VARCHAR(100) NOT NULL,
    contract VARCHAR(50) NOT NULL,
    bot_id INTEGER REFERENCES bots(id) ON DELETE SET NULL,
    trade_id VARCHAR(100),  -- Links to block_trade.block_id if applicable

    -- Prediction inputs
    funding_rate DECIMAL(18, 10) NOT NULL,  -- Rate used for prediction
    time_to_next_hours DECIMAL(10, 4) NOT NULL,  -- Hours to next funding
    interval_hours DECIMAL(10, 4) NOT NULL,  -- Funding interval (1h or 8h)
    horizon_hours DECIMAL(10, 4) NOT NULL,  -- Expected holding time

    -- Prediction outputs
    predicted_crossings INTEGER NOT NULL,  -- Expected funding events
    predicted_pnl_long DECIMAL(18, 10) NOT NULL,  -- Expected PnL for long
    predicted_pnl_short DECIMAL(18, 10) NOT NULL,  -- Expected PnL for short

    -- Uncertainty metrics (for model validation)
    locked_fraction DECIMAL(10, 6) NOT NULL DEFAULT 0,  -- How much rate was locked in
    sigma DECIMAL(18, 10) NOT NULL DEFAULT 0,  -- Uncertainty at prediction time
    buffer DECIMAL(18, 10) NOT NULL DEFAULT 0,  -- Conservative buffer applied

    -- Actual outcomes (updated after position closes)
    actual_crossings INTEGER,  -- Actual funding events crossed
    actual_pnl DECIMAL(18, 10),  -- Actual funding PnL realized
    actual_holding_hours DECIMAL(10, 4),  -- Actual holding time
    position_side VARCHAR(10),  -- 'long' or 'short'

    -- Computed errors (populated when actual values are known)
    crossing_error INTEGER,  -- actual_crossings - predicted_crossings
    pnl_error DECIMAL(18, 10),  -- actual_pnl - predicted_pnl
    pnl_error_pct DECIMAL(10, 6),  -- Error as percentage of prediction

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, completed, error

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- INDEXES for common query patterns
-- ==============================================================================

-- Time-series queries
CREATE INDEX IF NOT EXISTS idx_funding_pred_time
    ON funding_predictions(prediction_time);

-- Exchange+contract queries (most common)
CREATE INDEX IF NOT EXISTS idx_funding_pred_exchange_contract
    ON funding_predictions(exchange, contract);

-- Composite index for time-series by exchange/contract
CREATE INDEX IF NOT EXISTS idx_funding_pred_exchange_contract_time
    ON funding_predictions(exchange, contract, prediction_time);

-- Status filter (for finding pending predictions to update)
CREATE INDEX IF NOT EXISTS idx_funding_pred_status
    ON funding_predictions(status);

-- Bot-specific queries
CREATE INDEX IF NOT EXISTS idx_funding_pred_bot_id
    ON funding_predictions(bot_id)
    WHERE bot_id IS NOT NULL;

-- Trade linkage (for updating after trade closes)
CREATE INDEX IF NOT EXISTS idx_funding_pred_trade_id
    ON funding_predictions(trade_id)
    WHERE trade_id IS NOT NULL;

-- Error analysis queries (find largest prediction errors)
CREATE INDEX IF NOT EXISTS idx_funding_pred_pnl_error
    ON funding_predictions(pnl_error)
    WHERE pnl_error IS NOT NULL;

-- Locked fraction analysis (for validating uncertainty model)
CREATE INDEX IF NOT EXISTS idx_funding_pred_locked_fraction
    ON funding_predictions(locked_fraction);

-- ==============================================================================
-- TRIGGER: Update updated_at timestamp
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_funding_predictions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_funding_predictions_updated_at ON funding_predictions;
CREATE TRIGGER trigger_funding_predictions_updated_at
    BEFORE UPDATE ON funding_predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_funding_predictions_timestamp();

-- ==============================================================================
-- COMMENTS
-- ==============================================================================
COMMENT ON TABLE funding_predictions IS 'Tracks funding rate predictions vs actual outcomes for model validation';
COMMENT ON COLUMN funding_predictions.funding_rate IS 'Funding rate used for prediction (e.g., -0.0047 for -0.47%)';
COMMENT ON COLUMN funding_predictions.locked_fraction IS 'How much of funding rate was locked in (0-1, based on time-weighted averaging)';
COMMENT ON COLUMN funding_predictions.sigma IS 'Uncertainty (σ) at prediction time, used for conservative buffer';
COMMENT ON COLUMN funding_predictions.buffer IS 'Conservative buffer applied (k × σ)';
COMMENT ON COLUMN funding_predictions.pnl_error IS 'Prediction error: actual_pnl - predicted_pnl';
COMMENT ON COLUMN funding_predictions.pnl_error_pct IS 'Prediction error as percentage of prediction';
