"""Rename client_order_id to internal_id in order_executions.

Revision ID: 055
Create Date: 2026-02-05
"""

from alembic import op

# revision identifiers
revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename client_order_id column and recreate unique index."""
    # Rename column
    op.execute("ALTER TABLE order_executions RENAME COLUMN client_order_id TO internal_id")

    # Drop old unique index
    op.execute("DROP INDEX IF EXISTS idx_order_executions_exchange_client_order_id")

    # Create new unique index with updated name
    op.execute(
        "CREATE UNIQUE INDEX idx_order_executions_exchange_internal_id "
        "ON order_executions (exchange, internal_id) "
        "WHERE internal_id IS NOT NULL"
    )


def downgrade() -> None:
    """Revert column rename and index."""
    op.execute("DROP INDEX IF EXISTS idx_order_executions_exchange_internal_id")

    op.execute("ALTER TABLE order_executions RENAME COLUMN internal_id TO client_order_id")

    op.execute(
        "CREATE UNIQUE INDEX idx_order_executions_exchange_client_order_id "
        "ON order_executions (exchange, client_order_id) "
        "WHERE client_order_id IS NOT NULL"
    )
