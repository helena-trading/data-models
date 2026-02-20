"""Add has_any_execution flag to order_executions table

Boolean flag to identify orders with any trading activity (filled_quantity > 0).
Enables dashboard to filter:
- Canceled orders with partial fills
- Canceled orders with zero fills
- All orders that actually traded

Revision ID: 030
Revises: 029
Create Date: 2025-10-27 13:30:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add has_any_execution flag and populate data."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/030_add_has_any_execution_flag.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Remove has_any_execution column and index."""

    # Drop the index
    op.execute("DROP INDEX IF EXISTS idx_order_executions_has_execution;")

    # Drop the column
    op.execute("ALTER TABLE order_executions DROP COLUMN IF EXISTS has_any_execution;")
