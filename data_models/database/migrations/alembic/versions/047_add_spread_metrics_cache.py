"""Add spread metrics cache table for analytics API performance

This migration creates a cache table for expensive spread metric calculations
to improve API response times for the spread analytics endpoints.

Revision ID: 047
Revises: 046
Create Date: 2025-12-19 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "047"
down_revision: Union[str, None] = "046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create spread metrics cache table."""

    # Create spread metrics cache table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS spread_metrics_cache (
            id SERIAL PRIMARY KEY,
            calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            exchange_pair VARCHAR(100) NOT NULL,
            contract VARCHAR(50) NOT NULL,
            timeframe VARCHAR(20) NOT NULL,  -- '1h', '24h', '7d'
            metric_type VARCHAR(50) NOT NULL, -- 'distribution', 'volatility', 'mean_reversion', 'opportunity'

            -- Cached results (JSONB for flexibility)
            metrics JSONB NOT NULL,

            -- Cache control
            ttl_seconds INTEGER NOT NULL DEFAULT 300,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

            -- Metadata
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

            -- Unique constraint to prevent duplicate cache entries
            UNIQUE(exchange_pair, contract, timeframe, metric_type)
        );
        """
    )

    # Index for cache lookups
    op.execute(
        """
        CREATE INDEX idx_spread_metrics_cache_lookup
        ON spread_metrics_cache(exchange_pair, contract, expires_at);
        """
    )

    # Index for cache cleanup
    op.execute(
        """
        CREATE INDEX idx_spread_metrics_cache_expiry
        ON spread_metrics_cache(expires_at);
        """
    )

    # Index for metric type queries
    op.execute(
        """
        CREATE INDEX idx_spread_metrics_cache_type
        ON spread_metrics_cache(metric_type, expires_at);
        """
    )

    # Add comment to table
    op.execute(
        """
        COMMENT ON TABLE spread_metrics_cache IS
        'Cache for expensive spread metric calculations with TTL support';
        """
    )

    # Add comments to columns
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.exchange_pair IS
        'Exchange pair in format "exchange1:exchange2"';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.contract IS
        'Trading contract (e.g., BTC_USDT)';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.timeframe IS
        'Analysis timeframe (1h, 24h, 7d, etc.)';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.metric_type IS
        'Type of metric cached (distribution, volatility, mean_reversion, opportunity)';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.metrics IS
        'JSONB containing calculated metrics';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.ttl_seconds IS
        'Time to live in seconds';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN spread_metrics_cache.expires_at IS
        'Timestamp when cache entry expires';
        """
    )

    # Create function to update updated_at timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_spread_metrics_cache_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger to automatically update updated_at
    op.execute(
        """
        CREATE TRIGGER spread_metrics_cache_updated_at
            BEFORE UPDATE ON spread_metrics_cache
            FOR EACH ROW
            EXECUTE FUNCTION update_spread_metrics_cache_updated_at();
        """
    )

    # Create function to clean up expired cache entries
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_spread_metrics_cache()
        RETURNS void AS $$
        BEGIN
            DELETE FROM spread_metrics_cache
            WHERE expires_at <= CURRENT_TIMESTAMP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Add comment to cleanup function
    op.execute(
        """
        COMMENT ON FUNCTION cleanup_expired_spread_metrics_cache() IS
        'Removes expired cache entries from spread_metrics_cache table';
        """
    )


def downgrade() -> None:
    """Drop spread metrics cache table.

    Note: This is a destructive operation. All cached metrics will be lost.
    """

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS spread_metrics_cache_updated_at ON spread_metrics_cache;")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_spread_metrics_cache_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_spread_metrics_cache();")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_spread_metrics_cache_type;")
    op.execute("DROP INDEX IF EXISTS idx_spread_metrics_cache_expiry;")
    op.execute("DROP INDEX IF EXISTS idx_spread_metrics_cache_lookup;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS spread_metrics_cache;")
