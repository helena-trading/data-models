-- Migration 031: Create chat persistence tables
-- Description: Creates tables for storing chat conversations, messages, and user preferences
-- Database: Analytics DB (high-volume chat data)
-- Note: user_id stored as VARCHAR - no FK constraint as users table doesn't exist

-- ============================================================================
-- Table 1: chat_conversations
-- ============================================================================
-- Stores conversation metadata and summaries
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    summary TEXT,
    custom_metadata JSONB DEFAULT '{}' NOT NULL,
    is_archived BOOLEAN DEFAULT FALSE NOT NULL,
    message_count INTEGER DEFAULT 0 NOT NULL
);

-- Indexes for chat_conversations
CREATE INDEX IF NOT EXISTS idx_chat_conv_user_updated ON chat_conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_conv_archived ON chat_conversations(is_archived, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_conv_title_search ON chat_conversations USING gin(to_tsvector('english', title));

-- Trigger for auto-updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_chat_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_conversations_updated_at_trigger
BEFORE UPDATE ON chat_conversations
FOR EACH ROW
EXECUTE FUNCTION update_chat_conversations_updated_at();

-- ============================================================================
-- Table 2: chat_messages
-- ============================================================================
-- Stores individual messages within conversations
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    model VARCHAR(50),
    tokens_used INTEGER,
    custom_metadata JSONB DEFAULT '{}' NOT NULL,
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id)
        REFERENCES chat_conversations(id) ON DELETE CASCADE
);

-- Indexes for chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_msg_conv_time ON chat_messages(conversation_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_chat_msg_content_search ON chat_messages USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_chat_msg_timestamp ON chat_messages(timestamp DESC);

-- ============================================================================
-- Table 3: chat_user_preferences
-- ============================================================================
-- Stores user-specific chat preferences
CREATE TABLE IF NOT EXISTS chat_user_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    default_provider VARCHAR(20) DEFAULT 'claude' NOT NULL,
    max_context_messages INTEGER DEFAULT 50 NOT NULL,
    auto_save BOOLEAN DEFAULT TRUE NOT NULL,
    show_token_usage BOOLEAN DEFAULT TRUE NOT NULL,
    show_tool_details BOOLEAN DEFAULT TRUE NOT NULL,
    conversation_retention_days INTEGER DEFAULT 90 NOT NULL,
    enable_notifications BOOLEAN DEFAULT FALSE NOT NULL,
    preferences JSONB DEFAULT '{}' NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Trigger for auto-updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_chat_user_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_user_preferences_updated_at_trigger
BEFORE UPDATE ON chat_user_preferences
FOR EACH ROW
EXECUTE FUNCTION update_chat_user_preferences_updated_at();

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE chat_conversations IS 'Stores conversation metadata and AI-generated summaries';
COMMENT ON TABLE chat_messages IS 'Stores individual messages within conversations with tool execution data';
COMMENT ON TABLE chat_user_preferences IS 'Stores user-specific chat preferences and settings';

COMMENT ON COLUMN chat_conversations.user_id IS 'User identifier (no FK - users table does not exist)';
COMMENT ON COLUMN chat_conversations.summary IS 'AI-generated summary for context compression (nullable until generated)';
COMMENT ON COLUMN chat_conversations.custom_metadata IS 'Flexible JSON for tags, categories, etc.';
COMMENT ON COLUMN chat_conversations.message_count IS 'Denormalized count for quick filtering (updated by application)';

COMMENT ON COLUMN chat_messages.role IS 'Message sender: user, assistant, or system';
COMMENT ON COLUMN chat_messages.tool_calls IS 'JSONB array of tool executions (for assistant messages)';
COMMENT ON COLUMN chat_messages.model IS 'LLM model used (e.g., claude-3-5-sonnet-20241022)';
COMMENT ON COLUMN chat_messages.tokens_used IS 'Token count for cost tracking';

COMMENT ON COLUMN chat_user_preferences.default_provider IS 'Preferred LLM: claude or openai';
COMMENT ON COLUMN chat_user_preferences.max_context_messages IS 'Context window size (10-100)';
COMMENT ON COLUMN chat_user_preferences.conversation_retention_days IS 'Auto-archive conversations older than N days';
