"""TRUNCATE order_executions and add UNIQUE constraint (fast approach)

Start fresh with clean data instead of spending hours cleaning up duplicates.
Historical order data is not critical and can be regenerated from live trading.

Revision ID: 029
Revises: 027
Create Date: 2025-10-25 22:10:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "029"
down_revision: Union[str, None] = "027"  # Skip 028 (failed in production - too slow)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """TRUNCATE table and add UNIQUE constraint (fast)."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/029_truncate_and_add_unique_constraint.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Remove UNIQUE constraint (cannot restore truncated data)."""

    # Drop the UNIQUE index
    op.execute("DROP INDEX IF EXISTS idx_order_executions_unique_client_order;")
