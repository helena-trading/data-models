"""Spread normalization event database model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass
class SpreadNormalizationEvent:
    """Spread normalization event record for database storage.

    Tracks when spreads deviate from normal and then return to mean,
    useful for analyzing mean reversion patterns and timing.
    """

    detected_time: datetime
    normalized_time: Optional[datetime]  # None if still ongoing

    # Route info
    maker_exchange: str
    taker_exchange: str
    contract: str

    # Spread data
    peak_spread_bps: float  # Maximum spread during event
    normal_spread_bps: float  # Spread when normalized (within 1 std dev)
    mean_spread_bps: float  # Rolling mean at time of event
    std_dev_bps: float  # Standard deviation at time of event

    # Event characteristics
    duration_seconds: Optional[int]  # None if still ongoing
    reversion_pattern: Optional[str]  # 'fast', 'gradual', 'volatile', None if ongoing

    @classmethod
    def from_normalization_data(
        cls,
        detected_time: datetime,
        normalized_time: Optional[datetime],
        maker_exchange: str,
        taker_exchange: str,
        contract: str,
        peak_spread_bps: float,
        normal_spread_bps: float,
        mean_spread_bps: float,
        std_dev_bps: float,
        reversion_pattern: Optional[str] = None,
    ) -> "SpreadNormalizationEvent":
        """Create normalization event from monitor data.

        Args:
            detected_time: When abnormal spread was first detected
            normalized_time: When spread returned to normal (None if ongoing)
            maker_exchange: Maker side exchange
            taker_exchange: Taker side exchange
            contract: Contract symbol (e.g., "BTC_USDT")
            peak_spread_bps: Maximum spread observed during event
            normal_spread_bps: Spread value when normalized
            mean_spread_bps: Rolling mean spread
            std_dev_bps: Rolling standard deviation
            reversion_pattern: Pattern of reversion ('fast', 'gradual', 'volatile')

        Returns:
            SpreadNormalizationEvent instance ready for database insertion
        """
        # Calculate duration if normalized
        duration_seconds = None
        if normalized_time and detected_time:
            duration_seconds = int((normalized_time - detected_time).total_seconds())

        return cls(
            detected_time=detected_time,
            normalized_time=normalized_time,
            maker_exchange=maker_exchange,
            taker_exchange=taker_exchange,
            contract=contract,
            peak_spread_bps=peak_spread_bps,
            normal_spread_bps=normal_spread_bps,
            mean_spread_bps=mean_spread_bps,
            std_dev_bps=std_dev_bps,
            duration_seconds=duration_seconds,
            reversion_pattern=reversion_pattern,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO spread_normalization_events
            (detected_time, normalized_time, maker_exchange, taker_exchange, contract,
             peak_spread_bps, normal_spread_bps, mean_spread_bps, std_dev_bps,
             duration_seconds, reversion_pattern)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.detected_time,
            self.normalized_time,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.peak_spread_bps,
            self.normal_spread_bps,
            self.mean_spread_bps,
            self.std_dev_bps,
            self.duration_seconds,
            self.reversion_pattern,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO spread_normalization_events
            (detected_time, normalized_time, maker_exchange, taker_exchange, contract,
             peak_spread_bps, normal_spread_bps, mean_spread_bps, std_dev_bps,
             duration_seconds, reversion_pattern)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_tuple(self) -> Tuple[Any, ...]:
        """Convert to tuple for batch insert operations.

        Returns:
            Tuple of values in insert order
        """
        return (
            self.detected_time,
            self.normalized_time,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.peak_spread_bps,
            self.normal_spread_bps,
            self.mean_spread_bps,
            self.std_dev_bps,
            self.duration_seconds,
            self.reversion_pattern,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of normalization event
        """
        return {
            "detected_time": self.detected_time.isoformat() if self.detected_time else None,
            "normalized_time": self.normalized_time.isoformat() if self.normalized_time else None,
            "is_ongoing": self.normalized_time is None,
            "maker_exchange": self.maker_exchange,
            "taker_exchange": self.taker_exchange,
            "route": f"{self.maker_exchange}→{self.taker_exchange}",
            "contract": self.contract,
            "peak_spread_bps": self.peak_spread_bps,
            "normal_spread_bps": self.normal_spread_bps,
            "mean_spread_bps": self.mean_spread_bps,
            "std_dev_bps": self.std_dev_bps,
            "z_score_peak": (self.peak_spread_bps - self.mean_spread_bps) / self.std_dev_bps if self.std_dev_bps > 0 else 0,
            "duration_seconds": self.duration_seconds,
            "reversion_pattern": self.reversion_pattern,
        }

    def update_normalized(self, normalized_time: datetime, normal_spread_bps: float, pattern: str) -> None:
        """Update event when normalization completes.

        Args:
            normalized_time: When spread returned to normal
            normal_spread_bps: The normalized spread value
            pattern: Reversion pattern observed
        """
        self.normalized_time = normalized_time
        self.normal_spread_bps = normal_spread_bps
        self.reversion_pattern = pattern

        if self.detected_time:
            self.duration_seconds = int((normalized_time - self.detected_time).total_seconds())
