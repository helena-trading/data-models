"""Create bot_run_stats table in analytics database

This migration creates the bot_run_stats table to store bot run statistics
(orders, trades, PnL) in the analytics database where trade data lives.

This fixes the issue where BotRunUpdate was being sent to analytics DB
but the bot_runs table only existed in credentials DB, causing all
run statistics to remain at zero.

The table uses UPSERT (ON CONFLICT ... DO UPDATE) for efficient incremental
updates as trades occur.

Revision ID: 034
Revises: 033
Create Date: 2025-12-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bot_run_stats table for analytics-side run statistics."""

    # Create the table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_run_stats (
            id SERIAL PRIMARY KEY,
            bot_id INTEGER NOT NULL,
            run_id INTEGER NOT NULL,
            total_orders INTEGER DEFAULT 0,
            total_trades INTEGER DEFAULT 0,
            total_pnl DOUBLE PRECISION DEFAULT 0.0,
            error_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_updated TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Create indexes for efficient queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bot_run_stats_bot_run
        ON bot_run_stats(bot_id, run_id);
    """
    )

    # Unique constraint enables UPSERT (ON CONFLICT ... DO UPDATE)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_run_stats_unique
        ON bot_run_stats(bot_id, run_id);
    """
    )

    # Add table comment
    op.execute(
        """
        COMMENT ON TABLE bot_run_stats IS
        'Bot run statistics stored in analytics DB. Updated via UPSERT on each trade.';
    """
    )

    op.execute(
        """
        COMMENT ON COLUMN bot_run_stats.run_id IS
        'References bot_runs.id in credentials DB (cross-database, no FK constraint)';
    """
    )


def downgrade() -> None:
    """Drop bot_run_stats table.

    Note: This is a destructive operation. All run statistics will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_bot_run_stats_unique;")
    op.execute("DROP INDEX IF EXISTS idx_bot_run_stats_bot_run;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS bot_run_stats;")
