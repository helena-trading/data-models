"""
Data models for the reporting module.

This module defines the data structures used to represent various aspects
of the bot's activity for reporting purposes.

Active models:
- TradeInfo: Single trade execution info
- TimestampReport: Timestamps for trading operation stages
- LatencyMetrics: Latency measurements for operations
- BlockTradeInfo: Block trade (maker + taker pair) info
"""

import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_models.logging import warning
from data_models.models.enums.order import OrderSide


class TradeInfo(BaseModel):
    """Information about a single trade execution."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    internal_id: str = Field(default="")
    contract: str = Field(default="")
    order_id: str = Field(default="")
    exchange: str = Field(default="")
    side: OrderSide = Field(default_factory=lambda: OrderSide.BUY)
    price: float = Field(default=0.0, ge=0)
    size: float = Field(default=0.0, ge=0)
    value: float = Field(default=0.0)
    fees: float = Field(default=0.0, ge=0)
    raw_exchange_data: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, v: Any) -> OrderSide:
        """Convert side to OrderSide enum if it's not already."""
        if isinstance(v, OrderSide):
            return v
        elif isinstance(v, str):
            if v.lower() == "sell":
                return OrderSide.SELL
            elif v.lower() == "buy":
                return OrderSide.BUY
            else:
                warning(f"[TradeInfo] Unknown side string: {v}, defaulting to BUY")
                return OrderSide.BUY
        else:
            try:
                return OrderSide.from_string(v)
            except Exception as e:
                warning(f"[TradeInfo] Error converting side to OrderSide: {e}, using BUY as default")
                return OrderSide.BUY

    @model_validator(mode="after")
    def calculate_value(self) -> "TradeInfo":
        """Calculate value if not explicitly set."""
        if self.value == 0.0 and self.price > 0 and self.size > 0:
            self.value = round(self.price * self.size, 2)
        return self


class TimestampReport(BaseModel):
    """Timestamps for various stages of a trading operation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    start: int = Field(default=0, ge=0)
    process_execution: int = Field(default=0, ge=0)
    creating_maker: int = Field(default=0, ge=0)
    maker_live: int = Field(default=0, ge=0)
    cancelling_maker: int = Field(default=0, ge=0)
    resolve_maker_order: int = Field(default=0, ge=0)
    creating_taker: int = Field(default=0, ge=0)
    taker_live: int = Field(default=0, ge=0)
    complete: int = Field(default=0, ge=0)


class LatencyMetrics(BaseModel):
    """Latency measurements for various operations."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Orderbook latencies
    orderbook_latency_maker: int = Field(default=0, ge=0)
    orderbook_latency_taker: int = Field(default=0, ge=0)

    # Order placement latencies
    maker_placement_latency: int = Field(default=0, ge=0)
    taker_placement_latency: int = Field(default=0, ge=0)

    # Cancellation latencies
    cancel_request_latency: int = Field(default=0, ge=0)
    cancel_execution_latency: int = Field(default=0, ge=0)

    # Overall latencies
    lat_mkr: int = Field(default=0, ge=0)  # Maker order latency
    lat_tkr: int = Field(default=0, ge=0)  # Taker order latency
    lat_cyc: int = Field(default=0, ge=0)  # Full cycle latency

    # Fill notification latency (blindness window)
    # Time from when order filled on exchange (exchange timestamp) to when
    # WebSocket notification was received. Critical for understanding information delay.
    fill_notification_latency_ms: Optional[int] = Field(default=None, description="Fill notification latency in milliseconds")


class BlockTradeInfo(BaseModel):
    """Information about a block trade (maker and taker pair)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, arbitrary_types_allowed=True)

    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    client_id_id: str = Field(default="")
    maker_type: str = Field(default="")
    buy_exchange: str = Field(default="")
    sell_exchange: str = Field(default="")
    executed_spread: float = Field(default=0.0)
    slippage: float = Field(default=0.0)
    price_difference: float = Field(default=0.0)
    trade_value: float = Field(default=0.0)
    buy_price: float = Field(default=0.0, ge=0)
    sell_price: float = Field(default=0.0, ge=0)
    buy_size: float = Field(default=0.0, ge=0)
    sell_size: float = Field(default=0.0, ge=0)
    buy_side_trade: Optional["TradeInfo"] = Field(default=None)
    sell_side_trade: Optional["TradeInfo"] = Field(default=None)
    lifecycle_state: int = Field(default=0, ge=0)
    # Maker/taker exchange tracking (may differ from buy/sell sides)
    maker_exchange: Optional[str] = Field(default=None, description="Exchange acting as maker (may differ from buy_exchange)")
    taker_exchange: Optional[str] = Field(default=None, description="Exchange acting as taker (may differ from sell_exchange)")
    latency: int = Field(default=0, ge=0)
    tries: int = Field(default=0, ge=0)
    route: str = Field(default="")  # Route identifier (e.g., "route0", "route1")
    expected_spread: float = Field(default=0.0)  # The spread the bot was targeting
    slippage_bps: float = Field(default=0.0)  # Slippage in basis points
    maker_fee: float = Field(default=0.0)  # Maker fee for the trade
    taker_fee: float = Field(default=0.0)  # Taker fee for the trade

    @model_validator(mode="after")
    def validate_trades(self) -> "BlockTradeInfo":
        """Validate and complete the BlockTradeInfo."""
        # If both buy_side_trade and sell_side_trade are provided, validate them
        if self.buy_side_trade and self.sell_side_trade:
            # Ensure buy_side_trade is actually a buy
            if self.buy_side_trade.side != OrderSide.BUY:
                warning(f"[BlockTradeInfo] buy_side_trade has incorrect side {self.buy_side_trade.side}. Swapping trades.")
                self.buy_side_trade, self.sell_side_trade = (
                    self.sell_side_trade,
                    self.buy_side_trade,
                )

            # Update prices and sizes from the trades if not already set
            if self.buy_price == 0.0 and self.buy_side_trade:
                self.buy_price = self.buy_side_trade.price
            if self.sell_price == 0.0 and self.sell_side_trade:
                self.sell_price = self.sell_side_trade.price
            if self.buy_size == 0.0 and self.buy_side_trade:
                self.buy_size = self.buy_side_trade.size
            if self.sell_size == 0.0 and self.sell_side_trade:
                self.sell_size = self.sell_side_trade.size

        return self


__all__ = [
    "TradeInfo",
    "TimestampReport",
    "LatencyMetrics",
    "BlockTradeInfo",
]
