"""Bot run update model for tracking incremental updates to bot statistics.

This model writes to the bot_run_stats table in the ANALYTICS database,
not the bot_runs table in the credentials database. This separation allows
high-frequency stats updates without impacting the credentials database.
"""

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass
class BotRunUpdate:
    """Model for incremental updates to bot run statistics.

    This model is used to track updates that should be applied to the
    current bot run, such as incrementing order count or adding to P&L.

    Uses UPSERT (INSERT ... ON CONFLICT ... DO UPDATE) to efficiently
    handle both initial insert and subsequent updates.

    Writes to: bot_run_stats table in ANALYTICS database
    """

    bot_id: int
    run_id: int  # Required - references bot_runs.id in credentials DB
    orders_increment: int = 0  # Number of orders to add
    trades_increment: int = 0  # Number of trades (filled orders) to add
    pnl_increment: float = 0.0  # P&L amount to add
    error_increment: int = 0  # Number of errors to add (if needed)

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate UPSERT query for bot_run_stats table.

        Uses INSERT ... ON CONFLICT ... DO UPDATE to:
        - Create row on first update for this (bot_id, run_id)
        - Increment counters on subsequent updates

        Returns:
            Tuple of (query, params) for upserting bot_run_stats
        """
        # UPSERT: Insert if new, update if exists
        # Target table: bot_run_stats (in analytics DB)
        query = """
            INSERT INTO bot_run_stats (bot_id, run_id, total_orders, total_trades, total_pnl, error_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (bot_id, run_id)
            DO UPDATE SET
                total_orders = bot_run_stats.total_orders + EXCLUDED.total_orders,
                total_trades = bot_run_stats.total_trades + EXCLUDED.total_trades,
                total_pnl = bot_run_stats.total_pnl + EXCLUDED.total_pnl,
                error_count = bot_run_stats.error_count + EXCLUDED.error_count,
                last_updated = NOW()
        """

        params = (
            self.bot_id,
            self.run_id,
            self.orders_increment,
            self.trades_increment,
            self.pnl_increment,
            self.error_increment,
        )

        return query, params
