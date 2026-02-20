"""Add event_type column to bot_health_status table

Revision ID: 052
Revises: 051
Create Date: 2026-01-29

Converting from continuous health polling to event-based logging.
The event_type column indicates what triggered the health event:
  - websocket_disconnected: WebSocket connection lost
  - websocket_error: WebSocket error occurred
  - websocket_reconnected: WebSocket recovered
  - high_rest_ratio: REST fallback ratio exceeded 15%
  - high_error_rate: Error rate exceeded threshold
  - engine_unhealthy: Engine status changed to unhealthy
  - engine_recovered: Engine recovered to healthy

Old rows will have event_type = 'unknown' (legacy data from continuous polling)
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "052"
down_revision: Union[str, None] = "051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add event_type column to bot_health_status table."""

    # Add the event_type column with default 'unknown'
    op.execute(
        """
        ALTER TABLE bot_health_status
        ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) NOT NULL DEFAULT 'unknown';
        """
    )

    # Add check constraint for valid event types
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP CONSTRAINT IF EXISTS check_event_type;
        """
    )

    op.execute(
        """
        ALTER TABLE bot_health_status
        ADD CONSTRAINT check_event_type CHECK (
            event_type IN (
                'websocket_disconnected',
                'websocket_error',
                'websocket_reconnected',
                'high_rest_ratio',
                'high_error_rate',
                'engine_unhealthy',
                'engine_recovered',
                'unknown'
            )
        );
        """
    )

    # Create index for efficient event type queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bot_health_status_event_type
        ON bot_health_status (event_type);
        """
    )

    # Drop the unique constraint on (bot_id, reported_at) if exists
    # This was for continuous polling; not needed for event-based logging
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP CONSTRAINT IF EXISTS bot_health_status_bot_id_reported_at_key;
        """
    )

    # Add comment explaining the new event-based architecture
    op.execute(
        """
        COMMENT ON TABLE bot_health_status IS
        'Health events table - logs only when issues occur (event-based, not continuous polling)';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN bot_health_status.event_type IS
        'Type of health event that triggered this log entry';
        """
    )


def downgrade() -> None:
    """Remove event_type column from bot_health_status table."""

    # Drop index
    op.execute(
        """
        DROP INDEX IF EXISTS idx_bot_health_status_event_type;
        """
    )

    # Drop constraint
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP CONSTRAINT IF EXISTS check_event_type;
        """
    )

    # Drop column
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP COLUMN IF EXISTS event_type;
        """
    )

    # Re-add unique constraint (for continuous polling)
    op.execute(
        """
        ALTER TABLE bot_health_status
        ADD CONSTRAINT bot_health_status_bot_id_reported_at_key
        UNIQUE (bot_id, reported_at);
        """
    )
