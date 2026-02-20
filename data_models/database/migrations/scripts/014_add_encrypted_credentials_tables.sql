-- Migration: Add encrypted credentials tables
-- Description: Adds tables for storing encrypted API credentials with audit logging
-- Date: 2024-01-15

-- Add credential storage type to accounts table
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS credential_storage_type VARCHAR(20) DEFAULT 'reference';
-- Values: 'reference' (env var), 'encrypted' (database)

-- Create table for encrypted credentials
CREATE TABLE IF NOT EXISTS encrypted_credentials (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    credential_type VARCHAR(50) NOT NULL, -- 'api_key', 'api_secret', 'passphrase'
    encrypted_value TEXT NOT NULL,
    encryption_metadata JSONB NOT NULL, -- {algorithm, key_id, iv, auth_tag, version}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    UNIQUE(account_id, credential_type)
);

-- Create index for faster lookups
CREATE INDEX idx_encrypted_credentials_account_id ON encrypted_credentials(account_id);
CREATE INDEX idx_encrypted_credentials_last_accessed ON encrypted_credentials(last_accessed_at);

-- Create audit log table for credential access
CREATE TABLE IF NOT EXISTS credential_audit_log (
    id SERIAL PRIMARY KEY,
    credential_id INTEGER REFERENCES encrypted_credentials(id) ON DELETE SET NULL,
    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL, -- 'create', 'read', 'update', 'delete', 'rotate'
    bot_id INTEGER REFERENCES bots(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB -- Additional context like key rotation info
);

-- Create indexes for audit log queries
CREATE INDEX idx_credential_audit_log_timestamp ON credential_audit_log(timestamp);
CREATE INDEX idx_credential_audit_log_account_id ON credential_audit_log(account_id);
CREATE INDEX idx_credential_audit_log_bot_id ON credential_audit_log(bot_id);
CREATE INDEX idx_credential_audit_log_action ON credential_audit_log(action);

-- Add comments for documentation
COMMENT ON TABLE encrypted_credentials IS 'Stores encrypted API credentials for exchange accounts';
COMMENT ON COLUMN encrypted_credentials.credential_type IS 'Type of credential: api_key, api_secret, or passphrase';
COMMENT ON COLUMN encrypted_credentials.encrypted_value IS 'AES-256-GCM encrypted credential value';
COMMENT ON COLUMN encrypted_credentials.encryption_metadata IS 'Metadata needed for decryption: algorithm, key_id, iv, auth_tag, version';

COMMENT ON TABLE credential_audit_log IS 'Audit trail for all credential access and modifications';
COMMENT ON COLUMN credential_audit_log.action IS 'Action performed: create, read, update, delete, or rotate';
COMMENT ON COLUMN credential_audit_log.metadata IS 'Additional context about the action, such as rotation details';

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_encrypted_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update the updated_at column
CREATE TRIGGER encrypted_credentials_updated_at_trigger
BEFORE UPDATE ON encrypted_credentials
FOR EACH ROW
EXECUTE FUNCTION update_encrypted_credentials_updated_at();