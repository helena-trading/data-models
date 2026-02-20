-- Migration: Add bot_id to block_trades table
-- Purpose: Link block trades to the bot that executed them for better tracking and analytics
-- Date: 2025-08-04

-- Add bot_id column to block_trades table
ALTER TABLE block_trades 
ADD COLUMN IF NOT EXISTS bot_id INTEGER REFERENCES bots(id) ON DELETE SET NULL;

-- Create index for efficient queries by bot_id
CREATE INDEX IF NOT EXISTS idx_block_trades_bot_id ON block_trades(bot_id);

-- Add comment explaining the column
COMMENT ON COLUMN block_trades.bot_id IS 'ID of the bot that executed this trade, references bots(id)';