"""Funding rate snapshot database model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


@dataclass
class FundingRateSnapshot:
    """Funding rate snapshot record for database storage.

    Stores raw funding rate data from Loris Tools API with normalization
    factor for future processing. Phase 1 approach: store raw data,
    normalize later with dedicated engine.
    """

    timestamp: datetime
    exchange: str
    contract: str
    funding_rate: Decimal  # Raw rate from source (e.g., 0.0001 for 0.01%)
    normalization_factor: Decimal  # Funding interval in hours (e.g., 8, 1, 4)
    mark_price: Optional[Decimal] = None
    open_interest: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None

    @classmethod
    def from_loris_data(
        cls,
        exchange: str,
        contract: str,
        rate: float,
        funding_interval: int,
        timestamp: Optional[datetime] = None,
        mark_price: Optional[float] = None,
        open_interest: Optional[float] = None,
        volume_24h: Optional[float] = None,
    ) -> "FundingRateSnapshot":
        """Create snapshot from Loris API funding rate data.

        Args:
            exchange: Helena internal exchange name (e.g., "binance_futures")
            contract: Helena internal contract format (e.g., "BTC_USD")
            rate: Raw funding rate from Loris (e.g., 0.0001)
            funding_interval: Funding interval in hours (e.g., 8, 1)
            timestamp: Snapshot timestamp (defaults to now)
            mark_price: Mark price at snapshot time
            open_interest: Open interest in USD
            volume_24h: 24-hour trading volume in USD

        Returns:
            FundingRateSnapshot instance ready for database insertion
        """
        return cls(
            timestamp=timestamp or datetime.now(timezone.utc),
            exchange=exchange,
            contract=contract,
            funding_rate=Decimal(str(rate)),
            normalization_factor=Decimal(str(funding_interval)),
            mark_price=Decimal(str(mark_price)) if mark_price is not None else None,
            open_interest=Decimal(str(open_interest)) if open_interest is not None else None,
            volume_24h=Decimal(str(volume_24h)) if volume_24h is not None else None,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO funding_rates_snapshots
            (timestamp, exchange, contract, funding_rate, normalization_factor,
             mark_price, open_interest, volume_24h)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.timestamp,
            self.exchange,
            self.contract,
            self.funding_rate,
            self.normalization_factor,
            self.mark_price,
            self.open_interest,
            self.volume_24h,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO funding_rates_snapshots
            (timestamp, exchange, contract, funding_rate, normalization_factor,
             mark_price, open_interest, volume_24h)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of funding rate snapshot
        """
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "exchange": self.exchange,
            "contract": self.contract,
            "funding_rate": float(self.funding_rate) if self.funding_rate else None,
            "normalization_factor": float(self.normalization_factor) if self.normalization_factor else None,
            "mark_price": float(self.mark_price) if self.mark_price else None,
            "open_interest": float(self.open_interest) if self.open_interest else None,
            "volume_24h": float(self.volume_24h) if self.volume_24h else None,
        }
