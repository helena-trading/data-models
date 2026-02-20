"""Add maker_internal_id and taker_internal_id to block_trades table

Revision ID: 051
Revises: 050
Create Date: 2026-01-10

This migration adds internal_id columns to block_trades to enable reliable
joins with order_executions. The existing maker_order_id/taker_order_id columns
store exchange_order_ids which may not match order_executions.order_id due to
timing issues during order writes.

The internal_id is always available and consistent, making it the canonical
identifier for correlating orders across tables.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "051"
down_revision: Union[str, None] = "050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add maker_internal_id and taker_internal_id columns to block_trades table."""

    # Add maker_internal_id column
    op.execute(
        """
        ALTER TABLE block_trades
            ADD COLUMN IF NOT EXISTS maker_internal_id VARCHAR(100);
        """
    )

    # Add taker_internal_id column
    op.execute(
        """
        ALTER TABLE block_trades
            ADD COLUMN IF NOT EXISTS taker_internal_id VARCHAR(100);
        """
    )

    # Create index for efficient joins with order_executions via maker_internal_id
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_block_trades_maker_internal_id
        ON block_trades(maker_internal_id);
        """
    )

    # Create index for efficient joins with order_executions via taker_internal_id
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_block_trades_taker_internal_id
        ON block_trades(taker_internal_id);
        """
    )

    # Add comments to document the columns
    op.execute(
        """
        COMMENT ON COLUMN block_trades.maker_internal_id IS
        'Internal order ID for maker order - joins with order_executions.client_order_id';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN block_trades.taker_internal_id IS
        'Internal order ID for taker order - joins with order_executions.client_order_id';
        """
    )


def downgrade() -> None:
    """Remove maker_internal_id and taker_internal_id columns from block_trades table."""

    # Drop indexes first
    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_maker_internal_id;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_taker_internal_id;
        """
    )

    # Drop columns
    op.execute(
        """
        ALTER TABLE block_trades DROP COLUMN IF EXISTS maker_internal_id;
        """
    )

    op.execute(
        """
        ALTER TABLE block_trades DROP COLUMN IF EXISTS taker_internal_id;
        """
    )
