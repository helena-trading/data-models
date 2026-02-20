-- Migration: Change route_id from INTEGER to VARCHAR in block_trades
-- This allows storing string route identifiers like "graph_main", "graph_unwinder"

-- Step 1: Add new route column as VARCHAR
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS route VARCHAR(50);

-- Step 2: Migrate existing route_id data to route (convert int to string like "route0")
UPDATE block_trades
SET route = 'route' || route_id::text
WHERE route_id IS NOT NULL AND route IS NULL;

-- Step 3: Drop old route_id column
ALTER TABLE block_trades DROP COLUMN IF EXISTS route_id;

-- Step 4: Create index for route queries
DROP INDEX IF EXISTS idx_block_trades_route_id;
CREATE INDEX IF NOT EXISTS idx_block_trades_route ON block_trades(route);

-- Add comment
COMMENT ON COLUMN block_trades.route IS 'Route identifier (e.g., graph_main, graph_unwinder, route0, route1)';
