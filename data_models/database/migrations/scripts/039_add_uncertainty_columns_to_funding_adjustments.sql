-- Migration 039: Add uncertainty-aware buffer columns to funding_engine_adjustments
-- These columns capture the dynamic uncertainty metrics from the FundingModel
-- for validation of the uncertainty-aware pricing strategy.

-- ==============================================================================
-- ADD COLUMNS for uncertainty metrics
-- ==============================================================================

-- Locked fraction: How much of the funding rate is "locked in" (0-1)
-- For time-weighted exchanges (Bybit/Binance): uses m(m+1)/M(M+1) formula
-- For simple averaging (Hyperliquid): always 0
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS locked_fraction DECIMAL(10, 6);

-- Sigma: Base uncertainty at prediction time
-- σ = σ_0 × √(1 - locked) for time-weighted exchanges
-- Constant for Hyperliquid
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS sigma DECIMAL(18, 10);

-- Sigma total: Uncertainty scaled by sqrt(num_crossings)
-- For compound uncertainty across multiple funding events
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS sigma_total DECIMAL(18, 10);

-- Buffer: Conservative buffer applied (k × sigma_total)
-- This is subtracted from the funding benefit
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS buffer DECIMAL(18, 10);

-- Whether dynamic uncertainty is enabled (vs static safety_buffer)
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS use_dynamic_uncertainty BOOLEAN DEFAULT TRUE;

-- Number of funding events crossed (from discrete crossing model)
ALTER TABLE funding_engine_adjustments
ADD COLUMN IF NOT EXISTS num_crossings INTEGER DEFAULT 0;

-- ==============================================================================
-- INDEXES for uncertainty analysis
-- ==============================================================================

-- Index for locked_fraction analysis (validating time-weighted model)
CREATE INDEX IF NOT EXISTS idx_funding_adj_locked_fraction
    ON funding_engine_adjustments(locked_fraction);

-- Index for buffer analysis (understanding conservative adjustments)
CREATE INDEX IF NOT EXISTS idx_funding_adj_buffer
    ON funding_engine_adjustments(buffer);

-- Index for num_crossings (understanding funding event impact)
CREATE INDEX IF NOT EXISTS idx_funding_adj_num_crossings
    ON funding_engine_adjustments(num_crossings);

-- Composite index for exchange-specific uncertainty analysis
CREATE INDEX IF NOT EXISTS idx_funding_adj_exchange_uncertainty
    ON funding_engine_adjustments(exchange, locked_fraction, sigma);

-- ==============================================================================
-- COMMENTS
-- ==============================================================================
COMMENT ON COLUMN funding_engine_adjustments.locked_fraction IS 'Fraction of funding rate locked in (0-1), based on time-weighted averaging quirks';
COMMENT ON COLUMN funding_engine_adjustments.sigma IS 'Base uncertainty σ = σ_0 × √(1 - locked) for time-weighted exchanges';
COMMENT ON COLUMN funding_engine_adjustments.sigma_total IS 'Total uncertainty σ_total = σ × √(num_crossings)';
COMMENT ON COLUMN funding_engine_adjustments.buffer IS 'Conservative buffer = k × σ_total, subtracted from funding benefit';
COMMENT ON COLUMN funding_engine_adjustments.use_dynamic_uncertainty IS 'True if using dynamic uncertainty model, False if using static safety_buffer';
COMMENT ON COLUMN funding_engine_adjustments.num_crossings IS 'Number of funding events crossed during holding period';
