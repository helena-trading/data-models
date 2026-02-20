"""Add tags JSONB column to bots table

Revision ID: 054
Revises: 053
Create Date: 2026-02-04

Adds a tags JSONB column to the bots table for manual grouping/clustering.
Tags are simple string labels stored as a JSON array, with a GIN index
for efficient containment queries (e.g., WHERE tags @> '["prod"]').
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "054"
down_revision: Union[str, None] = "053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tags column and GIN index to bots table."""

    op.execute(
        """
        ALTER TABLE bots
        ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]';
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bots_tags_gin
        ON bots USING GIN (tags);
        """
    )


def downgrade() -> None:
    """Remove tags column and GIN index from bots table."""

    op.execute(
        """
        DROP INDEX IF EXISTS idx_bots_tags_gin;
        """
    )

    op.execute(
        """
        ALTER TABLE bots DROP COLUMN IF EXISTS tags;
        """
    )
