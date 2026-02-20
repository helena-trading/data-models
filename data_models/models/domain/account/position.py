"""
Complete Position model with Pydantic validation.

This module contains everything position-related in one place:
- Position Pydantic model with full validation
- Position utilities and computed properties
"""

import time
from decimal import Decimal
from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class Position(StrictBaseModel):
    """
    Standardized position model for futures exchanges with Pydantic validation.

    This class represents a trading position for a futures contract,
    with normalized fields across different exchanges.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Required fields
    contract: str = Field(..., description="Trading pair/contract (e.g., 'BTC_USDT')")
    exchange: str = Field(..., description="Exchange identifier (e.g., 'binance_futures')")
    size: float = Field(..., description="Position size (positive for long, negative for short)")

    # Optional fields with defaults
    entry_price: Optional[float] = Field(None, ge=0.0, description="Average entry price")
    mark_price: Optional[float] = Field(None, ge=0.0, description="Current mark price")
    liquidation_price: Optional[float] = Field(None, ge=0.0, description="Liquidation price if applicable")
    leverage: Optional[int] = Field(None, ge=1, description="Position leverage")
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized profit/loss")
    margin_type: Optional[str] = Field(None, description="Margin type: 'cross' or 'isolated'")
    margin_used: Optional[float] = Field(None, ge=0.0, description="Margin used for this position")
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Timestamp in milliseconds")
    raw_exchange_data: Dict[str, Any] = Field(default_factory=dict, description="Original exchange data", exclude=True)

    # Validators
    @field_validator("size")
    @classmethod
    def validate_size(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert and validate position size (accepts Decimal from exchange adapters)."""
        return float(v)

    @field_validator("entry_price", "mark_price", "liquidation_price", "unrealized_pnl", mode="before")
    @classmethod
    def validate_optional_floats(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[float]:
        """Convert optional price/PnL fields to float (accepts Decimal from exchange adapters)."""
        if v is None:
            return None
        return float(v)

    @field_validator("leverage", mode="before")
    @classmethod
    def validate_leverage(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[int]:
        """Convert leverage to int (accepts Decimal from exchange adapters)."""
        if v is None:
            return None
        return int(v)

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
    def notional_value(self) -> Optional[float]:
        """Get the current notional value of the position."""
        if self.mark_price is None:
            return None
        return abs(self.size) * self.mark_price

    @computed_field  # type: ignore[prop-decorator]
    @property
    def roi_percentage(self) -> Optional[float]:
        """Get the ROI percentage if entry and mark prices are available."""
        if self.entry_price is None or self.mark_price is None or self.entry_price == 0:
            return None
        return (self.mark_price - self.entry_price) / self.entry_price * 100 * (1 if self.size > 0 else -1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def direction(self) -> str:
        """Get the position direction as a string ('long', 'short', or 'flat')."""
        if self.size > 0:
            return "long"
        elif self.size < 0:
            return "short"
        else:
            return "flat"

    def to_dict(self) -> Dict[str, Union[str, int, float, None]]:
        """Convert to dictionary for serialization."""
        # Get base dict and manually remove computed fields (model_dump includes @computed_field)
        base_dict = self.model_dump(exclude={"raw_exchange_data"})
        # Remove computed fields to allow round-trip serialization
        for key in ["notional_value", "roi_percentage", "direction"]:
            base_dict.pop(key, None)
        return base_dict
