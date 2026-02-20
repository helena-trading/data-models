"""
Complete Ticker model with Pydantic validation.

This module contains everything ticker-related in one place:
- Ticker Pydantic model with full validation
- Price calculation utilities and computed properties
"""

import time
from decimal import Decimal
from typing import Any, Dict, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class Ticker(StrictBaseModel):
    """
    Standardized ticker model with price and trading data and Pydantic validation.

    This class represents market data for a trading pair including prices,
    volume, and computed properties like spreads.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Required fields
    exchange: str = Field(..., description="Exchange identifier")
    contract: str = Field(..., description="Trading pair/contract")
    last: float = Field(..., ge=0.0, description="Last traded price")
    bid: float = Field(..., ge=0.0, description="Best bid price")
    ask: float = Field(..., ge=0.0, description="Best ask price")

    # Optional fields with defaults
    high: float = Field(default=0.0, ge=0.0, description="24h high price")
    low: float = Field(default=0.0, ge=0.0, description="24h low price")
    open: float = Field(default=0.0, ge=0.0, description="24h open price")
    volume: float = Field(default=0.0, ge=0.0, description="24h trading volume")
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Timestamp of the ticker")
    raw_exchange_data: Dict[str, Any] = Field(default_factory=dict, description="Original exchange data", exclude=True)

    # Validators
    @field_validator("last", "bid", "ask", "high", "low", "open", "volume", mode="before")
    @classmethod
    def validate_prices(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert price values to float (accepts Decimal from exchange adapters)."""
        return float(v) if v is not None else 0.0

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Union[str, int, None]) -> int:
        """Validate and normalize timestamp."""
        if v is None:
            return _current_timestamp_ms()
        return int(v)

    # Computed properties
    @computed_field  # type: ignore[prop-decorator]
    @property
    def mid_price(self) -> float:
        """Get mid price between bid and ask."""
        return (self.bid + self.ask) / 2 if self.bid and self.ask else self.last

    @computed_field  # type: ignore[prop-decorator]
    @property
    def price(self) -> float:
        """Get current price (alias for last)."""
        return self.last

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> float:
        """Get spread between bid and ask."""
        return self.ask - self.bid if self.ask and self.bid else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread_percentage(self) -> float:
        """Get spread as percentage of mid price."""
        # Compute mid and spread directly (avoid accessing @computed_field as property)
        mid = (self.bid + self.ask) / 2 if self.bid and self.ask else self.last
        sprd = self.ask - self.bid if self.ask and self.bid else 0.0
        if mid > 0 and sprd > 0:
            return (sprd / mid) * 100
        return 0.0

    # Methods
    def to_dict(self) -> Dict[str, Union[str, float, int]]:
        """Convert to dictionary for serialization."""
        # Get base dict and manually remove computed fields (model_dump exclude doesn't work for @computed_field)
        base_dict = self.model_dump(exclude={"raw_exchange_data"})
        # Remove computed fields to allow round-trip serialization
        for key in ["mid_price", "price", "spread", "spread_percentage"]:
            base_dict.pop(key, None)
        return base_dict

    def get_mid_price(self) -> float:
        """Get mid price between bid and ask."""
        mid = self.mid_price  # @computed_field already returns float
        return mid if mid is not None else 0.0
