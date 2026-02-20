-- Migration: Add spread metrics cache table
-- Purpose: Cache expensive spread metric calculations for API performance
-- Author: Helena Bot Core
-- Date: 2024-12-19

-- Create spread metrics cache table
CREATE TABLE IF NOT EXISTS spread_metrics_cache (
    id SERIAL PRIMARY KEY,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exchange_pair VARCHAR(100) NOT NULL,
    contract VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,  -- '1h', '24h', '7d'
    metric_type VARCHAR(50) NOT NULL, -- 'distribution', 'volatility', 'mean_reversion', 'opportunity'

    -- Cached results (JSONB for flexibility)
    metrics JSONB NOT NULL,

    -- Cache control
    ttl_seconds INTEGER NOT NULL DEFAULT 300,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint to prevent duplicate cache entries
    UNIQUE(exchange_pair, contract, timeframe, metric_type)
);

-- Index for cache lookups
CREATE INDEX idx_spread_metrics_cache_lookup
ON spread_metrics_cache(exchange_pair, contract, expires_at);

-- Index for cache cleanup
CREATE INDEX idx_spread_metrics_cache_expiry
ON spread_metrics_cache(expires_at);

-- Index for metric type queries
CREATE INDEX idx_spread_metrics_cache_type
ON spread_metrics_cache(metric_type, expires_at);

-- Add comment to table
COMMENT ON TABLE spread_metrics_cache IS 'Cache for expensive spread metric calculations with TTL support';

-- Add comments to columns
COMMENT ON COLUMN spread_metrics_cache.exchange_pair IS 'Exchange pair in format "exchange1:exchange2"';
COMMENT ON COLUMN spread_metrics_cache.contract IS 'Trading contract (e.g., BTC_USDT)';
COMMENT ON COLUMN spread_metrics_cache.timeframe IS 'Analysis timeframe (1h, 24h, 7d, etc.)';
COMMENT ON COLUMN spread_metrics_cache.metric_type IS 'Type of metric cached (distribution, volatility, mean_reversion, opportunity)';
COMMENT ON COLUMN spread_metrics_cache.metrics IS 'JSONB containing calculated metrics';
COMMENT ON COLUMN spread_metrics_cache.ttl_seconds IS 'Time to live in seconds';
COMMENT ON COLUMN spread_metrics_cache.expires_at IS 'Timestamp when cache entry expires';

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_spread_metrics_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER spread_metrics_cache_updated_at
    BEFORE UPDATE ON spread_metrics_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_spread_metrics_cache_updated_at();

-- Create function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_spread_metrics_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM spread_metrics_cache
    WHERE expires_at <= CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Add comment to cleanup function
COMMENT ON FUNCTION cleanup_expired_spread_metrics_cache() IS 'Removes expired cache entries from spread_metrics_cache table';