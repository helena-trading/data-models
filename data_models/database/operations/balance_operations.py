"""Database operations for account balances.

NOTE: This module uses ANALYTICS database for balance queries.
Balances identified by exchange + asset (not account_id).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from data_models.database.core.db_config import get_analytics_db_manager
from data_models.database.tables.account_balance import AccountBalance


class BalanceOperations:
    """Handles database operations for account balances.

    NOTE: Uses ANALYTICS database. Balances identified by exchange + asset.
    """

    def __init__(self) -> None:
        """Initialize balance operations."""
        self.db = get_analytics_db_manager()

    def insert_balance(self, session: Session, balance: AccountBalance) -> AccountBalance:
        """Insert a single balance snapshot.

        Args:
            session: SQLAlchemy session
            balance: AccountBalance instance to insert

        Returns:
            Inserted AccountBalance with id populated
        """
        session.add(balance)
        session.flush()
        return balance

    def insert_balances_batch(self, session: Session, balances: List[AccountBalance]) -> List[AccountBalance]:
        """Insert multiple balance snapshots.

        Args:
            session: SQLAlchemy session
            balances: List of AccountBalance instances

        Returns:
            List of inserted AccountBalance instances
        """
        session.add_all(balances)
        session.flush()
        return balances

    def get_latest_balances_by_exchange(self, session: Session, exchange: str) -> List[AccountBalance]:
        """Get latest balance for each asset for a specific exchange.

        Returns balances from the most recent update cycle (last 2 minutes) to avoid
        mixing fresh data with stale data from different update times.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name

        Returns:
            List of latest AccountBalance records per asset from recent update
        """
        # Get all balances from last 2 minutes (captures latest update cycle)
        # This prevents mixing stale data (e.g., BTC from 3 hours ago) with
        # fresh data (e.g., USDT from 1 minute ago)
        query = text(
            """
            SELECT DISTINCT ON (asset)
                id, time, exchange, asset, balance, usd_value, allocated, available, created_at, updated_at
            FROM account_balances
            WHERE exchange = :exchange
              AND time > NOW() - INTERVAL '2 minutes'
            ORDER BY asset, time DESC
            """
        )

        results = session.execute(query, {"exchange": exchange}).fetchall()

        # Convert to AccountBalance objects
        balances = []
        for row in results:
            balance = AccountBalance(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                asset=row.asset,
                balance=row.balance,
                usd_value=row.usd_value,
                allocated=row.allocated,
                available=row.available,
            )
            balances.append(balance)

        return balances

    def get_latest_balances_all_exchanges(self, session: Session) -> List[AccountBalance]:
        """Get latest balance for each asset across all exchanges.

        Returns balances from the most recent update cycle (last 2 minutes) to avoid
        mixing fresh data with stale data from different update times.

        Returns:
            List of latest AccountBalance records per exchange and asset from recent updates
        """
        # Get all balances from last 2 minutes (captures latest update cycles)
        # This prevents mixing stale data with fresh data across different exchanges
        query = text(
            """
            SELECT DISTINCT ON (exchange, asset)
                id, time, exchange, asset, balance, usd_value, allocated, available, created_at, updated_at
            FROM account_balances
            WHERE time > NOW() - INTERVAL '2 minutes'
            ORDER BY exchange, asset, time DESC
            """
        )

        results = session.execute(query).fetchall()

        # Convert to AccountBalance objects
        balances = []
        for row in results:
            balance = AccountBalance(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                asset=row.asset,
                balance=row.balance,
                usd_value=row.usd_value,
                allocated=row.allocated,
                available=row.available,
            )
            balances.append(balance)

        return balances

    def get_latest_balances_with_account_id(self, session: Session) -> List[AccountBalance]:
        """Get latest balance for each asset per account_id.

        Returns balances from the most recent update cycle (last 2 minutes) grouped by account_id.
        Only returns records with account_id populated (new writes after migration 033).

        Returns:
            List of AccountBalance records with account_id, grouped by account_id and asset
        """
        query = text(
            """
            SELECT DISTINCT ON (account_id, asset)
                id, time, exchange, asset, balance, usd_value,
                allocated, available, account_id, correlation_confidence,
                created_at, updated_at
            FROM account_balances
            WHERE time > NOW() - INTERVAL '2 minutes'
              AND account_id IS NOT NULL
            ORDER BY account_id, asset, time DESC
            """
        )

        results = session.execute(query).fetchall()

        # Convert to AccountBalance objects
        balances = []
        for row in results:
            balance = AccountBalance(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                asset=row.asset,
                balance=row.balance,
                usd_value=row.usd_value,
                allocated=row.allocated,
                available=row.available,
                account_id=row.account_id,
                correlation_confidence=row.correlation_confidence,
            )
            balances.append(balance)

        return balances

    def get_latest_balances_by_account_id(self, session: Session, account_id: int) -> List[AccountBalance]:
        """Get latest balances for a specific account_id.

        Args:
            session: SQLAlchemy session
            account_id: Account ID to filter by

        Returns:
            List of AccountBalance records for the specified account
        """
        query = text(
            """
            SELECT DISTINCT ON (asset)
                id, time, exchange, asset, balance, usd_value,
                allocated, available, account_id, correlation_confidence,
                created_at, updated_at
            FROM account_balances
            WHERE time > NOW() - INTERVAL '2 minutes'
              AND account_id = :account_id
            ORDER BY asset, time DESC
            """
        )

        results = session.execute(query, {"account_id": account_id}).fetchall()

        balances = []
        for row in results:
            balance = AccountBalance(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                asset=row.asset,
                balance=row.balance,
                usd_value=row.usd_value,
                allocated=row.allocated,
                available=row.available,
                account_id=row.account_id,
                correlation_confidence=row.correlation_confidence,
            )
            balances.append(balance)

        return balances

    def get_balances_by_exchange(self, session: Session, exchange: str) -> List[AccountBalance]:
        """Get latest balances for a specific exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name to filter by

        Returns:
            List of latest AccountBalance records for the exchange
        """
        return self.get_latest_balances_by_exchange(session, exchange)

    def get_balance_history(
        self,
        session: Session,
        asset: Optional[str] = None,
        exchange: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AccountBalance]:
        """Get balance history with optional filters.

        Args:
            session: SQLAlchemy session
            asset: Filter by asset (optional)
            exchange: Filter by exchange (optional)
            start_time: Filter by start time (optional)
            end_time: Filter by end time (optional)
            limit: Maximum number of records to return

        Returns:
            List of AccountBalance records ordered by time DESC
        """
        query = session.query(AccountBalance)

        if asset:
            query = query.filter(AccountBalance.asset == asset)
        if exchange:
            query = query.filter(AccountBalance.exchange == exchange)
        if start_time:
            query = query.filter(AccountBalance.time >= start_time)
        if end_time:
            query = query.filter(AccountBalance.time <= end_time)

        query = query.order_by(desc(AccountBalance.time)).limit(limit)

        return query.all()

    def get_total_usd_value_by_exchange(self, session: Session, exchange: str) -> float:
        """Calculate total USD value for an exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name

        Returns:
            Total USD value across all assets
        """
        # Get latest balances
        balances = self.get_latest_balances_by_exchange(session, exchange)

        # Sum USD values
        total = sum(float(b.usd_value) if b.usd_value else 0.0 for b in balances)

        return total

    def get_aggregated_balances_by_currency(self, session: Session) -> List[Dict[str, Any]]:
        """Get aggregated balances across all exchanges by currency.

        Args:
            session: SQLAlchemy session

        Returns:
            List of dicts with currency, total_balance, total_usd_value, exchange_count
        """
        # Raw SQL query for complex aggregation
        query = """
            WITH latest_balances AS (
                SELECT DISTINCT ON (exchange, asset)
                    exchange,
                    asset,
                    balance,
                    usd_value,
                    time
                FROM account_balances
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY exchange, asset, time DESC
            )
            SELECT
                asset as currency,
                SUM(balance) as total_balance,
                SUM(usd_value) as total_usd_value,
                COUNT(DISTINCT exchange) as exchange_count
            FROM latest_balances
            GROUP BY asset
            ORDER BY total_usd_value DESC NULLS LAST
        """

        results = session.execute(text(query)).mappings().all()

        return [
            {
                "currency": row["currency"],
                "total_balance": float(row["total_balance"]) if row["total_balance"] else 0.0,
                "total_usd_value": float(row["total_usd_value"]) if row["total_usd_value"] else 0.0,
                "exchange_count": row["exchange_count"],
            }
            for row in results
        ]

    def get_aggregated_balances_by_exchange(self, session: Session) -> List[Dict[str, Any]]:
        """Get aggregated balances by exchange.

        Args:
            session: SQLAlchemy session

        Returns:
            List of dicts with exchange, total_usd_value, asset_count
        """
        query = """
            WITH latest_balances AS (
                SELECT DISTINCT ON (exchange, asset)
                    exchange,
                    asset,
                    usd_value,
                    time
                FROM account_balances
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY exchange, asset, time DESC
            )
            SELECT
                exchange,
                SUM(usd_value) as total_usd_value,
                COUNT(DISTINCT asset) as asset_count
            FROM latest_balances
            GROUP BY exchange
            ORDER BY total_usd_value DESC NULLS LAST
        """

        results = session.execute(text(query)).mappings().all()

        return [
            {
                "exchange": row["exchange"],
                "total_usd_value": float(row["total_usd_value"]) if row["total_usd_value"] else 0.0,
                "asset_count": row["asset_count"],
            }
            for row in results
        ]

    def delete_old_snapshots(
        self,
        session: Session,
        days_to_keep: int = 30,
        batch_size: int = 1000,
    ) -> int:
        """Delete balance snapshots older than specified days.

        Args:
            session: SQLAlchemy session
            days_to_keep: Number of days of history to keep
            batch_size: Number of records to delete per batch

        Returns:
            Number of records deleted
        """
        cutoff_time = datetime.utcnow() - __import__("datetime").timedelta(days=days_to_keep)

        total_deleted = 0
        while True:
            # Delete in batches to avoid long-running transactions
            result = (
                session.query(AccountBalance)
                .filter(AccountBalance.time < cutoff_time)
                .limit(batch_size)
                .delete(synchronize_session=False)
            )

            session.flush()
            total_deleted += result

            if result < batch_size:
                # No more records to delete
                break

        return total_deleted
