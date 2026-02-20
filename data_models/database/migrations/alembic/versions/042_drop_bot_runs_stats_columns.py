"""Drop duplicate stats columns from bot_runs table

Revision ID: 042
Revises: 041
Create Date: 2025-12-15

This migration removes the duplicate statistics columns (total_orders, total_trades,
total_pnl, error_count) from the bot_runs table in the credentials database.

These columns were never being updated because the actual statistics are tracked
in the bot_run_stats table in the analytics database. This caused the API to
always return zeros for historical runs' statistics.

The API has been updated to fetch stats from bot_run_stats for ALL runs,
making these columns redundant.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "042"
down_revision: Union[str, None] = "041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove duplicate stats columns from bot_runs table.

    These columns existed but were never updated - stats are tracked in
    bot_run_stats table in the analytics database.
    """

    # Drop the redundant columns
    op.execute(
        """
        ALTER TABLE bot_runs DROP COLUMN IF EXISTS total_orders;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs DROP COLUMN IF EXISTS total_trades;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs DROP COLUMN IF EXISTS total_pnl;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs DROP COLUMN IF EXISTS error_count;
    """
    )

    # Add a comment to clarify where stats are stored
    op.execute(
        """
        COMMENT ON TABLE bot_runs IS
        'Bot run lifecycle records. Statistics (orders, trades, pnl, errors) are stored in bot_run_stats table in analytics DB.';
    """
    )


def downgrade() -> None:
    """Re-add the stats columns to bot_runs table.

    Note: This will NOT restore any data - the columns will be NULL/default.
    """

    op.execute(
        """
        ALTER TABLE bot_runs ADD COLUMN IF NOT EXISTS total_orders INTEGER DEFAULT 0;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs ADD COLUMN IF NOT EXISTS total_trades INTEGER DEFAULT 0;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs ADD COLUMN IF NOT EXISTS total_pnl DOUBLE PRECISION DEFAULT 0.0;
    """
    )

    op.execute(
        """
        ALTER TABLE bot_runs ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0;
    """
    )
