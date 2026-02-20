"""
Order signal models for async order handling.

These dataclasses represent signals that flow from broker callbacks to the engine:
- AsyncOrderError: Captures async order failures for engine to handle
- InstantFillSignal: Signals immediate fills for fast state transitions

Note: Uses AsyncOrderErrorType from exchange_protocols (not a new enum).
"""

from dataclasses import dataclass
from typing import Optional

from data_models.models.domain.order.order import Order
from data_models.models.enums.trading import OrderRole
from data_models.models.protocols.exchange_protocols import AsyncOrderErrorType


@dataclass
class AsyncOrderError:
    """
    Error information from async order submission.

    Broker stores this when async callback fails.
    Engine queries and clears this to handle errors.

    Attributes:
        internal_id: Our internal order ID
        error_type: Classification of the error (uses existing AsyncOrderErrorType)
        backoff_until_ms: For rate limits, when to retry (epoch ms)
        message: Human-readable error message
    """

    internal_id: str
    error_type: AsyncOrderErrorType
    backoff_until_ms: Optional[int] = None
    message: Optional[str] = None


@dataclass
class InstantFillSignal:
    """
    Signal that an order was filled immediately in the creation callback.

    Broker stores this when async callback detects instant fill.
    Engine consumes this at tick start to trigger immediate state transition.

    This allows broker to signal instant fills WITHOUT managing state.
    State transitions happen exclusively in the engine.

    Attributes:
        internal_id: Our internal order ID
        order: The filled Order object
        order_role: MAKER or TAKER (determines state transition)
    """

    internal_id: str
    order: Order
    order_role: OrderRole
