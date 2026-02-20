"""Fill outcome log database model.

Logs fill outcomes for quote decisions to enable model calibration.
Links quote_decision_logs to actual fill/cancel results.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Tuple


@dataclass
class FillOutcomeLog:
    """
    Fill outcome log record for database storage.

    Records the actual outcome of orders created from quote decisions.
    This data is essential for:
    1. Calibrating the HazardFillModel (compare predicted vs actual fill rates)
    2. Computing realized EV (compare expected_value to actual profit)
    3. Understanding slippage and execution quality

    Attributes:
        time: Outcome timestamp
        internal_id: Links to quote_decision_logs.internal_id
        bot_id: Bot ID
        contract: Contract symbol
        outcome: "filled", "partially_filled", "cancelled", "expired"
        fill_time_ms: Time from order creation to fill
        predicted_fill_prob: Fill probability from quote decision
        filled_price: Actual fill price
        filled_quantity: Quantity filled
        slippage_bps: Difference from quoted price in bps
        fees_paid: Trading fees paid
        realized_pnl: Actual realized P&L (if available)
        exchange_order_id: Exchange order ID for reconciliation
    """

    time: datetime
    internal_id: str
    bot_id: int
    contract: str
    outcome: str  # "filled", "partially_filled", "cancelled", "expired"
    predicted_fill_prob: float

    # Optional fields (populated for fills)
    fill_time_ms: Optional[int] = None
    filled_price: Optional[Decimal] = None
    filled_quantity: Optional[Decimal] = None
    slippage_bps: Optional[float] = None
    fees_paid: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    exchange_order_id: Optional[str] = None
    quoted_price: Optional[Decimal] = None  # Original quoted price for slippage calc
    order_ttl_ms: Optional[int] = None  # How long order was active

    @classmethod
    def from_fill(
        cls,
        internal_id: str,
        bot_id: int,
        contract: str,
        predicted_fill_prob: float,
        quoted_price: float,
        filled_price: float,
        filled_quantity: float,
        fill_time_ms: int,
        fees_paid: Optional[float] = None,
        exchange_order_id: Optional[str] = None,
    ) -> "FillOutcomeLog":
        """
        Create from a successful fill.

        Args:
            internal_id: Quote decision internal ID
            bot_id: Bot ID
            contract: Contract symbol
            predicted_fill_prob: Fill prob from decision
            quoted_price: Price we quoted
            filled_price: Actual fill price
            filled_quantity: Amount filled
            fill_time_ms: Time to fill
            fees_paid: Fees
            exchange_order_id: Exchange order ID
        """
        # Calculate slippage
        slippage_bps = 0.0
        if quoted_price > 0:
            slippage_bps = (filled_price - quoted_price) / quoted_price * 10000

        return cls(
            time=datetime.now(tz=timezone.utc),
            internal_id=internal_id,
            bot_id=bot_id,
            contract=contract,
            outcome="filled",
            predicted_fill_prob=predicted_fill_prob,
            fill_time_ms=fill_time_ms,
            filled_price=Decimal(str(filled_price)),
            filled_quantity=Decimal(str(filled_quantity)),
            slippage_bps=slippage_bps,
            fees_paid=Decimal(str(fees_paid)) if fees_paid else None,
            exchange_order_id=exchange_order_id,
            quoted_price=Decimal(str(quoted_price)),
        )

    @classmethod
    def from_cancel(
        cls,
        internal_id: str,
        bot_id: int,
        contract: str,
        predicted_fill_prob: float,
        order_ttl_ms: int,
        exchange_order_id: Optional[str] = None,
        partial_fill_quantity: Optional[float] = None,
        partial_fill_price: Optional[float] = None,
    ) -> "FillOutcomeLog":
        """
        Create from a cancelled order.

        Args:
            internal_id: Quote decision internal ID
            bot_id: Bot ID
            contract: Contract symbol
            predicted_fill_prob: Fill prob from decision
            order_ttl_ms: How long order was active before cancel
            exchange_order_id: Exchange order ID
            partial_fill_quantity: If partially filled before cancel
            partial_fill_price: Avg price of partial fill
        """
        outcome = "partially_filled" if partial_fill_quantity else "cancelled"

        return cls(
            time=datetime.now(tz=timezone.utc),
            internal_id=internal_id,
            bot_id=bot_id,
            contract=contract,
            outcome=outcome,
            predicted_fill_prob=predicted_fill_prob,
            order_ttl_ms=order_ttl_ms,
            exchange_order_id=exchange_order_id,
            filled_quantity=(Decimal(str(partial_fill_quantity)) if partial_fill_quantity else None),
            filled_price=(Decimal(str(partial_fill_price)) if partial_fill_price else None),
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO fill_outcome_logs
            (time, internal_id, bot_id, contract, outcome, predicted_fill_prob,
             fill_time_ms, filled_price, filled_quantity, slippage_bps,
             fees_paid, realized_pnl, exchange_order_id, quoted_price, order_ttl_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.time,
            self.internal_id,
            self.bot_id,
            self.contract,
            self.outcome,
            self.predicted_fill_prob,
            self.fill_time_ms,
            self.filled_price,
            self.filled_quantity,
            self.slippage_bps,
            self.fees_paid,
            self.realized_pnl,
            self.exchange_order_id,
            self.quoted_price,
            self.order_ttl_ms,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts."""
        return """
            INSERT INTO fill_outcome_logs
            (time, internal_id, bot_id, contract, outcome, predicted_fill_prob,
             fill_time_ms, filled_price, filled_quantity, slippage_bps,
             fees_paid, realized_pnl, exchange_order_id, quoted_price, order_ttl_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_params(self) -> Tuple[Any, ...]:
        """Get parameters for batch insert."""
        return (
            self.time,
            self.internal_id,
            self.bot_id,
            self.contract,
            self.outcome,
            self.predicted_fill_prob,
            self.fill_time_ms,
            self.filled_price,
            self.filled_quantity,
            self.slippage_bps,
            self.fees_paid,
            self.realized_pnl,
            self.exchange_order_id,
            self.quoted_price,
            self.order_ttl_ms,
        )
