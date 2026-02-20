"""
Immutable data models for broker services.

All models use frozen dataclasses to ensure immutability, following
the engine service pattern for clean data transfer between layers.

These models are used by the broker services layer:
- OrderService uses OrderCreationRequest/OrderCreationResult
- LiquidationService uses LiquidationParams/MinOrderCheckResult
- AccumulatorService uses AccumulatorAdjustment
"""

from dataclasses import dataclass
from typing import Any, Optional

from data_models.models.enums.order import OrderSide, OrderType


@dataclass(frozen=True)
class OrderCreationRequest:
    """
    Input for order creation.

    Immutable request object containing all parameters needed to create
    an order on an exchange. The broker constructs this from bot state
    and passes it to the OrderService.
    """

    contract: str
    side: OrderSide
    price: float
    amount: float
    order_type: OrderType
    internal_id: str
    is_maker_order: bool = True
    route_id: Optional[str] = None


@dataclass(frozen=True)
class OrderCreationResult:
    """
    Output from order creation.

    Immutable result object returned by OrderService. The broker uses
    this to update bot state accordingly.

    For async orders, async_result contains the AsyncOrderResult object
    which can be used to register additional callbacks.
    """

    success: bool
    internal_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    is_async: bool = False
    async_result: Optional[Any] = None  # AsyncOrderResult for registering callbacks


@dataclass(frozen=True)
class LiquidationParams:
    """
    Prepared liquidation parameters.

    Contains all computed values needed to execute a liquidation order,
    including adjusted amounts from accumulator and exchange minimums.
    """

    contract: str
    adjusted_amount: float
    min_size: float
    min_notional: float
    used_accumulator: float
    trading_pair: Any  # TradingPair object


@dataclass(frozen=True)
class MinOrderCheckResult:
    """
    Minimum order size validation result.

    Indicates whether an order meets exchange minimum requirements
    and provides details for logging/debugging.
    """

    passes_minimum: bool
    rounded_amount: float
    notional_value: float
    reason: Optional[str] = None


@dataclass(frozen=True)
class AccumulatorAdjustment:
    """
    Result of adjusting an amount using the accumulator.

    Returned by AccumulatorService when applying accumulated
    small orders to a liquidation.
    """

    adjusted_amount: float
    used_from_accumulator: float
    was_adjusted: bool
