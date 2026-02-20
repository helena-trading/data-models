-- Create reference_prices table for storing latest market mid-prices
-- Used by dashboard for crypto-to-value conversions

CREATE TABLE IF NOT EXISTS reference_prices (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(250) NOT NULL,
    contract VARCHAR(50) NOT NULL,
    price NUMERIC(30, 10) NOT NULL,  -- Mid-price from orderbook (best_bid + best_ask) / 2
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint for latest price lookups and upserts
    CONSTRAINT uq_reference_price_exchange_contract UNIQUE (exchange, contract)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_reference_prices_exchange_contract ON reference_prices(exchange, contract);
CREATE INDEX IF NOT EXISTS idx_reference_prices_timestamp ON reference_prices(timestamp);

-- Create an update trigger for updated_at
CREATE OR REPLACE FUNCTION update_reference_prices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS reference_prices_updated_at_trigger ON reference_prices;
CREATE TRIGGER reference_prices_updated_at_trigger
BEFORE UPDATE ON reference_prices
FOR EACH ROW
EXECUTE FUNCTION update_reference_prices_updated_at();
