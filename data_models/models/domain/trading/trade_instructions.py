"""
Complete TradeInstructions model with Pydantic validation.

This module contains everything trade-instructions-related in one place:
- TradeInstructions Pydantic model with full validation
- Symbol conversion utilities
- Trading constraints and precision handling

TradeInstructions contains exchange-specific metadata about HOW to trade a pair:
- Price/size precision and formatting rules
- Minimum order sizes and notional values
- Fee rates (maker/taker)
- Futures-specific settings (leverage, funding)

For the trading pair identifier itself (WHAT you're trading), see TradingPair.
"""

import time
from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def _count_decimals(number: Union[int, float, str]) -> int:
    """Returns the number of decimal places in a given number."""
    try:
        number_str = str(number)
        if "." in number_str:
            return len(number_str.split(".")[1])
        else:
            return 0
    except Exception:
        return 0


class TradeInstructions(StrictBaseModel):
    """
    Exchange-specific trading instructions and constraints.

    This class contains all the metadata needed to properly format and validate
    orders for a specific trading pair on a specific exchange:
    - Precision rules (price_precision, size_precision, min_tick, step_size)
    - Size constraints (min_size, max_size, min_notional, max_notional)
    - Fee information (maker_fee, taker_fee)
    - Futures settings (is_futures, is_perpetual, max_leverage, funding_interval)

    Note: For the trading pair identifier (e.g., "BTC_USDT"), see TradingPair.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Required fields
    base_currency: str = Field(..., description="Base currency (e.g., 'BTC')")
    quote_currency: str = Field(..., description="Quote currency (e.g., 'USDT')")
    exchange: str = Field(..., description="Exchange identifier")

    # Trading constraints
    price_precision: int = Field(..., ge=0, description="Price decimal precision")
    size_precision: int = Field(..., ge=0, description="Size decimal precision")
    min_tick: float = Field(..., gt=0.0, description="Minimum price increment")
    min_size: float = Field(..., gt=0.0, description="Minimum order size")
    step_size: Optional[float] = Field(None, gt=0.0, description="Size increment between valid quantities")
    min_notional: float = Field(..., gt=0.0, description="Minimum notional value")

    # Contract type flags
    is_futures: bool = Field(default=False, description="Whether this is a futures contract")
    is_perpetual: bool = Field(default=False, description="Whether this is a perpetual futures")
    exchange_symbol: Optional[str] = Field(None, description="Exchange-specific symbol format")
    max_leverage: Optional[int] = Field(None, ge=1, description="Maximum leverage allowed")
    funding_interval_hours: Optional[int] = Field(None, ge=1, description="Hours between funding payments (futures only)")

    # Optional fields
    maker_fee: Optional[float] = Field(None, description="Maker fee rate")
    taker_fee: Optional[float] = Field(None, description="Taker fee rate")
    max_size: Optional[float] = Field(None, gt=0.0, description="Maximum order size")
    max_notional: Optional[float] = Field(None, gt=0.0, description="Maximum notional value")
    is_active: bool = Field(default=True, description="Whether pair is actively trading")
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Last updated timestamp")
    raw_exchange_data: Dict[str, Any] = Field(default_factory=dict, description="Original exchange data", exclude=True)

    # Validators
    @field_validator("min_tick", "min_size", "min_notional", mode="before")
    @classmethod
    def validate_positive_floats(cls, v: Union[str, int, float]) -> float:
        """Ensure positive values for constraints."""
        value = float(v)
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @field_validator("step_size", mode="before")
    @classmethod
    def validate_step_size(cls, v: Optional[Union[str, int, float]]) -> Optional[float]:
        """Validate step_size if provided."""
        if v is None:
            return None
        value = float(v)
        if value <= 0:
            raise ValueError("step_size must be positive")
        return value

    @field_validator("maker_fee", "taker_fee", mode="before")
    @classmethod
    def validate_fees(cls, v: Optional[Union[str, int, float]]) -> Optional[float]:
        """Convert fee values to float."""
        if v is None:
            return None
        return float(v)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Optional[Union[str, int, float]]) -> int:
        """Validate and normalize timestamp."""
        if v is None:
            return _current_timestamp_ms()
        return int(v)

    # Computed properties
    @computed_field
    def symbol(self) -> str:
        """Get the standardized symbol (BASE_QUOTE format)."""
        return f"{self.base_currency}_{self.quote_currency}"

    @computed_field
    def symbol_slash(self) -> str:
        """Get the symbol in BASE/QUOTE format."""
        return f"{self.base_currency}/{self.quote_currency}"

    @computed_field
    def effective_spread(self) -> float:
        """Get the effective spread including fees."""
        maker_fee = self.maker_fee or 0.0
        taker_fee = self.taker_fee or 0.0
        return (maker_fee + taker_fee) * 2  # Round trip cost

    # Utility methods
    def round_price(self, price: float) -> float:
        """Round price to the exchange's precision requirements."""
        if self.price_precision == 0:
            return float(int(price))
        return round(price, self.price_precision)

    def round_size(self, size: float) -> float:
        """Round size to the exchange's precision requirements."""
        if self.size_precision == 0:
            return float(int(size))
        return round(size, self.size_precision)

    def format_price(self, price: float) -> float:
        """Format price according to min_tick and precision."""
        if self.min_tick > 0:
            price = round(price / self.min_tick) * self.min_tick
        return self.round_price(price)

    def format_quantity(self, quantity: float) -> float:
        """Format quantity according to step_size and precision.

        Uses step_size if provided, otherwise derives from size_precision.
        This correctly separates minimum order size (min_size) from
        the increment between valid quantities (step_size).
        """
        # Use explicit step_size if provided, otherwise derive from size_precision
        effective_step = self.step_size if self.step_size else (10**-self.size_precision)
        if effective_step > 0:
            quantity = round(quantity / effective_step) * effective_step
        return self.round_size(quantity)

    def validate_order_size(self, size: float) -> bool:
        """Check if order size meets exchange requirements."""
        if size < self.min_size:
            return False
        if self.max_size and size > self.max_size:
            return False
        return True

    def validate_notional_value(self, price: float, size: float) -> bool:
        """Check if notional value meets exchange requirements."""
        notional = price * size
        if notional < self.min_notional:
            return False
        if self.max_notional and notional > self.max_notional:
            return False
        return True

    def to_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """Convert to dictionary for serialization."""
        base_dict = self.model_dump(exclude={"raw_exchange_data"})
        # Add computed fields
        base_dict.update(
            {
                "symbol": self.symbol,
                "symbol_slash": self.symbol_slash,
                "effective_spread": self.effective_spread,
            }
        )
        return base_dict

    def __str__(self) -> str:
        """String representation of the trade instructions."""
        return f"TradeInstructions({self.symbol} on {self.exchange})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"TradeInstructions(symbol={self.symbol!r}, exchange={self.exchange!r}, "
            f"min_size={self.min_size}, min_tick={self.min_tick})"
        )
