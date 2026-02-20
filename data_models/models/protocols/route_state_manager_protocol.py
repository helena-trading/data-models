"""
Route State Manager Protocol

Defines the interface for route state managers used by the command panel.

StateHolder implements this protocol for use with executors and command panel.
"""

from typing import Any, Optional, Protocol, runtime_checkable

from data_models.models.domain.market.quote import Quote
from data_models.models.domain.order.ids import InternalOrderId
from data_models.models.enums.trading import BotState


@runtime_checkable
class IRouteStateManager(Protocol):
    """
    Protocol for route state managers.

    StateHolder implements this protocol for use with executors
    and the command panel.

    This defines the common interface for inspecting route state, including:
    - Route identification
    - Contract information
    - Order IDs and state
    - Quote generation tracking
    """

    # ==================== Core Properties ====================

    @property
    def route(self) -> str:
        """Route identifier (e.g., 'route1', 'route2')."""
        ...

    # ==================== State Methods ====================

    def get_bot_state(self) -> BotState:
        """Get the current bot state."""
        ...

    # ==================== Contract Methods ====================

    def get_contract_maker(self) -> str:
        """Get the maker contract symbol."""
        ...

    def get_contract_taker(self) -> str:
        """Get the taker contract symbol."""
        ...

    # ==================== Order ID Methods ====================

    def get_maker_internal_id(self) -> Optional[InternalOrderId]:
        """Get the maker order internal ID (client order ID)."""
        ...

    def get_taker_internal_id(self) -> Optional[InternalOrderId]:
        """Get the taker order internal ID (client order ID)."""
        ...

    # ==================== Order ID Properties ====================
    # Internal order IDs (may be None before order is placed)

    @property
    def maker_order_id(self) -> Optional[InternalOrderId]:
        """Maker order internal ID."""
        ...

    @property
    def taker_order_id(self) -> Optional[InternalOrderId]:
        """Taker order internal ID."""
        ...

    # ==================== Trading State Properties ====================

    @property
    def target_spread(self) -> Optional[float]:
        """Target spread for this route."""
        ...

    @property
    def quote_sent(self) -> Optional[Quote]:
        """Last quote sent for this route."""
        ...


@runtime_checkable
class IThreadedRouteStateManager(IRouteStateManager, Protocol):
    """
    Extended protocol for threaded route state managers.

    Extends IRouteStateManager with threading-specific attributes
    like execution_count for monitoring purposes.
    """

    execution_count: int
    """Number of execution cycles completed."""


def get_route_info(sm: IRouteStateManager) -> dict[str, Any]:
    """
    Extract route information from a state manager.

    Args:
        sm: Route state manager implementing IRouteStateManager

    Returns:
        Dictionary with route information
    """
    route_info: dict[str, Any] = {
        "route": sm.route,
        "state": str(sm.get_bot_state()),
        "maker_contract": sm.get_contract_maker(),
        "taker_contract": sm.get_contract_taker(),
        "maker_internal_id": sm.get_maker_internal_id(),
        "taker_internal_id": sm.get_taker_internal_id(),
        "maker_order_id": sm.get_maker_internal_id(),
        "taker_order_id": sm.get_taker_internal_id(),
        "target_spread": sm.target_spread,
    }

    # Check for threaded-specific attributes
    if isinstance(sm, IThreadedRouteStateManager):
        route_info["execution_count"] = sm.execution_count

    return route_info
