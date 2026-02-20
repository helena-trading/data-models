"""Position history model for paired exchange positions during trade execution."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple


@dataclass
class PositionHistory:
    """Model for paired position history during trade execution.

    This model tracks positions on both maker and taker exchanges
    at the same point in time, allowing analysis of exposure and imbalances.
    """

    timestamp: int  # Unix timestamp in milliseconds
    maker_exchange: str
    taker_exchange: str
    contract: str
    maker_position: float
    taker_position: float
    exposure: float  # Absolute value of sum of positions

    @classmethod
    def create(
        cls,
        maker_exchange: str,
        taker_exchange: str,
        contract: str,
        maker_position: float,
        taker_position: float,
        timestamp: Optional[int] = None,
    ) -> "PositionHistory":
        """Create a position history record with calculated exposure.

        Args:
            maker_exchange: Name of the maker exchange
            taker_exchange: Name of the taker exchange
            contract: Contract symbol
            maker_position: Position size on maker exchange
            taker_position: Position size on taker exchange
            timestamp: Unix timestamp in milliseconds (defaults to current time)

        Returns:
            PositionHistory instance
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        return cls(
            timestamp=timestamp,
            maker_exchange=maker_exchange,
            taker_exchange=taker_exchange,
            contract=contract,
            maker_position=maker_position,
            taker_position=taker_position,
            exposure=abs(maker_position + taker_position),
        )

    def to_insert_query(self) -> Tuple[str, List[Any]]:
        """Generate INSERT query and parameters.

        Returns:
            Tuple of (query string, parameters list)
        """
        query = """
            INSERT INTO position_history
            (time, maker_exchange, taker_exchange, contract, maker_position, taker_position, exposure)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        # Convert timestamp to datetime
        dt = datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc)

        params = [
            dt,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.maker_position,
            self.taker_position,
            self.exposure,
        ]

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get the query template for batch inserts.

        Returns:
            Query string for batch inserts
        """
        return """
            INSERT INTO position_history
            (time, maker_exchange, taker_exchange, contract, maker_position, taker_position, exposure)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
