"""
Complete LiquidateInstructions model with Pydantic validation.

This unified model supports both standard cross-exchange arbitrage and
graph-based arbitrage with optional fields for graph-specific features.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ConfigDict, Field, computed_field, field_validator

from data_models.models.domain.base import StrictBaseModel
from data_models.models.enums.order import OrderSide


def _current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


class LiquidateInstructions(StrictBaseModel):
    """
    Unified liquidation instructions for all arbitrage strategies.

    Base fields are used by standard cross-exchange arbitrage.
    Optional graph fields are used by graph-based arbitrage for
    pre-calculated counter trades and multi-hop paths.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,  # Keep OrderSide as enum
        validate_default=True,
        populate_by_name=True,
    )

    # Base liquidation fields (required for all strategies)
    taker_price: float = Field(..., description="Price for taker order")
    taker_side: OrderSide = Field(..., description="Side for taker order")
    maker_price: float = Field(..., description="Price at which maker was filled")
    route: str = Field(..., min_length=1, description="Route identifier")

    # Graph arbitrage specific fields (optional)
    source_exchange: Optional[str] = Field(None, description="Exchange where maker order is placed")
    target_exchange: Optional[str] = Field(None, description="Exchange where counter trade is placed")
    source_contract: Optional[str] = Field(None, description="Contract on source exchange")
    target_contract: Optional[str] = Field(None, description="Contract on target exchange")

    # Full arbitrage path for multi-hop (optional)
    arbitrage_path: Optional[List[Tuple[str, str]]] = Field(
        None, description="List of (exchange, contract) tuples for multi-hop paths"
    )

    # Pre-calculated counter trade details (optional)
    counter_price: Optional[float] = Field(None, gt=0.0, description="Price for counter trade")
    counter_side: Optional[OrderSide] = Field(None, description="Side for counter trade")
    counter_amount: Optional[float] = Field(None, gt=0.0, description="Amount for counter trade")

    # Expected profit and slippage (optional)
    expected_profit: Optional[float] = Field(None, description="Expected profit in quote currency")
    max_slippage: Optional[float] = Field(None, ge=0.0, description="Maximum acceptable slippage")

    # Target spread parameters (mode-specific, REQUIRED - no defaults to prevent silent bugs)
    target_premium: float = Field(
        ..., description="Target premium % for SELL taker liquidation (0.0 for unwinding, 0.3 for market-making)"
    )
    target_discount: float = Field(
        ..., description="Target discount % for BUY taker liquidation (0.0 for unwinding, 0.3 for market-making)"
    )

    # Timing constraints (optional)
    max_execution_delay_ms: int = Field(default=1000, ge=0, description="Maximum delay for counter trade in milliseconds")

    # Opportunity metadata (optional)
    opportunity_id: str = Field(default="", description="Unique ID for this opportunity")
    quote_timestamp: int = Field(default_factory=_current_timestamp_ms, description="When the quote was generated (ms)")

    # Orderbook freshness tracking (for slippage analysis)
    taker_ob_age_at_quote_ms: int = Field(default=0, description="Age of taker orderbook when quote was generated (ms)")
    original_taker_price: float = Field(default=0.0, description="Taker reference price at quote time")

    @field_validator("taker_side", "counter_side", mode="before")
    @classmethod
    def validate_order_side(cls, v: str | OrderSide | None) -> Optional[OrderSide]:
        """Validate and normalize order side to enum."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return OrderSide(v.lower())
            except ValueError:
                for side in OrderSide:
                    if side.value.upper() == v.upper():
                        return side
                raise ValueError(f"Invalid order side: {v}") from None
        return v

    @field_validator("taker_price", "maker_price", "counter_price")
    @classmethod
    def validate_prices(cls, v: int | float | None) -> Optional[float]:
        """Ensure prices are positive if provided."""
        if v is None:
            return None
        if v <= 0:
            raise ValueError("Prices must be positive")
        return float(v)

    @field_validator("counter_amount")
    @classmethod
    def validate_amount(cls, v: int | float | None) -> Optional[float]:
        """Ensure amount is positive if provided."""
        if v is None:
            return None
        if v <= 0:
            raise ValueError("Amount must be positive")
        return float(v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_graph_arbitrage(self) -> bool:
        """Check if this is a graph arbitrage instruction."""
        return self.source_exchange is not None and self.target_exchange is not None and self.counter_price is not None

    def get_counter_trade_params(self) -> Optional[Dict[str, Any]]:
        """Get parameters for executing the counter trade (graph arbitrage only)."""
        is_graph_arb = self.is_graph_arbitrage
        if is_graph_arb is False:
            return None

        return {
            "exchange": self.target_exchange,
            "contract": self.target_contract,
            "side": self.counter_side,
            "price": self.counter_price,
            "amount": self.counter_amount,
            "max_slippage": self.max_slippage,
        }

    def is_still_valid(self, current_timestamp: int) -> bool:
        """Check if the liquidation instructions are still valid (graph arbitrage only)."""
        is_graph_arb = self.is_graph_arbitrage
        if is_graph_arb is False:
            return True  # Standard arbitrage doesn't have time constraints

        age_ms = current_timestamp - self.quote_timestamp
        return age_ms <= self.max_execution_delay_ms

    def adjust_for_partial_fill(self, filled_amount: float) -> None:
        """Adjust counter trade amount for partial fills (graph arbitrage only)."""
        is_graph_arb = self.is_graph_arbitrage
        if is_graph_arb is False or self.counter_amount is None:
            return

        if filled_amount < self.counter_amount:
            fill_ratio = filled_amount / self.counter_amount
            self.counter_amount = filled_amount
            if self.expected_profit is not None:
                self.expected_profit *= fill_ratio
