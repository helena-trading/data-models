-- Migration: Add columns for Orders API functionality
-- Description: Adds missing columns to order_executions table to support comprehensive order tracking and querying
-- Version: 027
-- Date: 2025-10-25

DO $$
BEGIN
    -- Add bot_id column (in addition to route_id for clarity and future-proofing)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'bot_id'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN bot_id INTEGER;
        RAISE NOTICE 'Added bot_id column to order_executions';
        -- Note: Skipping backfill to speed up migration. New orders will populate this field.
    ELSE
        RAISE NOTICE 'bot_id column already exists in order_executions';
    END IF;

    -- Add average_fill_price column (tracks average execution price)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'average_fill_price'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN average_fill_price DECIMAL(20, 8);
        RAISE NOTICE 'Added average_fill_price column to order_executions';
        -- Note: Skipping backfill to speed up migration. New orders will populate this field.
    ELSE
        RAISE NOTICE 'average_fill_price column already exists in order_executions';
    END IF;

    -- Add execution_time_ms column (time from order creation to fill)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'execution_time_ms'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN execution_time_ms INTEGER;
        RAISE NOTICE 'Added execution_time_ms column to order_executions';
        -- Note: Skipping backfill to speed up migration. New orders will populate this field.
    ELSE
        RAISE NOTICE 'execution_time_ms column already exists in order_executions';
    END IF;

    -- Add filled_at column (timestamp when order reached FILLED status)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'filled_at'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN filled_at TIMESTAMPTZ;
        RAISE NOTICE 'Added filled_at column to order_executions';
        -- Note: Skipping backfill to speed up migration. New orders will populate this field.
    ELSE
        RAISE NOTICE 'filled_at column already exists in order_executions';
    END IF;

    -- Add cancelled_at column (timestamp when order was cancelled)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'cancelled_at'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN cancelled_at TIMESTAMPTZ;
        RAISE NOTICE 'Added cancelled_at column to order_executions';
        -- Note: Skipping backfill to speed up migration. New orders will populate this field.
    ELSE
        RAISE NOTICE 'cancelled_at column already exists in order_executions';
    END IF;

    -- Add block_id column (link to block_trades for reconciliation)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_executions' AND column_name = 'block_id'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN block_id UUID;
        RAISE NOTICE 'Added block_id column to order_executions';

        -- Note: Foreign key constraint NOT added to avoid migration failures
        -- due to existing NULL values or orphaned references in production data.
        -- The column can still be used for reconciliation queries without the constraint.
        -- Future enhancement: Add FK constraint after data cleanup if needed.
    ELSE
        RAISE NOTICE 'block_id column already exists in order_executions';
    END IF;

    -- Create performance indexes for Orders API queries

    -- Index for bot_id queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions' AND indexname = 'idx_order_executions_bot_id'
    ) THEN
        CREATE INDEX idx_order_executions_bot_id ON order_executions(bot_id);
        RAISE NOTICE 'Created index idx_order_executions_bot_id';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_bot_id already exists';
    END IF;

    -- Composite index for status + time queries (most common query pattern)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions' AND indexname = 'idx_order_executions_status_time'
    ) THEN
        CREATE INDEX idx_order_executions_status_time ON order_executions(status, time DESC);
        RAISE NOTICE 'Created index idx_order_executions_status_time';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_status_time already exists';
    END IF;

    -- Composite index for bot + status + time queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions' AND indexname = 'idx_order_executions_bot_status_time'
    ) THEN
        CREATE INDEX idx_order_executions_bot_status_time ON order_executions(bot_id, status, time DESC);
        RAISE NOTICE 'Created index idx_order_executions_bot_status_time';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_bot_status_time already exists';
    END IF;

    -- Partial index for block_id lookups (only for orders with block_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions' AND indexname = 'idx_order_executions_block_id_partial'
    ) THEN
        CREATE INDEX idx_order_executions_block_id_partial ON order_executions(block_id)
        WHERE block_id IS NOT NULL;
        RAISE NOTICE 'Created partial index idx_order_executions_block_id_partial';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_block_id_partial already exists';
    END IF;

    -- Index for contract queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'order_executions' AND indexname = 'idx_order_executions_contract'
    ) THEN
        CREATE INDEX idx_order_executions_contract ON order_executions(contract);
        RAISE NOTICE 'Created index idx_order_executions_contract';
    ELSE
        RAISE NOTICE 'Index idx_order_executions_contract already exists';
    END IF;

    RAISE NOTICE 'Orders API migration completed successfully';

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Orders API migration failed: %', SQLERRM;
END $$;
