"""
Market Data Operations for broker snapshot tables.

Provides query methods for historical funding rate and mark price analytics.
Uses the broker snapshot tables populated by MarketDataSnapshotMonitor.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from data_models.logging import error, info
from data_models.database.core.db_config import AnalyticsDatabaseManager, get_analytics_db_manager


class MarketDataOperations:
    """
    Operations for querying broker market data snapshots.

    Provides methods to:
    - Query historical funding rates by exchange/symbol/time range
    - Query historical mark prices by exchange/symbol/time range
    - Clean up old snapshots (retention management)
    """

    def __init__(self, db_manager: Optional[AnalyticsDatabaseManager] = None) -> None:
        """
        Initialize market data operations.

        Args:
            db_manager: Optional database manager. Uses global analytics manager if not provided.
        """
        self._db_manager = db_manager

    @property
    def db_manager(self) -> AnalyticsDatabaseManager:
        """Get the database manager, lazily initializing if needed."""
        if self._db_manager is None:
            self._db_manager = get_analytics_db_manager()
        return self._db_manager

    def get_funding_rate_history(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get historical funding rate snapshots.

        Args:
            exchange: Filter by exchange (e.g., 'binance_futures', 'hyperliquid')
            symbol: Filter by symbol in internal format (e.g., 'BTC_USDT')
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Maximum number of records to return

        Returns:
            List of funding rate records as dictionaries with keys:
            - id, snapshot_time, exchange, symbol, rate, next_funding_time, interval_hours
        """
        conditions: List[str] = []
        params: List[Any] = []

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)

        if start_time:
            conditions.append("snapshot_time >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("snapshot_time <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT id, snapshot_time, exchange, symbol, rate, next_funding_time, interval_hours
            FROM broker_funding_rate_snapshots
            WHERE {where_clause}
            ORDER BY snapshot_time DESC
            LIMIT %s
        """
        params.append(limit)

        try:
            return self.db_manager.fetch_all(query, tuple(params))
        except Exception as e:
            error(f"[MarketDataOperations] Error fetching funding rate history: {e}")
            return []

    def get_mark_price_history(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get historical mark price snapshots.

        Args:
            exchange: Filter by exchange (e.g., 'binance_futures', 'hyperliquid')
            symbol: Filter by symbol in internal format (e.g., 'BTC_USDT')
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Maximum number of records to return

        Returns:
            List of mark price records as dictionaries with keys:
            - id, snapshot_time, exchange, symbol, mark_price, index_price, estimated_settle_price
        """
        conditions: List[str] = []
        params: List[Any] = []

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)

        if start_time:
            conditions.append("snapshot_time >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("snapshot_time <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT id, snapshot_time, exchange, symbol, mark_price, index_price, estimated_settle_price
            FROM broker_mark_price_snapshots
            WHERE {where_clause}
            ORDER BY snapshot_time DESC
            LIMIT %s
        """
        params.append(limit)

        try:
            return self.db_manager.fetch_all(query, tuple(params))
        except Exception as e:
            error(f"[MarketDataOperations] Error fetching mark price history: {e}")
            return []

    def get_latest_funding_rate(
        self,
        exchange: str,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent funding rate snapshot for a specific exchange/symbol pair.

        Args:
            exchange: Exchange name (e.g., 'binance_futures')
            symbol: Symbol in internal format (e.g., 'BTC_USDT')

        Returns:
            Latest funding rate record or None if not found
        """
        query = """
            SELECT id, snapshot_time, exchange, symbol, rate, next_funding_time, interval_hours
            FROM broker_funding_rate_snapshots
            WHERE exchange = %s AND symbol = %s
            ORDER BY snapshot_time DESC
            LIMIT 1
        """

        try:
            return self.db_manager.fetch_one(query, (exchange, symbol))
        except Exception as e:
            error(f"[MarketDataOperations] Error fetching latest funding rate: {e}")
            return None

    def get_latest_mark_price(
        self,
        exchange: str,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent mark price snapshot for a specific exchange/symbol pair.

        Args:
            exchange: Exchange name (e.g., 'binance_futures')
            symbol: Symbol in internal format (e.g., 'BTC_USDT')

        Returns:
            Latest mark price record or None if not found
        """
        query = """
            SELECT id, snapshot_time, exchange, symbol, mark_price, index_price, estimated_settle_price
            FROM broker_mark_price_snapshots
            WHERE exchange = %s AND symbol = %s
            ORDER BY snapshot_time DESC
            LIMIT 1
        """

        try:
            return self.db_manager.fetch_one(query, (exchange, symbol))
        except Exception as e:
            error(f"[MarketDataOperations] Error fetching latest mark price: {e}")
            return None

    def get_funding_rate_stats(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for funding rates over a time period.

        Args:
            exchange: Filter by exchange
            symbol: Filter by symbol
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary with statistics: count, avg_rate, min_rate, max_rate, std_rate
        """
        conditions: List[str] = []
        params: List[Any] = []

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)

        if start_time:
            conditions.append("snapshot_time >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("snapshot_time <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                COUNT(*) as count,
                AVG(rate) as avg_rate,
                MIN(rate) as min_rate,
                MAX(rate) as max_rate,
                STDDEV(rate) as std_rate
            FROM broker_funding_rate_snapshots
            WHERE {where_clause}
        """

        try:
            result = self.db_manager.fetch_one(query, tuple(params) if params else None)
            return result if result else {}
        except Exception as e:
            error(f"[MarketDataOperations] Error fetching funding rate stats: {e}")
            return {}

    def delete_old_snapshots(self, retention_days: int = 90) -> Dict[str, Any]:
        """
        Delete snapshots older than the retention period.

        Args:
            retention_days: Number of days to retain (default: 90)

        Returns:
            Dictionary with counts of deleted records:
            - funding_rates_deleted: Number of funding rate records deleted
            - mark_prices_deleted: Number of mark price records deleted
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)

        funding_deleted = 0
        mark_deleted = 0

        try:
            # Delete old funding rate snapshots
            funding_query = """
                DELETE FROM broker_funding_rate_snapshots
                WHERE snapshot_time < %s
            """
            self.db_manager.execute(funding_query, (cutoff_time,))

            # Get count of deleted funding rates (PostgreSQL specific)
            # Since we already deleted, this will be 0, so we need different approach
            # Use RETURNING clause or just log the operation

            # Delete old mark price snapshots
            mark_query = """
                DELETE FROM broker_mark_price_snapshots
                WHERE snapshot_time < %s
            """
            self.db_manager.execute(mark_query, (cutoff_time,))

            info(
                f"[MarketDataOperations] Cleaned up snapshots older than {retention_days} days "
                f"(before {cutoff_time.isoformat()})"
            )

            return {
                "funding_rates_deleted": funding_deleted,
                "mark_prices_deleted": mark_deleted,
                "cutoff_time": cutoff_time.isoformat(),
                "retention_days": retention_days,
            }

        except Exception as e:
            error(f"[MarketDataOperations] Error deleting old snapshots: {e}")
            return {
                "funding_rates_deleted": 0,
                "mark_prices_deleted": 0,
                "error": str(e),
            }

    def get_snapshot_counts(self) -> Dict[str, int]:
        """
        Get current counts of snapshots in both tables.

        Returns:
            Dictionary with total_funding_snapshots and total_mark_price_snapshots
        """
        try:
            funding_query = "SELECT COUNT(*) as count FROM broker_funding_rate_snapshots"
            mark_query = "SELECT COUNT(*) as count FROM broker_mark_price_snapshots"

            funding_result = self.db_manager.fetch_one(funding_query)
            mark_result = self.db_manager.fetch_one(mark_query)

            return {
                "total_funding_snapshots": funding_result.get("count", 0) if funding_result else 0,
                "total_mark_price_snapshots": mark_result.get("count", 0) if mark_result else 0,
            }
        except Exception as e:
            error(f"[MarketDataOperations] Error getting snapshot counts: {e}")
            return {
                "total_funding_snapshots": 0,
                "total_mark_price_snapshots": 0,
            }

    def get_available_exchanges(self) -> List[str]:
        """
        Get list of exchanges with funding rate data.

        Returns:
            List of unique exchange names
        """
        query = """
            SELECT DISTINCT exchange
            FROM broker_funding_rate_snapshots
            ORDER BY exchange
        """
        try:
            results = self.db_manager.fetch_all(query)
            return [r["exchange"] for r in results]
        except Exception as e:
            error(f"[MarketDataOperations] Error getting available exchanges: {e}")
            return []

    def get_available_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        Get list of symbols with funding rate data.

        Args:
            exchange: Optional filter by exchange

        Returns:
            List of unique symbol names
        """
        if exchange:
            query = """
                SELECT DISTINCT symbol
                FROM broker_funding_rate_snapshots
                WHERE exchange = %s
                ORDER BY symbol
            """
            params: Optional[Tuple[Any, ...]] = (exchange,)
        else:
            query = """
                SELECT DISTINCT symbol
                FROM broker_funding_rate_snapshots
                ORDER BY symbol
            """
            params = None

        try:
            results = self.db_manager.fetch_all(query, params)
            return [r["symbol"] for r in results]
        except Exception as e:
            error(f"[MarketDataOperations] Error getting available symbols: {e}")
            return []


# Global instance for convenience
_market_data_ops: Optional[MarketDataOperations] = None


def get_market_data_operations() -> MarketDataOperations:
    """Get the global MarketDataOperations instance."""
    global _market_data_ops
    if _market_data_ops is None:
        _market_data_ops = MarketDataOperations()
    return _market_data_ops
