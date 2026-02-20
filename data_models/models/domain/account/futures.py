"""
Futures-Specific Domain Models

Pydantic models for perpetual futures contracts shared across multiple exchanges.
These models are used by futures gateways (Binance Futures, Bybit, Hyperliquid).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class FundingRate(BaseModel):
    """
    Funding rate information for perpetual futures.

    This model standardizes funding rate data across different exchanges.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., min_length=1, description="Trading symbol in internal format (e.g., BTC_USDT)")
    rate: float = Field(..., description="Current funding rate (e.g., 0.0001 for 0.01%)")
    next_funding_time: int = Field(..., gt=0, description="Timestamp of next funding payment (milliseconds)")
    timestamp: int = Field(..., gt=0, description="When this data was retrieved (milliseconds)")
    interval_hours: int = Field(..., gt=0, description="Hours between funding payments (must be explicitly set per exchange)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Ensure symbol is not empty."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v

    @field_validator("rate", mode="before")
    @classmethod
    def validate_rate(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert rate to float (accepts Decimal from exchange adapters)."""
        return float(v)

    @computed_field
    def rate_percentage(self) -> float:
        """Get funding rate as percentage (e.g., 0.0001 -> 0.01)."""
        return self.rate * 100

    @computed_field
    def is_positive(self) -> bool:
        """True if funding rate is positive (longs pay shorts)."""
        return self.rate > 0

    @computed_field
    def is_negative(self) -> bool:
        """True if funding rate is negative (shorts pay longs)."""
        return self.rate < 0

    # Database persistence methods
    def to_insert_query(self, exchange: str) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Args:
            exchange: Exchange name (e.g., "binance_futures", "bybit")

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO broker_funding_rate_snapshots
            (snapshot_time, exchange, symbol, rate, next_funding_time, interval_hours)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            datetime.now(timezone.utc),
            exchange,
            self.symbol,
            self.rate,
            datetime.fromtimestamp(self.next_funding_time / 1000, tz=timezone.utc),
            self.interval_hours,
        )
        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility)."""
        return """
            INSERT INTO broker_funding_rate_snapshots
            (snapshot_time, exchange, symbol, rate, next_funding_time, interval_hours)
            VALUES (%s, %s, %s, %s, %s, %s)
        """


class MarkPrice(BaseModel):
    """
    Mark price information for perpetual futures.

    This model standardizes mark price data across different exchanges.

    The mark price is used for:
    - Unrealized PnL calculation
    - Liquidation price calculation
    - Margin requirement calculation
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., min_length=1, description="Trading symbol in internal format (e.g., BTC_USDT)")
    mark_price: float = Field(..., gt=0, description="Current mark price used for PnL calculation")
    index_price: float = Field(..., gt=0, description="Underlying index price from spot exchanges")
    estimated_settle_price: Optional[float] = Field(None, gt=0, description="Estimated settlement price")
    timestamp: int = Field(..., gt=0, description="When this data was retrieved (milliseconds)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Ensure symbol is not empty."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v

    @field_validator("mark_price", "index_price", mode="before")
    @classmethod
    def validate_prices(cls, v: Union[str, int, float, Decimal]) -> float:
        """Convert prices to float (accepts Decimal from exchange adapters)."""
        return float(v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def premium_to_index(self) -> float:
        """Calculate premium of mark price over index price."""
        return self.mark_price - self.index_price

    @computed_field  # type: ignore[prop-decorator]
    @property
    def premium_percentage(self) -> float:
        """Calculate premium as percentage of index price."""
        if self.index_price == 0:
            return 0.0
        premium = self.premium_to_index  # @computed_field already returns float
        return (premium / self.index_price) * 100

    @computed_field
    def is_premium(self) -> bool:
        """True if mark price is above index price."""
        return self.mark_price > self.index_price

    @computed_field
    def is_discount(self) -> bool:
        """True if mark price is below index price."""
        return self.mark_price < self.index_price

    # Database persistence methods
    def to_insert_query(self, exchange: str) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Args:
            exchange: Exchange name (e.g., "binance_futures", "bybit")

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO broker_mark_price_snapshots
            (snapshot_time, exchange, symbol, mark_price, index_price, estimated_settle_price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            datetime.now(timezone.utc),
            exchange,
            self.symbol,
            self.mark_price,
            self.index_price,
            self.estimated_settle_price,
        )
        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility)."""
        return """
            INSERT INTO broker_mark_price_snapshots
            (snapshot_time, exchange, symbol, mark_price, index_price, estimated_settle_price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
