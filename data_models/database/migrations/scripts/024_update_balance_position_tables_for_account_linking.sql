-- Migration: Update balance and position tables for account linking
-- Description: Add account_id foreign keys and update schema to match SQLAlchemy models

-- ============================================================================
-- Part 0: Increase exchange column size to support longer exchange names
-- ============================================================================

-- CRITICAL: Must increase column size BEFORE any other operations to prevent
-- "value too long for type character varying(50)" errors with test data

-- Increase accounts table exchange column first (referenced by foreign keys)
DO $$
BEGIN
    ALTER TABLE accounts ALTER COLUMN exchange TYPE VARCHAR(250);
    RAISE NOTICE 'Increased accounts.exchange column to VARCHAR(250)';
END $$;

DO $$
BEGIN
    ALTER TABLE account_balances ALTER COLUMN exchange TYPE VARCHAR(250);
    RAISE NOTICE 'Increased account_balances.exchange column to VARCHAR(250)';
END $$;

DO $$
BEGIN
    ALTER TABLE position_snapshots ALTER COLUMN exchange TYPE VARCHAR(250);
    RAISE NOTICE 'Increased position_snapshots.exchange column to VARCHAR(250)';
END $$;

-- ============================================================================
-- Part 1: Update account_balances table
-- ============================================================================

-- Add account_id foreign key column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'account_id'
    ) THEN
        ALTER TABLE account_balances
        ADD COLUMN account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added account_id column to account_balances';
    ELSE
        RAISE NOTICE 'Column account_id already exists in account_balances';
    END IF;
END $$;

-- Rename currency to asset if needed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'currency'
    ) THEN
        ALTER TABLE account_balances RENAME COLUMN currency TO asset;
        RAISE NOTICE 'Renamed currency column to asset in account_balances';
    ELSE
        RAISE NOTICE 'Column currency already renamed or does not exist';
    END IF;
END $$;

-- Rename free_balance to available if needed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'free_balance'
    ) THEN
        ALTER TABLE account_balances RENAME COLUMN free_balance TO available;
        RAISE NOTICE 'Renamed free_balance column to available in account_balances';
    END IF;
END $$;

-- Rename locked_balance to allocated if needed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'locked_balance'
    ) THEN
        ALTER TABLE account_balances RENAME COLUMN locked_balance TO allocated;
        RAISE NOTICE 'Renamed locked_balance column to allocated in account_balances';
    END IF;
END $$;

-- Rename total_balance to balance if needed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'total_balance'
    ) THEN
        ALTER TABLE account_balances RENAME COLUMN total_balance TO balance;
        RAISE NOTICE 'Renamed total_balance column to balance in account_balances';
    END IF;
END $$;

-- Add usd_value column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'usd_value'
    ) THEN
        ALTER TABLE account_balances
        ADD COLUMN usd_value NUMERIC(30, 10);
        RAISE NOTICE 'Added usd_value column to account_balances';
    END IF;
END $$;

-- Add updated_at column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_balances' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE account_balances
        ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added updated_at column to account_balances';
    END IF;
END $$;

-- Add trigger for updated_at
DROP TRIGGER IF EXISTS update_account_balances_updated_at ON account_balances;
CREATE TRIGGER update_account_balances_updated_at BEFORE UPDATE
    ON account_balances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Drop old indexes
DROP INDEX IF EXISTS idx_account_balances_exchange;
DROP INDEX IF EXISTS idx_account_balances_time;

-- Create new indexes for account_balances
CREATE INDEX IF NOT EXISTS idx_account_balances_time ON account_balances(time DESC);
CREATE INDEX IF NOT EXISTS idx_account_balances_exchange ON account_balances(exchange);
CREATE INDEX IF NOT EXISTS idx_account_balances_asset ON account_balances(asset);
CREATE INDEX IF NOT EXISTS idx_account_balances_account_time ON account_balances(account_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_account_balances_exchange_asset ON account_balances(exchange, asset);
CREATE INDEX IF NOT EXISTS idx_account_balances_account_asset ON account_balances(account_id, asset);

-- Add comments
COMMENT ON TABLE account_balances IS 'Account balance snapshots for tracking balance changes over time';
COMMENT ON COLUMN account_balances.account_id IS 'Foreign key to accounts table (NULL for legacy records)';
COMMENT ON COLUMN account_balances.time IS 'Timestamp when balance snapshot was taken';
COMMENT ON COLUMN account_balances.exchange IS 'Exchange identifier';
COMMENT ON COLUMN account_balances.asset IS 'Currency/asset symbol (BTC, ETH, USDT, etc.)';
COMMENT ON COLUMN account_balances.balance IS 'Total balance for this asset';
COMMENT ON COLUMN account_balances.usd_value IS 'USD equivalent value of balance';
COMMENT ON COLUMN account_balances.allocated IS 'Allocated/locked balance not available for trading';
COMMENT ON COLUMN account_balances.available IS 'Available balance for trading';

-- ============================================================================
-- Part 2: Update position_snapshots table
-- ============================================================================

-- Add account_id foreign key column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'position_snapshots' AND column_name = 'account_id'
    ) THEN
        ALTER TABLE position_snapshots
        ADD COLUMN account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added account_id column to position_snapshots';
    ELSE
        RAISE NOTICE 'Column account_id already exists in position_snapshots';
    END IF;
END $$;

-- Ensure contract column exists (should have been renamed in migration 016)
-- This is a safety check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'position_snapshots' AND column_name = 'symbol'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'position_snapshots' AND column_name = 'contract'
    ) THEN
        ALTER TABLE position_snapshots RENAME COLUMN symbol TO contract;
        RAISE NOTICE 'Renamed symbol column to contract in position_snapshots';
    END IF;
END $$;

-- Add updated_at column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'position_snapshots' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE position_snapshots
        ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added updated_at column to position_snapshots';
    END IF;
END $$;

-- Add trigger for updated_at
DROP TRIGGER IF EXISTS update_position_snapshots_updated_at ON position_snapshots;
CREATE TRIGGER update_position_snapshots_updated_at BEFORE UPDATE
    ON position_snapshots FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Ensure notional_value column exists (should have been added in migration 019)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'position_snapshots' AND column_name = 'notional_value'
    ) THEN
        ALTER TABLE position_snapshots
        ADD COLUMN notional_value NUMERIC(30, 10);
        RAISE NOTICE 'Added notional_value column to position_snapshots';
    END IF;
END $$;

-- Drop old indexes
DROP INDEX IF EXISTS idx_position_snapshots_exchange_symbol;
DROP INDEX IF EXISTS idx_position_snapshots_exchange_contract;
DROP INDEX IF EXISTS idx_position_snapshots_time;

-- Create new indexes for position_snapshots
CREATE INDEX IF NOT EXISTS idx_position_snapshots_time ON position_snapshots(time DESC);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange ON position_snapshots(exchange);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_contract ON position_snapshots(contract);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_time ON position_snapshots(account_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_exchange_contract ON position_snapshots(exchange, contract);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_contract ON position_snapshots(account_id, contract);

-- Add comments
COMMENT ON TABLE position_snapshots IS 'Position snapshots for tracking open positions over time';
COMMENT ON COLUMN position_snapshots.account_id IS 'Foreign key to accounts table (NULL for legacy records)';
COMMENT ON COLUMN position_snapshots.time IS 'Timestamp when position snapshot was taken';
COMMENT ON COLUMN position_snapshots.exchange IS 'Exchange identifier';
COMMENT ON COLUMN position_snapshots.contract IS 'Contract/symbol identifier';
COMMENT ON COLUMN position_snapshots.position_size IS 'Position size (positive for long, negative for short)';
COMMENT ON COLUMN position_snapshots.mark_price IS 'Current mark price of the contract';
COMMENT ON COLUMN position_snapshots.notional_value IS 'Notional value of position (size * mark_price)';
COMMENT ON COLUMN position_snapshots.unrealized_pnl IS 'Unrealized profit/loss';
COMMENT ON COLUMN position_snapshots.margin_used IS 'Margin used for this position';
COMMENT ON COLUMN position_snapshots.entry_price IS 'Average entry price';
COMMENT ON COLUMN position_snapshots.liquidation_price IS 'Liquidation price';

-- ============================================================================
-- Migration complete
-- ============================================================================
