"""Add account_id foreign keys to balance and position tables

This migration adds account_id columns to account_balances and position_snapshots
tables, enabling direct linking of balance/position data to exchange accounts.

Also renames columns in account_balances for better naming consistency:
- currency → asset
- free_balance → available
- locked_balance → allocated
- total_balance → balance

Adds new columns:
- usd_value to account_balances
- updated_at to both tables (with auto-update trigger)

Creates performance indexes for efficient querying.

Revision ID: 024
Revises: None
Create Date: 2025-10-21 16:00:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "024"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account_id columns, rename columns, create indexes.

    This migration uses the original idempotent SQL file to avoid
    PostgreSQL transaction abort issues with try/except blocks.

    The SQL file uses DO $$ blocks for proper conditional logic
    that doesn't abort transactions.
    """

    # Read the SQL migration file
    sql_file_path = os.path.join(
        os.path.dirname(__file__), "../../scripts/024_update_balance_position_tables_for_account_linking.sql"
    )

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the idempotent SQL migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Reverse the migration (rollback).

    Note: This is a destructive operation and should only be used
    in development or emergency rollback scenarios.
    """

    # Drop position_snapshots changes
    op.drop_index("idx_position_snapshots_account_contract", table_name="position_snapshots", if_exists=True)
    op.drop_index("idx_position_snapshots_exchange_contract", table_name="position_snapshots", if_exists=True)
    op.drop_index("idx_position_snapshots_account_time", table_name="position_snapshots", if_exists=True)
    op.drop_index("idx_position_snapshots_contract", table_name="position_snapshots", if_exists=True)
    op.drop_index("idx_position_snapshots_exchange", table_name="position_snapshots", if_exists=True)
    op.drop_index("idx_position_snapshots_time", table_name="position_snapshots", if_exists=True)

    op.execute("DROP TRIGGER IF EXISTS update_position_snapshots_updated_at ON position_snapshots;")
    op.execute("ALTER TABLE position_snapshots DROP COLUMN IF EXISTS updated_at;")
    op.execute("ALTER TABLE position_snapshots DROP CONSTRAINT IF EXISTS fk_position_snapshots_account_id;")
    op.execute("ALTER TABLE position_snapshots DROP COLUMN IF EXISTS account_id;")

    # Drop account_balances changes
    op.drop_index("idx_account_balances_account_asset", table_name="account_balances", if_exists=True)
    op.drop_index("idx_account_balances_exchange_asset", table_name="account_balances", if_exists=True)
    op.drop_index("idx_account_balances_account_time", table_name="account_balances", if_exists=True)
    op.drop_index("idx_account_balances_asset", table_name="account_balances", if_exists=True)
    op.drop_index("idx_account_balances_exchange", table_name="account_balances", if_exists=True)
    op.drop_index("idx_account_balances_time", table_name="account_balances", if_exists=True)

    op.execute("DROP TRIGGER IF EXISTS update_account_balances_updated_at ON account_balances;")
    op.execute("ALTER TABLE account_balances DROP COLUMN IF EXISTS updated_at;")
    op.execute("ALTER TABLE account_balances DROP COLUMN IF EXISTS usd_value;")

    # Reverse column renames (if they were renamed)
    op.execute("ALTER TABLE account_balances RENAME COLUMN balance TO total_balance;")
    op.execute("ALTER TABLE account_balances RENAME COLUMN allocated TO locked_balance;")
    op.execute("ALTER TABLE account_balances RENAME COLUMN available TO free_balance;")
    op.execute("ALTER TABLE account_balances RENAME COLUMN asset TO currency;")

    op.execute("ALTER TABLE account_balances DROP CONSTRAINT IF EXISTS fk_account_balances_account_id;")
    op.execute("ALTER TABLE account_balances DROP COLUMN IF EXISTS account_id;")
