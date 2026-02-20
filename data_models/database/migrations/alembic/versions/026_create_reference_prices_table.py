"""Create reference_prices table

This migration creates the reference_prices table for storing latest market
mid-prices for all initialized trading pairs across exchanges.

The reference prices are used by the dashboard to convert cryptocurrency
amounts to USD values without requiring real-time price feeds.

Prices are captured from orderbook mid-price (best_bid + best_ask) / 2 and
are updated at initialization and after trade execution.

Revision ID: 026
Revises: 025
Create Date: 2025-10-24 12:00:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create reference_prices table with indexes and triggers."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/026_create_reference_prices_table.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the idempotent SQL migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Drop reference_prices table and related objects.

    Note: This is a destructive operation and should only be used
    in development or emergency rollback scenarios.
    """

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS reference_prices_updated_at_trigger ON reference_prices;")
    op.execute("DROP FUNCTION IF EXISTS update_reference_prices_updated_at();")

    # Drop indexes (if they exist separately, though DROP TABLE CASCADE should handle them)
    op.execute("DROP INDEX IF EXISTS idx_reference_prices_timestamp;")
    op.execute("DROP INDEX IF EXISTS idx_reference_prices_exchange_contract;")

    # Drop the table
    op.execute("DROP TABLE IF EXISTS reference_prices CASCADE;")
