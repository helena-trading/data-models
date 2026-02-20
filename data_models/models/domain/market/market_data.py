"""
Market data domain model.

Represents non-orderbook market data snapshots (24h volume/open interest)
used by monitoring workflows and market-data-hub ingestion.
"""

from decimal import Decimal
from typing import Optional, Union

from pydantic import ConfigDict, Field, field_validator

from data_models.models.domain.base import StrictBaseModel


class MarketData(StrictBaseModel):
    """Normalized market-data snapshot for a single exchange:contract."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, populate_by_name=True)

    internal_contract: str = Field(
        ...,
        alias="symbol",
        min_length=1,
        description="Trading contract in internal format (e.g., BTC_USDT)",
    )
    timestamp: int = Field(..., gt=0, description="When this data was retrieved (milliseconds)")
    volume_24h: Optional[float] = Field(default=None, ge=0, description="24h base volume")
    quote_volume_24h: Optional[float] = Field(default=None, ge=0, description="24h quote volume")
    open_interest: Optional[float] = Field(default=None, ge=0, description="Open interest in contracts/units")
    open_interest_value: Optional[float] = Field(default=None, ge=0, description="Open interest notional value")

    @field_validator("internal_contract")
    @classmethod
    def validate_internal_contract(cls, v: str) -> str:
        """Ensure internal contract is not empty."""
        if not v or not v.strip():
            raise ValueError("internal_contract cannot be empty")
        return v.strip().upper().replace("-", "_").replace("/", "_")

    @field_validator("volume_24h", "quote_volume_24h", "open_interest", "open_interest_value", mode="before")
    @classmethod
    def validate_numeric(
        cls,
        v: Optional[Union[str, int, float, Decimal]],
    ) -> Optional[float]:
        """Convert numeric fields to float when present."""
        if v is None:
            return None
        return float(v)

    @property
    def symbol(self) -> str:
        """Backward-compatible alias for internal_contract."""
        return self.internal_contract
