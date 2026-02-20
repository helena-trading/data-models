-- Migration: Increase schema_migrations version column size
-- Description: Migration 024's filename is 55 chars, exceeding VARCHAR(50) limit

-- Increase the version column size to support longer migration filenames
DO $$
BEGIN
    ALTER TABLE schema_migrations ALTER COLUMN version TYPE VARCHAR(255);
    RAISE NOTICE 'Increased schema_migrations.version column to VARCHAR(255)';
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE 'schema_migrations table does not exist yet, will be created with correct size';
    WHEN undefined_column THEN
        RAISE NOTICE 'schema_migrations.version column does not exist yet, will be created with correct size';
END $$;
