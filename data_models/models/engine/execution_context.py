"""
Execution context for state-driven engine architecture.

This module provides the immutable ExecutionContext dataclass that carries
all state through the tick processing cycle. Handlers receive context,
perform operations, and return new context instances.

Thread Safety:
    ExecutionContext is frozen (immutable) - safe for concurrent access.
    All "with_*" methods return new instances.

Design Principles:
    - Immutable: Context cannot be modified in place
    - Complete: Contains all data needed for state processing
    - Typed: All fields are properly typed - NO untyped metadata dict
    - Composable: Uses nested sub-contexts for clear separation of concerns

Note: IGateway is referenced as a string annotation to avoid circular imports.
With `from __future__ import annotations`, this works at runtime.
"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple, Union

from data_models.models.domain.market.orderbook import Orderbook
from data_models.models.domain.market.quote import Quote
from data_models.models.domain.order.ids import ExchangeOrderId, InternalOrderId
from data_models.models.domain.order.signals import AsyncOrderError
from data_models.models.domain.trading.latency import LatencyData
from data_models.models.domain.trading.liquidation import LiquidateInstructions
from data_models.models.engine.graph import GraphOpportunity
from data_models.models.enums.trading import BotState, RoutingType
from data_models.models.protocols.lifecycle_protocols import IBotParametersManager

# Import sub-contexts from same directory
from .context import (
    ActiveOrderContext,
    BackoffState,
    DependencyState,
    GraphState,
    LiquidationState,
    MarketState,
    OrderState,
    RouteIdentity,
    TelemetryState,
    TimingState,
)


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable context for state machine execution.

    This context carries all state information through the tick processing
    cycle. State handlers receive this context, perform their operations,
    and return a new context instance with any updates.

    Architecture:
        ExecutionContext uses nested frozen dataclasses for clear separation:
        - route: RouteIdentity - exchange pair, contracts, bot identity
        - orders: OrderState - order IDs, retry counters
        - timing: TimingState - timestamps for timeout detection
        - backoff: BackoffState - rate limiting state
        - market: MarketState - orderbooks and quotes
        - dependencies: DependencyState - exchange interfaces
        - graph: GraphState (optional) - graph-engine specific state
        - liquidation: LiquidationState (optional) - liquidation instructions
        - telemetry: TelemetryState (optional) - monitoring data

    Immutability ensures:
        - Thread safety in concurrent environments
        - Clear data flow (input -> process -> output)
        - Easy testing (predictable state)
        - Debugging (full state at each step)

    Usage:
        # Read from context (direct field access)
        if context.orders.maker_internal_id is not None:
            order_status = await check_order(context.orders.maker_internal_id)

        # Read from context (property access)
        if context.maker_internal_id is not None:
            order_status = await check_order(context.maker_internal_id)

        # Return new context with updates
        return BotState.CREATING_MAKER, context.with_maker_internal_id(new_order_id)
    """

    # =========================================================================
    # Core State
    # =========================================================================

    bot_state: BotState
    """Current state of the bot state machine."""

    is_stopping: bool = False
    """Whether bot is in shutdown mode."""

    pending_async_error: Optional["AsyncOrderError"] = None
    """Pending async error from callbacks (e.g., WebSocket order rejection)."""

    small_order_accumulator: float = 0.0
    """Accumulator for small orders below minimum size."""

    # =========================================================================
    # Composed Sub-Contexts (required)
    # =========================================================================

    route: RouteIdentity = field(
        default_factory=lambda: RouteIdentity(
            route_id="",
            maker_exchange="",
            taker_exchange="",
            contract_maker="",
        )
    )
    """Route identification: exchanges, contracts, bot identity."""

    orders: OrderState = field(default_factory=OrderState)
    """Order tracking: IDs, lifecycle, retry counters."""

    timing: TimingState = field(default_factory=TimingState)
    """Timing state: timestamps for timeout detection."""

    backoff: BackoffState = field(default_factory=BackoffState)
    """Backoff state: rate limiting timestamps."""

    market: MarketState = field(default_factory=MarketState)
    """Market data: orderbooks and quotes."""

    dependencies: DependencyState = field(default_factory=DependencyState)
    """Dependencies: exchange interfaces, parameter managers."""

    # =========================================================================
    # Optional Sub-Contexts
    # =========================================================================

    graph: Optional[GraphState] = None
    """Graph-engine specific state (only for graph strategies)."""

    liquidation: Optional[LiquidationState] = None
    """Liquidation instructions (only when maker is filled)."""

    telemetry: Optional[TelemetryState] = None
    """Telemetry and monitoring data."""

    # =========================================================================
    # Compatibility Properties (access nested fields directly)
    # =========================================================================

    @property
    def route_id(self) -> str:
        """Route identifier."""
        return self.route.route_id

    @property
    def maker_exchange(self) -> str:
        """Name of maker exchange."""
        return self.route.maker_exchange

    @property
    def taker_exchange(self) -> str:
        """Name of taker exchange."""
        return self.route.taker_exchange

    @property
    def contract_maker(self) -> str:
        """Maker contract (e.g., 'BTC_USDT')."""
        return self.route.contract_maker

    @property
    def contract_taker(self) -> str:
        """Taker contract (e.g., 'BTC_USDT')."""
        return self.route.contract_taker

    @property
    def bot_id(self) -> Optional[int]:
        """Bot ID from database."""
        return self.route.bot_id

    @property
    def run_id(self) -> Optional[int]:
        """Run ID for this execution."""
        return self.route.run_id

    @property
    def routing_type(self) -> RoutingType:
        """Order routing strategy."""
        return self.route.routing_type

    @property
    def maker_internal_id(self) -> Optional[InternalOrderId]:
        """Internal ID of maker order - the ID we generate and send to exchange."""
        return self.orders.maker_internal_id

    @property
    def taker_internal_id(self) -> Optional[InternalOrderId]:
        """Internal ID of taker order - the ID we generate and send to exchange."""
        return self.orders.taker_internal_id

    @property
    def maker_exchange_order_id(self) -> Optional[ExchangeOrderId]:
        """Exchange-assigned ID of maker order (set after confirmation)."""
        return self.orders.maker_exchange_order_id

    @property
    def taker_exchange_order_id(self) -> Optional[ExchangeOrderId]:
        """Exchange-assigned ID of taker order (set after confirmation)."""
        return self.orders.taker_exchange_order_id

    @property
    def lifecycle_id(self) -> Optional[str]:
        """Unique ID for order lifecycle tracking."""
        return self.orders.lifecycle_id

    @property
    def tick_timestamp(self) -> int:
        """Timestamp when tick started (milliseconds)."""
        return self.timing.tick_timestamp

    @property
    def order_request_time(self) -> Optional[int]:
        """When maker order was requested (ms)."""
        return self.timing.order_request_time

    @property
    def taker_order_request_time(self) -> Optional[int]:
        """When taker order was requested (ms)."""
        return self.timing.taker_order_request_time

    @property
    def global_backoff_until_ms(self) -> Optional[int]:
        """Pause all order creation until this time (ms)."""
        return self.backoff.global_backoff_until_ms

    @property
    def cancel_backoff_until_ms(self) -> Optional[int]:
        """Pause cancel requests until this time (ms)."""
        return self.backoff.cancel_backoff_until_ms

    @property
    def maker_orderbook(self) -> Optional["Orderbook"]:
        """Current maker exchange orderbook."""
        return self.market.maker_orderbook

    @property
    def taker_orderbook(self) -> Optional["Orderbook"]:
        """Current taker exchange orderbook."""
        return self.market.taker_orderbook

    @property
    def quote(self) -> Optional["Quote"]:
        """Generated quote for this tick."""
        return self.market.quote

    @property
    def quote_sent(self) -> Optional["Quote"]:
        """Quote that was sent when order was created."""
        return self.market.quote_sent

    @property
    def parameters_manager(self) -> Optional["IBotParametersManager"]:
        """Bot parameters manager instance."""
        return self.dependencies.parameters_manager

    @property
    def maker_exchange_interface(self) -> Optional["IGateway"]:
        """Maker exchange gateway interface."""
        return self.dependencies.maker_exchange_interface

    @property
    def taker_exchange_interface(self) -> Optional["IGateway"]:
        """Taker exchange gateway interface."""
        return self.dependencies.taker_exchange_interface

    @property
    def exchanges(self) -> Tuple["IGateway", ...]:
        """All exchange gateways (graph engine)."""
        return self.graph.exchanges if self.graph else ()

    @property
    def trading_pairs(self) -> Tuple[str, ...]:
        """All trading pairs/contracts (graph engine)."""
        return self.graph.trading_pairs if self.graph else ()

    @property
    def active_order_context(self) -> Optional["ActiveOrderContext"]:
        """Active order context (graph engine)."""
        return self.graph.active_order_context if self.graph else None

    # =========================================================================
    # Convenience Properties
    # =========================================================================

    @property
    def has_maker_order(self) -> bool:
        """Check if maker order exists."""
        return self.orders.maker_internal_id is not None

    @property
    def has_taker_order(self) -> bool:
        """Check if taker order exists."""
        return self.orders.taker_internal_id is not None

    @property
    def has_both_orders(self) -> bool:
        """Check if both orders exist."""
        return self.has_maker_order and self.has_taker_order

    @property
    def has_orderbooks(self) -> bool:
        """Check if both orderbooks are available."""
        return self.market.maker_orderbook is not None and self.market.taker_orderbook is not None

    @property
    def opportunity(self) -> Optional["GraphOpportunity"]:
        """Get opportunity (graph engine specific)."""
        return self.graph.opportunity if self.graph else None

    @property
    def has_async_error(self) -> bool:
        """Check if there's a pending async error to process."""
        return self.pending_async_error is not None

    @property
    def is_in_backoff(self) -> bool:
        """Check if currently in global backoff period."""
        if self.backoff.global_backoff_until_ms is None:
            return False
        return int(time.time() * 1000) < self.backoff.global_backoff_until_ms

    @property
    def is_in_cancel_backoff(self) -> bool:
        """Check if currently in cancel backoff period."""
        if self.backoff.cancel_backoff_until_ms is None:
            return False
        return int(time.time() * 1000) < self.backoff.cancel_backoff_until_ms

    # =========================================================================
    # Immutable Update Methods (return new instances)
    # =========================================================================

    def with_state(self, new_state: BotState) -> "ExecutionContext":
        """Return new context with updated state."""
        return dataclasses.replace(self, bot_state=new_state)

    def with_maker_internal_id(
        self,
        internal_id: Optional[Union[str, InternalOrderId]],
        lifecycle_id: Optional[str] = None,
    ) -> "ExecutionContext":
        """Return new context with maker internal ID set.

        This is the ID we generate and send to the exchange as our internal_id.

        Args:
            internal_id: Maker internal ID (string or InternalOrderId)
            lifecycle_id: Optional lifecycle ID for order tracking
        """
        if internal_id is None:
            new_orders = dataclasses.replace(self.orders, maker_internal_id=None)
        elif isinstance(internal_id, str):
            new_orders = dataclasses.replace(
                self.orders,
                maker_internal_id=InternalOrderId(internal_id),
                lifecycle_id=lifecycle_id if lifecycle_id else self.orders.lifecycle_id,
            )
        else:
            new_orders = dataclasses.replace(
                self.orders,
                maker_internal_id=internal_id,
                lifecycle_id=lifecycle_id if lifecycle_id else self.orders.lifecycle_id,
            )
        return dataclasses.replace(self, orders=new_orders)

    def with_taker_internal_id(self, internal_id: Optional[Union[str, InternalOrderId]]) -> "ExecutionContext":
        """Return new context with taker internal ID set.

        This is the ID we generate and send to the exchange as our internal_id.
        """
        if internal_id is None:
            new_orders = dataclasses.replace(self.orders, taker_internal_id=None)
        elif isinstance(internal_id, str):
            new_orders = dataclasses.replace(self.orders, taker_internal_id=InternalOrderId(internal_id))
        else:
            new_orders = dataclasses.replace(self.orders, taker_internal_id=internal_id)
        return dataclasses.replace(self, orders=new_orders)

    def with_maker_exchange_order_id(
        self,
        exchange_order_id: Optional[Union[str, ExchangeOrderId]],
    ) -> "ExecutionContext":
        """Return new context with maker exchange order ID set.

        This is the ID assigned by the exchange after order confirmation.
        Used for cancellation on exchanges that require their own ID (e.g., Ripio Trade UUID).

        Args:
            exchange_order_id: Exchange-assigned order ID (string or ExchangeOrderId)
        """
        if exchange_order_id is None:
            new_orders = dataclasses.replace(self.orders, maker_exchange_order_id=None)
        elif isinstance(exchange_order_id, str):
            new_orders = dataclasses.replace(
                self.orders,
                maker_exchange_order_id=ExchangeOrderId(exchange_order_id),
            )
        else:
            new_orders = dataclasses.replace(
                self.orders,
                maker_exchange_order_id=exchange_order_id,
            )
        return dataclasses.replace(self, orders=new_orders)

    def with_taker_exchange_order_id(
        self,
        exchange_order_id: Optional[Union[str, ExchangeOrderId]],
    ) -> "ExecutionContext":
        """Return new context with taker exchange order ID set.

        This is the ID assigned by the exchange after order confirmation.

        Args:
            exchange_order_id: Exchange-assigned order ID (string or ExchangeOrderId)
        """
        if exchange_order_id is None:
            new_orders = dataclasses.replace(self.orders, taker_exchange_order_id=None)
        elif isinstance(exchange_order_id, str):
            new_orders = dataclasses.replace(
                self.orders,
                taker_exchange_order_id=ExchangeOrderId(exchange_order_id),
            )
        else:
            new_orders = dataclasses.replace(
                self.orders,
                taker_exchange_order_id=exchange_order_id,
            )
        return dataclasses.replace(self, orders=new_orders)

    def with_order_request_time(self, timestamp: Optional[int]) -> "ExecutionContext":
        """Return new context with order request timestamp set."""
        new_timing = dataclasses.replace(self.timing, order_request_time=timestamp)
        return dataclasses.replace(self, timing=new_timing)

    def with_quote(self, quote: "Quote") -> "ExecutionContext":
        """Return new context with quote set."""
        new_market = dataclasses.replace(self.market, quote=quote)
        return dataclasses.replace(self, market=new_market)

    def with_quote_sent(self, quote_sent: "Quote") -> "ExecutionContext":
        """Return new context with quote_sent (the quote used for order creation)."""
        new_market = dataclasses.replace(self.market, quote_sent=quote_sent)
        return dataclasses.replace(self, market=new_market)

    def with_orderbooks(
        self,
        maker_orderbook: Optional["Orderbook"] = None,
        taker_orderbook: Optional["Orderbook"] = None,
    ) -> "ExecutionContext":
        """Return new context with updated orderbooks."""
        new_market = dataclasses.replace(
            self.market,
            maker_orderbook=maker_orderbook,
            taker_orderbook=taker_orderbook,
        )
        return dataclasses.replace(self, market=new_market)

    def with_stopping(self, is_stopping: bool = True) -> "ExecutionContext":
        """Return new context with stopping flag set."""
        return dataclasses.replace(self, is_stopping=is_stopping)

    def with_dependencies(
        self,
        parameters_manager: Optional["IBotParametersManager"] = None,
        maker_exchange: Optional["IGateway"] = None,
        taker_exchange: Optional["IGateway"] = None,
    ) -> "ExecutionContext":
        """
        Return new context with operational dependencies set.

        Args:
            parameters_manager: Bot parameters manager instance
            maker_exchange: Maker exchange gateway interface
            taker_exchange: Taker exchange gateway interface

        Returns:
            New ExecutionContext with dependencies set
        """
        updates: Dict[str, Any] = {}
        if parameters_manager is not None:
            updates["parameters_manager"] = parameters_manager
        if maker_exchange is not None:
            updates["maker_exchange_interface"] = maker_exchange
        if taker_exchange is not None:
            updates["taker_exchange_interface"] = taker_exchange

        new_deps = dataclasses.replace(self.dependencies, **updates)
        return dataclasses.replace(self, dependencies=new_deps)

    def with_async_error(
        self,
        error: "AsyncOrderError",
    ) -> "ExecutionContext":
        """
        Return new context with async error set.

        Used by StateHolder when applying async events from callbacks.

        Args:
            error: AsyncOrderError from async callback

        Returns:
            New ExecutionContext with pending_async_error set
        """
        return dataclasses.replace(self, pending_async_error=error)

    def with_backoff(
        self,
        backoff_until_ms: int,
    ) -> "ExecutionContext":
        """
        Return new context with global backoff set.

        Used when rate limit errors occur to pause order creation.

        Args:
            backoff_until_ms: Epoch milliseconds until which to backoff

        Returns:
            New ExecutionContext with global_backoff_until_ms set
        """
        new_backoff = dataclasses.replace(self.backoff, global_backoff_until_ms=backoff_until_ms)
        return dataclasses.replace(self, backoff=new_backoff)

    def with_cancel_backoff(
        self,
        backoff_until_ms: int,
    ) -> "ExecutionContext":
        """
        Return new context with cancel backoff set.

        Used when cancel rate limit errors occur.

        Args:
            backoff_until_ms: Epoch milliseconds until which to backoff cancels

        Returns:
            New ExecutionContext with cancel_backoff_until_ms set
        """
        new_backoff = dataclasses.replace(self.backoff, cancel_backoff_until_ms=backoff_until_ms)
        return dataclasses.replace(self, backoff=new_backoff)

    def with_bot_identity(
        self,
        bot_id: Optional[int] = None,
        run_id: Optional[int] = None,
    ) -> "ExecutionContext":
        """
        Return new context with bot identity fields set.

        Args:
            bot_id: Bot ID from database
            run_id: Run ID for this execution

        Returns:
            New ExecutionContext with identity fields set
        """
        updates: Dict[str, Any] = {}
        if bot_id is not None:
            updates["bot_id"] = bot_id
        if run_id is not None:
            updates["run_id"] = run_id

        new_route = dataclasses.replace(self.route, **updates)
        return dataclasses.replace(self, route=new_route)

    def with_routing_type(
        self,
        routing_type: RoutingType,
    ) -> "ExecutionContext":
        """
        Return new context with routing type set.

        Args:
            routing_type: Routing strategy (BUY, SELL, or BEST)

        Returns:
            New ExecutionContext with routing_type set
        """
        new_route = dataclasses.replace(self.route, routing_type=routing_type)
        return dataclasses.replace(self, route=new_route)

    def with_contracts(
        self,
        contract_maker: Optional[str] = None,
        contract_taker: Optional[str] = None,
    ) -> "ExecutionContext":
        """
        Return new context with contract fields set.

        Args:
            contract_maker: Maker contract (e.g., 'BTC_USDT')
            contract_taker: Taker contract (e.g., 'BTC_USDT')

        Returns:
            New ExecutionContext with contract fields set
        """
        updates: Dict[str, Any] = {}
        if contract_maker is not None:
            updates["contract_maker"] = contract_maker
        if contract_taker is not None:
            updates["contract_taker"] = contract_taker

        new_route = dataclasses.replace(self.route, **updates)
        return dataclasses.replace(self, route=new_route)

    def with_accumulator(
        self,
        accumulator: float,
    ) -> "ExecutionContext":
        """
        Return new context with small order accumulator updated.

        Args:
            accumulator: New accumulator value

        Returns:
            New ExecutionContext with small_order_accumulator set
        """
        return dataclasses.replace(self, small_order_accumulator=accumulator)

    def clear_async_error(self) -> "ExecutionContext":
        """
        Return new context with async error cleared.

        Called after processing an async error.

        Returns:
            New ExecutionContext with pending_async_error = None
        """
        return dataclasses.replace(self, pending_async_error=None)

    def with_graph_context(
        self,
        exchanges: Sequence["IGateway"],
        trading_pairs: Sequence[str],
    ) -> "ExecutionContext":
        """
        Return new context with graph engine context set.

        This method sets the typed fields for graph arbitrage engines
        which need access to all exchanges and contracts.

        Args:
            exchanges: Sequence of exchange gateway interfaces
            trading_pairs: Sequence of trading pair strings (e.g., BTC_USD, ETH_USD)

        Returns:
            New ExecutionContext with graph context set
        """
        new_graph = dataclasses.replace(
            self.graph or GraphState(),
            exchanges=tuple(exchanges),
            trading_pairs=tuple(trading_pairs),
        )
        return dataclasses.replace(self, graph=new_graph)

    def with_active_order_context(
        self,
        active_order_context: "ActiveOrderContext",
    ) -> "ExecutionContext":
        """
        Return new context with active order context set.

        Used by graph engine to track the current maker/taker exchange
        routing for an active order lifecycle.

        Args:
            active_order_context: Immutable context for exchange routing

        Returns:
            New ExecutionContext with active order context set
        """
        new_graph = dataclasses.replace(
            self.graph or GraphState(),
            active_order_context=active_order_context,
        )
        return dataclasses.replace(self, graph=new_graph)

    def with_request_tracking(
        self,
        order_request_time: Optional[int] = None,
        taker_order_request_time: Optional[int] = None,
    ) -> "ExecutionContext":
        """
        Return new context with request tracking fields set.

        Used for timeout detection.

        Args:
            order_request_time: Timestamp when maker order was requested (ms)
            taker_order_request_time: Timestamp when taker order was requested (ms)

        Returns:
            New ExecutionContext with request tracking set
        """
        # Update timing sub-context
        timing_updates: Dict[str, Any] = {}
        if order_request_time is not None:
            timing_updates["order_request_time"] = order_request_time
        if taker_order_request_time is not None:
            timing_updates["taker_order_request_time"] = taker_order_request_time

        if timing_updates:
            new_timing = dataclasses.replace(self.timing, **timing_updates)
            return dataclasses.replace(self, timing=new_timing)

        return self

    # =========================================================================
    # New typed update methods (replacing metadata usage)
    # =========================================================================

    def with_timing_state(
        self,
        taker_sent_time: Optional[int] = None,
        cancel_sent_time: Optional[int] = None,
        taker_request_time: Optional[int] = None,
        maker_fill_timestamp: Optional[int] = None,
        taker_fill_timestamp: Optional[int] = None,
    ) -> "ExecutionContext":
        """
        Return new context with timing state updates.

        Replaces metadata usage for timing fields.

        Args:
            taker_sent_time: When taker entered TAKER_LIVE state (ms)
            cancel_sent_time: When cancel request was sent (ms)
            taker_request_time: When taker order was requested (ms)
            maker_fill_timestamp: When maker fill was detected (ms)
            taker_fill_timestamp: When taker fill was detected (ms)

        Returns:
            New ExecutionContext with timing updates
        """
        updates: Dict[str, Any] = {}
        if taker_sent_time is not None:
            updates["taker_sent_time"] = taker_sent_time
        if cancel_sent_time is not None:
            updates["cancel_sent_time"] = cancel_sent_time
        if taker_request_time is not None:
            updates["taker_request_time"] = taker_request_time
        if maker_fill_timestamp is not None:
            updates["maker_fill_timestamp"] = maker_fill_timestamp
        if taker_fill_timestamp is not None:
            updates["taker_fill_timestamp"] = taker_fill_timestamp

        if updates:
            new_timing = dataclasses.replace(self.timing, **updates)
            return dataclasses.replace(self, timing=new_timing)
        return self

    def with_retry_counters(
        self,
        taker_creation_attempts: Optional[int] = None,
        taker_retry_reason: Optional[str] = None,
        cancel_nonce_tries: Optional[int] = None,
        resolve_cancel_attempts: Optional[int] = None,
        cancel_already_terminal: Optional[bool] = None,
    ) -> "ExecutionContext":
        """
        Return new context with retry counter updates.

        Replaces metadata usage for retry counters.

        Args:
            taker_creation_attempts: Number of taker creation attempts
            taker_retry_reason: Reason for last taker retry
            cancel_nonce_tries: Number of cancel nonce error retries
            resolve_cancel_attempts: Number of cancel retries from RESOLVE_MAKER_ORDER
            cancel_already_terminal: Order is already terminal on exchange (needs REST verification)

        Returns:
            New ExecutionContext with retry counter updates
        """
        updates: Dict[str, Any] = {}
        if taker_creation_attempts is not None:
            updates["taker_creation_attempts"] = taker_creation_attempts
        if taker_retry_reason is not None:
            updates["taker_retry_reason"] = taker_retry_reason
        if cancel_nonce_tries is not None:
            updates["cancel_nonce_tries"] = cancel_nonce_tries
        if resolve_cancel_attempts is not None:
            updates["resolve_cancel_attempts"] = resolve_cancel_attempts
        if cancel_already_terminal is not None:
            updates["cancel_already_terminal"] = cancel_already_terminal

        if updates:
            new_orders = dataclasses.replace(self.orders, **updates)
            return dataclasses.replace(self, orders=new_orders)
        return self

    def with_backoff_state(
        self,
        global_backoff_until_ms: Optional[int] = None,
        cancel_backoff_until_ms: Optional[int] = None,
    ) -> "ExecutionContext":
        """
        Return new context with backoff state updates.

        Args:
            global_backoff_until_ms: Pause all operations until this time
            cancel_backoff_until_ms: Pause cancel requests until this time

        Returns:
            New ExecutionContext with backoff updates
        """
        updates: Dict[str, Any] = {}
        if global_backoff_until_ms is not None:
            updates["global_backoff_until_ms"] = global_backoff_until_ms
        if cancel_backoff_until_ms is not None:
            updates["cancel_backoff_until_ms"] = cancel_backoff_until_ms

        if updates:
            new_backoff = dataclasses.replace(self.backoff, **updates)
            return dataclasses.replace(self, backoff=new_backoff)
        return self

    def with_graph_state(
        self,
        opportunity: Optional["GraphOpportunity"] = None,
        current_opportunity: Optional["GraphOpportunity"] = None,
        target_spread: Optional[float] = None,
        cycle_count: Optional[int] = None,
        opportunity_switches: Optional[int] = None,
        total_profit: Optional[float] = None,
    ) -> "ExecutionContext":
        """
        Return new context with graph state updates.

        Replaces metadata usage for graph-specific fields.

        Args:
            opportunity: Current graph opportunity
            current_opportunity: Opportunity for comparison
            target_spread: Target spread for current opportunity
            cycle_count: Number of completed trading cycles
            opportunity_switches: Number of opportunity changes
            total_profit: Cumulative profit across cycles

        Returns:
            New ExecutionContext with graph state updates
        """
        updates: Dict[str, Any] = {}
        if opportunity is not None:
            updates["opportunity"] = opportunity
        if current_opportunity is not None:
            updates["current_opportunity"] = current_opportunity
        if target_spread is not None:
            updates["target_spread"] = target_spread
        if cycle_count is not None:
            updates["cycle_count"] = cycle_count
        if opportunity_switches is not None:
            updates["opportunity_switches"] = opportunity_switches
        if total_profit is not None:
            updates["total_profit"] = total_profit

        if updates:
            new_graph = dataclasses.replace(self.graph or GraphState(), **updates)
            return dataclasses.replace(self, graph=new_graph)
        return self

    def with_liquidation(
        self,
        instructions: "LiquidateInstructions",
    ) -> "ExecutionContext":
        """
        Return new context with liquidation instructions set.

        Replaces metadata usage for liquidate_instructions.

        Args:
            instructions: LiquidateInstructions for taker order creation

        Returns:
            New ExecutionContext with liquidation state set
        """
        new_liquidation = LiquidationState(instructions=instructions)
        return dataclasses.replace(self, liquidation=new_liquidation)

    def with_telemetry(
        self,
        wait_for_taker_fill: Optional[bool] = None,
        latency_data: Optional["LatencyData"] = None,
    ) -> "ExecutionContext":
        """
        Return new context with telemetry updates.

        Replaces metadata usage for telemetry fields.

        Args:
            wait_for_taker_fill: Whether to wait for taker fill confirmation
            latency_data: Collected latency metrics

        Returns:
            New ExecutionContext with telemetry updates
        """
        current = self.telemetry or TelemetryState()
        updates: Dict[str, Any] = {}
        if wait_for_taker_fill is not None:
            updates["wait_for_taker_fill"] = wait_for_taker_fill
        if latency_data is not None:
            updates["latency_data"] = latency_data

        if updates:
            new_telemetry = dataclasses.replace(current, **updates)
            return dataclasses.replace(self, telemetry=new_telemetry)
        return self

    # =========================================================================
    # Reset Methods
    # =========================================================================

    def clear_orders(self) -> "ExecutionContext":
        """
        Return new context with order IDs cleared.

        Used when transitioning back to START after order failure/completion.
        Preserves route info and exchange interfaces.
        Clears order-specific tracking (IDs, quotes, request tracking, async errors).
        """
        # Reset orders sub-context
        new_orders = OrderState()

        # Reset timing (keep tick_timestamp)
        new_timing = TimingState(tick_timestamp=self.timing.tick_timestamp)

        # Reset market (keep orderbooks, clear quotes)
        new_market = dataclasses.replace(
            self.market,
            quote=None,
            quote_sent=None,
        )

        # Clear graph active order context
        new_graph = None
        if self.graph is not None:
            new_graph = dataclasses.replace(self.graph, active_order_context=None)

        return dataclasses.replace(
            self,
            orders=new_orders,
            timing=new_timing,
            market=new_market,
            graph=new_graph,
            liquidation=None,
            pending_async_error=None,
        )

    def clear_for_new_cycle(self) -> "ExecutionContext":
        """
        Return new context ready for a new trading cycle.

        Clears order IDs, quotes, request tracking while preserving route
        configuration and exchange interfaces. Used after PROCESS_EXECUTION completes.

        Graph-specific persistent state (cycle_count, opportunity_switches, total_profit)
        is preserved via the GraphState sub-context.
        """
        # Reset orders sub-context
        new_orders = OrderState()

        # Reset timing with new tick timestamp
        new_timing = TimingState(tick_timestamp=int(time.time() * 1000))

        # Reset market
        new_market = MarketState()

        # Update graph state (preserve persistent fields, clear order context)
        new_graph = None
        if self.graph is not None:
            new_graph = dataclasses.replace(
                self.graph,
                active_order_context=None,
                cycle_count=self.graph.cycle_count + 1,
            )

        return dataclasses.replace(
            self,
            bot_state=BotState.START,
            orders=new_orders,
            timing=new_timing,
            market=new_market,
            graph=new_graph,
            liquidation=None,
            pending_async_error=None,
        )

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create_initial(
        cls,
        route_id: str,
        maker_exchange: str,
        taker_exchange: str,
        contract_maker: str,
        contract_taker: str,
    ) -> "ExecutionContext":
        """
        Factory method to create initial context for a route.

        Args:
            route_id: Route identifier
            maker_exchange: Maker exchange name
            taker_exchange: Taker exchange name
            contract_maker: Maker contract (e.g., 'BTC_USDT')
            contract_taker: Taker contract (e.g., 'BTC_USDT')

        Returns:
            New ExecutionContext in START state
        """
        route = RouteIdentity(
            route_id=route_id,
            maker_exchange=maker_exchange,
            taker_exchange=taker_exchange,
            contract_maker=contract_maker,
            contract_taker=contract_taker,
        )
        timing = TimingState(tick_timestamp=int(time.time() * 1000))

        return cls(
            bot_state=BotState.START,
            route=route,
            timing=timing,
        )

    # =========================================================================
    # Debug/Logging
    # =========================================================================

    def summary(self) -> str:
        """Return a concise summary string for logging."""
        parts = [
            f"route={self.route.route_id}",
            f"state={self.bot_state.name}",
            f"contract_maker={self.route.contract_maker}",
            f"contract_taker={self.route.contract_taker}",
        ]
        if self.orders.maker_internal_id:
            parts.append(f"maker_id={self.orders.maker_internal_id}")
        if self.orders.taker_internal_id:
            parts.append(f"taker_id={self.orders.taker_internal_id}")
        if self.orders.lifecycle_id:
            parts.append(f"lifecycle={self.orders.lifecycle_id}")
        return " | ".join(parts)


__all__ = ["ExecutionContext"]
