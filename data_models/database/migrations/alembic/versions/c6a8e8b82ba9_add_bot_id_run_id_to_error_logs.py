"""add_bot_id_run_id_to_error_logs

Revision ID: c6a8e8b82ba9
Revises: 040
Create Date: 2025-12-13 18:39:03.371021

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6a8e8b82ba9"
down_revision: Union[str, None] = "040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, create the error_logs table if it doesn't exist (from script 003)
    # This handles the case where the table was never created via Alembic
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS error_logs (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            level VARCHAR(20) NOT NULL,
            exchange VARCHAR(50),
            component VARCHAR(100) NOT NULL,
            error_type VARCHAR(100),
            message TEXT NOT NULL,
            traceback TEXT,
            context JSONB,
            route_id INTEGER,
            order_id BIGINT,
            resolved BOOLEAN DEFAULT FALSE,
            resolution_notes TEXT
        );
    """
    )

    # Create original indexes if table was just created
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_error_logs_level_time ON error_logs (level, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_exchange_time ON error_logs (exchange, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_component_time ON error_logs (component, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs (error_type, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_unresolved ON error_logs (time DESC) WHERE resolved = FALSE;
    """
    )

    # Add bot_id and run_id columns to error_logs table
    op.execute(
        """
        ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS bot_id INTEGER;
        ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS run_id INTEGER;
    """
    )

    # Create indexes for efficient querying by bot_id and run_id
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_error_logs_bot_id_time ON error_logs (bot_id, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_run_id_time ON error_logs (run_id, time DESC);
        CREATE INDEX IF NOT EXISTS idx_error_logs_bot_run ON error_logs (bot_id, run_id, time DESC);
    """
    )

    # Update the recent_unresolved_errors view to include bot_id and run_id
    op.execute(
        """
        DROP VIEW IF EXISTS recent_unresolved_errors;
        CREATE VIEW recent_unresolved_errors AS
        SELECT
            time,
            level,
            exchange,
            component,
            error_type,
            message,
            context->>'order_id' as order_id,
            context->>'contract' as contract,
            bot_id,
            run_id
        FROM error_logs
        WHERE resolved = FALSE
        AND time > NOW() - INTERVAL '24 hours'
        ORDER BY time DESC;
    """
    )


def downgrade() -> None:
    # Recreate original view without bot_id and run_id
    op.execute(
        """
        DROP VIEW IF EXISTS recent_unresolved_errors;
        CREATE VIEW recent_unresolved_errors AS
        SELECT
            time,
            level,
            exchange,
            component,
            error_type,
            message,
            context->>'order_id' as order_id,
            context->>'contract' as contract
        FROM error_logs
        WHERE resolved = FALSE
        AND time > NOW() - INTERVAL '24 hours'
        ORDER BY time DESC;
    """
    )

    # Drop indexes
    op.execute(
        """
        DROP INDEX IF EXISTS idx_error_logs_bot_run;
        DROP INDEX IF EXISTS idx_error_logs_run_id_time;
        DROP INDEX IF EXISTS idx_error_logs_bot_id_time;
    """
    )

    # Drop columns
    op.execute(
        """
        ALTER TABLE error_logs DROP COLUMN IF EXISTS run_id;
        ALTER TABLE error_logs DROP COLUMN IF EXISTS bot_id;
    """
    )
