"""
Funding Engine Operations for dashboard visualization API.

Provides query methods for funding engine adjustments and spread impacts
stored in the analytics database.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from data_models.logging import error, info
from data_models.database.core.db_config import AnalyticsDatabaseManager, get_analytics_db_manager


class FundingEngineOperations:
    """
    Operations for querying funding engine data.

    Provides methods to:
    - Query historical price adjustments by exchange/contract/time range
    - Query historical spread impacts by route/contract/time range
    - Get aggregated statistics for dashboard visualization
    - Get time-series data for charting
    """

    def __init__(self, db_manager: Optional[AnalyticsDatabaseManager] = None) -> None:
        """
        Initialize funding engine operations.

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

    # ==================== ADJUSTMENTS ====================

    def get_adjustments(
        self,
        exchange: Optional[str] = None,
        contract: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get historical price adjustment records.

        Args:
            exchange: Filter by exchange (e.g., 'binance_futures')
            contract: Filter by contract (e.g., 'BTC_USD')
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination

        Returns:
            Tuple of (list of adjustment records, total count)
        """
        conditions: List[str] = []
        params: List[Any] = []

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if contract:
            conditions.append("contract = %s")
            params.append(contract)

        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as count
            FROM funding_engine_adjustments
            WHERE {where_clause}
        """

        # Get data with pagination
        data_query = f"""
            SELECT id, timestamp, exchange, contract,
                   original_bid, original_ask, adjusted_bid, adjusted_ask,
                   bid_delta, ask_delta, delta_pct,
                   funding_rate, funding_interval_hours,
                   horizon_hours, safety_buffer
            FROM funding_engine_adjustments
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """

        try:
            count_result = self.db_manager.fetch_one(count_query, tuple(params) if params else None)
            total = count_result.get("count", 0) if count_result else 0

            data_params = params + [limit, offset]
            results = self.db_manager.fetch_all(data_query, tuple(data_params))

            return results, total
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching adjustments: {e}")
            return [], 0

    def get_latest_adjustments(
        self,
        exchange: Optional[str] = None,
        contract: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent adjustment for each exchange-contract pair.

        Uses DISTINCT ON for efficient deduplication.

        Args:
            exchange: Optional filter by exchange
            contract: Optional filter by contract

        Returns:
            List of latest adjustment records (one per exchange-contract pair)
        """
        conditions: List[str] = []
        params: List[Any] = []

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if contract:
            conditions.append("contract = %s")
            params.append(contract)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT DISTINCT ON (exchange, contract)
                   id, timestamp, exchange, contract,
                   original_bid, original_ask, adjusted_bid, adjusted_ask,
                   bid_delta, ask_delta, delta_pct,
                   funding_rate, funding_interval_hours,
                   horizon_hours, safety_buffer
            FROM funding_engine_adjustments
            WHERE {where_clause}
            ORDER BY exchange, contract, timestamp DESC
        """

        try:
            return self.db_manager.fetch_all(query, tuple(params) if params else None)
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching latest adjustments: {e}")
            return []

    def get_adjustment_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: str = "exchange",
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for adjustments.

        Args:
            start_time: Start of time range
            end_time: End of time range
            group_by: Grouping dimension ('exchange', 'contract', 'both')

        Returns:
            Dictionary with grouped statistics and overall summary
        """
        conditions: List[str] = []
        params: List[Any] = []

        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        result: Dict[str, Any] = {}

        try:
            # By exchange
            if group_by in ("exchange", "both"):
                exchange_query = f"""
                    SELECT
                        exchange,
                        COUNT(*) as count,
                        AVG(delta_pct) as avg_delta_pct,
                        MAX(delta_pct) as max_delta_pct,
                        MIN(delta_pct) as min_delta_pct,
                        SUM(CASE WHEN delta_pct > 0 THEN 1 ELSE 0 END) as positive_count,
                        SUM(CASE WHEN delta_pct < 0 THEN 1 ELSE 0 END) as negative_count
                    FROM funding_engine_adjustments
                    WHERE {where_clause}
                    GROUP BY exchange
                    ORDER BY exchange
                """
                exchange_results = self.db_manager.fetch_all(exchange_query, tuple(params) if params else None)
                result["by_exchange"] = {r["exchange"]: r for r in exchange_results}

            # By contract
            if group_by in ("contract", "both"):
                contract_query = f"""
                    SELECT
                        contract,
                        COUNT(*) as count,
                        AVG(delta_pct) as avg_delta_pct,
                        MAX(delta_pct) as max_delta_pct,
                        MIN(delta_pct) as min_delta_pct,
                        SUM(CASE WHEN delta_pct > 0 THEN 1 ELSE 0 END) as positive_count,
                        SUM(CASE WHEN delta_pct < 0 THEN 1 ELSE 0 END) as negative_count
                    FROM funding_engine_adjustments
                    WHERE {where_clause}
                    GROUP BY contract
                    ORDER BY contract
                """
                contract_results = self.db_manager.fetch_all(contract_query, tuple(params) if params else None)
                result["by_contract"] = {r["contract"]: r for r in contract_results}

            # Overall
            overall_query = f"""
                SELECT
                    COUNT(*) as total_records,
                    AVG(delta_pct) as avg_delta_pct,
                    MAX(delta_pct) as max_delta_pct,
                    MIN(delta_pct) as min_delta_pct,
                    SUM(CASE WHEN delta_pct > 0 THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN delta_pct < 0 THEN 1 ELSE 0 END) as negative_count
                FROM funding_engine_adjustments
                WHERE {where_clause}
            """
            overall_result = self.db_manager.fetch_one(overall_query, tuple(params) if params else None)
            result["overall"] = overall_result if overall_result else {}

            return result
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching adjustment stats: {e}")
            return {}

    def get_adjustment_timeseries(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: str = "1h",
        exchange: Optional[str] = None,
        contract: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get time-bucketed adjustment data for charting.

        Args:
            start_time: Start of time range
            end_time: End of time range
            interval: Time bucket size ('1m', '5m', '15m', '1h', '4h', '1d')
            exchange: Optional filter by exchange
            contract: Optional filter by contract

        Returns:
            List of time-bucketed aggregated data
        """
        # Map interval to PostgreSQL interval
        interval_map = {
            "1m": "1 minute",
            "5m": "5 minutes",
            "15m": "15 minutes",
            "1h": "1 hour",
            "4h": "4 hours",
            "1d": "1 day",
        }
        pg_interval = interval_map.get(interval, "1 hour")

        conditions: List[str] = []
        params: List[Any] = []

        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if contract:
            conditions.append("contract = %s")
            params.append(contract)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                date_trunc({pg_interval.split()[1]!r}, timestamp) as bucket,
                COUNT(*) as count,
                AVG(delta_pct) as avg_delta_pct,
                MAX(delta_pct) as max_delta_pct,
                MIN(delta_pct) as min_delta_pct,
                AVG(ABS(bid_delta)) as avg_bid_delta,
                AVG(ABS(ask_delta)) as avg_ask_delta
            FROM funding_engine_adjustments
            WHERE {where_clause}
            GROUP BY bucket
            ORDER BY bucket ASC
        """

        try:
            return self.db_manager.fetch_all(query, tuple(params) if params else None)
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching adjustment timeseries: {e}")
            return []

    # ==================== SPREAD IMPACTS ====================

    def get_spread_impacts(
        self,
        maker_exchange: Optional[str] = None,
        taker_exchange: Optional[str] = None,
        contract: Optional[str] = None,
        impact_direction: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get historical spread impact records.

        Args:
            maker_exchange: Filter by maker exchange
            taker_exchange: Filter by taker exchange
            contract: Filter by contract
            impact_direction: Filter by impact ('wider', 'narrower', 'neutral')
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination

        Returns:
            Tuple of (list of spread impact records, total count)
        """
        conditions: List[str] = []
        params: List[Any] = []

        if maker_exchange:
            conditions.append("maker_exchange = %s")
            params.append(maker_exchange)

        if taker_exchange:
            conditions.append("taker_exchange = %s")
            params.append(taker_exchange)

        if contract:
            conditions.append("contract = %s")
            params.append(contract)

        if impact_direction:
            conditions.append("impact_direction = %s")
            params.append(impact_direction)

        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as count
            FROM funding_engine_spread_impacts
            WHERE {where_clause}
        """

        # Get data with pagination
        data_query = f"""
            SELECT id, timestamp, maker_exchange, taker_exchange, contract,
                   raw_spread_pct, adjusted_spread_pct, spread_delta_pct,
                   impact_direction, horizon_hours, safety_buffer
            FROM funding_engine_spread_impacts
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """

        try:
            count_result = self.db_manager.fetch_one(count_query, tuple(params) if params else None)
            total = count_result.get("count", 0) if count_result else 0

            data_params = params + [limit, offset]
            results = self.db_manager.fetch_all(data_query, tuple(data_params))

            # Add computed route field
            for r in results:
                r["route"] = f"{r['maker_exchange']}→{r['taker_exchange']}"

            return results, total
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching spread impacts: {e}")
            return [], 0

    def get_latest_spread_impacts(
        self,
        maker_exchange: Optional[str] = None,
        taker_exchange: Optional[str] = None,
        contract: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent spread impact for each route-contract pair.

        Uses DISTINCT ON for efficient deduplication.

        Args:
            maker_exchange: Optional filter by maker exchange
            taker_exchange: Optional filter by taker exchange
            contract: Optional filter by contract

        Returns:
            List of latest spread impact records (one per route-contract pair)
        """
        conditions: List[str] = []
        params: List[Any] = []

        if maker_exchange:
            conditions.append("maker_exchange = %s")
            params.append(maker_exchange)

        if taker_exchange:
            conditions.append("taker_exchange = %s")
            params.append(taker_exchange)

        if contract:
            conditions.append("contract = %s")
            params.append(contract)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT DISTINCT ON (maker_exchange, taker_exchange, contract)
                   id, timestamp, maker_exchange, taker_exchange, contract,
                   raw_spread_pct, adjusted_spread_pct, spread_delta_pct,
                   impact_direction, horizon_hours, safety_buffer
            FROM funding_engine_spread_impacts
            WHERE {where_clause}
            ORDER BY maker_exchange, taker_exchange, contract, timestamp DESC
        """

        try:
            results = self.db_manager.fetch_all(query, tuple(params) if params else None)

            # Add computed route field
            for r in results:
                r["route"] = f"{r['maker_exchange']}→{r['taker_exchange']}"

            return results
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching latest spread impacts: {e}")
            return []

    def get_spread_impact_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for spread impacts.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary with route and contract statistics, plus best routes
        """
        conditions: List[str] = []
        params: List[Any] = []

        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        result: Dict[str, Any] = {}

        try:
            # By route
            route_query = f"""
                SELECT
                    maker_exchange || '→' || taker_exchange as route,
                    COUNT(*) as count,
                    AVG(spread_delta_pct) as avg_spread_delta_pct,
                    SUM(CASE WHEN impact_direction = 'narrower' THEN 1 ELSE 0 END) as narrower_count,
                    SUM(CASE WHEN impact_direction = 'wider' THEN 1 ELSE 0 END) as wider_count,
                    SUM(CASE WHEN impact_direction = 'neutral' THEN 1 ELSE 0 END) as neutral_count
                FROM funding_engine_spread_impacts
                WHERE {where_clause}
                GROUP BY maker_exchange, taker_exchange
                ORDER BY route
            """
            route_results = self.db_manager.fetch_all(route_query, tuple(params) if params else None)
            result["by_route"] = {r["route"]: r for r in route_results}

            # By contract
            contract_query = f"""
                SELECT
                    contract,
                    COUNT(*) as count,
                    AVG(spread_delta_pct) as avg_spread_delta_pct,
                    SUM(CASE WHEN impact_direction = 'narrower' THEN 1 ELSE 0 END) as narrower_count,
                    SUM(CASE WHEN impact_direction = 'wider' THEN 1 ELSE 0 END) as wider_count
                FROM funding_engine_spread_impacts
                WHERE {where_clause}
                GROUP BY contract
                ORDER BY contract
            """
            contract_results = self.db_manager.fetch_all(contract_query, tuple(params) if params else None)
            result["by_contract"] = {r["contract"]: r for r in contract_results}

            # Best routes (most beneficial - most negative spread delta = tighter spreads)
            best_routes_query = f"""
                SELECT
                    maker_exchange || '→' || taker_exchange as route,
                    contract,
                    AVG(spread_delta_pct) as avg_benefit
                FROM funding_engine_spread_impacts
                WHERE {where_clause} AND impact_direction = 'narrower'
                GROUP BY maker_exchange, taker_exchange, contract
                ORDER BY avg_benefit ASC
                LIMIT 10
            """
            best_routes = self.db_manager.fetch_all(best_routes_query, tuple(params) if params else None)
            result["best_routes"] = best_routes

            # Overall
            overall_query = f"""
                SELECT
                    COUNT(*) as total_records,
                    AVG(spread_delta_pct) as avg_spread_delta_pct,
                    SUM(CASE WHEN impact_direction = 'narrower' THEN 1 ELSE 0 END) as narrower_count,
                    SUM(CASE WHEN impact_direction = 'wider' THEN 1 ELSE 0 END) as wider_count,
                    SUM(CASE WHEN impact_direction = 'neutral' THEN 1 ELSE 0 END) as neutral_count
                FROM funding_engine_spread_impacts
                WHERE {where_clause}
            """
            overall_result = self.db_manager.fetch_one(overall_query, tuple(params) if params else None)
            result["overall"] = overall_result if overall_result else {}

            return result
        except Exception as e:
            error(f"[FundingEngineOperations] Error fetching spread impact stats: {e}")
            return {}

    # ==================== CLEANUP ====================

    def delete_old_data(self, retention_days: int = 90) -> Dict[str, Any]:
        """
        Delete funding engine data older than the retention period.

        Args:
            retention_days: Number of days to retain (default: 90)

        Returns:
            Dictionary with deletion results
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)

        try:
            # Delete old adjustments
            adj_query = """
                DELETE FROM funding_engine_adjustments
                WHERE timestamp < %s
            """
            self.db_manager.execute(adj_query, (cutoff_time,))

            # Delete old spread impacts
            spread_query = """
                DELETE FROM funding_engine_spread_impacts
                WHERE timestamp < %s
            """
            self.db_manager.execute(spread_query, (cutoff_time,))

            info(
                f"[FundingEngineOperations] Cleaned up data older than {retention_days} days "
                f"(before {cutoff_time.isoformat()})"
            )

            return {
                "success": True,
                "cutoff_time": cutoff_time.isoformat(),
                "retention_days": retention_days,
            }

        except Exception as e:
            error(f"[FundingEngineOperations] Error deleting old data: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Global instance for convenience
_funding_engine_ops: Optional[FundingEngineOperations] = None


def get_funding_engine_operations() -> FundingEngineOperations:
    """Get the global FundingEngineOperations instance."""
    global _funding_engine_ops
    if _funding_engine_ops is None:
        _funding_engine_ops = FundingEngineOperations()
    return _funding_engine_ops
