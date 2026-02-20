"""
Bybit API response models.

This module contains typed dataclasses for all Bybit API responses,
providing type safety and clear data structures for the gateway implementation.

Response Envelope Types:
    BybitRestEnvelope - Generic REST API response wrapper
    BybitListEnvelope - Response with 'list' array in result
    BybitWebSocketEnvelope - WebSocket message wrapper

These envelope types eliminate isinstance checks by providing type-safe parsing
of Bybit's standard response structures.
"""

import time
from decimal import Decimal
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ============================================================================
# GENERIC RESPONSE ENVELOPE TYPES
# ============================================================================

T = TypeVar("T")


class BybitRestEnvelope(BaseModel, Generic[T]):
    """Generic Bybit REST API response envelope.

    All Bybit REST responses follow this structure:
    {
        "retCode": 0,
        "retMsg": "OK",
        "result": { ... },  # Typed payload
        "retExtInfo": {},
        "time": 1234567890
    }

    Usage:
        # Parse response with typed result
        envelope = BybitRestEnvelope[BybitPositionResponse].model_validate(response)
        if envelope.is_success:
            position = envelope.result  # Type: BybitPositionResponse

        # Parse response with list result
        envelope = BybitListEnvelope[BybitPositionResponse].model_validate(response)
        for pos in envelope.items:
            ...  # Type: BybitPositionResponse
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    retCode: int = Field(default=0, description="Response code (0 = success)")
    retMsg: str = Field(default="OK", description="Response message")
    result: Optional[T] = Field(default=None, description="Response payload")
    retExtInfo: Optional[Dict[str, Any]] = Field(default=None, description="Extended info")
    time: Optional[int] = Field(default=None, description="Server timestamp")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if request was successful."""
        return self.retCode == 0


class BybitListResult(BaseModel, Generic[T]):
    """Bybit list result wrapper for paginated responses.

    Many Bybit endpoints return:
    {
        "result": {
            "list": [...],
            "nextPageCursor": "..."
        }
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    list: List[T] = Field(default_factory=list, description="List of items")
    nextPageCursor: Optional[str] = Field(default=None, description="Cursor for next page")
    category: Optional[str] = Field(default=None, description="Category (linear/inverse)")


class BybitListEnvelope(BaseModel, Generic[T]):
    """Bybit REST response with list in result.

    For endpoints that return arrays:
    {
        "retCode": 0,
        "result": {
            "list": [item1, item2, ...]
        }
    }

    Usage:
        envelope = BybitListEnvelope[BybitPositionResponse].model_validate(response)
        for position in envelope.items:
            ...  # Each item is BybitPositionResponse
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    retCode: int = Field(default=0, description="Response code")
    retMsg: str = Field(default="OK", description="Response message")
    result: Optional[BybitListResult[T]] = Field(default=None, description="Result with list")
    retExtInfo: Optional[Dict[str, Any]] = Field(default=None, description="Extended info")
    time: Optional[int] = Field(default=None, description="Server timestamp")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if request was successful."""
        return self.retCode == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[T]:
        """Get list items directly."""
        if self.result and self.result.list:
            return self.result.list
        return []


class BybitWebSocketEnvelope(BaseModel, Generic[T]):
    """Bybit WebSocket message envelope.

    WebSocket messages follow:
    {
        "topic": "position",
        "data": [...] or {...},
        "ts": 1234567890
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    topic: str = Field(..., description="WebSocket topic/channel")
    data: Union[T, List[T]] = Field(..., description="Message payload (single or list)")
    ts: Optional[int] = Field(default=None, description="Message timestamp")
    type: Optional[str] = Field(default=None, description="Message type (snapshot/delta)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[T]:
        """Get data as list (handles both single item and list)."""
        if isinstance(self.data, list):
            return self.data
        return [self.data]


# ============================================================================
# SPECIFIC RESPONSE MODELS
# ============================================================================


class BybitOrderCreateResponse(BaseModel):
    """Minimal Bybit order creation response.

    Bybit's POST /v5/order/create returns minimal data:
    {"result": {"orderId": "xxx", "orderLinkId": "yyy"}}

    Full order details (price, qty, status) must come from:
    - Original OrderRequest (for initial state)
    - WebSocket order updates (for status changes)
    - GET /v5/order/realtime (for polling)
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    orderId: str = Field(..., description="Exchange-assigned order ID")
    orderLinkId: Optional[str] = Field(default=None, description="Client order ID (orderLinkId)")


class BybitOrderResponse(BaseModel):
    """Bybit full order response model.

    Used for:
    - GET /v5/order/realtime (query orders)
    - GET /v5/order/history (order history)
    - WebSocket order topic updates
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    orderId: str = Field(..., description="Unique order ID from exchange")
    orderLinkId: str = Field(..., description="Client order ID")
    symbol: str = Field(..., description="Trading pair (e.g., BTCUSDT)")
    price: str = Field(..., description="Order price")
    qty: str = Field(..., description="Order quantity")
    side: str = Field(..., description="Buy or Sell")
    orderType: str = Field(..., description="Limit, Market, etc.")
    orderStatus: str = Field(..., description="New, Filled, Cancelled, etc.")
    timeInForce: str = Field(..., description="GTC, IOC, FOK")
    cumExecQty: str = Field(..., description="Cumulative executed quantity")
    cumExecValue: str = Field(..., description="Cumulative executed value")
    avgPrice: str = Field(..., description="Average fill price")
    createdTime: str = Field(..., description="Creation timestamp")
    updatedTime: str = Field(..., description="Last update timestamp")
    cumExecFee: Optional[str] = Field(None, description="Cumulative execution fees")
    blockTradeId: Optional[str] = Field(None, description="Block trade ID")
    cancelType: Optional[str] = Field(None, description="Cancel type")
    rejectReason: Optional[str] = Field(None, description="Rejection reason if rejected")
    leavesQty: Optional[str] = Field(None, description="Remaining quantity")
    leavesValue: Optional[str] = Field(None, description="Remaining value")
    lastPriceOnCreated: Optional[str] = Field(None, description="Last price when order was created")
    createType: Optional[str] = Field(None, description="Order creation type")
    stopOrderType: Optional[str] = Field(None, description="Stop order type")
    triggerPrice: Optional[str] = Field(None, description="Trigger price for conditional orders")
    triggerBy: Optional[str] = Field(None, description="Trigger price type (MarkPrice, LastPrice, IndexPrice)")
    trailingPercentage: Optional[str] = Field(None, description="Trailing stop percentage if applicable")
    basePrice: Optional[str] = Field(None, description="Base price for conditional orders")
    trailingValue: Optional[str] = Field(None, description="Trailing stop value if applicable")
    tpTriggerBy: Optional[str] = Field(None, description="Take profit trigger price type")
    slTriggerBy: Optional[str] = Field(None, description="Stop loss trigger price type")
    triggerDirection: Optional[int] = Field(None, description="Trigger direction (1: rise, 2: fall)")
    positionIdx: Optional[int] = Field(None, description="Position index for futures")
    smpType: Optional[str] = Field(None, description="SMP (Self Match Prevention) type")
    smpGroup: Optional[Union[str, int]] = Field(None, description="SMP group (string or integer)")
    smpOrderId: Optional[str] = Field(None, description="SMP order ID")
    tpslMode: Optional[str] = Field(None, description="TP/SL mode")
    tpLimitPrice: Optional[str] = Field(None, description="Take profit limit price")
    slLimitPrice: Optional[str] = Field(None, description="Stop loss limit price")
    placeType: Optional[str] = Field(None, description="Place type")
    isLeverage: Optional[str] = Field(None, description="Leverage flag")
    markPrice: Optional[str] = Field(None, description="Mark price at time of order")
    indexPrice: Optional[str] = Field(None, description="Index price at time of order")
    activationPrice: Optional[str] = Field(None, description="Activation price for conditional orders")
    reduceOnly: Optional[bool] = Field(None, description="Reduce only flag")
    closeOnTrigger: Optional[bool] = Field(None, description="Close on trigger flag")
    takeProfit: Optional[str] = Field(None, description="Take profit price")
    stopLoss: Optional[str] = Field(None, description="Stop loss price")
    orderIv: Optional[str] = Field(None, description="Implied volatility for options")
    marketUnit: Optional[str] = Field(None, description="Market unit")

    def get_price_decimal(self) -> Decimal:
        """Get price as Decimal for precision calculations."""
        return Decimal(self.price) if self.price else Decimal("0")

    def get_qty_decimal(self) -> Decimal:
        """Get quantity as Decimal for precision calculations."""
        return Decimal(self.qty) if self.qty else Decimal("0")

    def get_cumulative_qty_decimal(self) -> Decimal:
        """Get cumulative executed quantity as Decimal."""
        return Decimal(self.cumExecQty) if self.cumExecQty else Decimal("0")

    def get_average_price_decimal(self) -> Decimal:
        """Get average price as Decimal."""
        return Decimal(self.avgPrice) if self.avgPrice else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_buy_order(self) -> bool:
        """Check if this is a buy order."""
        return self.side.lower() == "buy"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.orderStatus.lower() == "filled"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.orderStatus.lower() == "partiallyfilled"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        """Check if order is still active (not filled or cancelled)."""
        return self.orderStatus.lower() in ["new", "partiallyfilled"]


class BybitOrderbookResponse(BaseModel):
    """Bybit orderbook response model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    timestamp: int = Field(..., description="Orderbook timestamp")
    bids: List[List[str]] = Field(..., description="List of [price, size] bid levels")
    asks: List[List[str]] = Field(..., description="List of [price, size] ask levels")
    updateId: int = Field(..., description="Update ID for this orderbook")

    def get_best_bid_price(self) -> Optional[Decimal]:
        """Get best bid price as Decimal."""
        if self.bids and len(self.bids) > 0:
            return Decimal(self.bids[0][0])
        return None

    def get_best_ask_price(self) -> Optional[Decimal]:
        """Get best ask price as Decimal."""
        if self.asks and len(self.asks) > 0:
            return Decimal(self.asks[0][0])
        return None

    def get_best_bid_size(self) -> Optional[Decimal]:
        """Get best bid size as Decimal."""
        if self.bids and len(self.bids) > 0:
            return Decimal(self.bids[0][1])
        return None

    def get_best_ask_size(self) -> Optional[Decimal]:
        """Get best ask size as Decimal."""
        if self.asks and len(self.asks) > 0:
            return Decimal(self.asks[0][1])
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate spread between best bid and ask."""
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None


class BybitTickerResponse(BaseModel):
    """Bybit ticker response model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    lastPrice: str = Field(..., description="Last trade price")
    bid1Price: str = Field(..., description="Best bid price")
    bid1Size: str = Field(..., description="Best bid size")
    ask1Price: str = Field(..., description="Best ask price")
    ask1Size: str = Field(..., description="Best ask size")
    volume24h: str = Field(..., description="24h trading volume")
    turnover24h: str = Field(..., description="24h turnover")
    price24hPcnt: str = Field(..., description="24h price change percentage")
    highPrice24h: str = Field(..., description="24h high price")
    lowPrice24h: str = Field(..., description="24h low price")

    def get_last_price_decimal(self) -> Decimal:
        """Get last price as Decimal."""
        return Decimal(self.lastPrice) if self.lastPrice else Decimal("0")

    def get_bid_price_decimal(self) -> Decimal:
        """Get bid price as Decimal."""
        return Decimal(self.bid1Price) if self.bid1Price else Decimal("0")

    def get_ask_price_decimal(self) -> Decimal:
        """Get ask price as Decimal."""
        return Decimal(self.ask1Price) if self.ask1Price else Decimal("0")

    def get_volume_decimal(self) -> Decimal:
        """Get 24h volume as Decimal."""
        return Decimal(self.volume24h) if self.volume24h else Decimal("0")

    def get_price_change_percent_decimal(self) -> Decimal:
        """Get 24h price change percentage as Decimal."""
        return Decimal(self.price24hPcnt) if self.price24hPcnt else Decimal("0")


class BybitBalance(BaseModel):
    """Bybit balance model.

    Handles both UNIFIED and CONTRACT account types:
    - UNIFIED accounts use 'equity' for available balance
    - CONTRACT accounts use 'availableBalance'
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    coin: str = Field(..., description="Currency (e.g., BTC)")
    walletBalance: str = Field(..., description="Total balance")
    availableBalance: Optional[str] = Field(None, description="Available for trading (CONTRACT accounts)")
    equity: Optional[str] = Field(None, description="Equity/available balance (UNIFIED accounts)")
    locked: Optional[str] = Field(None, description="Locked amount in orders")

    def get_total_balance_decimal(self) -> Decimal:
        """Get total balance as Decimal."""
        return Decimal(self.walletBalance) if self.walletBalance else Decimal("0")

    def get_available_balance_decimal(self) -> Decimal:
        """Get available balance as Decimal.

        For UNIFIED accounts: uses 'equity' field
        For CONTRACT accounts: uses 'availableBalance' field
        """
        # Try equity first (UNIFIED accounts)
        if self.equity:
            return Decimal(self.equity)
        # Fall back to availableBalance (CONTRACT accounts)
        elif self.availableBalance:
            return Decimal(self.availableBalance)
        # If neither is available, assume all balance is available
        else:
            return self.get_total_balance_decimal()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def locked_balance(self) -> Decimal:
        """Calculate locked balance.

        Uses explicit 'locked' field if available,
        otherwise calculates as (total - available).
        """
        if self.locked:
            return Decimal(self.locked)
        else:
            return self.get_total_balance_decimal() - self.get_available_balance_decimal()


class BybitPositionResponse(BaseModel):
    """Bybit position response model."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Buy or Sell")
    size: str = Field(..., description="Position size")
    avgPrice: str = Field(..., description="Average entry price")
    positionValue: str = Field(..., description="Position value")
    unrealisedPnl: str = Field(..., description="Unrealized PnL")
    realisedPnl: str = Field(default="0", description="Realized PnL")

    def get_size_decimal(self) -> Decimal:
        """Get position size as Decimal."""
        return Decimal(self.size) if self.size else Decimal("0")

    def get_avg_price_decimal(self) -> Decimal:
        """Get average price as Decimal."""
        return Decimal(self.avgPrice) if self.avgPrice else Decimal("0")

    def get_position_value_decimal(self) -> Decimal:
        """Get position value as Decimal."""
        return Decimal(self.positionValue) if self.positionValue else Decimal("0")

    def get_unrealized_pnl_decimal(self) -> Decimal:
        """Get unrealized PnL as Decimal."""
        return Decimal(self.unrealisedPnl) if self.unrealisedPnl else Decimal("0")

    def get_realized_pnl_decimal(self) -> Decimal:
        """Get realized PnL as Decimal."""
        return Decimal(self.realisedPnl) if self.realisedPnl else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_long_position(self) -> bool:
        """Check if this is a long position."""
        return self.side.lower() == "buy"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_short_position(self) -> bool:
        """Check if this is a short position."""
        return self.side.lower() == "sell"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_position(self) -> bool:
        """Check if there's an actual position (size > 0)."""
        return self.get_size_decimal() > Decimal("0")


# WebSocket models
class BybitWebSocketOrderUpdate(BaseModel):
    """Bybit WebSocket order update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="order")
    data: Dict[str, Any] = Field(..., description="Order update data")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_id(self) -> Optional[str]:
        """Extract order ID from data."""
        return cast(Optional[str], self.data.get("orderId"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_link_id(self) -> Optional[str]:
        """Extract order link ID from data."""
        return self.data.get("orderLinkId")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def symbol(self) -> Optional[str]:
        """Extract symbol from data."""
        return self.data.get("symbol")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_status(self) -> Optional[str]:
        """Extract order status from data."""
        return self.data.get("orderStatus")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def side(self) -> Optional[str]:
        """Extract order side from data."""
        return self.data.get("side")


class BybitWebSocketDepthUpdate(BaseModel):
    """Bybit WebSocket depth update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="orderbook.{depth}.{symbol}")
    type: str = Field(..., description="snapshot or delta")
    data: Dict[str, Any] = Field(..., description="Orderbook update")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def symbol(self) -> Optional[str]:
        """Extract symbol from data."""
        return self.data.get("s")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bids(self) -> List[List[str]]:
        """Extract bids from data."""
        return cast(List[List[str]], self.data.get("b", []))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asks(self) -> List[List[str]]:
        """Extract asks from data."""
        return cast(List[List[str]], self.data.get("a", []))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def timestamp(self) -> Optional[int]:
        """Extract timestamp from data."""
        return self.data.get("ts")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def update_id(self) -> Optional[int]:
        """Extract update ID from data."""
        return self.data.get("u")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot update."""
        return self.type == "snapshot"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_delta(self) -> bool:
        """Check if this is a delta update."""
        return self.type == "delta"


class BybitWebSocketBalanceUpdate(BaseModel):
    """Bybit WebSocket balance update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="wallet")
    data: Dict[str, Any] = Field(..., description="Balance update")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def coins(self) -> List[Dict[str, Any]]:
        """Extract coins list from data."""
        return cast(List[Dict[str, Any]], self.data.get("coin", []))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def account_type(self) -> Optional[str]:
        """Extract account type from data."""
        return self.data.get("accountType")

    def get_coin_balance(self, coin: str) -> Optional[Dict[str, str]]:
        """Get balance for specific coin."""
        for coin_data in self.coins:
            if coin_data.get("coin") == coin:
                return coin_data
        return None


class BybitWebSocketTradeUpdate(BaseModel):
    """Bybit WebSocket trade update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="publicTrade.{symbol}")
    data: List[Dict[str, Any]] = Field(..., description="Trade updates")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def symbol(self) -> Optional[str]:
        """Extract symbol from topic."""
        if "." in self.topic:
            return self.topic.split(".")[-1]
        return None

    def get_latest_trade(self) -> Optional[Dict[str, Any]]:
        """Get the latest trade from the update."""
        if self.data:
            return self.data[0]  # Bybit sends latest trade first
        return None

    def get_latest_price(self) -> Optional[Decimal]:
        """Get the latest trade price as Decimal."""
        latest = self.get_latest_trade()
        if latest and "p" in latest:
            return Decimal(latest["p"])
        return None


class BybitWebSocketPositionUpdate(BaseModel):
    """Bybit WebSocket position update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="position")
    data: List[Dict[str, Any]] = Field(..., description="Position updates")

    def get_position_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position update for specific symbol."""
        for pos_data in self.data:
            if pos_data.get("symbol") == symbol:
                return pos_data
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def symbols(self) -> List[str]:
        """Get all symbols in this position update."""
        symbols: List[str] = [str(pos.get("symbol")) for pos in self.data if pos.get("symbol")]
        return symbols


class BybitWebSocketExecutionUpdate(BaseModel):
    """Bybit WebSocket execution update model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(..., description="execution")
    data: List[Dict[str, Any]] = Field(..., description="Execution updates")

    def get_execution_for_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get execution update for specific order ID."""
        for exec_data in self.data:
            if exec_data.get("orderId") == order_id:
                return exec_data
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_ids(self) -> List[str]:
        """Get all order IDs in this execution update."""
        order_ids: List[str] = [str(exec.get("orderId")) for exec in self.data if exec.get("orderId")]
        return order_ids

    @computed_field  # type: ignore[prop-decorator]
    @property
    def symbols(self) -> List[str]:
        """Get all symbols in this execution update."""
        symbols: List[str] = [str(exec.get("symbol")) for exec in self.data if exec.get("symbol")]
        return symbols


# Enhanced WebSocket Response Models for Type Safety


class BybitWSMinimalOrderResponse(BaseModel):
    """Minimal WebSocket order response from Bybit.

    Bybit WebSocket API returns minimal data for performance optimization.
    This represents the actual fields returned by the WebSocket API.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    orderId: str = Field(..., description="Exchange order ID")
    orderLinkId: str = Field(..., description="Client order ID")
    reqId: str = Field(..., description="Request ID for correlation")
    retCode: int = Field(..., description="Response code (0 = success)")
    retMsg: str = Field(..., description="Response message")
    time: Optional[int] = Field(None, description="Response timestamp")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if order was successful."""
        return self.retCode == 0


class BybitEnrichedOrderResponse(BaseModel):
    """Order response enriched with request data.

    Since WebSocket returns minimal data, we enrich the response
    with data from the original request to maintain consistency
    with REST API responses.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    orderId: str = Field(..., description="Exchange order ID")
    orderLinkId: str = Field(..., description="Client order ID")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Order side")
    orderType: str = Field(..., description="Order type")
    qty: str = Field(..., description="Order quantity")
    price: str = Field(..., description="Order price")
    orderStatus: str = Field(default="New", description="Order status (Orders start as New)")
    timeInForce: str = Field(default="GTC", description="Time in force")
    cumExecQty: str = Field(default="0", description="Cumulative executed quantity")
    cumExecValue: str = Field(default="0", description="Cumulative executed value")
    avgPrice: str = Field(default="0", description="Average price")
    createdTime: str = Field(default="", description="Creation timestamp")
    updatedTime: str = Field(default="", description="Update timestamp")

    @classmethod
    def from_ws_response_and_request(
        cls, ws_response: Dict[str, Any], request_data: Dict[str, Any]
    ) -> "BybitEnrichedOrderResponse":
        """Create enriched response from WebSocket response and request data."""
        return cls(
            orderId=ws_response.get("orderId", ""),
            orderLinkId=ws_response.get("orderLinkId", ""),
            symbol=request_data.get("symbol", ""),
            side=request_data.get("side", ""),
            orderType=request_data.get("orderType", ""),
            qty=request_data.get("qty", "0"),
            price=request_data.get("price", "0"),
            timeInForce=request_data.get("timeInForce", "GTC"),
            createdTime=str(int(time.time() * 1000)),
            updatedTime=str(int(time.time() * 1000)),
        )


class BybitApiError(BaseModel):
    """Bybit API error response model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    retCode: int = Field(..., description="Error code")
    retMsg: str = Field(..., description="Error message")
    result: Dict[str, Any] = Field(..., description="Additional error data")
    retExtInfo: Optional[Dict[str, Any]] = Field(None, description="Extended error info")
    time: Optional[int] = Field(None, description="Error timestamp")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_rate_limit_error(self) -> bool:
        """Check if this is a rate limit error."""
        return self.retCode == 10002

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_insufficient_balance_error(self) -> bool:
        """Check if this is an insufficient balance error."""
        return self.retCode == 10001

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_order_not_found_error(self) -> bool:
        """Check if this is an order not found error."""
        return self.retCode == 10003

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_invalid_api_key_error(self) -> bool:
        """Check if this is an invalid API key error."""
        return self.retCode == 10004

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_signature_error(self) -> bool:
        """Check if this is a signature verification error."""
        return self.retCode == 10005

    def __str__(self) -> str:
        """String representation of the error."""
        return f"BybitApiError(code={self.retCode}, message={self.retMsg!r})"
