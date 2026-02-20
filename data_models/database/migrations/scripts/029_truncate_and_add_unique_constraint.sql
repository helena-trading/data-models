-- Migration: TRUNCATE order_executions and add UNIQUE constraint (FAST approach)
-- Description: Start fresh with clean data instead of cleaning up 8.6M+ rows with duplicates
-- Version: 029
-- Date: 2025-10-25

DO $$
BEGIN
    RAISE NOTICE 'Migration 029: Starting fresh with order_executions table';

    -- Step 1: TRUNCATE table (instant - removes all rows)
    TRUNCATE TABLE order_executions CASCADE;
    RAISE NOTICE 'TRUNCATED order_executions table - all historical orders removed';

    -- Step 2: Create UNIQUE constraint (instant on empty table)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions'
          AND indexname = 'idx_order_executions_unique_client_order'
    ) THEN
        -- Create partial UNIQUE index (only for non-NULL client_order_id)
        CREATE UNIQUE INDEX idx_order_executions_unique_client_order
        ON order_executions(exchange, client_order_id)
        WHERE client_order_id IS NOT NULL;

        RAISE NOTICE 'Created UNIQUE constraint on (exchange, client_order_id)';
    ELSE
        RAISE NOTICE 'UNIQUE constraint already exists';
    END IF;

    RAISE NOTICE 'Migration 029 completed successfully - table is clean and ready for new orders';

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration 029 failed: %', SQLERRM;
END $$;
