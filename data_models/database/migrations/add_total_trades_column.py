"""Add total_trades column to bot_runs table."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    """Add total_trades column to bot_runs table."""
    op.add_column("bot_runs", sa.Column("total_trades", sa.Integer(), nullable=True, default=0))

    # Set default value for existing rows
    op.execute("UPDATE bot_runs SET total_trades = 0 WHERE total_trades IS NULL")

    # Make column non-nullable after setting defaults
    op.alter_column("bot_runs", "total_trades", nullable=False)


def downgrade() -> None:
    """Remove total_trades column from bot_runs table."""
    op.drop_column("bot_runs", "total_trades")
