"""
Gateway health snapshot model for centralized health cache.

This model represents a point-in-time health status from an exchange gateway.
Gateways push these snapshots to the centralized cache, and the engine reads
from the cache to make trading decisions.
"""

from typing import Optional

from data_models.models.domain.base import StrictBaseModel


class GatewayHealthSnapshot(StrictBaseModel):
    """
    Point-in-time health snapshot from an exchange gateway.

    This model captures all health-related information that the engine
    needs to make trading decisions. Gateways push updates when their
    health state changes.

    Attributes:
        exchange: Exchange identifier (e.g., "binance_futures", "bybit")
        timestamp: Snapshot creation time in milliseconds (epoch)
        is_connected: REST API connection status
        is_ws_healthy: Overall WebSocket health status
        last_reconnect_ms: Timestamp of last WebSocket reconnection (ms), None if never reconnected
        reconnect_count: Total number of WebSocket reconnections since startup
        in_grace_period: Whether orders should be blocked after recent reconnect
        grace_period_until_ms: When grace period ends (ms), None if not in grace period
        error_message: Error description if unhealthy, None if healthy

    Usage:
        # Gateway pushes health update
        snapshot = GatewayHealthSnapshot(
            exchange="binance_futures",
            timestamp=int(time.time() * 1000),
            is_connected=True,
            is_ws_healthy=True,
            reconnect_count=0,
            in_grace_period=False,
        )
        market_data_broker.update_gateway_health_from_gateway(snapshot)

        # Engine checks health before creating orders
        if market_data_broker.can_exchange_trade("binance_futures"):
            create_maker_order()
    """

    exchange: str
    timestamp: int
    is_connected: bool
    is_ws_healthy: bool
    last_reconnect_ms: Optional[int] = None
    reconnect_count: int = 0
    in_grace_period: bool = False
    grace_period_until_ms: Optional[int] = None
    error_message: Optional[str] = None

    # Per-stream WS health (optional - only populated by exchanges that report it)
    subprocess_alive: bool = True
    order_ws_connected: Optional[bool] = None
    private_ws_connected: Optional[bool] = None
    public_ws_connected: Optional[bool] = None

    @property
    def can_trade(self) -> bool:
        """
        Determine if trading is allowed based on health state.

        Trading is allowed when:
        1. REST API is connected
        2. WebSocket is healthy
        3. Not in grace period after reconnection

        Returns:
            True if all conditions met, False otherwise
        """
        return self.is_connected and self.is_ws_healthy and not self.in_grace_period


__all__ = ["GatewayHealthSnapshot"]
