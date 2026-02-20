"""
Complete Orderbook model with Pydantic validation.

This module contains everything orderbook-related in one place:
- OrderbookLevel Pydantic model for price levels
- Orderbook Pydantic model with full validation
- Best bid/ask utilities and computed properties
"""

import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class OrderbookLevel(StrictBaseModel):
    """Single price level in the orderbook with Pydantic validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    price: float = Field(..., gt=0.0, description="Price level")
    amount: float = Field(..., ge=0.0, description="Quantity available at this price")

    @field_validator("price", "amount", mode="before")
    @classmethod
    def validate_amounts(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert price/amount to float (accepts Decimal from exchange adapters)."""
        return float(v)

    def to_dict(self) -> Dict[str, float]:
        """Convert the orderbook level to a dictionary representation."""
        return {"price": self.price, "amount": self.amount}


class Orderbook(StrictBaseModel):
    """Standardized orderbook model with Pydantic validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Required fields
    contract: str = Field(..., alias="symbol", description="Trading pair/contract")
    exchange: str = Field(..., description="Exchange identifier")
    bids: List[OrderbookLevel] = Field(..., description="Buy orders, sorted by price (descending)")
    asks: List[OrderbookLevel] = Field(..., description="Sell orders, sorted by price (ascending)")

    # Optional fields with defaults
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Timestamp of the orderbook")
    sequence_number: Optional[int] = Field(None, description="Some exchanges provide sequence numbers")
    raw_exchange_data: Dict[str, Any] = Field(default_factory=dict, description="Original exchange data", exclude=True)

    @field_validator("bids", "asks", mode="before")
    @classmethod
    def validate_levels(
        cls,
        v: List[
            Union[
                Dict[str, Any],
                List[Union[str, int, float, Decimal]],
                tuple[Union[str, int, float, Decimal], Union[str, int, float, Decimal]],
                OrderbookLevel,
            ]
        ],
    ) -> List[OrderbookLevel]:
        """Convert various level formats to OrderbookLevel objects.

        Accepts:
        - OrderbookLevel instances
        - Dict format: {"price": 100.0, "amount": 5.0}
        - List/tuple format: [100.0, 5.0] or (Decimal("100.0"), Decimal("5.0"))
        """
        if not v:
            return []

        levels = []
        for item in v:
            if isinstance(item, OrderbookLevel):
                levels.append(item)
            elif isinstance(item, dict):
                # Handle dict format {"price": 100.0, "amount": 5.0}
                levels.append(OrderbookLevel(price=float(item["price"]), amount=float(item["amount"])))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                # Handle array/tuple format [100.0, 5.0] or (Decimal, Decimal)
                levels.append(OrderbookLevel(price=float(item[0]), amount=float(item[1])))

        return levels

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Optional[Union[str, int, float]]) -> int:
        """Validate and normalize timestamp."""
        if v is None:
            return _current_timestamp_ms()
        return int(v)

    # Computed properties
    @computed_field  # type: ignore[prop-decorator]
    @property
    def best_bid(self) -> Optional[OrderbookLevel]:
        """Get the highest bid (buy) price level from the orderbook."""
        return self.bids[0] if self.bids else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def best_ask(self) -> Optional[OrderbookLevel]:
        """Get the lowest ask (sell) price level from the orderbook."""
        return self.asks[0] if self.asks else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate the mid price between the best bid and best ask."""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> Optional[float]:
        """Get the spread between best bid and ask."""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread_percentage(self) -> Optional[float]:
        """Get spread as percentage of mid price."""
        mid_price_value = self.mid_price
        spread_value = self.spread
        if mid_price_value and spread_value:
            return (spread_value / mid_price_value) * 100
        return None

    def to_dict(self) -> Dict[str, Union[str, int, float, None, List[Dict[str, float]]]]:
        """Convert the orderbook to a dictionary representation."""
        base_dict = self.model_dump(exclude={"raw_exchange_data"})

        # Convert levels to dict format
        base_dict["bids"] = [bid.to_dict() for bid in self.bids]
        base_dict["asks"] = [ask.to_dict() for ask in self.asks]

        # Add computed fields for serialization
        base_dict.update(
            {
                "mid_price": self.mid_price,
                "spread": self.spread,
                "spread_percentage": self.spread_percentage,
            }
        )

        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Orderbook":
        """Create Orderbook from dictionary with proper symbol/contract aliasing.

        Args:
            data: Dictionary containing orderbook data

        Returns:
            Orderbook: Validated orderbook instance
        """
        data_copy = data.copy()

        if "symbol" in data_copy and "contract" in data_copy:
            del data_copy["symbol"]
        elif "symbol" in data_copy and "contract" not in data_copy:
            data_copy["contract"] = data_copy.pop("symbol")

        return cls.model_validate(data_copy)
