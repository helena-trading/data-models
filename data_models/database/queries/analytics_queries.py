"""Analytics queries for the database."""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import pandas as pd

# Use analytics database for all analytics queries
from data_models.database.core.db_config import get_analytics_db_manager


class AnalyticsQueries:
    """Provides analytics queries for the Helena bot database.

    NOTE: Uses ANALYTICS database for all queries (orders, trades, positions, metrics).
    """

    def __init__(self) -> None:
        self.db = get_analytics_db_manager()

    def get_trading_summary(  # type: ignore[no-any-unimported]
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get trading summary statistics."""
        query = """
            SELECT
                DATE(time) as trade_date,
                exchange,
                contract,
                COUNT(*) as order_count,
                SUM(CASE WHEN status = 'filled' THEN 1 ELSE 0 END) as filled_orders,
                SUM(size * price) as total_volume,
                AVG(price) as avg_price,
                SUM(fees) as total_fees
            FROM order_executions
            WHERE 1=1
        """

        params = []
        if start_date:
            query += " AND time >= %s"
            params.append(start_date)
        if end_date:
            query += " AND time <= %s"
            params.append(end_date)

        query += " GROUP BY DATE(time), exchange, contract ORDER BY trade_date DESC"

        if self.db.pool is None:
            raise RuntimeError("Database pool not initialized")
        return pd.read_sql_query(query, self.db.pool.getconn(), params=params or None)

    def get_latency_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get latency statistics for the last N hours."""
        query = """
            SELECT
                metric_type,
                exchange_maker,
                exchange_taker,
                COUNT(*) as sample_count,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as median_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency
            FROM latency_metrics
            WHERE time > NOW() - INTERVAL '%s hours'
            GROUP BY metric_type, exchange_maker, exchange_taker
            ORDER BY metric_type, avg_latency
        """

        results = self.db.fetch_all(query, (hours,))

        # Group by metric type
        stats: Dict[str, Any] = {}
        for row in results:
            metric_type = row["metric_type"]
            if metric_type not in stats:
                stats[metric_type] = []
            stats[metric_type].append(
                {
                    "exchanges": f"{row['exchange_maker']} -> {row['exchange_taker']}",
                    "samples": row["sample_count"],
                    "avg_ms": round(row["avg_latency"], 2),
                    "min_ms": row["min_latency"],
                    "max_ms": row["max_latency"],
                    "median_ms": round(row["median_latency"], 2),
                    "p95_ms": round(row["p95_latency"], 2),
                    "p99_ms": round(row["p99_latency"], 2),
                }
            )

        return stats

    def get_pnl_summary(self, days: int = 7) -> pd.DataFrame:  # type: ignore[no-any-unimported]
        """Get P&L summary from block trades."""
        query = """
            SELECT
                DATE(time) as trade_date,
                maker_exchange,
                taker_exchange,
                contract,
                COUNT(*) as trade_count,
                SUM(size) as total_size,
                SUM(size * maker_price) as total_volume,
                SUM(spread_captured) as gross_profit,
                SUM(total_fees) as total_fees,
                SUM(net_profit) as net_profit,
                AVG(spread_captured / NULLIF(size * maker_price, 0) * 10000) as avg_spread_bps,
                AVG(execution_time_ms) as avg_execution_ms
            FROM block_trades
            WHERE lifecycle_state = 'completed'
              AND time > NOW() - INTERVAL '%s days'
            GROUP BY DATE(time), maker_exchange, taker_exchange, contract
            ORDER BY trade_date DESC, net_profit DESC
        """

        if self.db.pool is None:
            raise RuntimeError("Database pool not initialized")
        return pd.read_sql_query(query, self.db.pool.getconn(), params=(days,))

    def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current positions across all exchanges."""
        query = """
            WITH latest_positions AS (
                SELECT DISTINCT ON (exchange, contract)
                    time,
                    exchange,
                    contract,
                    position_size,
                    mark_price,
                    notional_value,
                    unrealized_pnl,
                    margin_used,
                    entry_price
                FROM position_snapshots
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY exchange, contract, time DESC
            )
            SELECT * FROM latest_positions
            WHERE position_size != 0
            ORDER BY ABS(notional_value) DESC
        """

        results = self.db.fetch_all(query)

        positions = []
        for row in results:
            positions.append(
                {
                    "time": row["time"],
                    "exchange": row["exchange"],
                    "contract": row["contract"],
                    "size": float(row["position_size"]),
                    "mark_price": (float(row["mark_price"]) if row["mark_price"] else None),
                    "notional": (float(row["notional_value"]) if row["notional_value"] else None),
                    "pnl": (float(row["unrealized_pnl"]) if row["unrealized_pnl"] else None),
                    "margin": float(row["margin_used"]) if row["margin_used"] else None,
                    "entry_price": (float(row["entry_price"]) if row["entry_price"] else None),
                }
            )

        return positions

    def get_order_fill_rate(self, hours: int = 24) -> Dict[str, Any]:
        """Get order fill rates by exchange."""
        query = """
            SELECT
                exchange,
                COUNT(*) as total_orders,
                SUM(CASE WHEN status IN ('filled', 'partially_filled') THEN 1 ELSE 0 END) as filled_orders,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders
            FROM order_executions
            WHERE time > NOW() - INTERVAL '%s hours'
            GROUP BY exchange
        """

        results = self.db.fetch_all(query, (hours,))

        fill_rates: Dict[str, Any] = {}
        for row in results:
            total = row["total_orders"]
            if total is not None and total > 0:
                fill_rates[row["exchange"]] = {
                    "fill_rate": round(row["filled_orders"] / total * 100, 2),
                    "cancel_rate": round(row["cancelled_orders"] / total * 100, 2),
                    "reject_rate": round(row["rejected_orders"] / total * 100, 2),
                    "total_orders": total,
                }

        return fill_rates

    def get_spread_analysis(self, hours: int = 1) -> pd.DataFrame:  # type: ignore[no-any-unimported]
        """Analyze spreads across exchanges."""
        query = """
            SELECT
                time_bucket('1 minute', time) AS bucket,
                exchange,
                contract,
                AVG(spread_bps) as avg_spread_bps,
                MIN(spread_bps) as min_spread_bps,
                MAX(spread_bps) as max_spread_bps,
                AVG(bid_size) as avg_bid_size,
                AVG(ask_size) as avg_ask_size
            FROM market_data
            WHERE time > NOW() - INTERVAL '%s hours'
              AND spread_bps IS NOT NULL
            GROUP BY bucket, exchange, contract
            ORDER BY bucket DESC, exchange, contract
        """

        if self.db.pool is None:
            raise RuntimeError("Database pool not initialized")
        return pd.read_sql_query(query, self.db.pool.getconn(), params=(hours,))

    def get_hourly_volume(self, days: int = 7) -> pd.DataFrame:  # type: ignore[no-any-unimported]
        """Get hourly trading volume."""
        query = """
            SELECT
                time_bucket('1 hour', time) AS hour,
                exchange,
                SUM(size * price) as volume,
                COUNT(*) as trade_count
            FROM order_executions
            WHERE time > NOW() - INTERVAL '%s days'
              AND status = 'filled'
            GROUP BY hour, exchange
            ORDER BY hour DESC
        """

        if self.db.pool is None:
            raise RuntimeError("Database pool not initialized")
        return pd.read_sql_query(query, self.db.pool.getconn(), params=(days,))

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        metrics = {
            "latency_stats": self.get_latency_statistics(hours),
            "fill_rates": self.get_order_fill_rate(hours),
            "current_positions": self.get_current_positions(),
        }

        # Add summary statistics
        pnl_df = self.get_pnl_summary(days=1)
        if not pnl_df.empty:
            metrics["daily_pnl"] = {
                "gross_profit": float(pnl_df["gross_profit"].sum()),
                "total_fees": float(pnl_df["total_fees"].sum()),
                "net_profit": float(pnl_df["net_profit"].sum()),
                "trade_count": int(pnl_df["trade_count"].sum()),
                "avg_spread_bps": float(pnl_df["avg_spread_bps"].mean()),
            }

        return metrics

    def get_recent_errors(self, hours: int = 24, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        """Get recent error logs."""
        query = """
            SELECT
                time,
                level,
                exchange,
                component,
                error_type,
                message,
                context,
                resolved,
                resolution_notes
            FROM error_logs
            WHERE time > NOW() - INTERVAL '%s hours'
        """

        params = [hours]
        if unresolved_only:
            query += " AND resolved = FALSE"

        query += " ORDER BY time DESC LIMIT 100"

        results = self.db.fetch_all(query, tuple(params))

        errors = []
        for row in results:
            errors.append(
                {
                    "time": row["time"],
                    "level": row["level"],
                    "exchange": row["exchange"],
                    "component": row["component"],
                    "error_type": row["error_type"],
                    "message": row["message"],
                    "context": row["context"],
                    "resolved": row["resolved"],
                    "resolution_notes": row["resolution_notes"],
                }
            )

        return errors

    def get_error_frequency(self, days: int = 7) -> pd.DataFrame:  # type: ignore[no-any-unimported]
        """Get error frequency analysis."""
        query = """
            SELECT
                DATE(time) as error_date,
                level,
                component,
                error_type,
                exchange,
                COUNT(*) as error_count
            FROM error_logs
            WHERE time > NOW() - INTERVAL '%s days'
            GROUP BY DATE(time), level, component, error_type, exchange
            ORDER BY error_date DESC, error_count DESC
        """

        if self.db.pool is None:
            raise RuntimeError("Database pool not initialized")
        return pd.read_sql_query(query, self.db.pool.getconn(), params=(days,))

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary statistics."""
        query = """
            SELECT
                level,
                COUNT(*) as count,
                COUNT(DISTINCT component) as affected_components,
                COUNT(DISTINCT exchange) as affected_exchanges
            FROM error_logs
            WHERE time > NOW() - INTERVAL '%s hours'
            GROUP BY level
        """

        results = self.db.fetch_all(query, (hours,))

        summary: Dict[str, Any] = {
            "total_errors": 0,
            "by_level": {},
            "recent_errors": self.get_recent_errors(hours=1, unresolved_only=True)[:10],
        }

        for row in results:
            summary["total_errors"] += row["count"]
            by_level = cast(Dict[str, Any], summary["by_level"])
            by_level[row["level"]] = {
                "count": row["count"],
                "affected_components": row["affected_components"],
                "affected_exchanges": row["affected_exchanges"],
            }

        return summary


# Singleton instance
_analytics = None


def get_analytics() -> AnalyticsQueries:
    """Get the analytics queries instance."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsQueries()
    return _analytics
