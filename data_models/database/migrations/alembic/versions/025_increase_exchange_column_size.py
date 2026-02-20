"""Increase exchange column size to 250 characters

This migration increases the VARCHAR size of the exchange column from 50 to 250
characters in both account_balances and position_snapshots tables to support
longer exchange identifiers.

Revision ID: 025
Revises: 024
Create Date: 2025-10-22 15:10:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase exchange column size to VARCHAR(250)."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/025_increase_exchange_column_size.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the idempotent SQL migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Reverse the migration (rollback to VARCHAR(50)).

    Warning: This will fail if there are exchange names longer than 50 chars.
    """

    # Attempt to reduce column size (will fail if data exceeds 50 chars)
    op.execute("ALTER TABLE account_balances ALTER COLUMN exchange TYPE VARCHAR(50);")
    op.execute("ALTER TABLE position_snapshots ALTER COLUMN exchange TYPE VARCHAR(50);")
