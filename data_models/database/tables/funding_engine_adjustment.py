"""Funding engine price adjustment database model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


@dataclass
class FundingEngineAdjustment:
    """Funding engine price adjustment record for database storage.

    Stores how FundingEngine translates funding rates into actual
    bid/ask price adjustments. This is the derived data showing
    the engine's output.
    """

    timestamp: datetime
    exchange: str
    contract: str

    # Original prices
    original_bid: Decimal
    original_ask: Decimal

    # Adjusted prices (engine output)
    adjusted_bid: Decimal
    adjusted_ask: Decimal

    # Deltas
    bid_delta: Decimal
    ask_delta: Decimal
    delta_pct: Decimal

    # Funding context
    funding_rate: Optional[Decimal] = None
    funding_interval_hours: int = 8

    # Engine params
    horizon_hours: Decimal = Decimal("8.0")
    safety_buffer: Decimal = Decimal("0.0")

    # Uncertainty metrics (new for uncertainty-aware pricing)
    locked_fraction: Optional[Decimal] = None
    sigma: Optional[Decimal] = None
    sigma_total: Optional[Decimal] = None
    buffer: Optional[Decimal] = None
    use_dynamic_uncertainty: bool = True
    num_crossings: int = 0

    @classmethod
    def from_monitor_data(
        cls,
        timestamp: datetime,
        exchange: str,
        contract: str,
        bid: float,
        ask: float,
        adjusted_bid: float,
        adjusted_ask: float,
        bid_delta: float,
        ask_delta: float,
        delta_pct: float,
        funding_rate: Optional[float] = None,
        funding_interval_hours: int = 8,
        horizon_hours: float = 8.0,
        safety_buffer: float = 0.0,
        # Uncertainty metrics
        locked_fraction: Optional[float] = None,
        sigma: Optional[float] = None,
        sigma_total: Optional[float] = None,
        buffer: Optional[float] = None,
        use_dynamic_uncertainty: bool = True,
        num_crossings: int = 0,
    ) -> "FundingEngineAdjustment":
        """Create adjustment record from monitor data.

        Args:
            timestamp: When the adjustment was calculated
            exchange: Exchange name (e.g., "binance_futures")
            contract: Contract symbol (e.g., "BTC_USD")
            bid: Original bid price
            ask: Original ask price
            adjusted_bid: Adjusted bid price
            adjusted_ask: Adjusted ask price
            bid_delta: Change in bid price
            ask_delta: Change in ask price
            delta_pct: Change as percentage
            funding_rate: Funding rate used for calculation
            funding_interval_hours: Funding interval (e.g., 8)
            horizon_hours: FundingEngine horizon parameter
            safety_buffer: FundingEngine safety buffer parameter
            locked_fraction: Fraction of funding rate locked in (0-1)
            sigma: Base uncertainty at prediction time
            sigma_total: Total uncertainty (scaled by sqrt(crossings))
            buffer: Conservative buffer applied (k * sigma_total)
            use_dynamic_uncertainty: Whether dynamic uncertainty is enabled
            num_crossings: Number of funding events crossed

        Returns:
            FundingEngineAdjustment instance ready for database insertion
        """
        return cls(
            timestamp=timestamp or datetime.now(timezone.utc),
            exchange=exchange,
            contract=contract,
            original_bid=Decimal(str(bid)),
            original_ask=Decimal(str(ask)),
            adjusted_bid=Decimal(str(adjusted_bid)),
            adjusted_ask=Decimal(str(adjusted_ask)),
            bid_delta=Decimal(str(bid_delta)),
            ask_delta=Decimal(str(ask_delta)),
            delta_pct=Decimal(str(delta_pct)),
            funding_rate=Decimal(str(funding_rate)) if funding_rate is not None else None,
            funding_interval_hours=funding_interval_hours,
            horizon_hours=Decimal(str(horizon_hours)),
            safety_buffer=Decimal(str(safety_buffer)),
            # Uncertainty metrics
            locked_fraction=Decimal(str(locked_fraction)) if locked_fraction is not None else None,
            sigma=Decimal(str(sigma)) if sigma is not None else None,
            sigma_total=Decimal(str(sigma_total)) if sigma_total is not None else None,
            buffer=Decimal(str(buffer)) if buffer is not None else None,
            use_dynamic_uncertainty=use_dynamic_uncertainty,
            num_crossings=num_crossings,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO funding_engine_adjustments
            (timestamp, exchange, contract, original_bid, original_ask,
             adjusted_bid, adjusted_ask, bid_delta, ask_delta, delta_pct,
             funding_rate, funding_interval_hours, horizon_hours, safety_buffer,
             locked_fraction, sigma, sigma_total, buffer, use_dynamic_uncertainty, num_crossings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.timestamp,
            self.exchange,
            self.contract,
            self.original_bid,
            self.original_ask,
            self.adjusted_bid,
            self.adjusted_ask,
            self.bid_delta,
            self.ask_delta,
            self.delta_pct,
            self.funding_rate,
            self.funding_interval_hours,
            self.horizon_hours,
            self.safety_buffer,
            self.locked_fraction,
            self.sigma,
            self.sigma_total,
            self.buffer,
            self.use_dynamic_uncertainty,
            self.num_crossings,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO funding_engine_adjustments
            (timestamp, exchange, contract, original_bid, original_ask,
             adjusted_bid, adjusted_ask, bid_delta, ask_delta, delta_pct,
             funding_rate, funding_interval_hours, horizon_hours, safety_buffer,
             locked_fraction, sigma, sigma_total, buffer, use_dynamic_uncertainty, num_crossings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_tuple(self) -> Tuple[Any, ...]:
        """Convert to tuple for batch insert operations.

        Returns:
            Tuple of values in insert order
        """
        return (
            self.timestamp,
            self.exchange,
            self.contract,
            self.original_bid,
            self.original_ask,
            self.adjusted_bid,
            self.adjusted_ask,
            self.bid_delta,
            self.ask_delta,
            self.delta_pct,
            self.funding_rate,
            self.funding_interval_hours,
            self.horizon_hours,
            self.safety_buffer,
            self.locked_fraction,
            self.sigma,
            self.sigma_total,
            self.buffer,
            self.use_dynamic_uncertainty,
            self.num_crossings,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation of adjustment record
        """
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "exchange": self.exchange,
            "contract": self.contract,
            "original_bid": float(self.original_bid) if self.original_bid else None,
            "original_ask": float(self.original_ask) if self.original_ask else None,
            "adjusted_bid": float(self.adjusted_bid) if self.adjusted_bid else None,
            "adjusted_ask": float(self.adjusted_ask) if self.adjusted_ask else None,
            "bid_delta": float(self.bid_delta) if self.bid_delta else None,
            "ask_delta": float(self.ask_delta) if self.ask_delta else None,
            "delta_pct": float(self.delta_pct) if self.delta_pct else None,
            "funding_rate": float(self.funding_rate) if self.funding_rate else None,
            "funding_interval_hours": self.funding_interval_hours,
            "horizon_hours": float(self.horizon_hours) if self.horizon_hours else None,
            "safety_buffer": float(self.safety_buffer) if self.safety_buffer else None,
            # Uncertainty metrics
            "locked_fraction": float(self.locked_fraction) if self.locked_fraction is not None else None,
            "sigma": float(self.sigma) if self.sigma is not None else None,
            "sigma_total": float(self.sigma_total) if self.sigma_total is not None else None,
            "buffer": float(self.buffer) if self.buffer is not None else None,
            "use_dynamic_uncertainty": self.use_dynamic_uncertainty,
            "num_crossings": self.num_crossings,
        }
