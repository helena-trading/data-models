"""Add account_id to analytics tables for account-aware analytics

Adds account_id column to account_balances and position_snapshots tables
to enable account-level analytics while keeping credentials separate.

This follows the same pattern as bot_id - stored as plain integer without
foreign key constraint due to cross-database architecture (credentials DB
vs analytics DB).

Also adds correlation_confidence column to track backfill quality.

Revision ID: 033
Revises: 032
Create Date: 2025-12-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account_id and correlation_confidence to analytics tables."""

    # Add account_id to account_balances
    # Plain integer, no FK constraint (cross-database reference to credentials DB)
    op.execute(
        """
        ALTER TABLE account_balances
        ADD COLUMN IF NOT EXISTS account_id INTEGER;
    """
    )

    # Add correlation_confidence to track backfill quality
    # Values: 'NEW' (written with account_id), 'HIGH', 'MEDIUM', 'LOW', 'AMBIGUOUS', 'NO_ACCOUNT'
    op.execute(
        """
        ALTER TABLE account_balances
        ADD COLUMN IF NOT EXISTS correlation_confidence VARCHAR(20) DEFAULT 'NEW';
    """
    )

    # Create indexes for efficient queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_account_balances_account_id
        ON account_balances(account_id);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_account_balances_account_exchange_time
        ON account_balances(account_id, exchange, time);
    """
    )

    # Add account_id to position_snapshots
    op.execute(
        """
        ALTER TABLE position_snapshots
        ADD COLUMN IF NOT EXISTS account_id INTEGER;
    """
    )

    op.execute(
        """
        ALTER TABLE position_snapshots
        ADD COLUMN IF NOT EXISTS correlation_confidence VARCHAR(20) DEFAULT 'NEW';
    """
    )

    # Create indexes for efficient queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_id
        ON position_snapshots(account_id);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_exchange_time
        ON position_snapshots(account_id, exchange, time);
    """
    )

    # Update existing records to mark them as needing backfill
    op.execute(
        """
        UPDATE account_balances
        SET correlation_confidence = 'UNPROCESSED'
        WHERE correlation_confidence = 'NEW' AND account_id IS NULL;
    """
    )

    op.execute(
        """
        UPDATE position_snapshots
        SET correlation_confidence = 'UNPROCESSED'
        WHERE correlation_confidence = 'NEW' AND account_id IS NULL;
    """
    )


def downgrade() -> None:
    """Remove account_id and correlation_confidence from analytics tables.

    Note: This is a destructive operation. All account correlation data will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_account_balances_account_id;")
    op.execute("DROP INDEX IF EXISTS idx_account_balances_account_exchange_time;")
    op.execute("DROP INDEX IF EXISTS idx_position_snapshots_account_id;")
    op.execute("DROP INDEX IF EXISTS idx_position_snapshots_account_exchange_time;")

    # Drop columns
    op.execute("ALTER TABLE account_balances DROP COLUMN IF EXISTS account_id;")
    op.execute("ALTER TABLE account_balances DROP COLUMN IF EXISTS correlation_confidence;")
    op.execute("ALTER TABLE position_snapshots DROP COLUMN IF EXISTS account_id;")
    op.execute("ALTER TABLE position_snapshots DROP COLUMN IF EXISTS correlation_confidence;")
