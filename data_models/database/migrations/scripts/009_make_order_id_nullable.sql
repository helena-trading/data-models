-- Make order_id nullable in order_executions table
-- This allows orders to be saved when first created, before the exchange assigns an order_id
ALTER TABLE order_executions ALTER COLUMN order_id DROP NOT NULL;