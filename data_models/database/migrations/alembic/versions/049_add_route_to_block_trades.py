"""add_route_to_block_trades

Revision ID: 049
Revises: 048
Create Date: 2025-12-15

This migration adds a 'route' column to block_trades table to store
string route identifiers like "graph_main", "graph_unwinder", "route0", etc.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "049"
down_revision: Union[str, None] = "048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new route column as VARCHAR
    op.execute(
        """
        ALTER TABLE block_trades ADD COLUMN IF NOT EXISTS route VARCHAR(50);
    """
    )

    # Step 2: Migrate existing route_id data to route (only if route_id column exists)
    # Using DO block to conditionally execute if column exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'block_trades' AND column_name = 'route_id'
            ) THEN
                UPDATE block_trades
                SET route = 'route' || route_id::text
                WHERE route_id IS NOT NULL AND route IS NULL;

                ALTER TABLE block_trades DROP COLUMN route_id;
            END IF;
        END $$;
    """
    )

    # Step 3: Drop old index and create new one
    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_route_id;
        CREATE INDEX IF NOT EXISTS idx_block_trades_route ON block_trades(route);
    """
    )

    # Add comment
    op.execute(
        """
        COMMENT ON COLUMN block_trades.route IS 'Route identifier (e.g., graph_main, graph_unwinder, route0, route1)';
    """
    )


def downgrade() -> None:
    # Drop index
    op.execute(
        """
        DROP INDEX IF EXISTS idx_block_trades_route;
    """
    )

    # Drop route column
    op.execute(
        """
        ALTER TABLE block_trades DROP COLUMN IF EXISTS route;
    """
    )
