-- Migration: Add has_any_execution flag to order_executions table
-- Description: Boolean flag to identify orders that had any trading activity (filled_quantity > 0)
-- Version: 030
-- Date: 2025-10-27

DO $$
BEGIN
    RAISE NOTICE 'Migration 030: Adding has_any_execution flag to order_executions';

    -- Step 1: Add column with default FALSE
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions'
          AND column_name = 'has_any_execution'
    ) THEN
        ALTER TABLE order_executions
        ADD COLUMN has_any_execution BOOLEAN DEFAULT FALSE NOT NULL;

        RAISE NOTICE 'Added has_any_execution column to order_executions';
    ELSE
        RAISE NOTICE 'Column has_any_execution already exists';
    END IF;

    -- Step 2: Populate existing data
    -- Set TRUE for orders with any fills (filled_quantity > 0)
    UPDATE order_executions
    SET has_any_execution = TRUE
    WHERE filled_quantity IS NOT NULL AND filled_quantity > 0;

    RAISE NOTICE 'Populated has_any_execution for existing orders';

    -- Step 3: Create index for fast filtering
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions'
          AND indexname = 'idx_order_executions_has_execution'
    ) THEN
        CREATE INDEX idx_order_executions_has_execution
        ON order_executions(has_any_execution, time DESC);

        RAISE NOTICE 'Created index idx_order_executions_has_execution';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_has_execution already exists';
    END IF;

    RAISE NOTICE 'Migration 030 completed successfully';

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration 030 failed: %', SQLERRM;
END $$;
