"""Database operations for position snapshots.

NOTE: This module uses ANALYTICS database for position queries.
Positions identified by exchange + contract (not account_id).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from data_models.database.core.db_config import get_analytics_db_manager
from data_models.database.tables.position_snapshot import PositionSnapshot


class PositionOperations:
    """Handles database operations for position snapshots.

    NOTE: Uses ANALYTICS database. Positions identified by exchange + contract.
    """

    def __init__(self) -> None:
        """Initialize position operations."""
        self.db = get_analytics_db_manager()

    def insert_position(self, session: Session, position: PositionSnapshot) -> PositionSnapshot:
        """Insert a single position snapshot.

        Args:
            session: SQLAlchemy session
            position: PositionSnapshot instance to insert

        Returns:
            Inserted PositionSnapshot with id populated
        """
        session.add(position)
        session.flush()
        return position

    def insert_positions_batch(self, session: Session, positions: List[PositionSnapshot]) -> List[PositionSnapshot]:
        """Insert multiple position snapshots.

        Args:
            session: SQLAlchemy session
            positions: List of PositionSnapshot instances

        Returns:
            List of inserted PositionSnapshot instances
        """
        session.add_all(positions)
        session.flush()
        return positions

    def get_latest_positions_by_exchange(self, session: Session, exchange: str) -> List[PositionSnapshot]:
        """Get latest position for each contract for a specific exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name

        Returns:
            List of latest PositionSnapshot records per contract
        """
        # Subquery to get max time per contract for the exchange
        subquery = (
            session.query(
                PositionSnapshot.contract,
                func.max(PositionSnapshot.time).label("max_time"),
            )
            .filter(PositionSnapshot.exchange == exchange)
            .group_by(PositionSnapshot.contract)
            .subquery()
        )

        # Join to get full records with latest timestamp
        results = (
            session.query(PositionSnapshot)
            .join(
                subquery,
                (PositionSnapshot.contract == subquery.c.contract) & (PositionSnapshot.time == subquery.c.max_time),
            )
            .filter(PositionSnapshot.exchange == exchange)
            .all()
        )

        return results

    def get_latest_open_positions_by_exchange(self, session: Session, exchange: str) -> List[PositionSnapshot]:
        """Get latest open positions (non-zero size) for a specific exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name

        Returns:
            List of latest open PositionSnapshot records
        """
        positions = self.get_latest_positions_by_exchange(session, exchange)
        # Filter for non-zero positions
        return [p for p in positions if p.position_size and p.position_size != 0]

    def get_latest_positions_all_exchanges(self, session: Session) -> List[PositionSnapshot]:
        """Get latest position for each contract across all exchanges.

        Returns:
            List of latest PositionSnapshot records per exchange and contract
        """
        # Subquery to get max time per exchange and contract
        subquery = (
            session.query(
                PositionSnapshot.exchange,
                PositionSnapshot.contract,
                func.max(PositionSnapshot.time).label("max_time"),
            )
            .group_by(PositionSnapshot.exchange, PositionSnapshot.contract)
            .subquery()
        )

        # Join to get full records
        results = (
            session.query(PositionSnapshot)
            .join(
                subquery,
                (PositionSnapshot.exchange == subquery.c.exchange)
                & (PositionSnapshot.contract == subquery.c.contract)
                & (PositionSnapshot.time == subquery.c.max_time),
            )
            .all()
        )

        return results

    def get_latest_open_positions_all_exchanges(self, session: Session) -> List[PositionSnapshot]:
        """Get latest open positions (non-zero size) across all exchanges.

        Returns:
            List of latest open PositionSnapshot records
        """
        positions = self.get_latest_positions_all_exchanges(session)
        # Filter for non-zero positions
        return [p for p in positions if p.position_size and p.position_size != 0]

    def get_latest_positions_with_account_id(self, session: Session, max_age_hours: int = 8760) -> List[PositionSnapshot]:
        """Get latest position for each contract per account_id.

        Returns the most recent position snapshot for each account_id + contract combination.
        Only returns records with account_id populated (new writes after migration 033).

        Args:
            session: SQLAlchemy session
            max_age_hours: Maximum age in hours (default 8760 = 1 year, effectively no limit)

        Returns:
            List of PositionSnapshot records with account_id, grouped by account_id and contract
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        query = text(
            """
            SELECT DISTINCT ON (account_id, contract)
                id, time, exchange, contract, position_size, entry_price,
                mark_price, liquidation_price, unrealized_pnl, notional_value,
                margin_used, account_id, correlation_confidence,
                created_at, updated_at
            FROM position_snapshots
            WHERE account_id IS NOT NULL
              AND time >= :cutoff_time
            ORDER BY account_id, contract, time DESC
            """
        )

        results = session.execute(query, {"cutoff_time": cutoff_time}).fetchall()

        # Convert to PositionSnapshot objects
        positions = []
        for row in results:
            position = PositionSnapshot(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                contract=row.contract,
                position_size=row.position_size,
                entry_price=row.entry_price,
                mark_price=row.mark_price,
                liquidation_price=row.liquidation_price,
                unrealized_pnl=row.unrealized_pnl,
                notional_value=row.notional_value,
                margin_used=row.margin_used,
                account_id=row.account_id,
                correlation_confidence=row.correlation_confidence,
            )
            positions.append(position)

        return positions

    def get_latest_positions_by_account_id(
        self, session: Session, account_id: int, max_age_hours: int = 8760
    ) -> List[PositionSnapshot]:
        """Get latest positions for a specific account_id.

        Returns the most recent position snapshot for each contract for the given account.

        Args:
            session: SQLAlchemy session
            account_id: Account ID to filter by
            max_age_hours: Maximum age in hours (default 8760 = 1 year, effectively no limit)

        Returns:
            List of PositionSnapshot records for the specified account
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        query = text(
            """
            SELECT DISTINCT ON (contract)
                id, time, exchange, contract, position_size, entry_price,
                mark_price, liquidation_price, unrealized_pnl, notional_value,
                margin_used, account_id, correlation_confidence,
                created_at, updated_at
            FROM position_snapshots
            WHERE account_id = :account_id
              AND time >= :cutoff_time
            ORDER BY contract, time DESC
            """
        )

        results = session.execute(query, {"account_id": account_id, "cutoff_time": cutoff_time}).fetchall()

        positions = []
        for row in results:
            position = PositionSnapshot(
                id=row.id,
                time=row.time,
                exchange=row.exchange,
                contract=row.contract,
                position_size=row.position_size,
                entry_price=row.entry_price,
                mark_price=row.mark_price,
                liquidation_price=row.liquidation_price,
                unrealized_pnl=row.unrealized_pnl,
                notional_value=row.notional_value,
                margin_used=row.margin_used,
                account_id=row.account_id,
                correlation_confidence=row.correlation_confidence,
            )
            positions.append(position)

        return positions

    def get_positions_by_exchange(self, session: Session, exchange: str) -> List[PositionSnapshot]:
        """Get latest positions for a specific exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name to filter by

        Returns:
            List of latest PositionSnapshot records for the exchange
        """
        # Simply get latest positions for this exchange
        return self.get_latest_positions_by_exchange(session, exchange)

    def get_positions_by_contract(self, session: Session, contract: str) -> List[PositionSnapshot]:
        """Get latest positions for a specific contract across all exchanges.

        Args:
            session: SQLAlchemy session
            contract: Contract to filter by

        Returns:
            List of latest PositionSnapshot records for the contract
        """
        # Subquery to get max time per exchange for the contract
        subquery = (
            session.query(
                PositionSnapshot.exchange,
                func.max(PositionSnapshot.time).label("max_time"),
            )
            .filter(PositionSnapshot.contract == contract)
            .group_by(PositionSnapshot.exchange)
            .subquery()
        )

        # Join to get full records
        results = (
            session.query(PositionSnapshot)
            .join(
                subquery,
                (PositionSnapshot.exchange == subquery.c.exchange) & (PositionSnapshot.time == subquery.c.max_time),
            )
            .filter(PositionSnapshot.contract == contract)
            .all()
        )

        return results

    def get_position_history(
        self,
        session: Session,
        contract: Optional[str] = None,
        exchange: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[PositionSnapshot]:
        """Get position history with optional filters.

        Args:
            session: SQLAlchemy session
            contract: Filter by contract (optional)
            exchange: Filter by exchange (optional)
            start_time: Filter by start time (optional)
            end_time: Filter by end time (optional)
            limit: Maximum number of records to return

        Returns:
            List of PositionSnapshot records ordered by time DESC
        """
        query = session.query(PositionSnapshot)

        if contract:
            query = query.filter(PositionSnapshot.contract == contract)
        if exchange:
            query = query.filter(PositionSnapshot.exchange == exchange)
        if start_time:
            query = query.filter(PositionSnapshot.time >= start_time)
        if end_time:
            query = query.filter(PositionSnapshot.time <= end_time)

        query = query.order_by(desc(PositionSnapshot.time)).limit(limit)

        return query.all()

    def get_total_exposure_by_exchange(self, session: Session, exchange: str) -> Dict[str, float]:
        """Calculate total exposure for an exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name

        Returns:
            Dict with total_exposure_usd, total_unrealized_pnl
        """
        # Get latest open positions
        positions = self.get_latest_open_positions_by_exchange(session, exchange)

        # Calculate totals
        total_exposure = sum(abs(float(p.notional_value)) if p.notional_value else 0.0 for p in positions)
        total_unrealized_pnl = sum(float(p.unrealized_pnl) if p.unrealized_pnl else 0.0 for p in positions)

        return {
            "total_exposure_usd": total_exposure,
            "total_unrealized_pnl": total_unrealized_pnl,
            "open_positions_count": len(positions),
        }

    def get_aggregated_positions_by_contract(self, session: Session) -> List[Dict[str, Any]]:
        """Get aggregated positions across all exchanges by contract.

        Args:
            session: SQLAlchemy session

        Returns:
            List of dicts with contract, net_position, total_exposure, exchange_count
        """
        query = """
            WITH latest_positions AS (
                SELECT DISTINCT ON (exchange, contract)
                    exchange,
                    contract,
                    position_size,
                    notional_value,
                    unrealized_pnl,
                    time
                FROM position_snapshots
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY exchange, contract, time DESC
            )
            SELECT
                contract,
                SUM(position_size) as net_position,
                SUM(ABS(notional_value)) as total_exposure,
                SUM(unrealized_pnl) as total_unrealized_pnl,
                COUNT(DISTINCT exchange) as exchange_count,
                array_agg(DISTINCT exchange) as exchanges
            FROM latest_positions
            WHERE position_size != 0
            GROUP BY contract
            ORDER BY total_exposure DESC NULLS LAST
        """

        results = session.execute(text(query)).mappings().all()

        return [
            {
                "contract": row["contract"],
                "net_position": float(row["net_position"]) if row["net_position"] else 0.0,
                "total_exposure": float(row["total_exposure"]) if row["total_exposure"] else 0.0,
                "total_unrealized_pnl": float(row["total_unrealized_pnl"]) if row["total_unrealized_pnl"] else 0.0,
                "exchange_count": row["exchange_count"],
                "exchanges": row["exchanges"],
            }
            for row in results
        ]

    def get_aggregated_positions_by_exchange(self, session: Session) -> List[Dict[str, Any]]:
        """Get aggregated positions by exchange.

        Args:
            session: SQLAlchemy session

        Returns:
            List of dicts with exchange, total_exposure, position_count
        """
        query = """
            WITH latest_positions AS (
                SELECT DISTINCT ON (exchange, contract)
                    exchange,
                    contract,
                    position_size,
                    notional_value,
                    unrealized_pnl,
                    time
                FROM position_snapshots
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY exchange, contract, time DESC
            )
            SELECT
                exchange,
                SUM(ABS(notional_value)) as total_exposure,
                SUM(unrealized_pnl) as total_unrealized_pnl,
                COUNT(*) as position_count,
                COUNT(DISTINCT contract) as unique_contracts
            FROM latest_positions
            WHERE position_size != 0
            GROUP BY exchange
            ORDER BY total_exposure DESC NULLS LAST
        """

        results = session.execute(text(query)).mappings().all()

        return [
            {
                "exchange": row["exchange"],
                "total_exposure": float(row["total_exposure"]) if row["total_exposure"] else 0.0,
                "total_unrealized_pnl": float(row["total_unrealized_pnl"]) if row["total_unrealized_pnl"] else 0.0,
                "position_count": row["position_count"],
                "unique_contracts": row["unique_contracts"],
            }
            for row in results
        ]

    def delete_old_snapshots(
        self,
        session: Session,
        days_to_keep: int = 30,
        batch_size: int = 1000,
    ) -> int:
        """Delete position snapshots older than specified days.

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
                session.query(PositionSnapshot)
                .filter(PositionSnapshot.time < cutoff_time)
                .limit(batch_size)
                .delete(synchronize_session=False)
            )

            session.flush()
            total_deleted += result

            if result < batch_size:
                # No more records to delete
                break

        return total_deleted
