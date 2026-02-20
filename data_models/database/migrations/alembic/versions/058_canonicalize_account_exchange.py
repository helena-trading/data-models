"""Canonicalize account exchange names to ExchangeName enum values

Existing accounts may store raw aliases like "binance" or "ripio" instead of
the canonical ExchangeName values ("binance_futures", "ripio_trade").  This
migration resolves the aliases using the account_type column to disambiguate
where needed (e.g. binance → binance_futures vs binance_spot).

Targets: credentials database (accounts table)

Revision ID: 058
Revises: 057
Create Date: 2026-02-09

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "058"
down_revision: Union[str, None] = "057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Canonicalize exchange column to ExchangeName enum values."""

    # "binance" + futures → "binance_futures"
    op.execute(
        """
        UPDATE accounts
        SET exchange = 'binance_futures'
        WHERE exchange = 'binance' AND account_type = 'futures';
        """
    )

    # "binance" + spot → "binance_spot"
    op.execute(
        """
        UPDATE accounts
        SET exchange = 'binance_spot'
        WHERE exchange = 'binance' AND account_type = 'spot';
        """
    )

    # "ripio" → "ripio_trade"
    op.execute(
        """
        UPDATE accounts
        SET exchange = 'ripio_trade'
        WHERE exchange = 'ripio';
        """
    )


def downgrade() -> None:
    """Revert to legacy alias names."""

    op.execute(
        """
        UPDATE accounts
        SET exchange = 'binance'
        WHERE exchange IN ('binance_futures', 'binance_spot');
        """
    )

    op.execute(
        """
        UPDATE accounts
        SET exchange = 'ripio'
        WHERE exchange = 'ripio_trade';
        """
    )
