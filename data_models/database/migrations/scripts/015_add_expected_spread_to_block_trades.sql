-- Add expected_spread column to block_trades table for slippage tracking
-- Version: 015
-- Description: Add expected_spread to calculate actual slippage (expected - actual spread)

-- Add expected_spread column to track what spread the bot was targeting
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS expected_spread NUMERIC(20,8);

-- Add maker_fee and taker_fee columns to properly track fees separately
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS maker_fee NUMERIC(20,8);
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS taker_fee NUMERIC(20,8);

-- Add slippage basis points for easier analysis
ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS slippage_bps NUMERIC(10,2);

-- Add comments to document the new columns
COMMENT ON COLUMN block_trades.expected_spread IS 'The spread (price difference) the bot expected to capture when entering the trade';
COMMENT ON COLUMN block_trades.slippage_pct IS 'Percentage slippage: ((expected_spread - spread_captured) / expected_spread) * 100';
COMMENT ON COLUMN block_trades.slippage_bps IS 'Slippage in basis points for easier analysis';
COMMENT ON COLUMN block_trades.maker_fee IS 'Fee paid on the maker exchange';
COMMENT ON COLUMN block_trades.taker_fee IS 'Fee paid on the taker exchange';

-- Create index for slippage analysis
CREATE INDEX IF NOT EXISTS idx_block_trades_slippage ON block_trades(slippage_bps) WHERE slippage_bps IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_block_trades_expected_spread ON block_trades(expected_spread) WHERE expected_spread IS NOT NULL;

-- Update existing records to calculate slippage_bps from slippage_pct if available
UPDATE block_trades 
SET slippage_bps = slippage_pct * 100 
WHERE slippage_pct IS NOT NULL AND slippage_bps IS NULL;