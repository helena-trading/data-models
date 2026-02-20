"""
Shared result models for state handlers.

This module contains dataclasses that are used across multiple handlers
to avoid code duplication and ensure consistent type definitions.

All models are frozen (immutable) for thread safety and to prevent
accidental state mutation during order lifecycle processing.

Note: ActiveOrderContext was moved to context.py to break circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple, Optional

from data_models.models.domain.order.order import Order
from data_models.models.engine.execution_context import ExecutionContext


class TimeoutResult(NamedTuple):
    """Result of handling a timeout in the engine.

    Used by BaseEngine.handle_timeout() and _handle_specific_timeout().
    """

    new_state: Optional[str]
    """New bot state name if changed, None if no state change."""

    context: "ExecutionContext"
    """Updated execution context after timeout handling."""


@dataclass(frozen=True)
class MakerFillResult:
    """
    Result of checking maker order fill status.

    Used by both CrossMakerLiveHandler and GraphMakerLiveHandler
    to communicate fill status and cancellation decisions.

    The maker_order field carries the Order object for price adjustment
    calculations in LiquidationService (avg_price for slippage protection).
    """

    is_filled: bool = False
    fill_amount: Optional[float] = None
    fill_price: Optional[float] = None
    maker_order: Optional["Order"] = None
    should_cancel: bool = False
    cancel_reason: Optional[str] = None


@dataclass(frozen=True)
class TakerOrderResult:
    """
    Result of creating a taker order.

    Returned by maker_live handlers after successfully initiating
    a taker order to liquidate a filled maker position.
    """

    internal_id: str
    req_id: Optional[str] = None


@dataclass(frozen=True)
class MakerOrderServiceResult:
    """
    Result of MakerOrderService.route_maker_order().

    Contains all data needed by the handler to build the new context.
    Services return data, handlers build context.
    """

    success: bool = False
    """True if order was created successfully."""

    internal_id: Optional[str] = None
    """Internal order ID string (sent to exchange as our internal_id)."""

    quote_sent: Optional[Any] = None
    """The quote that was used to create the order."""

    liquidate_instructions: Optional[Any] = None
    """Instructions for taker order (LiquidateInstructions)."""

    error: Optional[str] = None
    """Error message if success=False."""


@dataclass(frozen=True)
class BetterOpportunityResult:
    """
    Result of checking for better trading opportunities.

    Graph-specific: Used by GraphMakerLiveHandler to decide
    whether to cancel current order and switch to a better opportunity.
    """

    should_switch: bool = False
    new_opportunity: Optional[Any] = None
    improvement: float = 0.0  # Improvement in profitability (percentage)


__all__ = [
    "MakerFillResult",
    "MakerOrderServiceResult",
    "TakerOrderResult",
    "BetterOpportunityResult",
    "TimeoutResult",
]
