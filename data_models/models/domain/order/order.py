"""
Complete Order model with Pydantic validation.

This module contains the Order Pydantic model with full validation.
Enums are imported from the centralized src.models.enums module.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, ValidationInfo, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel
from data_models.models.domain.order.ids import ExchangeOrderId, InternalOrderId
from data_models.models.enums.order import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from data_models.models.enums.order import normalize_order_type as _normalize_order_type
from data_models.models.enums.order import normalize_side as _normalize_side
from data_models.models.enums.order import normalize_status as _normalize_status


class Order(StrictBaseModel):
    """
    Standardized order model with Pydantic validation.

    This class provides a consistent representation of orders across different
    exchanges, with automatic validation and type conversion.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,  # Keep enums as enums
        validate_default=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,  # Allow custom types like InternalOrderId
    )

    # TYPE-SAFE ID FIELDS (CRITICAL FOR CLARITY)
    exchange_order_id: Optional[ExchangeOrderId] = Field(
        default=None, description="Exchange-assigned order ID (None until exchange confirms order)"
    )
    internal_id: InternalOrderId = Field(..., description="Our internally-generated ID for tracking (set at order creation)")

    # Required fields
    contract: str = Field(..., description="Trading pair in standardized format")
    exchange: str = Field(..., description="Exchange identifier (e.g., 'binance_spot')")
    side: OrderSide = Field(..., description="Buy or sell direction")
    price: float = Field(..., ge=0.0, description="Order price")
    amount: float = Field(..., ge=0.0, description="Total order size")

    # Optional fields with defaults
    filled_amount: float = Field(default=0.0, ge=0.0, description="Amount that has been executed")
    status: OrderStatus = Field(default=OrderStatus.NEW, description="Order status")
    order_type: OrderType = Field(default=OrderType.LIMIT, description="Type of order")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Creation/update timestamp in ms")
    avg_price: float = Field(default=0.0, ge=0.0, description="Average execution price for filled amount")
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection (e.g., badAloPxRejected)")
    raw_exchange_data: Dict[str, Any] = Field(
        default_factory=dict, description="Original exchange-specific data", exclude=True
    )

    # Fields for tracking execution state
    update_time: Optional[int] = Field(default=None, description="Last update timestamp from exchange in ms")
    has_any_execution: bool = Field(default=False, description="Whether order has had any execution (fills)")
    route_id: Optional[str] = Field(default=None, description="Route identifier for multi-leg trades")

    # Futures-specific fields
    reduce_only: bool = Field(default=False, description="Reduce-only flag (can only close positions, not open)")

    # Telemetry metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry metadata (event_id, parent_event_id, timing, etc.)",
    )

    # Validators
    @field_validator("internal_id", mode="before")
    @classmethod
    def validate_internal_id(cls, v: str | InternalOrderId | None) -> InternalOrderId:
        """Ensure internal_id is an InternalOrderId type."""
        if not v:
            raise ValueError("internal_id is required")
        if isinstance(v, str):
            return InternalOrderId(v)
        return v

    @field_validator("exchange_order_id", mode="before")
    @classmethod
    def validate_exchange_order_id(cls, v: str | ExchangeOrderId | None) -> Optional[ExchangeOrderId]:
        """Ensure exchange_order_id is an ExchangeOrderId type if provided."""
        if v is None:
            return None
        if isinstance(v, str):
            return ExchangeOrderId(v)
        return v

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, v: str | OrderSide | None) -> OrderSide:
        """Normalize order side to an OrderSide enum."""
        return _normalize_side(v)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str | OrderStatus | None) -> OrderStatus:
        """Normalize order status to an OrderStatus enum."""
        return _normalize_status(v)

    @field_validator("order_type", mode="before")
    @classmethod
    def validate_order_type(cls, v: str | OrderType | None) -> OrderType:
        """Normalize order type to an OrderType enum."""
        return _normalize_order_type(v)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Optional[int]) -> int:
        """Normalize timestamp to milliseconds."""
        if v is not None and v > 0:
            return int(v)
        return int(time.time() * 1000)

    @field_validator("price", "amount", "avg_price", mode="before")
    @classmethod
    def validate_numeric_fields(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert numeric fields to float (accepts Decimal from exchange adapters)."""
        return float(v)

    @field_validator("filled_amount", mode="before")
    @classmethod
    def validate_filled_amount_type(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert filled_amount to float (accepts Decimal from exchange adapters)."""
        return float(v)

    @field_validator("filled_amount")
    @classmethod
    def validate_filled_amount(cls, v: float, info: ValidationInfo) -> float:
        """Validate filled amount doesn't exceed total amount."""
        if "amount" in info.data:
            amount = info.data["amount"]
            if v > amount + 1e-8:  # Allow small floating point errors
                raise ValueError(f"filled_amount ({v}) cannot exceed amount ({amount})")
        return v

    # Computed properties
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        terminal_states = [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ]
        return self.status in terminal_states

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED or (self.filled_amount > 0 and abs(self.filled_amount - self.amount) < 1e-8)

    @computed_field
    def is_active(self) -> bool:
        """Check if order is still active."""
        active_statuses = [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED, OrderStatus.OPEN]
        return self.status in active_statuses

    @computed_field
    def is_canceled(self) -> bool:
        """Check if order is canceled."""
        return self.status == OrderStatus.CANCELED

    @computed_field
    def is_rejected(self) -> bool:
        """Check if order is rejected."""
        return self.status == OrderStatus.REJECTED

    @computed_field
    def remaining_amount(self) -> float:
        """Get remaining amount to be filled."""
        return max(0.0, self.amount - self.filled_amount)

    @computed_field
    def fill_percentage(self) -> float:
        """Get fill percentage."""
        if self.amount <= 0:
            return 0.0
        return min(100.0, (self.filled_amount / self.amount) * 100.0)

    # Methods
    def update_status(self, new_status: OrderStatus) -> bool:
        """Update order status with terminal state protection.

        Args:
            new_status: The new status to set (must be OrderStatus enum)

        Returns:
            True if status was updated, False if blocked by terminal state protection
        """
        terminal_states = [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ]

        if self.status in terminal_states:
            if new_status not in terminal_states:
                return False

        self.status = new_status
        return True

    def to_dict(self) -> Dict[str, Union[str, float, int, bool, None]]:
        """Convert order to dictionary format."""
        base_dict = self.model_dump(exclude={"raw_exchange_data"})
        base_dict.update(
            {
                "internal_id": str(self.internal_id),
                "exchange_order_id": str(self.exchange_order_id) if self.exchange_order_id else None,
                "side": self.side.value,
                "status": self.status.value,
                "order_type": self.order_type.value,
                "is_filled": self.is_filled,
                "is_active": self.is_active,
                "remaining_amount": self.remaining_amount,
                "fill_percentage": self.fill_percentage,
            }
        )
        return base_dict

    def __str__(self) -> str:
        """String representation of the order."""
        display_id = str(self.exchange_order_id) if self.exchange_order_id else str(self.internal_id)
        return (
            f"Order({self.exchange} {display_id}: "
            f"{self.side.value} {self.amount} {self.contract} @ {self.price} "
            f"[{self.status.value}])"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Order(exchange_id={self.exchange_order_id!r}, internal_id={self.internal_id!r}, "
            f"exchange={self.exchange!r}, contract={self.contract!r}, "
            f"side={self.side.value!r}, price={self.price}, amount={self.amount}, "
            f"filled={self.filled_amount}, status={self.status.value!r}, "
            f"type={self.order_type.value!r})"
        )
