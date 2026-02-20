"""Add bot_id and client_id columns to latency_metrics table

Revision ID: 043
Revises: 042
Create Date: 2025-12-18

This migration adds bot_id and client_id columns to the latency_metrics table
to enable correlation between latency data and specific bots/trades.

These columns are critical for:
- Linking latency data to specific bots for performance analysis
- Correlating latency with block_trades via client_id
- Analyzing fill notification latency per bot/exchange/contract
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "043"
down_revision: Union[str, None] = "042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bot_id and client_id columns to latency_metrics table."""

    # Add bot_id column
    op.execute(
        """
        ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS bot_id INTEGER;
    """
    )

    # Add client_id column (matches block_trades.internal_id format)
    op.execute(
        """
        ALTER TABLE latency_metrics ADD COLUMN IF NOT EXISTS client_id VARCHAR(100);
    """
    )

    # Create indexes for efficient queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_latency_metrics_bot_id ON latency_metrics(bot_id);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_latency_metrics_client_id ON latency_metrics(client_id);
    """
    )

    # Add composite index for bot_id + metric_type (common query pattern)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_latency_metrics_bot_metric
        ON latency_metrics(bot_id, metric_type);
    """
    )

    # Add comments to document the columns
    op.execute(
        """
        COMMENT ON COLUMN latency_metrics.bot_id IS
        'Bot ID that generated this latency metric (logical reference, no FK constraint)';
    """
    )

    op.execute(
        """
        COMMENT ON COLUMN latency_metrics.client_id IS
        'Client order ID for correlating with block_trades.internal_id';
    """
    )


def downgrade() -> None:
    """Remove bot_id and client_id columns from latency_metrics table."""

    # Drop indexes first
    op.execute(
        """
        DROP INDEX IF EXISTS idx_latency_metrics_bot_metric;
    """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS idx_latency_metrics_client_id;
    """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS idx_latency_metrics_bot_id;
    """
    )

    # Drop columns
    op.execute(
        """
        ALTER TABLE latency_metrics DROP COLUMN IF EXISTS client_id;
    """
    )

    op.execute(
        """
        ALTER TABLE latency_metrics DROP COLUMN IF EXISTS bot_id;
    """
    )
