"""Add run_id to block_trades table

Revision ID: 045
Revises: 044
Create Date: 2025-12-18

This migration adds run_id column to the block_trades table to enable
filtering trades by specific bot run sessions.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "045"
down_revision: Union[str, None] = "044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_id column and indexes to block_trades table."""

    # Add run_id column to block_trades table
    op.execute(
        """
        ALTER TABLE block_trades
            ADD COLUMN IF NOT EXISTS run_id INTEGER;
        """
    )

    # Create index for efficient filtering by run_id
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_block_trades_run_id ON block_trades(run_id);
        """
    )

    # Create composite index for bot_id + run_id queries (common filter pattern)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_block_trades_bot_run ON block_trades(bot_id, run_id);
        """
    )

    # Add comment to document the column
    op.execute(
        """
        COMMENT ON COLUMN block_trades.run_id IS 'References bot_runs.id - identifies which bot run session created this trade';
        """
    )


def downgrade() -> None:
    """Remove run_id column and related indexes from block_trades table."""

    # Drop indexes first
    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_bot_run;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_run_id;
        """
    )

    # Drop column
    op.execute(
        """
        ALTER TABLE block_trades DROP COLUMN IF EXISTS run_id;
        """
    )
