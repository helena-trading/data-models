"""Create pricing spread tables for real-time spread monitoring

This migration creates:
1. pricing_spread_snapshots - Real-time spread data from WebSocket orderbooks
2. spread_normalization_events - Spread mean reversion tracking

These tables enable:
- Real-time spread analysis using WebSocket data
- Historical spread pattern analysis
- Mean reversion timing studies
- Cross-exchange arbitrage opportunity tracking

Revision ID: 046
Revises: 045
Create Date: 2025-12-19 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "046"
down_revision: Union[str, None] = "045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pricing spread tables."""

    # 1. Create pricing_spread_snapshots table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_spread_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_time TIMESTAMPTZ NOT NULL,
            spread_type VARCHAR(20) NOT NULL,  -- 'intra' or 'cross'

            -- Exchange info
            maker_exchange VARCHAR(50) NOT NULL,
            taker_exchange VARCHAR(50),  -- NULL for intra-exchange spreads
            contract VARCHAR(50) NOT NULL,

            -- Price data (using DOUBLE PRECISION for WebSocket efficiency)
            bid_maker DOUBLE PRECISION NOT NULL,
            ask_maker DOUBLE PRECISION NOT NULL,
            bid_taker DOUBLE PRECISION,  -- NULL for intra-exchange spreads
            ask_taker DOUBLE PRECISION,  -- NULL for intra-exchange spreads

            -- Spread metrics
            spread_bps DOUBLE PRECISION NOT NULL,  -- Basis points
            spread_pct DOUBLE PRECISION NOT NULL,  -- Percentage
            mid_price DOUBLE PRECISION NOT NULL,

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for pricing_spread_snapshots
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pricing_spread_time
        ON pricing_spread_snapshots(snapshot_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pricing_spread_route
        ON pricing_spread_snapshots(maker_exchange, taker_exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pricing_spread_contract_time
        ON pricing_spread_snapshots(contract, snapshot_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pricing_spread_type
        ON pricing_spread_snapshots(spread_type);
    """
    )

    # 2. Create spread_normalization_events table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS spread_normalization_events (
            id SERIAL PRIMARY KEY,
            detected_time TIMESTAMPTZ NOT NULL,
            normalized_time TIMESTAMPTZ,  -- NULL if still ongoing

            -- Route info
            maker_exchange VARCHAR(50) NOT NULL,
            taker_exchange VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,

            -- Spread data
            peak_spread_bps DOUBLE PRECISION NOT NULL,  -- Maximum spread during event
            normal_spread_bps DOUBLE PRECISION NOT NULL,  -- Spread when normalized
            mean_spread_bps DOUBLE PRECISION NOT NULL,  -- Rolling mean
            std_dev_bps DOUBLE PRECISION NOT NULL,  -- Rolling standard deviation

            -- Event characteristics
            duration_seconds INTEGER,  -- NULL if still ongoing
            reversion_pattern VARCHAR(20),  -- 'fast', 'gradual', 'volatile'

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for spread_normalization_events
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_normalization_detected_time
        ON spread_normalization_events(detected_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_normalization_route
        ON spread_normalization_events(maker_exchange, taker_exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_normalization_pattern
        ON spread_normalization_events(reversion_pattern);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_normalization_ongoing
        ON spread_normalization_events(normalized_time)
        WHERE normalized_time IS NULL;
    """
    )

    # Table comments
    op.execute(
        """
        COMMENT ON TABLE pricing_spread_snapshots IS
        'Real-time spread data from WebSocket orderbooks for intra and cross-exchange spreads';
    """
    )
    op.execute(
        """
        COMMENT ON TABLE spread_normalization_events IS
        'Tracks spread deviation and normalization events for mean reversion analysis';
    """
    )

    # Column comments for clarity
    op.execute(
        """
        COMMENT ON COLUMN pricing_spread_snapshots.spread_type IS
        'Type of spread: intra (bid-ask same exchange) or cross (arbitrage between exchanges)';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_normalization_events.reversion_pattern IS
        'Pattern of spread normalization: fast (<30s), gradual (30s-5m), volatile (>5m or erratic)';
    """
    )


def downgrade() -> None:
    """Drop pricing spread tables.

    Note: This is a destructive operation. All pricing spread data will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_normalization_ongoing;")
    op.execute("DROP INDEX IF EXISTS idx_normalization_pattern;")
    op.execute("DROP INDEX IF EXISTS idx_normalization_route;")
    op.execute("DROP INDEX IF EXISTS idx_normalization_detected_time;")

    op.execute("DROP INDEX IF EXISTS idx_pricing_spread_type;")
    op.execute("DROP INDEX IF EXISTS idx_pricing_spread_contract_time;")
    op.execute("DROP INDEX IF EXISTS idx_pricing_spread_route;")
    op.execute("DROP INDEX IF EXISTS idx_pricing_spread_time;")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS spread_normalization_events;")
    op.execute("DROP TABLE IF EXISTS pricing_spread_snapshots;")
