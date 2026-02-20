-- Migration: Create bot_run_stats table in analytics database
-- Purpose: Store bot run statistics (orders, trades, PnL) in analytics DB
--          to fix issue where stats were being sent to wrong database

CREATE TABLE IF NOT EXISTS bot_run_stats (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,           -- References bot_runs.id in credentials DB (no FK, cross-DB)
    total_orders INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    total_pnl DOUBLE PRECISION DEFAULT 0.0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Primary lookup: by bot_id and run_id (both needed for API queries)
CREATE INDEX IF NOT EXISTS idx_bot_run_stats_bot_run ON bot_run_stats(bot_id, run_id);

-- Unique constraint: one stats row per bot run (enables UPSERT)
CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_run_stats_unique ON bot_run_stats(bot_id, run_id);

-- Comment on table
COMMENT ON TABLE bot_run_stats IS 'Bot run statistics stored in analytics DB. Updated via UPSERT on each trade.';
COMMENT ON COLUMN bot_run_stats.run_id IS 'References bot_runs.id in credentials DB (cross-database, no FK constraint)';
