-- Create user_settings table for storing user preferences
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    -- Live testing preferences
    run_live_tests_before_start BOOLEAN DEFAULT false,
    live_test_efficiency BOOLEAN DEFAULT true,
    live_test_exchange BOOLEAN DEFAULT true,
    live_test_cancel_maker BOOLEAN DEFAULT true,
    live_test_cancel_inverted BOOLEAN DEFAULT false,
    live_test_execution BOOLEAN DEFAULT false,
    
    -- Other user preferences (can be extended)
    theme TEXT DEFAULT 'dark',
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    
    -- Flexible JSON storage for additional settings
    preferences JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create an update trigger for updated_at
CREATE OR REPLACE FUNCTION update_user_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_settings_updated_at_trigger
BEFORE UPDATE ON user_settings
FOR EACH ROW
EXECUTE FUNCTION update_user_settings_updated_at();

-- Insert default settings for a default user (can be customized)
INSERT INTO user_settings (user_id, run_live_tests_before_start) 
VALUES ('default', false)
ON CONFLICT (user_id) DO NOTHING;