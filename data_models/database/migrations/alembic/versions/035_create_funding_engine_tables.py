"""Create funding engine tables and fix missing funding_rates_snapshots

This migration creates:
1. funding_rates_snapshots - Missing table for existing FundingRateSnapshot model
2. funding_engine_adjustments - Price adjustment data from FundingEngine
3. funding_engine_spread_impacts - Cross-exchange spread impact analysis

These tables enable persistence of derived funding engine data for:
- Backtesting funding strategies
- Analyzing route performance under different funding conditions
- Validating engine calculations over time

Revision ID: 035
Revises: 034
Create Date: 2025-12-03 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create funding engine tables."""

    # 1. Create funding_rates_snapshots (missing table for existing model)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_rates_snapshots (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,
            funding_rate NUMERIC(20, 10) NOT NULL,
            normalization_factor NUMERIC(10, 2) NOT NULL,
            mark_price NUMERIC(30, 10),
            open_interest NUMERIC(30, 2),
            volume_24h NUMERIC(30, 2),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for funding_rates_snapshots
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_rates_snapshots_timestamp
        ON funding_rates_snapshots(timestamp);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_rates_snapshots_exchange_contract
        ON funding_rates_snapshots(exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_rates_snapshots_exchange_time
        ON funding_rates_snapshots(exchange, timestamp);
    """
    )

    # 2. Create funding_engine_adjustments table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_engine_adjustments (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,

            -- Original prices
            original_bid NUMERIC(30, 10),
            original_ask NUMERIC(30, 10),

            -- Adjusted prices (engine output)
            adjusted_bid NUMERIC(30, 10),
            adjusted_ask NUMERIC(30, 10),

            -- Deltas
            bid_delta NUMERIC(30, 10),
            ask_delta NUMERIC(30, 10),
            delta_pct NUMERIC(12, 8),

            -- Funding context
            funding_rate NUMERIC(12, 10),
            funding_interval_hours INTEGER DEFAULT 8,

            -- Engine params
            horizon_hours NUMERIC(10, 2),
            safety_buffer NUMERIC(12, 8),

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for funding_engine_adjustments
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_timestamp
        ON funding_engine_adjustments(timestamp);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_exchange_contract
        ON funding_engine_adjustments(exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_exchange_time
        ON funding_engine_adjustments(exchange, timestamp);
    """
    )

    # 3. Create funding_engine_spread_impacts table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_engine_spread_impacts (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,

            -- Route info
            maker_exchange VARCHAR(50) NOT NULL,
            taker_exchange VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,

            -- Spread analysis
            raw_spread_pct NUMERIC(12, 8),
            adjusted_spread_pct NUMERIC(12, 8),
            spread_delta_pct NUMERIC(12, 8),
            impact_direction VARCHAR(20),

            -- Engine params
            horizon_hours NUMERIC(10, 2),
            safety_buffer NUMERIC(12, 8),

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for funding_engine_spread_impacts
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_spread_impact_timestamp
        ON funding_engine_spread_impacts(timestamp);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_spread_impact_route
        ON funding_engine_spread_impacts(maker_exchange, taker_exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_spread_impact_direction
        ON funding_engine_spread_impacts(impact_direction);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_spread_impact_contract_time
        ON funding_engine_spread_impacts(contract, timestamp);
    """
    )

    # Table comments
    op.execute(
        """
        COMMENT ON TABLE funding_rates_snapshots IS
        'Raw funding rate snapshots from exchanges (Loris API data)';
    """
    )
    op.execute(
        """
        COMMENT ON TABLE funding_engine_adjustments IS
        'FundingEngine price adjustment calculations - shows how funding rates translate to bid/ask changes';
    """
    )
    op.execute(
        """
        COMMENT ON TABLE funding_engine_spread_impacts IS
        'Cross-exchange spread impact analysis - shows which routes benefit from funding adjustments';
    """
    )


def downgrade() -> None:
    """Drop funding engine tables.

    Note: This is a destructive operation. All funding engine data will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_spread_impact_contract_time;")
    op.execute("DROP INDEX IF EXISTS idx_spread_impact_direction;")
    op.execute("DROP INDEX IF EXISTS idx_spread_impact_route;")
    op.execute("DROP INDEX IF EXISTS idx_spread_impact_timestamp;")

    op.execute("DROP INDEX IF EXISTS idx_funding_adj_exchange_time;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_exchange_contract;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_timestamp;")

    op.execute("DROP INDEX IF EXISTS idx_funding_rates_snapshots_exchange_time;")
    op.execute("DROP INDEX IF EXISTS idx_funding_rates_snapshots_exchange_contract;")
    op.execute("DROP INDEX IF EXISTS idx_funding_rates_snapshots_timestamp;")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS funding_engine_spread_impacts;")
    op.execute("DROP TABLE IF EXISTS funding_engine_adjustments;")
    op.execute("DROP TABLE IF EXISTS funding_rates_snapshots;")
