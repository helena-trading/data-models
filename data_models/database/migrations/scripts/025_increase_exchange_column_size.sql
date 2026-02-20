-- Migration: Increase exchange column size to support longer exchange names
-- Description: Change exchange VARCHAR(50) to VARCHAR(250) in account_balances and position_snapshots

-- ============================================================================
-- Part 1: Update account_balances.exchange column
-- ============================================================================

DO $$
BEGIN
    -- Increase exchange column size in account_balances
    ALTER TABLE account_balances ALTER COLUMN exchange TYPE VARCHAR(250);
    RAISE NOTICE 'Increased account_balances.exchange column to VARCHAR(250)';
END $$;

-- ============================================================================
-- Part 2: Update position_snapshots.exchange column
-- ============================================================================

DO $$
BEGIN
    -- Increase exchange column size in position_snapshots
    ALTER TABLE position_snapshots ALTER COLUMN exchange TYPE VARCHAR(250);
    RAISE NOTICE 'Increased position_snapshots.exchange column to VARCHAR(250)';
END $$;

-- ============================================================================
-- Migration complete
-- ============================================================================
