"""Normalize strategy_type and exchange names to canonical values

This migration updates:
1. strategy_type: 'cross_exchange_arbitrage' → 'cross_arb' (canonical name)
2. config.exchanges.taker: 'binance' → 'binance_spot' (canonical ExchangeName)

Revision ID: 048
Revises: 047
Create Date: 2026-01-06 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "048"
down_revision: Union[str, None] = "047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update strategy_type and exchange names to canonical values."""

    # 1. Update strategy_type from 'cross_exchange_arbitrage' to 'cross_arb'
    op.execute(
        """
        UPDATE bots
        SET strategy_type = 'cross_arb',
            updated_at = NOW()
        WHERE strategy_type = 'cross_exchange_arbitrage';
        """
    )

    # 2. Update config.exchanges.taker from 'binance' to 'binance_spot'
    #    Using JSONB set for proper JSON manipulation
    op.execute(
        """
        UPDATE bots
        SET config = jsonb_set(
            config,
            '{exchanges,taker}',
            '"binance_spot"'
        ),
        updated_at = NOW()
        WHERE config->'exchanges'->>'taker' = 'binance';
        """
    )

    # 3. Update config.exchanges.maker from 'binance' to 'binance_spot' (if any)
    op.execute(
        """
        UPDATE bots
        SET config = jsonb_set(
            config,
            '{exchanges,maker}',
            '"binance_spot"'
        ),
        updated_at = NOW()
        WHERE config->'exchanges'->>'maker' = 'binance';
        """
    )


def downgrade() -> None:
    """Revert to legacy names (not recommended)."""

    # 1. Revert strategy_type
    op.execute(
        """
        UPDATE bots
        SET strategy_type = 'cross_exchange_arbitrage',
            updated_at = NOW()
        WHERE strategy_type = 'cross_arb';
        """
    )

    # 2. Revert taker exchange name
    op.execute(
        """
        UPDATE bots
        SET config = jsonb_set(
            config,
            '{exchanges,taker}',
            '"binance"'
        ),
        updated_at = NOW()
        WHERE config->'exchanges'->>'taker' = 'binance_spot';
        """
    )

    # 3. Revert maker exchange name
    op.execute(
        """
        UPDATE bots
        SET config = jsonb_set(
            config,
            '{exchanges,maker}',
            '"binance"'
        ),
        updated_at = NOW()
        WHERE config->'exchanges'->>'maker' = 'binance_spot';
        """
    )
