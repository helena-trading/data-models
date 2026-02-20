"""Drop foreign key constraint from bot_health_status table

Reason: bot_health_status is in the analytics database, but the bots table
is in the credentials database. Cross-database foreign keys are not supported
in PostgreSQL. The bot_id column should be a logical reference only.

This migration drops the FK constraint that was mistakenly added in migration 022.

Revision ID: 037
Revises: 036
Create Date: 2025-12-09 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "037"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the FK constraint from bot_health_status."""

    # Drop the foreign key constraint
    op.execute(
        """
        ALTER TABLE bot_health_status
        DROP CONSTRAINT IF EXISTS bot_health_status_bot_id_fkey;
    """
    )

    # Add comment explaining the relationship
    op.execute(
        """
        COMMENT ON COLUMN bot_health_status.bot_id IS
        'Logical reference to bots.id (no FK - cross-database reference to credentials DB)';
    """
    )


def downgrade() -> None:
    """Re-add the FK constraint (not recommended - will fail cross-DB)."""

    # Remove the comment
    op.execute(
        """
        COMMENT ON COLUMN bot_health_status.bot_id IS NULL;
    """
    )

    # Note: Re-adding FK would fail since bots table is in different database
    # This downgrade is intentionally a no-op for the FK
