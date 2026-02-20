"""
Complete Balance model with Pydantic validation.

This module contains everything balance-related in one place:
- Balance Pydantic model with full validation
- Balance utilities and computed properties
"""

import time
from decimal import Decimal
from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class Balance(StrictBaseModel):
    """
    Standardized balance model for exchanges with Pydantic validation.

    This class represents a currency balance on an exchange,
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
    currency: str = Field(..., description="Currency code (e.g., 'BTC', 'USDT')")
    exchange: str = Field(..., description="Exchange identifier (e.g., 'binance_spot')")
    free: float = Field(..., ge=0.0, description="Available balance")

    # Optional fields with defaults
    locked: float = Field(default=0.0, ge=0.0, description="Locked/in-use balance")
    timestamp: int = Field(default_factory=_current_timestamp_ms, description="Timestamp in milliseconds")
    raw_exchange_data: Dict[str, Any] = Field(default_factory=dict, description="Original exchange data", exclude=True)

    # Validators
    @field_validator("free", "locked", mode="before")
    @classmethod
    def validate_amounts(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert balance amounts to float (accepts Decimal from exchange adapters)."""
        return float(v)

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
    def total(self) -> float:
        """Get the total balance (free + locked)."""
        return self.free + self.locked

    def to_dict(self) -> Dict[str, Union[str, int, float]]:
        """Convert to dictionary for serialization."""
        # Get base dict and manually remove computed field (model_dump exclude doesn't work for @computed_field)
        base_dict = self.model_dump(exclude={"raw_exchange_data"})
        # Remove computed field to allow round-trip serialization
        base_dict.pop("total", None)
        return base_dict
