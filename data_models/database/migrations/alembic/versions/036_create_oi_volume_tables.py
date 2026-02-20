"""Create Open Interest and Volume snapshot tables

This migration creates:
1. broker_open_interest_snapshots - Store OI data from exchanges
2. broker_volume_snapshots - Store 24h volume data from exchanges

These tables enable the /api/v1/funding/adjustments/latest endpoint to return
open_interest and volume_24h data for funding engine visualization.

Revision ID: 036
Revises: 035
Create Date: 2025-12-04 15:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create OI and Volume snapshot tables."""

    # 1. Create broker_open_interest_snapshots table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS broker_open_interest_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_time TIMESTAMPTZ NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            open_interest NUMERIC(30, 8),
            open_interest_value NUMERIC(30, 2),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for broker_open_interest_snapshots
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_oi_snapshot_time
        ON broker_open_interest_snapshots(snapshot_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_oi_exchange_symbol
        ON broker_open_interest_snapshots(exchange, symbol);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_oi_exchange_time
        ON broker_open_interest_snapshots(exchange, snapshot_time DESC);
    """
    )

    # 2. Create broker_volume_snapshots table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS broker_volume_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_time TIMESTAMPTZ NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            volume_24h NUMERIC(30, 8),
            quote_volume_24h NUMERIC(30, 2),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for broker_volume_snapshots
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_vol_snapshot_time
        ON broker_volume_snapshots(snapshot_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_vol_exchange_symbol
        ON broker_volume_snapshots(exchange, symbol);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_broker_vol_exchange_time
        ON broker_volume_snapshots(exchange, snapshot_time DESC);
    """
    )

    # Table comments
    op.execute(
        """
        COMMENT ON TABLE broker_open_interest_snapshots IS
        'Open Interest snapshots from exchanges for funding engine visualization';
    """
    )
    op.execute(
        """
        COMMENT ON TABLE broker_volume_snapshots IS
        '24h Volume snapshots from exchanges for funding engine visualization';
    """
    )


def downgrade() -> None:
    """Drop OI and Volume snapshot tables.

    Note: This is a destructive operation. All OI/Volume data will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_broker_vol_exchange_time;")
    op.execute("DROP INDEX IF EXISTS idx_broker_vol_exchange_symbol;")
    op.execute("DROP INDEX IF EXISTS idx_broker_vol_snapshot_time;")

    op.execute("DROP INDEX IF EXISTS idx_broker_oi_exchange_time;")
    op.execute("DROP INDEX IF EXISTS idx_broker_oi_exchange_symbol;")
    op.execute("DROP INDEX IF EXISTS idx_broker_oi_snapshot_time;")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS broker_volume_snapshots;")
    op.execute("DROP TABLE IF EXISTS broker_open_interest_snapshots;")
