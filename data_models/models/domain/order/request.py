"""
Complete OrderRequest model with Pydantic validation.

This module contains everything order-request-related in one place:
- OrderRequest Pydantic model with full type safety
- Validated order parameters with enums
"""

import time
from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel
from data_models.models.enums.order import OrderRequestStatus, OrderSide, OrderType


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class OrderRequest(StrictBaseModel):
    """
    Fully-typed order request model with Pydantic validation.

    All order parameters are explicit typed fields with validation.
    No dict-based storage - everything is type-safe.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Identity
    internal_id: str = Field(..., description="Our internally-generated order ID")

    # Order parameters (fully typed)
    symbol: str = Field(..., description="Trading pair symbol")
    side: OrderSide = Field(..., description="Order side (BUY/SELL)")
    order_type: OrderType = Field(..., description="Order type (LIMIT/MARKET/POST_ONLY)")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (required for limit orders)")
    route_id: Optional[str] = Field(None, description="Route identifier for OrderStreamClient routing")

    # Order flags
    post_only: bool = Field(default=False, description="Post-only flag (maker orders)")
    reduce_only: bool = Field(default=False, description="Reduce-only flag (close positions)")
    position_side: str = Field(default="BOTH", description="Position side for futures (BOTH/LONG/SHORT)")
    time_in_force: str = Field(default="GTC", description="Time in force (GTC/IOC/FOK)")

    # Futures-specific fields (optional, with defaults)
    close_position: bool = Field(default=False, description="Close entire position (futures)")
    stop_price: Optional[float] = Field(None, description="Stop price for stop/take profit orders")
    working_type: Optional[str] = Field(None, description="Working type for stop orders (MARK_PRICE/CONTRACT_PRICE)")

    # Tracking fields
    exchange_order_id: Optional[str] = Field(None, description="Exchange-assigned order ID")
    internal_status: OrderRequestStatus = Field(
        default=OrderRequestStatus.SUCCESS, description="Internal status classification"
    )
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Request timestamp")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Optional[Union[str, int, float]]) -> int:
        """Validate and normalize timestamp."""
        if v is None:
            return _current_timestamp_ms()
        return int(v)

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, v: str | OrderSide) -> OrderSide:
        """Convert string to OrderSide enum."""
        if isinstance(v, str):
            return OrderSide.from_string(v)
        return v

    @field_validator("order_type", mode="before")
    @classmethod
    def validate_order_type(cls, v: str | OrderType) -> OrderType:
        """Convert string to OrderType enum."""
        if isinstance(v, str):
            return OrderType.from_string(v)
        return v

    # Computed properties
    @computed_field
    def is_successful(self) -> bool:
        """Check if the request was successful."""
        return self.internal_status == OrderRequestStatus.SUCCESS

    @computed_field
    def is_pending(self) -> bool:
        """Check if the request is still pending."""
        return self.internal_status == OrderRequestStatus.PENDING

    @computed_field
    def has_exchange_id(self) -> bool:
        """Check if exchange order ID is available."""
        return self.exchange_order_id is not None

    @computed_field
    def is_error(self) -> bool:
        """Check if the request resulted in an error."""
        error_statuses = [
            OrderRequestStatus.TIMEOUT_ERROR,
            OrderRequestStatus.INSUFFICIENT_FUNDS,
            OrderRequestStatus.UNKNOWN_REJECTION,
            OrderRequestStatus.CRITICAL_ERROR,
            OrderRequestStatus.INTERNAL_ERROR,
            OrderRequestStatus.PRICE_FILTER_REJECTION,
            OrderRequestStatus.POST_ONLY_REJECTED,
            OrderRequestStatus.LIMIT_MAKER_REJECTED,
            OrderRequestStatus.WEBSOCKET_NOT_CONNECTED,
            OrderRequestStatus.RATE_LIMIT_ERROR,
        ]
        return self.internal_status in error_statuses

    # Methods
    def update_with_response(
        self,
        exchange_order_id: Optional[str] = None,
        status: Optional[OrderRequestStatus] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update the request with exchange response data.

        Args:
            exchange_order_id: Exchange-assigned order ID
            status: New status (must be OrderRequestStatus enum)
            error: Error message if applicable
        """
        if exchange_order_id:
            self.exchange_order_id = exchange_order_id

        if status is not None:
            self.internal_status = status

        if error:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()

    def __str__(self) -> str:
        """String representation of the order request."""
        return f"OrderRequest(internal_id={self.internal_id}, status={self.internal_status.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"OrderRequest(internal_id={self.internal_id!r}, "
            f"exchange_order_id={self.exchange_order_id!r}, "
            f"status={self.internal_status.value!r})"
        )
