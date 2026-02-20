"""Create broker market data snapshot tables

Creates two tables for historical market data persistence:
1. broker_funding_rate_snapshots - Periodic funding rate snapshots from broker caches
2. broker_mark_price_snapshots - Periodic mark price snapshots from broker caches

These tables store data directly from the broker's FundingRate and MarkPrice
Pydantic models, enabling historical analytics with 90+ day retention.

Revision ID: 032
Revises: 031
Create Date: 2025-11-28 00:00:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create broker market data snapshot tables with indexes."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/032_create_broker_market_data_tables.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Drop broker market data snapshot tables.

    Note: This is a destructive operation and should only be used
    in development or emergency rollback scenarios.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_broker_funding_snapshots_time;")
    op.execute("DROP INDEX IF EXISTS idx_broker_funding_snapshots_exchange_symbol;")
    op.execute("DROP INDEX IF EXISTS idx_broker_funding_snapshots_time_exchange;")
    op.execute("DROP INDEX IF EXISTS idx_broker_funding_snapshots_symbol_time;")

    op.execute("DROP INDEX IF EXISTS idx_broker_mark_snapshots_time;")
    op.execute("DROP INDEX IF EXISTS idx_broker_mark_snapshots_exchange_symbol;")
    op.execute("DROP INDEX IF EXISTS idx_broker_mark_snapshots_time_exchange;")
    op.execute("DROP INDEX IF EXISTS idx_broker_mark_snapshots_symbol_time;")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS broker_funding_rate_snapshots CASCADE;")
    op.execute("DROP TABLE IF EXISTS broker_mark_price_snapshots CASCADE;")
