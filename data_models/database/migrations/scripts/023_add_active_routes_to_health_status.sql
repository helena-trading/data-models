-- Migration: Add active routes tracking to bot_health_status table
-- This allows us to track which routes are actively sending orders without parsing logs

-- Add active_routes column to store array of active route names
ALTER TABLE bot_health_status 
ADD COLUMN active_routes TEXT[] DEFAULT '{}';

-- Add route statistics as JSONB for detailed per-route metrics
ALTER TABLE bot_health_status 
ADD COLUMN route_statistics JSONB;

-- Add index for searching by active routes
CREATE INDEX idx_bot_health_status_active_routes ON bot_health_status USING GIN(active_routes);

-- Add comments
COMMENT ON COLUMN bot_health_status.active_routes IS 'Array of route names that are actively sending orders';
COMMENT ON COLUMN bot_health_status.route_statistics IS 'Per-route statistics: orders created, last order time, etc.';

-- Example route_statistics format:
-- {
--   "route1": {
--     "orders_last_minute": 25,
--     "last_order_time": "2024-01-01T12:00:00Z",
--     "is_active": true
--   },
--   "route2": {
--     "orders_last_minute": 0,
--     "last_order_time": "2024-01-01T11:45:00Z",
--     "is_active": false
--   }
-- }