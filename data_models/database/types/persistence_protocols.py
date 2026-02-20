"""Persistence-layer protocols for database ingress data.

These protocols describe the minimum attribute surface the database layer
needs from runtime objects. Keeping this boundary protocol-based prevents
direct imports from runtime domain model modules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Sequence, Tuple


class OrderLike(Protocol):
    """Minimum order shape required by OrderExecution."""

    exchange_order_id: Optional[Any]
    internal_id: Optional[Any]
    status: Optional[Any]
    side: Optional[Any]
    order_type: Optional[Any]
    contract: str
    price: Optional[float]
    amount: Optional[float]
    filled_amount: Optional[float]
    avg_price: Optional[float]
    timestamp: Optional[float]
    raw_exchange_data: Optional[Dict[str, Any]]


class OrderbookLevelLike(Protocol):
    """Single orderbook level."""

    price: float
    amount: float


class OrderbookLike(Protocol):
    """Minimum orderbook shape required by persistence models."""

    bids: Sequence[OrderbookLevelLike]
    asks: Sequence[OrderbookLevelLike]
    timestamp: Optional[float]
    contract: str
    sequence_number: Optional[int]


class PositionLike(Protocol):
    """Minimum position shape required by PositionSnapshot."""

    contract: str
    size: Optional[float]
    mark_price: Optional[float]
    notional_value: Optional[float]
    unrealized_pnl: Optional[float]
    entry_price: Optional[float]
    liquidation_price: Optional[float]


class BalanceLike(Protocol):
    """Minimum balance shape required by AccountBalance."""

    currency: str
    total: Optional[float]
    locked: Optional[float]
    free: Optional[float]


class LatencyDataLike(Protocol):
    """Minimum latency payload shape required by LatencyMetric."""

    orderbook_latency_maker: Optional[float]
    maker_latency: Optional[float]
    cancel_request_latency: Optional[float]
    cycle_latency: Optional[float]
    fill_notification_latency_ms: Optional[float]
    timestamp: Optional[float]
    maker_exchange: Optional[str]
    taker_exchange: Optional[str]
    maker_contract: Optional[str]
    state_timestamps: Optional[Dict[str, Any]]
    route_id: Optional[int]
    bot_id: Optional[int]
    client_id: Optional[str]


class BrokerMarketDataLike(Protocol):
    """Models accepted by DatabaseWriter broker market-data queue."""

    @staticmethod
    def batch_insert_query() -> str:
        """Get batch INSERT SQL query."""
        ...

    def to_insert_query(self, exchange: str) -> Tuple[str, Tuple[Any, ...]]:
        """Get SQL and params for a specific exchange."""
        ...
