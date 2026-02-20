"""
Complete Trade model with Pydantic validation.

This module contains the Trade class representing a single executed trade
from the market data feed (not to be confused with block trades).
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from data_models.models.domain.base import StrictBaseModel
from data_models.models.enums.trading import TradeSide


class Trade(StrictBaseModel):
    """
    Pydantic model representing a single market trade.

    This represents an executed trade from the market data feed,
    showing actual transactions between market participants.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,  # Keep TradeSide as enum
        validate_default=True,
        populate_by_name=True,
    )

    # Trade identification
    trade_id: str = Field(..., min_length=1, description="Exchange-specific trade ID")
    contract: str = Field(..., min_length=1, description="Trading pair/contract")

    # Trade details
    price: Decimal = Field(..., gt=0, description="Execution price")
    amount: Decimal = Field(..., gt=0, description="Trade size/quantity")
    side: TradeSide = Field(..., description="Trade side (taker's perspective)")

    # Timestamp
    timestamp: int = Field(..., gt=0, description="Unix timestamp in milliseconds")

    # Optional fields
    maker_order_id: Optional[str] = Field(None, description="Maker's order ID if available")
    taker_order_id: Optional[str] = Field(None, description="Taker's order ID if available")
    fee: Optional[Decimal] = Field(None, ge=0, description="Trading fee if available")

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, v: Any) -> TradeSide:
        """Validate and normalize trade side to enum."""
        if isinstance(v, TradeSide):
            return v
        if isinstance(v, str):
            normalized = v.lower()
            try:
                return TradeSide(normalized)
            except ValueError:
                for side in TradeSide:
                    if side.value.upper() == v.upper():
                        return side
                return TradeSide.UNKNOWN
        raise ValueError(f"Invalid trade side type: {type(v).__name__}, expected TradeSide or str")

    @field_validator("price", "amount", mode="before")
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Convert numeric types to Decimal."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        raise ValueError(f"Invalid decimal field type: {type(v).__name__}, expected Decimal, int, float, or str")

    @field_validator("fee", mode="before")
    @classmethod
    def validate_fee(cls, v: Any) -> Optional[Decimal]:
        """Convert fee to Decimal if provided."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        raise ValueError(f"Invalid fee type: {type(v).__name__}, expected Decimal, int, float, str, or None")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "trade_id": self.trade_id,
            "contract": self.contract,
            "price": float(self.price),
            "amount": float(self.amount),
            "side": self.side.value,
            "timestamp": self.timestamp,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "fee": float(self.fee) if self.fee else None,
        }

    def __str__(self) -> str:
        """String representation of trade."""
        return (
            f"Trade(id={self.trade_id}, contract={self.contract}, "
            f"price={self.price}, amount={self.amount}, side={self.side.value})"
        )
