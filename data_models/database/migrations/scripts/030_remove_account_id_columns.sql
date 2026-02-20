-- Migration 030: Remove account_id columns from analytics tables
-- Part of dual-database segregation project
--
-- CRITICAL: Run this AFTER data migration is complete and validated
--
-- This migration:
-- 1. Drops account_id column from position_snapshots (analytics DB)
-- 2. Drops account_id column from account_balances (analytics DB)
-- 3. Drops associated indexes
-- 4. Converts bot_id FK to plain integer in credential_audit_log (credentials DB)
--
-- IMPORTANT: This is a destructive migration
-- Ensure backups exist before running

-- =============================================================================
-- ANALYTICS DATABASE CHANGES
-- =============================================================================

-- Drop indexes that reference account_id in position_snapshots
DROP INDEX IF EXISTS idx_position_snapshots_account_time;
DROP INDEX IF EXISTS idx_position_snapshots_account_contract;

-- Drop account_id column from position_snapshots
ALTER TABLE position_snapshots DROP COLUMN IF EXISTS account_id;

-- Add new indexes for exchange-based queries
CREATE INDEX IF NOT EXISTS idx_position_snapshots_time ON position_snapshots(time);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange_time ON position_snapshots(exchange, time);

-- Drop indexes that reference account_id in account_balances
DROP INDEX IF EXISTS idx_account_balances_account_time;
DROP INDEX IF EXISTS idx_account_balances_account_asset;

-- Drop account_id column from account_balances
ALTER TABLE account_balances DROP COLUMN IF EXISTS account_id;

-- Add new indexes for exchange-based queries
CREATE INDEX IF NOT EXISTS idx_account_balances_time ON account_balances(time);
CREATE INDEX IF NOT EXISTS idx_account_balances_exchange_time ON account_balances(exchange, time);

-- =============================================================================
-- CREDENTIALS DATABASE CHANGES
-- =============================================================================

-- Convert bot_id from foreign key to plain integer in credential_audit_log
-- Drop the foreign key constraint
ALTER TABLE credential_audit_log DROP CONSTRAINT IF EXISTS credential_audit_log_bot_id_fkey;

-- Column remains as Integer (no need to modify, just remove FK constraint)
-- bot_id is already nullable, so no change needed

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Run these after migration to verify success:

-- Analytics DB verification:
-- SELECT table_name, column_name FROM information_schema.columns
-- WHERE table_name IN ('position_snapshots', 'account_balances')
-- AND column_name = 'account_id';
-- Expected: 0 rows

-- Credentials DB verification:
-- SELECT constraint_name FROM information_schema.table_constraints
-- WHERE table_name = 'credential_audit_log'
-- AND constraint_type = 'FOREIGN KEY'
-- AND constraint_name LIKE '%bot_id%';
-- Expected: 0 rows

-- Index verification (Analytics DB):
-- SELECT indexname FROM pg_indexes
-- WHERE tablename IN ('position_snapshots', 'account_balances')
-- ORDER BY tablename, indexname;
-- Expected: New exchange-based indexes, no account_id indexes
