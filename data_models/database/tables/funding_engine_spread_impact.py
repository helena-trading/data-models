"""Funding engine spread impact database model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Tuple


@dataclass
class FundingEngineSpreadImpact:
    """Funding engine spread impact record for database storage.

    Stores how funding adjustments affect cross-exchange spreads.
    Shows which routes benefit or suffer from funding rate differentials.
    """

    timestamp: datetime

    # Route info
    maker_exchange: str
    taker_exchange: str
    contract: str

    # Spread analysis
    raw_spread_pct: Decimal
    adjusted_spread_pct: Decimal
    spread_delta_pct: Decimal
    impact_direction: str  # 'wider', 'narrower', 'neutral'

    # Engine params
    horizon_hours: Decimal = Decimal("8.0")
    safety_buffer: Decimal = Decimal("0.0")

    @classmethod
    def from_monitor_data(
        cls,
        timestamp: datetime,
        route: str,
        contract: str,
        raw_spread: float,
        adj_spread: float,
        delta: float,
        impact: str,
        horizon_hours: float = 8.0,
        safety_buffer: float = 0.0,
    ) -> "FundingEngineSpreadImpact":
        """Create spread impact record from monitor data.

        Args:
            timestamp: When the spread was calculated
            route: Route string (e.g., "binance_futures→bybit")
            contract: Contract symbol (e.g., "BTC_USD")
            raw_spread: Original spread percentage
            adj_spread: Adjusted spread percentage
            delta: Change in spread percentage
            impact: Impact direction ("wider", "narrower", "neutral")
            horizon_hours: FundingEngine horizon parameter
            safety_buffer: FundingEngine safety buffer parameter

        Returns:
            FundingEngineSpreadImpact instance ready for database insertion
        """
        # Parse route into maker and taker exchanges
        # Format: "maker_exchange→taker_exchange" or "maker_exchange->taker_exchange"
        if "→" in route:
            parts = route.split("→")
        elif "->" in route:
            parts = route.split("->")
        else:
            parts = [route, route]

        maker_exchange = parts[0].strip() if len(parts) > 0 else ""
        taker_exchange = parts[1].strip() if len(parts) > 1 else ""

        # Normalize impact direction
        impact_lower = str(impact).lower().strip()
        if "narrow" in impact_lower or "tighter" in impact_lower:
            impact_direction = "narrower"
        elif "wide" in impact_lower:
            impact_direction = "wider"
        else:
            impact_direction = "neutral"

        return cls(
            timestamp=timestamp or datetime.now(timezone.utc),
            maker_exchange=maker_exchange,
            taker_exchange=taker_exchange,
            contract=contract,
            raw_spread_pct=Decimal(str(raw_spread)),
            adjusted_spread_pct=Decimal(str(adj_spread)),
            spread_delta_pct=Decimal(str(delta)),
            impact_direction=impact_direction,
            horizon_hours=Decimal(str(horizon_hours)),
            safety_buffer=Decimal(str(safety_buffer)),
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO funding_engine_spread_impacts
            (timestamp, maker_exchange, taker_exchange, contract,
             raw_spread_pct, adjusted_spread_pct, spread_delta_pct,
             impact_direction, horizon_hours, safety_buffer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.timestamp,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.raw_spread_pct,
            self.adjusted_spread_pct,
            self.spread_delta_pct,
            self.impact_direction,
            self.horizon_hours,
            self.safety_buffer,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO funding_engine_spread_impacts
            (timestamp, maker_exchange, taker_exchange, contract,
             raw_spread_pct, adjusted_spread_pct, spread_delta_pct,
             impact_direction, horizon_hours, safety_buffer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_tuple(self) -> Tuple[Any, ...]:
        """Convert to tuple for batch insert operations.

        Returns:
            Tuple of values in insert order
        """
        return (
            self.timestamp,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.raw_spread_pct,
            self.adjusted_spread_pct,
            self.spread_delta_pct,
            self.impact_direction,
            self.horizon_hours,
            self.safety_buffer,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of spread impact record
        """
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "maker_exchange": self.maker_exchange,
            "taker_exchange": self.taker_exchange,
            "route": f"{self.maker_exchange}→{self.taker_exchange}",
            "contract": self.contract,
            "raw_spread_pct": float(self.raw_spread_pct) if self.raw_spread_pct else None,
            "adjusted_spread_pct": float(self.adjusted_spread_pct) if self.adjusted_spread_pct else None,
            "spread_delta_pct": float(self.spread_delta_pct) if self.spread_delta_pct else None,
            "impact_direction": self.impact_direction,
            "horizon_hours": float(self.horizon_hours) if self.horizon_hours else None,
            "safety_buffer": float(self.safety_buffer) if self.safety_buffer else None,
        }
