"""Add database indexes for analytics query performance.

This migration adds indexes to the block_trades table to optimize
analytics queries. These indexes significantly improve query performance
for the analytics endpoints used by the MCP server and dashboard.

Indexes added:
- idx_block_trades_time: For date range queries
- idx_block_trades_bot_id: For bot-specific filtering
- idx_block_trades_lifecycle_state: For completed trades filtering
- idx_block_trades_contract: For contract grouping
- idx_block_trades_time_lifecycle: Composite index for common query pattern

Expected performance improvement:
- Typical analytics queries: < 5 seconds (down from 30+ seconds)
- Large date range queries (30 days): < 10 seconds
"""

from alembic import op


def upgrade() -> None:
    """Add analytics indexes to block_trades table."""
    # Index on time column for date range queries
    # Used by: block-trades, performance-summary, daily-breakdown
    op.create_index(
        "idx_block_trades_time", "block_trades", ["time"], unique=False, postgresql_concurrently=True, if_not_exists=True
    )

    # Index on bot_id for bot-specific queries
    # Used by: block-trades with bot_id filter
    op.create_index(
        "idx_block_trades_bot_id", "block_trades", ["bot_id"], unique=False, postgresql_concurrently=True, if_not_exists=True
    )

    # Index on lifecycle_state for filtering completed trades
    # Used by: performance-summary, daily-breakdown
    op.create_index(
        "idx_block_trades_lifecycle_state",
        "block_trades",
        ["lifecycle_state"],
        unique=False,
        postgresql_concurrently=True,
        if_not_exists=True,
    )

    # Index on contract for grouping and filtering
    # Used by: comprehensive-metrics, daily-breakdown
    op.create_index(
        "idx_block_trades_contract",
        "block_trades",
        ["contract"],
        unique=False,
        postgresql_concurrently=True,
        if_not_exists=True,
    )

    # Composite index for the most common query pattern:
    # WHERE time >= :start_date AND lifecycle_state = 'completed'
    # This is used by both performance-summary and daily-breakdown
    op.create_index(
        "idx_block_trades_time_lifecycle",
        "block_trades",
        ["time", "lifecycle_state"],
        unique=False,
        postgresql_concurrently=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove analytics indexes from block_trades table."""
    op.drop_index("idx_block_trades_time_lifecycle", table_name="block_trades", postgresql_concurrently=True, if_exists=True)
    op.drop_index("idx_block_trades_contract", table_name="block_trades", postgresql_concurrently=True, if_exists=True)
    op.drop_index("idx_block_trades_lifecycle_state", table_name="block_trades", postgresql_concurrently=True, if_exists=True)
    op.drop_index("idx_block_trades_bot_id", table_name="block_trades", postgresql_concurrently=True, if_exists=True)
    op.drop_index("idx_block_trades_time", table_name="block_trades", postgresql_concurrently=True, if_exists=True)
