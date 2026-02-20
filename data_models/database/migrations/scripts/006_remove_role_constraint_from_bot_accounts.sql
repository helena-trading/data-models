-- Migration: Remove role constraint from bot_accounts
-- Description: Allow accounts to be used in different roles across different bots
-- The role field stays to indicate how the account is used in each specific bot

-- Drop the existing unique constraint that prevents an account from being used in different roles
ALTER TABLE bot_accounts DROP CONSTRAINT IF EXISTS bot_role_unique;
ALTER TABLE bot_accounts DROP CONSTRAINT IF EXISTS _bot_role_uc;

-- Add a new unique constraint that prevents duplicate assignments of the same account to the same bot
-- This allows the same account to be used by multiple bots in any role
ALTER TABLE bot_accounts ADD CONSTRAINT bot_account_assignment_unique UNIQUE (bot_id, account_id);

-- Add comment explaining the new constraint
COMMENT ON CONSTRAINT bot_account_assignment_unique ON bot_accounts IS 'Ensures each account can only be assigned once per bot, but allows the same account to be used by multiple bots in any role';