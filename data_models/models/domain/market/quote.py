"""
Complete Quote model with Pydantic validation.

This module contains the Quote class representing a trading quote with bid and ask details.
A quote is used by the broker to send orders to the exchange gateway.
"""

from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from data_models.models.domain.base import StrictBaseModel
from data_models.models.enums.order import OrderType


class Quote(StrictBaseModel):
    """
    Pydantic model representing a trading quote with bid and ask details.

    A quote contains all information needed by the broker to create orders,
    including prices, sizes, spreads, and liquidity for both bid and ask sides.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,  # Keep OrderType as enum
        validate_default=True,
        populate_by_name=True,
    )

    # Contract
    contract: str = Field(..., min_length=1, description="Trading pair contract")

    # Bid side
    bid_price: float = Field(..., gt=0.0, description="Bid price")
    bid_size: float = Field(..., gt=0.0, description="Bid size/amount")
    bid_type: OrderType = Field(..., description="Order type for bid")
    bid_spread: float = Field(..., description="Bid spread")
    bid_distance: float = Field(..., description="Bid distance from mid")
    bid_conversion: float = Field(..., description="Bid conversion rate")
    bid_distance_test: bool = Field(..., description="Whether bid passes distance test")
    bid_liquidity: float = Field(..., ge=0.0, description="Available bid liquidity")

    # Ask side
    ask_price: float = Field(..., gt=0.0, description="Ask price")
    ask_size: float = Field(..., gt=0.0, description="Ask size/amount")
    ask_type: OrderType = Field(..., description="Order type for ask")
    ask_spread: float = Field(..., description="Ask spread")
    ask_distance: float = Field(..., description="Ask distance from mid")
    ask_conversion: float = Field(..., description="Ask conversion rate")
    ask_distance_test: bool = Field(..., description="Whether ask passes distance test")
    ask_liquidity: float = Field(..., ge=0.0, description="Available ask liquidity")

    # Graph arbitrage metadata (optional fields for graph engine)
    opportunity_context: Optional[Dict[str, Any]] = Field(
        None, description="Graph opportunity context (source, target, spread, path_type)"
    )
    exchange_context: Optional[Dict[str, str]] = Field(
        None,
        description="Exchange routing context (maker_exchange, taker_exchange, maker_contract, taker_contract, universal_contract)",
    )
    explicit_sides: Optional[Dict[str, str]] = Field(None, description="Explicit maker/taker sides for graph routing")

    # Telemetry metadata
    event_id: Optional[str] = Field(None, description="Event ID for telemetry correlation (e.g., 'evt_a3f9b2')")

    # Mode-specific target spreads (REQUIRED - each thread has independent parameters)
    target_premium: float = Field(
        ..., description="Target premium % used to generate this quote (0.0 for unwinding, 0.3 for market-making)"
    )
    target_discount: float = Field(
        ..., description="Target discount % used to generate this quote (0.0 for unwinding, 0.3 for market-making)"
    )

    # Taker reference context for audit logging (populated when TakerReferenceCalculator is enabled)
    taker_reference_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Taker reference calculation context (bbo, vwap, ref, adjustment, levels, depth) for audit",
    )

    @field_validator("bid_type", "ask_type", mode="before")
    @classmethod
    def validate_order_type(cls, v: str | OrderType) -> OrderType:
        """Validate and normalize order type to enum."""
        if isinstance(v, str):
            try:
                return OrderType(v.lower())
            except ValueError:
                for order_type in OrderType:
                    if order_type.value.upper() == v.upper():
                        return order_type
                raise ValueError(f"Invalid order type: {v}") from None
        return v

    @field_validator("bid_price", "ask_price")
    @classmethod
    def validate_prices(cls, v: float) -> float:
        """Ensure prices are positive."""
        if v <= 0:
            raise ValueError("Prices must be positive")
        return v

    @field_validator("bid_size", "ask_size")
    @classmethod
    def validate_sizes(cls, v: float) -> float:
        """Ensure sizes are positive."""
        if v <= 0:
            raise ValueError("Sizes must be positive")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert Quote to dictionary with enum values."""
        result = {
            "contract": self.contract,
            "bid_price": self.bid_price,
            "bid_size": self.bid_size,
            "bid_type": self.bid_type.value,
            "bid_spread": self.bid_spread,
            "bid_distance": self.bid_distance,
            "bid_conversion": self.bid_conversion,
            "bid_distance_test": self.bid_distance_test,
            "bid_liquidity": self.bid_liquidity,
            "ask_price": self.ask_price,
            "ask_size": self.ask_size,
            "ask_type": self.ask_type.value,
            "ask_spread": self.ask_spread,
            "ask_distance": self.ask_distance,
            "ask_conversion": self.ask_conversion,
            "ask_distance_test": self.ask_distance_test,
            "ask_liquidity": self.ask_liquidity,
        }

        if self.opportunity_context is not None:
            result["opportunity_context"] = self.opportunity_context
        if self.exchange_context is not None:
            result["exchange_context"] = self.exchange_context
        if self.explicit_sides is not None:
            result["explicit_sides"] = self.explicit_sides
        if self.event_id is not None:
            result["event_id"] = self.event_id

        return result

    @classmethod
    def from_dict(cls, quote_dict: Dict[str, Any]) -> "Quote":
        """Create Quote from dictionary."""
        return cls(**quote_dict)
