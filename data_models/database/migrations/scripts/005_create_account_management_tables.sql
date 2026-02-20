-- Migration: Create account management tables
-- Description: Add tables for managing exchange accounts that can be shared across multiple bots

-- Create accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    credential_ref VARCHAR(200) NOT NULL,
    is_testnet BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create index on exchange for faster lookups
CREATE INDEX IF NOT EXISTS idx_accounts_exchange ON accounts(exchange);
CREATE INDEX IF NOT EXISTS idx_accounts_is_active ON accounts(is_active);

-- Create bot_accounts junction table
CREATE TABLE IF NOT EXISTS bot_accounts (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('maker', 'taker')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure a bot can only have one account per role
    CONSTRAINT bot_role_unique UNIQUE (bot_id, role)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_bot_accounts_bot_id ON bot_accounts(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_accounts_account_id ON bot_accounts(account_id);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE
    ON accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment to tables
COMMENT ON TABLE accounts IS 'Exchange account configurations that can be shared across multiple bots';
COMMENT ON TABLE bot_accounts IS 'Junction table linking bots to their exchange accounts';

-- Add comments to columns
COMMENT ON COLUMN accounts.name IS 'Unique human-readable name for the account';
COMMENT ON COLUMN accounts.exchange IS 'Exchange identifier (hyperliquid, bybit, binance, etc.)';
COMMENT ON COLUMN accounts.account_type IS 'Type of account (spot, futures, perpetual, inverse)';
COMMENT ON COLUMN accounts.credential_ref IS 'Reference to credentials (env var name or AWS secret path)';
COMMENT ON COLUMN accounts.is_testnet IS 'Whether this is a testnet account';
COMMENT ON COLUMN accounts.is_active IS 'Whether this account is active and can be used';
COMMENT ON COLUMN accounts.description IS 'Optional description of the account';

COMMENT ON COLUMN bot_accounts.role IS 'Role of the account in the bot strategy (maker or taker)';