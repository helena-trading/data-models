"""
Engine context models and sub-context dataclasses.

This module provides:
1. Sub-context dataclasses for ExecutionContext decomposition (RouteIdentity, OrderState, etc.)
2. Tick-level models (TickContext, StartConditionsResult)

All dataclasses are frozen (immutable) for thread safety.
Use dataclasses.replace() to create modified copies.

Design Principles:
    - Immutable: All state is frozen - no in-place mutation
    - Type-safe: No Dict[str, Any] escape hatches
    - Composable: ExecutionContext composes these sub-contexts
    - Clear: Field names describe their purpose

Note: IGateway is referenced as a string annotation to avoid circular imports.
With `from __future__ import annotations`, this works at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from data_models.models.domain.market.orderbook import Orderbook
from data_models.models.domain.market.quote import Quote
from data_models.models.domain.order.ids import ExchangeOrderId, InternalOrderId
from data_models.models.domain.trading.latency import LatencyData
from data_models.models.domain.trading.liquidation import LiquidateInstructions
from data_models.models.engine.graph import GraphOpportunity
from data_models.models.enums.trading import BotState, RoutingType
from data_models.models.protocols.lifecycle_protocols import IBotParametersManager

# =============================================================================
# Order Context (moved from results.py to break circular import)
# =============================================================================


@dataclass(frozen=True)
class ActiveOrderContext:
    """
    Immutable context saved when an order is created.

    This is the single source of truth for which exchanges are involved
    in an active order. Used to prevent exchange lookup ambiguity when
    multiple exchanges support the same contract.

    Graph-specific: Required because graph engine can trade on any
    exchange combination, unlike cross engine which has fixed pairs.

    frozen=True ensures immutability (prevents accidental mutation
    during order lifecycle).
    """

    maker_contract: str
    taker_contract: str
    maker_exchange_name: str
    taker_exchange_name: str


# =============================================================================
# ExecutionContext Sub-Contexts
# =============================================================================


@dataclass(frozen=True)
class RouteIdentity:
    """
    Immutable route identification.

    Contains all information needed to identify a trading route:
    - Exchange pair (maker/taker)
    - Contract pair (maker/taker)
    - Bot identity (bot_id, run_id)
    - Routing configuration

    Attributes:
        route_id: Unique route identifier (e.g., 'route1', 'thread_main')
        maker_exchange: Name of maker exchange (e.g., 'binance_spot')
        taker_exchange: Name of taker exchange (e.g., 'hyperliquid')
        contract_maker: Maker contract (e.g., 'BTC_USDT')
        contract_taker: Taker contract (e.g., 'BTC_USDT')
        bot_id: Bot ID from database (optional)
        run_id: Run ID for this execution (optional)
        routing_type: Order routing strategy (BEST, MAKER_ONLY, etc.)
    """

    route_id: str
    maker_exchange: str
    taker_exchange: str
    contract_maker: str
    contract_taker: str = ""
    bot_id: Optional[int] = None
    run_id: Optional[int] = None
    routing_type: RoutingType = RoutingType.BEST


@dataclass(frozen=True)
class OrderState:
    """
    Immutable order tracking state.

    Contains order IDs and retry counters for order lifecycle management.

    ID Naming Convention:
        - maker_internal_id: The ID WE generate and send to exchange as internal_id
        - taker_internal_id: The ID WE generate and send to exchange as internal_id
        - maker_exchange_order_id: The ID assigned by the EXCHANGE after order confirmation
        - taker_exchange_order_id: The ID assigned by the EXCHANGE after order confirmation

    Attributes:
        maker_internal_id: Internal ID of maker order - ID we generate (None until created)
        taker_internal_id: Internal ID of taker order - ID we generate (None until created)
        maker_exchange_order_id: Exchange-assigned ID of maker order (None until confirmed)
        taker_exchange_order_id: Exchange-assigned ID of taker order (None until confirmed)
        lifecycle_id: Unique ID for order lifecycle tracking/correlation
        taker_creation_attempts: Number of taker creation attempts (for retry logic)
        taker_retry_reason: Reason for last taker retry (for debugging)
        cancel_nonce_tries: Number of cancel attempts due to nonce errors
        resolve_cancel_attempts: Number of cancel retry attempts from RESOLVE_MAKER_ORDER
    """

    # Internal IDs - IDs we generate and send to exchange as internal_id
    # These are used as cache keys for order lookup
    maker_internal_id: Optional["InternalOrderId"] = None
    taker_internal_id: Optional["InternalOrderId"] = None

    # Exchange-assigned IDs - set after order confirmation
    # Used for cancellation on exchanges that require their own ID (e.g., Ripio Trade UUID)
    maker_exchange_order_id: Optional["ExchangeOrderId"] = None
    taker_exchange_order_id: Optional["ExchangeOrderId"] = None

    # Lifecycle tracking for correlation/debugging
    lifecycle_id: Optional[str] = None

    # Retry counters
    taker_creation_attempts: int = 0
    taker_retry_reason: Optional[str] = None
    cancel_nonce_tries: int = 0
    resolve_cancel_attempts: int = 0

    # Cancel response signal: order is already terminal on exchange,
    # needs REST verification for full order payload (with fills).
    cancel_already_terminal: bool = False


@dataclass(frozen=True)
class TimingState:
    """
    Immutable timing state for timeout detection.

    Contains timestamps for tracking order lifecycle timing.

    Attributes:
        tick_timestamp: Timestamp when tick started (milliseconds)
        order_request_time: When maker order was requested (ms)
        taker_order_request_time: When taker order was requested (ms)
        taker_sent_time: When taker entered TAKER_LIVE state (ms)
        cancel_sent_time: When cancel request was sent (ms)
        taker_request_time: Alias for taker_order_request_time
        maker_fill_timestamp: When maker fill was detected (ms) - for cycle latency
        taker_fill_timestamp: When taker fill was detected (ms) - for cycle latency
    """

    tick_timestamp: int = 0
    order_request_time: Optional[int] = None
    taker_order_request_time: Optional[int] = None
    taker_sent_time: Optional[int] = None
    cancel_sent_time: Optional[int] = None
    taker_request_time: Optional[int] = None
    # Fill detection timestamps - captured when fills are detected by handlers
    maker_fill_timestamp: Optional[int] = None
    taker_fill_timestamp: Optional[int] = None


@dataclass(frozen=True)
class BackoffState:
    """
    Immutable backoff state for rate limiting.

    Contains timestamps until which certain operations should be paused.

    Attributes:
        global_backoff_until_ms: Pause all order creation until this time (ms)
        cancel_backoff_until_ms: Pause cancel requests until this time (ms)
    """

    global_backoff_until_ms: Optional[int] = None
    cancel_backoff_until_ms: Optional[int] = None


@dataclass(frozen=True)
class MarketState:
    """
    Immutable market data state.

    Contains orderbooks and quotes for the current tick.

    Attributes:
        maker_orderbook: Current maker exchange orderbook
        taker_orderbook: Current taker exchange orderbook
        quote: Generated quote for this tick
        quote_sent: Quote that was sent when order was created
    """

    maker_orderbook: Optional["Orderbook"] = None
    taker_orderbook: Optional["Orderbook"] = None
    quote: Optional["Quote"] = None
    quote_sent: Optional["Quote"] = None


@dataclass(frozen=True)
class DependencyState:
    """
    Immutable dependency injection state.

    Contains references to exchange interfaces and parameter managers.
    These are set by the tick engine and used by handlers.

    Attributes:
        parameters_manager: Bot parameters manager instance
        maker_exchange_interface: Maker exchange gateway interface
        taker_exchange_interface: Taker exchange gateway interface
    """

    parameters_manager: Optional["IBotParametersManager"] = None
    maker_exchange_interface: Optional["IGateway"] = None
    taker_exchange_interface: Optional["IGateway"] = None


@dataclass(frozen=True)
class GraphState:
    """
    Immutable graph-engine specific state.

    Contains state specific to multi-exchange graph arbitrage.
    Only populated for graph engine contexts.

    Attributes:
        exchanges: Tuple of all exchange gateways in the graph
        trading_pairs: Tuple of all contracts in the graph (e.g., BTC_USD, ETH_USD)
        active_order_context: Current maker/taker exchange routing context
        opportunity: Current graph opportunity being traded
        current_opportunity: Opportunity for comparison
        target_spread: Target spread for current opportunity
        cycle_count: Number of completed trading cycles
        opportunity_switches: Number of times opportunity changed
        total_profit: Cumulative profit across cycles
    """

    exchanges: Tuple["IGateway", ...] = ()
    trading_pairs: Tuple[str, ...] = ()
    active_order_context: Optional["ActiveOrderContext"] = None
    opportunity: Optional["GraphOpportunity"] = None
    current_opportunity: Optional["GraphOpportunity"] = None
    target_spread: Optional[float] = None
    cycle_count: int = 0
    opportunity_switches: int = 0
    total_profit: float = 0.0


@dataclass(frozen=True)
class LiquidationState:
    """
    Immutable liquidation state.

    Contains instructions for liquidating a filled maker position.
    Only populated when a maker order has been filled.

    Attributes:
        instructions: Liquidation instructions for taker order creation
    """

    instructions: Optional["LiquidateInstructions"] = None


@dataclass(frozen=True)
class TelemetryState:
    """
    Immutable telemetry and monitoring state.

    Contains latency data and behavioral flags for monitoring.

    Attributes:
        latency_data: Collected latency metrics
        wait_for_taker_fill: Whether to wait for taker fill confirmation
    """

    latency_data: Optional["LatencyData"] = None
    wait_for_taker_fill: bool = True


# =============================================================================
# Tick-Level Models
# =============================================================================


@dataclass(frozen=True)
class TickContext:
    """Immutable context for a single tick processing cycle.

    Contains all state and data needed by state handlers, avoiding
    repeated lookups and ensuring consistent data throughout the tick.

    This is a derived snapshot built from ExecutionContext by CrossContextBuilder.
    Used by the cross engine for convenient handler access.

    Attributes:
        bot_state: Current state of the bot state machine
        maker_id: Internal ID of the maker/primary order (if any)
        taker_id: Internal ID of the taker/secondary order (if any)
        quote_sent: Quote that was sent when order was created
        route: Trading route identifier
        is_stopping: Whether bot is in stopping state
        book_taker: Taker/secondary exchange orderbook
        book_maker: Maker/primary exchange orderbook
        current_buy_price_taker: Best bid price on taker exchange
        current_sell_price_taker: Best ask price on taker exchange
        book_taker_latency: Latency of taker orderbook in milliseconds
        quote: Generated quote for this tick
        lifecycle_id: Unique ID for order lifecycle tracking
        t0: Current timestamp in milliseconds
    """

    bot_state: BotState
    maker_id: Optional[InternalOrderId]
    taker_id: Optional[InternalOrderId]
    quote_sent: Optional["Quote"]
    route: str
    is_stopping: bool
    book_taker: Optional["Orderbook"]
    book_maker: Optional["Orderbook"]
    current_buy_price_taker: Optional[float]
    current_sell_price_taker: Optional[float]
    book_taker_latency: Optional[int]
    quote: Optional["Quote"]
    lifecycle_id: Optional[str]
    t0: int  # Current timestamp in milliseconds


@dataclass(frozen=True)
class StartConditionsResult:
    """Result of start conditions check for creating an order.

    Contains whether all conditions are met and detailed information
    for debugging when orders are blocked.

    Attributes:
        all_met: True if all conditions passed
        reason: Human-readable explanation if blocked
        condition_flags: Individual condition results for debugging
    """

    all_met: bool
    reason: str
    condition_flags: Dict[str, bool]

    @classmethod
    def success(cls) -> "StartConditionsResult":
        """Create a successful result where all conditions are met."""
        return cls(
            all_met=True,
            reason="",
            condition_flags={},
        )

    @classmethod
    def blocked(cls, reason: str, flags: Dict[str, bool]) -> "StartConditionsResult":
        """Create a blocked result with explanation.

        Args:
            reason: Human-readable explanation of why blocked
            flags: Dictionary of condition name to pass/fail status
        """
        return cls(
            all_met=False,
            reason=reason,
            condition_flags=flags,
        )


__all__ = [
    # Order context
    "ActiveOrderContext",
    # ExecutionContext sub-contexts
    "RouteIdentity",
    "OrderState",
    "TimingState",
    "BackoffState",
    "MarketState",
    "DependencyState",
    "GraphState",
    "LiquidationState",
    "TelemetryState",
    # Tick-level models
    "TickContext",
    "StartConditionsResult",
]
