-- Migration 025: create private-data-hub tables

CREATE TABLE IF NOT EXISTS private_data_hubs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    process_type VARCHAR(80) NOT NULL DEFAULT 'private_data_hub',
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS private_data_hub_accounts (
    id SERIAL PRIMARY KEY,
    hub_id INTEGER NOT NULL REFERENCES private_data_hubs(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    contracts JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_private_data_hub_account UNIQUE (hub_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_private_data_hub_accounts_hub_id
    ON private_data_hub_accounts (hub_id);

CREATE INDEX IF NOT EXISTS idx_private_data_hub_accounts_account_id
    ON private_data_hub_accounts (account_id);
