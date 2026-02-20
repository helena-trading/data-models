"""Market metrics snapshot database models for Open Interest and Volume."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


@dataclass
class OpenInterestSnapshot:
    """Open interest snapshot record for database storage.

    Stores open interest data from exchange market data services.
    """

    timestamp: datetime
    exchange: str
    symbol: str
    open_interest: Decimal  # Open interest in contracts or USD
    open_interest_value: Optional[Decimal] = None  # USD value (if available)

    @classmethod
    def from_monitor_data(
        cls,
        timestamp: datetime,
        exchange: str,
        symbol: str,
        open_interest: float,
        open_interest_value: Optional[float] = None,
    ) -> "OpenInterestSnapshot":
        """Create snapshot from monitor data.

        Args:
            timestamp: Snapshot timestamp
            exchange: Exchange name (e.g., "binance_futures")
            symbol: Helena internal contract format (e.g., "BTC_USD")
            open_interest: Open interest value
            open_interest_value: Optional USD value of open interest

        Returns:
            OpenInterestSnapshot instance ready for database insertion
        """
        return cls(
            timestamp=timestamp,
            exchange=exchange,
            symbol=symbol,
            open_interest=Decimal(str(open_interest)),
            open_interest_value=Decimal(str(open_interest_value)) if open_interest_value else None,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO broker_open_interest_snapshots
            (snapshot_time, exchange, symbol, open_interest, open_interest_value)
            VALUES (%s, %s, %s, %s, %s)
        """

        params = (
            self.timestamp,
            self.exchange,
            self.symbol,
            self.open_interest,
            self.open_interest_value,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO broker_open_interest_snapshots
            (snapshot_time, exchange, symbol, open_interest, open_interest_value)
            VALUES (%s, %s, %s, %s, %s)
        """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of open interest snapshot
        """
        return {
            "snapshot_time": self.timestamp.isoformat() if self.timestamp else None,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "open_interest": float(self.open_interest) if self.open_interest else None,
            "open_interest_value": float(self.open_interest_value) if self.open_interest_value else None,
        }


@dataclass
class VolumeSnapshot:
    """24-hour volume snapshot record for database storage.

    Stores trading volume data from exchange market data services.
    """

    timestamp: datetime
    exchange: str
    symbol: str
    volume_24h: Decimal  # Volume in quote currency (USD/USDT)
    volume_24h_base: Optional[Decimal] = None  # Volume in base currency

    @classmethod
    def from_monitor_data(
        cls,
        timestamp: datetime,
        exchange: str,
        symbol: str,
        volume_24h: float,
        volume_24h_base: Optional[float] = None,
    ) -> "VolumeSnapshot":
        """Create snapshot from monitor data.

        Args:
            timestamp: Snapshot timestamp
            exchange: Exchange name (e.g., "binance_futures")
            symbol: Helena internal contract format (e.g., "BTC_USD")
            volume_24h: 24-hour volume in quote currency (USD/USDT)
            volume_24h_base: Optional 24-hour volume in base currency

        Returns:
            VolumeSnapshot instance ready for database insertion
        """
        return cls(
            timestamp=timestamp,
            exchange=exchange,
            symbol=symbol,
            volume_24h=Decimal(str(volume_24h)),
            volume_24h_base=Decimal(str(volume_24h_base)) if volume_24h_base else None,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO broker_volume_snapshots
            (snapshot_time, exchange, symbol, volume_24h, quote_volume_24h)
            VALUES (%s, %s, %s, %s, %s)
        """

        params = (
            self.timestamp,
            self.exchange,
            self.symbol,
            self.volume_24h,
            self.volume_24h_base,  # Maps to quote_volume_24h in DB for clarity
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO broker_volume_snapshots
            (snapshot_time, exchange, symbol, volume_24h, quote_volume_24h)
            VALUES (%s, %s, %s, %s, %s)
        """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of volume snapshot
        """
        return {
            "snapshot_time": self.timestamp.isoformat() if self.timestamp else None,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "volume_24h": float(self.volume_24h) if self.volume_24h else None,
            "volume_24h_base": float(self.volume_24h_base) if self.volume_24h_base else None,
        }
