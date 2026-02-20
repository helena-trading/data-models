"""Add Orders API columns to order_executions

This migration adds columns required for the Orders API endpoints:
- bot_id: Bot identifier (in addition to route_id for clarity)
- average_fill_price: Average execution price for filled orders
- execution_time_ms: Time from creation to fill in milliseconds
- filled_at: Timestamp when order reached FILLED status
- cancelled_at: Timestamp when order was cancelled
- block_id: Link to block_trades for reconciliation

Also creates performance indexes for efficient querying.

Revision ID: 027
Revises: 026
Create Date: 2025-10-25 11:00:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Orders API columns and indexes to order_executions table."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/027_add_orders_api_columns.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the idempotent SQL migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Remove Orders API columns and indexes.

    Note: This is a destructive operation and should only be used
    in development or emergency rollback scenarios.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_order_executions_bot_id;")
    op.execute("DROP INDEX IF EXISTS idx_order_executions_status_time;")
    op.execute("DROP INDEX IF EXISTS idx_order_executions_bot_status_time;")
    op.execute("DROP INDEX IF EXISTS idx_order_executions_block_id_partial;")
    op.execute("DROP INDEX IF EXISTS idx_order_executions_contract;")

    # Note: Foreign key constraint was not added in upgrade, so no need to drop it

    # Drop columns
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS bot_id;")
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS average_fill_price;")
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS execution_time_ms;")
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS filled_at;")
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS cancelled_at;")
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS block_id;")
