"""
Trading-related enums.

Centralized definitions for trading state, side, and routing enums.
"""

from enum import Enum, auto
from typing import Any, Optional

from .order import OrderSide


class OrderRole(str, Enum):
    """
    Role of an order in a trading pair.

    This enum replaces string-based role discrimination with type-safe values.

    Attributes:
        MAKER: Maker order (provides liquidity to the orderbook)
        TAKER: Taker order (takes liquidity from the orderbook)
    """

    MAKER = "MAKER"
    TAKER = "TAKER"

    def __str__(self) -> str:
        """Return string value for compatibility with existing code."""
        return self.value

    @classmethod
    def from_string(cls, role: str) -> "OrderRole":
        """Create OrderRole from string (case-insensitive)."""
        role_upper = role.upper()
        if role_upper == "MAKER":
            return cls.MAKER
        elif role_upper == "TAKER":
            return cls.TAKER
        else:
            raise ValueError(f"Invalid order role: {role}. Must be 'MAKER' or 'TAKER'.")


class OrderTypeRole(str, Enum):
    """
    Order type role for operations that need to distinguish maker from taker.

    Used in contexts like timeout handling, metrics collection, and error handling.

    Attributes:
        MAKER: Maker order type (provides liquidity)
        TAKER: Taker order type (takes liquidity)
    """

    MAKER = "maker"
    TAKER = "taker"

    def __str__(self) -> str:
        """Return string value for compatibility with existing code."""
        return self.value

    @classmethod
    def from_string(cls, role: str) -> "OrderTypeRole":
        """Create OrderTypeRole from string (case-insensitive)."""
        role_lower = role.lower()
        if role_lower == "maker":
            return cls.MAKER
        elif role_lower == "taker":
            return cls.TAKER
        else:
            raise ValueError(f"Invalid order type role: {role}. Must be 'maker' or 'taker'.")


class TradeSide(str, Enum):
    """Side of the trade (from taker's perspective)."""

    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class BotState(Enum):
    """
    Enum representing all possible states of the arbitrage bot.

    States:
    - START: Bot does not have an active maker or taker id and can generate a new order.
    - CREATING_MAKER: Initiated creating maker order to exchange but has not received id yet.
    - MAKER_CREATED: Maker order has been created and confirmed by exchange.
    - MAKER_LIVE: Maker order is live waiting cancellation or execution.
    - MAKER_EXECUTED: Maker order has been executed successfully.
    - CANCELLING_MAKER: Initiated order cancellation to exchange but has not received confirmation yet.
    - RECEIVING_CANCEL: Waiting for confirmation of cancellation request.
    - RESOLVE_MAKER_ORDER: Process that determines the final state of a maker order and appropriate next actions.
    - CREATING_TAKER: Initiated creating taker order to exchange but has not received id yet.
    - TAKER_CREATED: Taker order has been created and confirmed by exchange.
    - TAKER_LIVE: Taker order is live waiting to process execution.
    - TAKER_EXECUTED: Taker order has been executed successfully.
    - RESOLVE_TAKER_ORDER: Process that determines the final state of a taker order (REST fallback).
    - PROCESS_EXECUTION: Taker order is live waiting to process execution.
    - ERROR: Bot has encountered a critical error and has been stopped for safety.
    """

    START = auto()  # Bot does not have an active maker or taker id and can generate a new order
    CREATING_MAKER = auto()  # Initiated creating maker order but has not received id yet
    MAKER_CREATED = auto()  # Maker order has been created and confirmed by exchange
    MAKER_LIVE = auto()  # Maker order is live waiting cancellation or execution
    MAKER_EXECUTED = auto()  # Maker order has been executed successfully
    CANCELLING_MAKER = auto()  # Initiated order cancellation but has not received confirmation yet
    RECEIVING_CANCEL = auto()  # Waiting for confirmation of cancellation request
    RESOLVE_MAKER_ORDER = auto()  # Process that determines the final state of a maker order and decides next action
    CREATING_TAKER = auto()  # Initiated creating taker order but has not received id yet
    TAKER_CREATED = auto()  # Taker order has been created and confirmed by exchange
    TAKER_LIVE = auto()  # Taker order is live waiting to process execution
    TAKER_EXECUTED = auto()  # Taker order has been executed successfully
    RESOLVE_TAKER_ORDER = auto()  # Process that determines final taker state (REST fallback)
    PROCESS_EXECUTION = auto()  # Taker order is live waiting to process execution
    ERROR = auto()  # Bot has encountered a critical error and has been stopped for safety


class OperationResult(Enum):
    """
    High-level operation outcome for engine decision making.

    This enum abstracts away exchange-specific error details (nonce errors,
    rate limits, etc.) into simple outcomes that the engine can handle.

    The engine should ONLY see these outcomes:
    - SUCCESS: Operation completed successfully
    - PENDING: Still waiting for confirmation
    - TIMEOUT: Request timed out - needs REST verification (distinct from error)
    - RETRYABLE: Failed but can retry (broker handles details like nonce resync)
    - CRITICAL: Failed, stop trading (unrecoverable)

    Design Principle:
        - Engine = Pure State Machine (only decides "what next")
        - Broker = Error Normalization (handles nonce resync, rate limit backoff)
        - Gateway = Error Classification (maps exchange responses to typed errors)

    Example - Handler becomes simple:
        match result.status:
            case OperationResult.SUCCESS:
                return BotState.MAKER_LIVE, context
            case OperationResult.PENDING:
                return BotState.CREATING_MAKER, context
            case OperationResult.TIMEOUT:
                return BotState.RESOLVE_MAKER_ORDER, context
            case OperationResult.RETRYABLE:
                return BotState.START, context.clear_orders()
            case OperationResult.CRITICAL:
                return BotState.ERROR, context
    """

    SUCCESS = auto()
    """Operation completed successfully."""

    PENDING = auto()
    """Still waiting for confirmation."""

    TIMEOUT = auto()
    """Request timed out - may or may not exist on exchange, needs REST verification."""

    RETRYABLE = auto()
    """Failed but can retry (broker handles details like nonce resync, rate limit backoff)."""

    CRITICAL = auto()
    """Failed, stop trading (unrecoverable - e.g., authentication error, insufficient funds on taker)."""


class RoutingType(str, Enum):
    """
    Engine-level instruction for how to route orders based on market conditions.

    This model represents a high-level trading strategy parameter that tells
    the engine how to select which side (buy or sell) to use when creating orders.
    It's distinct from OrderSide which represents the actual direction of an order.
    """

    # Always create buy orders on the maker side (premium path)
    BUY = "buy"

    # Always create sell orders on the maker side (discount path)
    SELL = "sell"

    # Choose the side with the most favorable market conditions
    BEST = "best"

    @classmethod
    def is_valid(cls, value: Any) -> bool:
        """Check if a value is a valid routing type."""
        if not value:
            return False
        return value.lower() in [cls.BUY, cls.SELL, cls.BEST]

    @classmethod
    def determine_maker_side(
        cls,
        routing_type: str,
        premium_conditions: bool,
        discount_conditions: bool,
        bid_distance: Optional[float] = None,
        ask_distance: Optional[float] = None,
    ) -> Optional["OrderSide"]:
        """
        Determine the maker order side based on routing type and market conditions.

        This implements the core routing logic seen in order_routing_arb.py.

        Args:
            routing_type: One of 'buy', 'sell', or 'best'
            premium_conditions: Boolean for whether premium conditions are met
            discount_conditions: Boolean for whether discount conditions are met
            bid_distance: Optional distance metric for bid side
            ask_distance: Optional distance metric for ask side

        Returns:
            OrderSide: The order side to use (OrderSide.BUY or OrderSide.SELL), or None if no valid path
        """
        from .order import OrderSide

        if routing_type == cls.BUY:
            # With 'buy' routing, only check premium path
            if premium_conditions:
                return OrderSide.BUY

        elif routing_type == cls.SELL:
            # With 'sell' routing, only check discount path
            if discount_conditions:
                return OrderSide.SELL

        elif routing_type == cls.BEST:
            # With 'best' routing, check both paths and choose the better one
            if premium_conditions and discount_conditions:
                # If we have distance metrics, use them to choose the better path
                if bid_distance is not None and ask_distance is not None:
                    if bid_distance < ask_distance:
                        return OrderSide.BUY
                    else:
                        return OrderSide.SELL
                # Without distance metrics, prefer premium path
                return OrderSide.BUY
            # If only one path is available, use it
            elif premium_conditions:
                return OrderSide.BUY
            elif discount_conditions:
                return OrderSide.SELL

        # If no conditions satisfied, return None (no valid routing path)
        return None


__all__ = [
    "OrderRole",
    "OrderTypeRole",
    "TradeSide",
    "BotState",
    "OperationResult",
    "RoutingType",
]
