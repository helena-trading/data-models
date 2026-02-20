"""Add websocket_unhealthy and websocket_failed to check_event_type constraint.

Revision ID: 056
Revises: 055
Create Date: 2026-02-05

The health_reporter generates event_type=f"websocket_{status}" where status
can be "unhealthy" or "failed", but these were missing from the check constraint
added in migration 052. This caused DB insert failures (check_event_type violation)
when WebSocket health changed to unhealthy, which contributed to bot 36 crash
on run 778.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "056"
down_revision: Union[str, None] = "055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add websocket_unhealthy and websocket_failed to check_event_type."""

    # Drop old constraint
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP CONSTRAINT IF EXISTS check_event_type;
        """
    )

    # Re-create with additional event types
    op.execute(
        """
        ALTER TABLE bot_health_status
        ADD CONSTRAINT check_event_type CHECK (
            event_type IN (
                'websocket_disconnected',
                'websocket_error',
                'websocket_reconnected',
                'websocket_unhealthy',
                'websocket_failed',
                'high_rest_ratio',
                'high_error_rate',
                'engine_unhealthy',
                'engine_recovered',
                'unknown'
            )
        );
        """
    )


def downgrade() -> None:
    """Revert to original check_event_type constraint."""

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
