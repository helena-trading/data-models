-- Migration: Add route_id column to order_executions table
-- This migration adds the missing route_id column that is required for tracking which route executed the order

-- Add route_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'order_executions' 
        AND column_name = 'route_id'
    ) THEN
        ALTER TABLE order_executions ADD COLUMN route_id INTEGER;
        
        -- Add index for better query performance
        CREATE INDEX idx_order_executions_route_id ON order_executions(route_id);
        
        RAISE NOTICE 'Added route_id column to order_executions table';
    ELSE
        RAISE NOTICE 'route_id column already exists in order_executions table';
    END IF;
END $$;