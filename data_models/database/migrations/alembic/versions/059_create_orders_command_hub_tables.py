"""Create orders command hub configuration tables.

Creates:
- orders_command_hubs
- orders_command_hub_accounts

Revision ID: 059
Revises: 058
Create Date: 2026-02-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "059"
down_revision: Union[str, None] = "058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create orders command hub tables."""
    op.create_table(
        "orders_command_hubs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "process_type",
            sa.String(length=80),
            nullable=False,
            server_default="orders_command_hub",
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "orders_command_hub_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hub_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hub_id"], ["orders_command_hubs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hub_id", "account_id", name="uq_orders_command_hub_account"),
    )
    op.create_index(
        "ix_orders_command_hub_accounts_hub_id",
        "orders_command_hub_accounts",
        ["hub_id"],
        unique=False,
    )
    op.create_index(
        "ix_orders_command_hub_accounts_account_id",
        "orders_command_hub_accounts",
        ["account_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop orders command hub tables."""
    op.drop_index("ix_orders_command_hub_accounts_account_id", table_name="orders_command_hub_accounts")
    op.drop_index("ix_orders_command_hub_accounts_hub_id", table_name="orders_command_hub_accounts")
    op.drop_table("orders_command_hub_accounts")
    op.drop_table("orders_command_hubs")
