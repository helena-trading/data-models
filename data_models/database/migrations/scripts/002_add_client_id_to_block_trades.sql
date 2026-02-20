-- Add client_id column to block_trades table
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS client_id VARCHAR(100);

-- Create index for client_id lookups
CREATE INDEX IF NOT EXISTS idx_block_trades_client_id ON block_trades (client_id, time DESC);