"""Add indexes for DISTINCT ON latest queries

These indexes optimize the /latest API endpoints that use DISTINCT ON queries
to get the most recent record per group. Without these indexes, PostgreSQL
must scan the entire table and sort, causing 15-30 second response times.

Tables optimized:
- funding_engine_adjustments: DISTINCT ON (exchange, contract)
- funding_engine_spread_impacts: DISTINCT ON (maker_exchange, taker_exchange, contract)
- broker_mark_price_snapshots: DISTINCT ON (exchange, symbol)
- broker_open_interest_snapshots: DISTINCT ON (exchange, symbol)
- broker_volume_snapshots: DISTINCT ON (exchange, symbol)

Expected improvement: 15-30s → <1s for /latest endpoints

Revision ID: 040
Revises: 039
Create Date: 2025-12-13 15:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "040"
down_revision: Union[str, None] = "039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for DISTINCT ON latest queries."""

    # Index for funding_engine_adjustments /latest endpoint
    # Query: DISTINCT ON (exchange, contract) ... ORDER BY exchange, contract, timestamp DESC
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_latest_lookup
            ON funding_engine_adjustments(exchange, contract, timestamp DESC);
    """
    )

    # Index for funding_engine_spread_impacts /latest endpoint
    # Query: DISTINCT ON (maker_exchange, taker_exchange, contract) ... ORDER BY ... timestamp DESC
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_spread_impacts_latest_lookup
            ON funding_engine_spread_impacts(maker_exchange, taker_exchange, contract, timestamp DESC);
    """
    )

    # Index for broker_mark_price_snapshots /latest endpoint
    # Query: DISTINCT ON (exchange, symbol) ... ORDER BY exchange, symbol, snapshot_time DESC
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mark_prices_latest_lookup
            ON broker_mark_price_snapshots(exchange, symbol, snapshot_time DESC);
    """
    )

    # Index for broker_open_interest_snapshots /latest endpoint
    # Query: DISTINCT ON (exchange, symbol) ... ORDER BY exchange, symbol, snapshot_time DESC
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_open_interest_latest_lookup
            ON broker_open_interest_snapshots(exchange, symbol, snapshot_time DESC);
    """
    )

    # Index for broker_volume_snapshots /latest endpoint
    # Query: DISTINCT ON (exchange, symbol) ... ORDER BY exchange, symbol, snapshot_time DESC
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_volume_latest_lookup
            ON broker_volume_snapshots(exchange, symbol, snapshot_time DESC);
    """
    )

    # Add comments
    op.execute(
        """
        COMMENT ON INDEX idx_funding_adj_latest_lookup IS
        'Optimizes DISTINCT ON (exchange, contract) for /funding/adjustments/latest endpoint';
    """
    )
    op.execute(
        """
        COMMENT ON INDEX idx_spread_impacts_latest_lookup IS
        'Optimizes DISTINCT ON (maker_exchange, taker_exchange, contract) for /funding/spread-impacts/latest endpoint';
    """
    )
    op.execute(
        """
        COMMENT ON INDEX idx_mark_prices_latest_lookup IS
        'Optimizes DISTINCT ON (exchange, symbol) for /funding/mark-prices/latest endpoint';
    """
    )


def downgrade() -> None:
    """Remove indexes for DISTINCT ON latest queries."""

    op.execute("DROP INDEX IF EXISTS idx_volume_latest_lookup;")
    op.execute("DROP INDEX IF EXISTS idx_open_interest_latest_lookup;")
    op.execute("DROP INDEX IF EXISTS idx_mark_prices_latest_lookup;")
    op.execute("DROP INDEX IF EXISTS idx_spread_impacts_latest_lookup;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_latest_lookup;")
