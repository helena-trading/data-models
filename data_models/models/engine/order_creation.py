"""
Data models for order creation services.

These dataclasses provide type-safe, immutable data structures for passing
information between maker and taker order creation components.

Thread Safety:
    All models are immutable dataclasses - safe to share across threads.

Note: IGateway is referenced as a string annotation to avoid circular imports.
With `from __future__ import annotations`, this works at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from data_models.models.domain.order.order import Order
from data_models.models.domain.trading.liquidation import LiquidateInstructions
from data_models.models.enums.order import OrderSide
from data_models.models.enums.trading import BotState

# ExecutionContext is now in the same layer - direct import
from .execution_context import ExecutionContext

# =============================================================================
# Shared Order Creation Models
# =============================================================================


@dataclass(frozen=True)
class OrderbookPrices:
    """
    Extracted orderbook price data from maker and taker exchanges.

    Contains best bid/ask prices and latency information for both sides
    of the arbitrage. Used by multiple components to make routing decisions.

    Attributes:
        maker_bid: Best bid price on maker exchange
        maker_ask: Best ask price on maker exchange
        taker_bid: Best bid price on taker exchange
        taker_ask: Best ask price on taker exchange
        maker_latency_ms: Orderbook age in milliseconds (maker)
        taker_latency_ms: Orderbook age in milliseconds (taker)
    """

    maker_bid: float
    maker_ask: float
    taker_bid: float
    taker_ask: float
    maker_latency_ms: float
    taker_latency_ms: float

    def __post_init__(self) -> None:
        """Validate prices are positive."""
        if any(
            p <= 0
            for p in [
                self.maker_bid,
                self.maker_ask,
                self.taker_bid,
                self.taker_ask,
            ]
        ):
            raise ValueError("All prices must be positive")


@dataclass(frozen=True)
class TradingConstraints:
    """
    Trading constraints for an exchange.

    Contains minimum size, precision, and balance information needed
    to validate and size orders correctly.

    Attributes:
        min_size: Minimum order size (max of exchange min and value-based min)
        min_value_usd: Minimum order value in USD
        size_precision: Decimal places for size rounding
        is_spot: True if spot exchange (needs balance checks)
        is_futures: True if futures exchange
        balance: Optional balance dict {"base": X, "quote": Y} for spot exchanges
    """

    min_size: float
    min_value_usd: float
    size_precision: int
    is_spot: bool
    is_futures: bool
    balance: Optional[Dict[str, float]] = None

    def __post_init__(self) -> None:
        """Validate constraints are sensible."""
        if self.min_size < 0:
            raise ValueError("min_size cannot be negative")
        if self.min_value_usd < 0:
            raise ValueError("min_value_usd cannot be negative")
        if self.size_precision < 0:
            raise ValueError("size_precision cannot be negative")


@dataclass(frozen=True)
class PositionCheckResult:
    """
    Result of position limit check.

    Indicates whether a trade can proceed and provides context about
    remaining capacity for position building.

    Attributes:
        can_trade: Whether the trade is allowed
        reason: Human-readable explanation
        remaining_room_usd: USD value of remaining position capacity
    """

    can_trade: bool
    reason: str
    remaining_room_usd: float

    def __post_init__(self) -> None:
        """Validate remaining room is non-negative."""
        if self.remaining_room_usd < 0:
            raise ValueError("remaining_room_usd cannot be negative")


# =============================================================================
# Maker Order Creation Models
# =============================================================================


@dataclass(frozen=True)
class RoutingDecision:
    """
    Complete routing decision with all parameters needed to create an order.

    This is the output of the routing decision process, containing
    everything needed by the order executor.

    Attributes:
        maker_side: BUY or SELL on maker exchange
        taker_side: Opposite side on taker exchange
        maker_price: Price for maker order
        taker_price: Price for taker order (saved for liquidation)
        size: Order size
        can_execute: Whether the order should be created
        block_reason: If can_execute is False, explains why
    """

    maker_side: OrderSide
    taker_side: OrderSide
    maker_price: float
    taker_price: float
    size: float
    can_execute: bool
    block_reason: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate decision consistency."""
        if self.can_execute and self.size <= 0:
            raise ValueError("Cannot execute with size <= 0")
        if not self.can_execute and self.block_reason is None:
            raise ValueError("Must provide block_reason when can_execute is False")


# =============================================================================
# Taker Order Creation Models
# =============================================================================


@dataclass(frozen=True)
class TakerCreationResult:
    """
    Result of taker order creation.

    Returned by TakerCreationService.create() to communicate success/failure
    and provide the updated context.
    """

    success: bool
    """True if taker order was created successfully."""

    context: "ExecutionContext"
    """Updated context (with taker_order_id if successful)."""

    next_state: BotState
    """Next state to transition to."""

    error: Optional[str] = None
    """Error message if creation failed."""


@dataclass(frozen=True)
class LiquidationPriceParams:
    """
    Parameters for liquidation price calculation.

    These parameters control how the taker price is adjusted based on
    the actual maker fill price and slippage tolerance.

    Attributes:
        accepted_slippage: Maximum acceptable slippage percentage (e.g., 0.1 = 0.1%)
        target_premium: Target premium for SELL orders (from quote engine)
        target_discount: Target discount for BUY orders (from quote engine)
        max_price_deviation_percent: Maximum allowed deviation between avg_price and
            maker_price before falling back to maker_price (default: 20%)
    """

    accepted_slippage: float
    target_premium: float
    target_discount: float
    max_price_deviation_percent: float = 20.0


@dataclass(frozen=True)
class LiquidationContext:
    """
    Context for liquidation execution.

    Contains all the exchange and order information needed to execute
    a liquidation order.

    Attributes:
        taker_exchange: Exchange gateway for taker order placement
        taker_contract: Contract to trade on taker exchange (e.g., "BTC_USDT")
        maker_order: The filled maker order being liquidated
        filled_amount: Amount to liquidate (from maker fill)
        instructions: Original liquidation instructions from quote engine
        internal_id: Internal order ID for tracking
    """

    taker_exchange: "IGateway"
    taker_contract: str
    maker_order: "Order"
    filled_amount: float
    instructions: "LiquidateInstructions"
    internal_id: str


@dataclass(frozen=True)
class LiquidationResult:
    """
    Result of liquidation calculation and execution.

    Attributes:
        success: True if liquidation order was created successfully
        taker_internal_id: Internal ID of taker order (None if failed)
        adjusted_price: Final price used for taker order
        price_source: Source of price used ("avg_price", "maker_price", or "instructions")
        updated_instructions: Updated LiquidateInstructions with adjusted price
        liquidation_location: Location code for tracking
        error: Error message if liquidation failed
    """

    success: bool
    taker_internal_id: Optional[str] = None
    adjusted_price: Optional[float] = None
    price_source: str = "instructions"
    updated_instructions: Optional["LiquidateInstructions"] = None
    liquidation_location: Optional[int] = None
    error: Optional[str] = None


__all__ = [
    # Shared
    "OrderbookPrices",
    "TradingConstraints",
    "PositionCheckResult",
    # Maker
    "RoutingDecision",
    # Taker
    "TakerCreationResult",
    "LiquidationPriceParams",
    "LiquidationContext",
    "LiquidationResult",
]
