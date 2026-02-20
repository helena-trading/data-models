-- Migration: Add UNIQUE constraint to order_executions and clean up duplicates
-- Description: Prevents duplicate order recording by enforcing uniqueness at database level
-- Version: 028
-- Date: 2025-10-25

DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    -- Step 1: Count existing duplicates for reporting
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT client_order_id, exchange, COUNT(*) as cnt
        FROM order_executions
        WHERE client_order_id IS NOT NULL
        GROUP BY client_order_id, exchange
        HAVING COUNT(*) > 1
    ) AS duplicates;

    RAISE NOTICE 'Found % orders with duplicates based on (exchange, client_order_id)', duplicate_count;

    -- Step 2: Delete duplicate rows, keeping the NEWEST (highest id) for each (exchange, client_order_id)
    -- This ensures we keep the most recent/complete record
    IF duplicate_count > 0 THEN
        WITH duplicates_to_delete AS (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY exchange, client_order_id ORDER BY id DESC) as rn
                FROM order_executions
                WHERE client_order_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        DELETE FROM order_executions
        WHERE id IN (SELECT id FROM duplicates_to_delete);

        GET DIAGNOSTICS duplicate_count = ROW_COUNT;
        RAISE NOTICE 'Deleted % duplicate order execution records', duplicate_count;
    ELSE
        RAISE NOTICE 'No duplicates found - table is clean';
    END IF;

    -- Step 3: Create UNIQUE constraint if it doesn't exist
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

    RAISE NOTICE 'Migration 028 completed successfully';

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration 028 failed: %', SQLERRM;
END $$;
