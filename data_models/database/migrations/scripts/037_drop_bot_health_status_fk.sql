-- Migration: Drop foreign key constraint from bot_health_status table
--
-- Reason: bot_health_status is in the analytics database, but the bots table
-- is in the credentials database. Cross-database foreign keys are not supported
-- in PostgreSQL. The bot_id column should be a logical reference only.
--
-- This migration drops the FK constraint that was mistakenly added in migration 022.

-- Drop the foreign key constraint
ALTER TABLE bot_health_status
DROP CONSTRAINT IF EXISTS bot_health_status_bot_id_fkey;

-- Add comment explaining the relationship
COMMENT ON COLUMN bot_health_status.bot_id IS 'Logical reference to bots.id (no FK - cross-database reference to credentials DB)';
