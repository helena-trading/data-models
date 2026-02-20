-- Migration: Fix block_trades maker_side and taker_side columns
-- These columns are not used in the BlockTrade model and should be nullable

-- Make maker_side and taker_side nullable
ALTER TABLE block_trades 
    ALTER COLUMN maker_side DROP NOT NULL,
    ALTER COLUMN taker_side DROP NOT NULL;

-- Add comment to explain why these are nullable
COMMENT ON COLUMN block_trades.maker_side IS 'Legacy column - side information now tracked via buy/sell exchange columns';
COMMENT ON COLUMN block_trades.taker_side IS 'Legacy column - side information now tracked via buy/sell exchange columns';