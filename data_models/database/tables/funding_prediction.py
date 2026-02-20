"""Funding prediction tracking database model.

Tracks funding rate predictions vs actual outcomes to validate
the uncertainty-aware pricing model. This enables:
1. Measuring prediction accuracy by exchange and time-to-funding
2. Calibrating sigma_0 parameters empirically
3. Identifying systematic prediction errors
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


@dataclass
class FundingPrediction:
    """Funding prediction record for database storage.

    Captures the prediction made at entry time and (eventually) the
    actual outcome, enabling error analysis.

    Workflow:
    1. At trade entry: Create record with predicted values
    2. After funding events: Update with actual_* fields
    3. Analysis: Compare predicted vs actual, compute error distributions
    """

    # When the prediction was made
    prediction_time: datetime

    # Identifiers (required)
    exchange: str
    contract: str

    # Prediction inputs (required)
    funding_rate: Decimal  # Rate used for prediction
    time_to_next_hours: Decimal  # Hours to next funding at prediction time
    interval_hours: Decimal  # Funding interval (1h for HL, 8h for others)
    horizon_hours: Decimal  # Expected holding time

    # Prediction outputs (required)
    predicted_crossings: int  # Expected number of funding events
    predicted_pnl_long: Decimal  # Expected funding PnL for long position
    predicted_pnl_short: Decimal  # Expected funding PnL for short position

    # Uncertainty metrics (required for model validation)
    locked_fraction: Decimal  # How much of rate was "locked in"
    sigma: Decimal  # Uncertainty at prediction time
    buffer: Decimal  # Conservative buffer applied

    # --- All optional fields below (with defaults) ---

    # Optional identifiers
    bot_id: Optional[int] = None
    trade_id: Optional[str] = None  # Links to block_trade if applicable

    # Actual outcomes (updated after position closes)
    actual_crossings: Optional[int] = None  # Actual funding events crossed
    actual_pnl: Optional[Decimal] = None  # Actual funding PnL realized
    actual_holding_hours: Optional[Decimal] = None  # Actual holding time
    position_side: Optional[str] = None  # 'long' or 'short'

    # Computed errors (populated when actual values are known)
    crossing_error: Optional[int] = None  # actual_crossings - predicted_crossings
    pnl_error: Optional[Decimal] = None  # actual_pnl - predicted_pnl
    pnl_error_pct: Optional[Decimal] = None  # Error as percentage of prediction

    # Status
    status: str = "pending"  # pending, completed, error

    @classmethod
    def from_pricing_metadata(
        cls,
        exchange: str,
        contract: str,
        metadata: Dict[str, Any],
        horizon_hours: float,
        bot_id: Optional[int] = None,
        trade_id: Optional[str] = None,
    ) -> "FundingPrediction":
        """Create prediction record from FundingModel metadata.

        Args:
            exchange: Exchange name
            contract: Contract symbol
            metadata: Metadata dict from PriceAdjustment
            horizon_hours: Expected holding time
            bot_id: Optional bot identifier
            trade_id: Optional trade/block ID

        Returns:
            FundingPrediction ready for database insertion
        """
        return cls(
            prediction_time=datetime.now(timezone.utc),
            exchange=exchange,
            contract=contract,
            bot_id=bot_id,
            trade_id=trade_id,
            funding_rate=Decimal(str(metadata.get("funding_rate", 0))),
            time_to_next_hours=Decimal(str(metadata.get("time_to_next_hours", 0))),
            interval_hours=Decimal(str(metadata.get("interval_hours", 8))),
            horizon_hours=Decimal(str(horizon_hours)),
            predicted_crossings=int(metadata.get("num_crossings", 0)),
            predicted_pnl_long=Decimal(str(metadata.get("fund_pnl_long", 0))),
            predicted_pnl_short=Decimal(str(metadata.get("fund_pnl_short", 0))),
            locked_fraction=Decimal(str(metadata.get("locked_fraction", 0))),
            sigma=Decimal(str(metadata.get("sigma", 0))),
            buffer=Decimal(str(metadata.get("buffer", 0))),
            status="pending",
        )

    def update_with_actual(
        self,
        actual_crossings: int,
        actual_pnl: float,
        actual_holding_hours: float,
        position_side: str,
    ) -> None:
        """Update record with actual outcomes after position closes.

        Args:
            actual_crossings: Number of funding events actually crossed
            actual_pnl: Actual funding PnL realized
            actual_holding_hours: Actual time position was held
            position_side: 'long' or 'short'
        """
        self.actual_crossings = actual_crossings
        self.actual_pnl = Decimal(str(actual_pnl))
        self.actual_holding_hours = Decimal(str(actual_holding_hours))
        self.position_side = position_side

        # Compute errors
        self.crossing_error = actual_crossings - self.predicted_crossings

        # Use correct prediction based on side
        predicted_pnl = float(self.predicted_pnl_long if position_side == "long" else self.predicted_pnl_short)
        self.pnl_error = Decimal(str(actual_pnl - predicted_pnl))

        # Percentage error (avoid division by zero)
        if abs(predicted_pnl) > 1e-10:
            self.pnl_error_pct = Decimal(str((actual_pnl - predicted_pnl) / abs(predicted_pnl)))
        else:
            self.pnl_error_pct = None

        self.status = "completed"

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters for DatabaseWriter.

        Returns:
            Tuple of (SQL query string, parameter tuple)
        """
        query = """
            INSERT INTO funding_predictions
            (prediction_time, exchange, contract, bot_id, trade_id,
             funding_rate, time_to_next_hours, interval_hours, horizon_hours,
             predicted_crossings, predicted_pnl_long, predicted_pnl_short,
             locked_fraction, sigma, buffer,
             actual_crossings, actual_pnl, actual_holding_hours, position_side,
             crossing_error, pnl_error, pnl_error_pct, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.prediction_time,
            self.exchange,
            self.contract,
            self.bot_id,
            self.trade_id,
            self.funding_rate,
            self.time_to_next_hours,
            self.interval_hours,
            self.horizon_hours,
            self.predicted_crossings,
            self.predicted_pnl_long,
            self.predicted_pnl_short,
            self.locked_fraction,
            self.sigma,
            self.buffer,
            self.actual_crossings,
            self.actual_pnl,
            self.actual_holding_hours,
            self.position_side,
            self.crossing_error,
            self.pnl_error,
            self.pnl_error_pct,
            self.status,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts (DatabaseWriter compatibility).

        Returns:
            SQL INSERT statement for batch operations
        """
        return """
            INSERT INTO funding_predictions
            (prediction_time, exchange, contract, bot_id, trade_id,
             funding_rate, time_to_next_hours, interval_hours, horizon_hours,
             predicted_crossings, predicted_pnl_long, predicted_pnl_short,
             locked_fraction, sigma, buffer,
             actual_crossings, actual_pnl, actual_holding_hours, position_side,
             crossing_error, pnl_error, pnl_error_pct, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s)
        """

    @staticmethod
    def update_actual_query() -> str:
        """Get query for updating with actual outcomes.

        Returns:
            SQL UPDATE statement
        """
        return """
            UPDATE funding_predictions
            SET actual_crossings = %s,
                actual_pnl = %s,
                actual_holding_hours = %s,
                position_side = %s,
                crossing_error = %s,
                pnl_error = %s,
                pnl_error_pct = %s,
                status = 'completed'
            WHERE trade_id = %s
        """

    def to_tuple(self) -> Tuple[Any, ...]:
        """Convert to tuple for batch insert operations.

        Returns:
            Tuple of values in insert order
        """
        return (
            self.prediction_time,
            self.exchange,
            self.contract,
            self.bot_id,
            self.trade_id,
            self.funding_rate,
            self.time_to_next_hours,
            self.interval_hours,
            self.horizon_hours,
            self.predicted_crossings,
            self.predicted_pnl_long,
            self.predicted_pnl_short,
            self.locked_fraction,
            self.sigma,
            self.buffer,
            self.actual_crossings,
            self.actual_pnl,
            self.actual_holding_hours,
            self.position_side,
            self.crossing_error,
            self.pnl_error,
            self.pnl_error_pct,
            self.status,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation
        """
        return {
            "prediction_time": self.prediction_time.isoformat() if self.prediction_time else None,
            "exchange": self.exchange,
            "contract": self.contract,
            "bot_id": self.bot_id,
            "trade_id": self.trade_id,
            "funding_rate": float(self.funding_rate) if self.funding_rate else None,
            "time_to_next_hours": float(self.time_to_next_hours) if self.time_to_next_hours else None,
            "interval_hours": float(self.interval_hours) if self.interval_hours else None,
            "horizon_hours": float(self.horizon_hours) if self.horizon_hours else None,
            "predicted_crossings": self.predicted_crossings,
            "predicted_pnl_long": float(self.predicted_pnl_long) if self.predicted_pnl_long else None,
            "predicted_pnl_short": float(self.predicted_pnl_short) if self.predicted_pnl_short else None,
            "locked_fraction": float(self.locked_fraction) if self.locked_fraction else None,
            "sigma": float(self.sigma) if self.sigma else None,
            "buffer": float(self.buffer) if self.buffer else None,
            "actual_crossings": self.actual_crossings,
            "actual_pnl": float(self.actual_pnl) if self.actual_pnl else None,
            "actual_holding_hours": float(self.actual_holding_hours) if self.actual_holding_hours else None,
            "position_side": self.position_side,
            "crossing_error": self.crossing_error,
            "pnl_error": float(self.pnl_error) if self.pnl_error else None,
            "pnl_error_pct": float(self.pnl_error_pct) if self.pnl_error_pct else None,
            "status": self.status,
        }
