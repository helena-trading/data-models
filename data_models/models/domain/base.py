"""
Base Pydantic models for domain entities.

These models provide strict validation and serialization for all domain entities.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T", bound="StrictBaseModel")


class StrictBaseModel(BaseModel):
    """
    Base model with strict validation.

    Features:
    - Extra fields forbidden (no Dict[str, Any] behavior)
    - Assignment validation enabled
    - JSON serialization optimized for performance
    - Decimal support for financial precision
    """

    model_config = ConfigDict(
        # Strict mode - no extra fields allowed
        extra="forbid",
        # Validate on assignment
        validate_assignment=True,
        # Use enum values for serialization
        use_enum_values=True,
        # Optimize JSON encoding
        json_encoders={
            Decimal: str,  # Preserve decimal precision
            datetime: lambda v: v.isoformat(),
        },
        # Better error messages
        validate_default=True,
        # Allow field names to be populated by alias
        populate_by_name=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for legacy compatibility."""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Convert model to JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_dict(cls: "type[T]", data: Dict[str, Any]) -> T:
        """Create model from dictionary with validation."""
        return cls.model_validate(data)

    @classmethod
    def from_dict_unsafe(cls: "type[T]", data: Dict[str, Any]) -> T:
        """Create model without validation (performance critical paths)."""
        result = cls.model_construct(**data)
        return cast(T, result)


class ExchangeResponseModel(StrictBaseModel):
    """
    Base model for exchange API responses.
    """

    exchange: str = Field(..., description="Exchange identifier")
    timestamp: Optional[int] = Field(None, description="Response timestamp in ms")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Original exchange response for debugging", exclude=True)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> Optional[int]:
        """Convert various timestamp formats to milliseconds."""
        if v is None:
            return None
        if isinstance(v, str):
            if "T" in v:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            return int(v)
        if isinstance(v, (int, float)):
            if v < 10_000_000_000:
                return int(v * 1000)
            return int(v)
        return int(v) if v is not None else None


__all__ = ["StrictBaseModel", "ExchangeResponseModel"]
