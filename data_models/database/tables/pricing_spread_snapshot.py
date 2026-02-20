"""Pricing spread snapshot database model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass
class PricingSpreadSnapshot:
    """Pricing spread snapshot record for database storage.

    Stores real-time spread data from WebSocket orderbooks for both
    intra-exchange (bid-ask) and cross-exchange (arbitrage) spreads.
    """

    snapshot_time: datetime
    spread_type: str  # 'intra' or 'cross'

    # Exchange info
    maker_exchange: str
    taker_exchange: Optional[str]  # None for intra-exchange spreads
    contract: str

    # Price data
    bid_maker: float
    ask_maker: float
    bid_taker: Optional[float]  # None for intra-exchange spreads
    ask_taker: Optional[float]  # None for intra-exchange spreads

    # Spread metrics
    spread_bps: float  # Basis points
    spread_pct: float  # Percentage
    mid_price: float

    @classmethod
    def from_snapshot(
        cls,
        timestamp: datetime,
        spread_type: str,
        maker_exchange: str,
        taker_exchange: Optional[str],
        contract: str,
        bid_maker: float,
        ask_maker: float,
        bid_taker: Optional[float],
        ask_taker: Optional[float],
        spread_bps: float,
        spread_pct: float,
        mid_price: float,
    ) -> "PricingSpreadSnapshot":
        """Create pricing spread snapshot from monitor data.

        Args:
            timestamp: When the spread was captured
            spread_type: Type of spread ('intra' or 'cross')
            maker_exchange: Primary exchange
            taker_exchange: Secondary exchange (None for intra-exchange)
            contract: Contract symbol (e.g., "BTC_USDT")
            bid_maker: Best bid on maker exchange
            ask_maker: Best ask on maker exchange
            bid_taker: Best bid on taker exchange (None for intra)
            ask_taker: Best ask on taker exchange (None for intra)
            spread_bps: Spread in basis points
            spread_pct: Spread as percentage
            mid_price: Middle price for reference

        Returns:
            PricingSpreadSnapshot instance ready for database insertion
        """
        return cls(
            snapshot_time=timestamp or datetime.now(timezone.utc),
            spread_type=spread_type.lower(),
            maker_exchange=maker_exchange,
            taker_exchange=taker_exchange,
            contract=contract,
            bid_maker=bid_maker,
            ask_maker=ask_maker,
            bid_taker=bid_taker,
            ask_taker=ask_taker,
            spread_bps=spread_bps,
            spread_pct=spread_pct,
            mid_price=mid_price,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO pricing_spread_snapshots
            (snapshot_time, spread_type, maker_exchange, taker_exchange, contract,
             bid_maker, ask_maker, bid_taker, ask_taker,
             spread_bps, spread_pct, mid_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.snapshot_time,
            self.spread_type,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.bid_maker,
            self.ask_maker,
            self.bid_taker,
            self.ask_taker,
            self.spread_bps,
            self.spread_pct,
            self.mid_price,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO pricing_spread_snapshots
            (snapshot_time, spread_type, maker_exchange, taker_exchange, contract,
             bid_maker, ask_maker, bid_taker, ask_taker,
             spread_bps, spread_pct, mid_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_tuple(self) -> Tuple[Any, ...]:
        """Convert to tuple for batch insert operations.

        Returns:
            Tuple of values in insert order
        """
        return (
            self.snapshot_time,
            self.spread_type,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.bid_maker,
            self.ask_maker,
            self.bid_taker,
            self.ask_taker,
            self.spread_bps,
            self.spread_pct,
            self.mid_price,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of spread snapshot
        """
        result = {
            "snapshot_time": self.snapshot_time.isoformat() if self.snapshot_time else None,
            "spread_type": self.spread_type,
            "maker_exchange": self.maker_exchange,
            "contract": self.contract,
            "bid_maker": self.bid_maker,
            "ask_maker": self.ask_maker,
            "spread_bps": self.spread_bps,
            "spread_pct": self.spread_pct,
            "mid_price": self.mid_price,
        }

        # Add taker fields only for cross-exchange spreads
        if self.spread_type == "cross":
            result.update(
                {
                    "taker_exchange": self.taker_exchange,
                    "bid_taker": self.bid_taker,
                    "ask_taker": self.ask_taker,
                    "route": f"{self.maker_exchange}→{self.taker_exchange}",
                }
            )

        return result
