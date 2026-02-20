-- Rename symbol column to contract in order_executions table
ALTER TABLE order_executions RENAME COLUMN symbol TO contract;