"""
Binance Spot API Response Models

Pydantic models for Binance Spot API responses to replace Dict[str, Any] usage.
These models provide type safety, runtime validation, and better IDE support.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field


class BinanceFill(BaseModel):
    """Trade fill information within an order."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    price: str = Field(..., description="Execution price")
    qty: str = Field(..., description="Execution quantity")
    commission: str = Field(..., description="Commission amount")
    commissionAsset: str = Field(..., description="Commission asset (e.g., BNB)")
    tradeId: int = Field(..., description="Trade ID")


class BinanceOrderResponse(BaseModel):
    """
    Binance order response model.

    Used for both REST order creation responses and order query responses.
    Note: Uses extra="ignore" to handle new fields Binance adds over time.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    symbol: str = Field(..., description="Exchange symbol format (e.g., BTCUSDT)")
    orderId: int = Field(..., description="Unique order ID assigned by exchange")
    orderListId: int = Field(..., description="OCO order list ID (-1 if not OCO)")
    clientOrderId: str = Field(..., description="Client-provided order ID")
    price: str = Field(..., description="Order price (0.00000000 for market orders)")
    origQty: str = Field(..., description="Original order quantity")
    executedQty: str = Field(..., description="Quantity already executed")
    cummulativeQuoteQty: str = Field(..., description="Cumulative quote asset transacted quantity")
    status: str = Field(..., description="Order status: NEW, PARTIALLY_FILLED, FILLED, CANCELED, etc.")
    timeInForce: str = Field(..., description="Time in force: GTC, IOC, FOK")
    type: str = Field(..., description="Order type: LIMIT, MARKET, LIMIT_MAKER")
    side: str = Field(..., description="Order side: BUY or SELL")

    # Timestamp fields: POST responses have transactTime, GET responses have time/updateTime
    transactTime: Optional[int] = Field(None, description="Transaction timestamp (POST /order responses only)")
    time: Optional[int] = Field(None, description="Order creation timestamp (GET /order responses only)")
    updateTime: Optional[int] = Field(None, description="Last update timestamp (GET /order responses only)")

    fills: Optional[List[BinanceFill]] = Field(None, description="Trade fills for this order")
    origQuoteOrderQty: Optional[str] = Field(None, description="Original quote order quantity (for MARKET orders)")
    workingTime: Optional[int] = Field(None, description="Working time when order starts affecting orderbook")
    selfTradePreventionMode: Optional[str] = Field(
        None, description="Self trade prevention mode: EXPIRE_TAKER, EXPIRE_MAKER, EXPIRE_BOTH, NONE"
    )

    @computed_field
    def effective_timestamp(self) -> int:
        """Best available timestamp: transactTime (POST) > updateTime (GET) > time (GET) > 0."""
        return self.transactTime or self.updateTime or self.time or 0

    @computed_field
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "FILLED"

    @computed_field
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in ["NEW", "PARTIALLY_FILLED"]

    @computed_field
    def average_price(self) -> float:
        """Calculate average execution price."""
        executed = float(self.executedQty)
        cumulative = float(self.cummulativeQuoteQty)
        return cumulative / executed if executed > 0 else 0.0


class BinanceOrderbookEntry(BaseModel):
    """Single orderbook level."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    price: str = Field(..., description="Price level")
    quantity: str = Field(..., description="Quantity at this level")

    def to_float_tuple(self) -> tuple[float, float]:
        """Convert to float tuple for internal use."""
        return (float(self.price), float(self.quantity))


class BinanceOrderbookResponse(BaseModel):
    """
    Binance orderbook (depth) response.

    Used for REST /api/v3/depth endpoint responses.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    lastUpdateId: int = Field(..., description="Last update ID for this orderbook")
    bids: List[List[str]] = Field(..., description="List of [price, quantity] bid levels")
    asks: List[List[str]] = Field(..., description="List of [price, quantity] ask levels")

    def get_bid_entries(self) -> List[BinanceOrderbookEntry]:
        """Convert bid strings to typed entries."""
        return [BinanceOrderbookEntry(price=bid[0], quantity=bid[1]) for bid in self.bids]

    def get_ask_entries(self) -> List[BinanceOrderbookEntry]:
        """Convert ask strings to typed entries."""
        return [BinanceOrderbookEntry(price=ask[0], quantity=ask[1]) for ask in self.asks]


class BinanceTickerResponse(BaseModel):
    """
    Binance 24hr ticker response.

    Used for REST /api/v3/ticker/24hr endpoint.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    priceChange: str = Field(..., description="Price change in 24hr")
    priceChangePercent: str = Field(..., description="Price change percent")
    weightedAvgPrice: str = Field(..., description="Weighted average price")
    prevClosePrice: str = Field(..., description="Previous close price")
    lastPrice: str = Field(..., description="Latest price")
    lastQty: str = Field(..., description="Latest trade quantity")
    bidPrice: str = Field(..., description="Best bid price")
    bidQty: str = Field(..., description="Best bid quantity")
    askPrice: str = Field(..., description="Best ask price")
    askQty: str = Field(..., description="Best ask quantity")
    openPrice: str = Field(..., description="Open price 24hr ago")
    highPrice: str = Field(..., description="Highest price in 24hr")
    lowPrice: str = Field(..., description="Lowest price in 24hr")
    volume: str = Field(..., description="Total traded base asset volume")
    quoteVolume: str = Field(..., description="Total traded quote asset volume")
    openTime: int = Field(..., description="Open timestamp")
    closeTime: int = Field(..., description="Close timestamp")
    firstId: int = Field(..., description="First trade ID")
    lastId: int = Field(..., description="Last trade ID")
    count: int = Field(..., description="Trade count")


class BinanceBalance(BaseModel):
    """Account balance for a single asset."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    asset: str = Field(..., description="Asset symbol (e.g., BTC)")
    free: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Locked in orders")

    @computed_field
    def total(self) -> float:
        """Calculate total balance."""
        return float(self.free) + float(self.locked)


class BinanceAccountResponse(BaseModel):
    """
    Binance account information response.

    Used for REST /api/v3/account endpoint.
    Note: Uses extra="ignore" to handle new fields Binance adds over time.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    makerCommission: int = Field(..., description="Maker commission rate (basis points)")
    takerCommission: int = Field(..., description="Taker commission rate (basis points)")
    buyerCommission: int = Field(..., description="Buyer commission rate")
    sellerCommission: int = Field(..., description="Seller commission rate")
    canTrade: bool = Field(..., description="Can place orders")
    canWithdraw: bool = Field(..., description="Can withdraw")
    canDeposit: bool = Field(..., description="Can deposit")
    updateTime: int = Field(..., description="Last account update timestamp")
    accountType: str = Field(..., description="Account type (e.g., SPOT)")
    balances: List[Dict[str, Any]] = Field(..., description="Raw balance data (will be parsed)")
    permissions: List[str] = Field(..., description="Account permissions")

    def get_balances(self) -> List[BinanceBalance]:
        """Get typed balance objects."""
        return [BinanceBalance(asset=bal["asset"], free=bal["free"], locked=bal["locked"]) for bal in self.balances]

    def get_balance(self, asset: str) -> Optional[BinanceBalance]:
        """Get balance for specific asset."""
        for bal in self.balances:
            if bal["asset"] == asset:
                return BinanceBalance(asset=bal["asset"], free=bal["free"], locked=bal["locked"])
        return None


class BinanceTrade(BaseModel):
    """Recent trade data."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: int = Field(..., description="Trade ID")
    price: str = Field(..., description="Trade price")
    qty: str = Field(..., description="Trade quantity")
    quoteQty: str = Field(..., description="Quote quantity")
    time: int = Field(..., description="Trade timestamp")
    isBuyerMaker: bool = Field(..., description="True if buyer was maker")
    isBestMatch: bool = Field(..., description="Was the best price match")


class BinanceSymbolInfo(BaseModel):
    """
    Trading rules and information for a symbol.

    Part of exchange info response.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    status: str = Field(..., description="Trading status (e.g., TRADING)")
    baseAsset: str = Field(..., description="Base asset")
    baseAssetPrecision: int = Field(..., description="Base asset precision")
    quoteAsset: str = Field(..., description="Quote asset")
    quotePrecision: int = Field(..., description="Quote asset precision")
    quoteAssetPrecision: int = Field(..., description="Quote asset precision (for amounts)")
    baseCommissionPrecision: int = Field(..., description="Base commission precision")
    quoteCommissionPrecision: int = Field(..., description="Quote commission precision")
    orderTypes: List[str] = Field(..., description="Allowed order types")
    icebergAllowed: bool = Field(..., description="Iceberg orders allowed")
    ocoAllowed: bool = Field(..., description="OCO orders allowed")
    quoteOrderQtyMarketAllowed: bool = Field(..., description="Quote order qty market orders allowed")
    isSpotTradingAllowed: bool = Field(..., description="Spot trading allowed")
    isMarginTradingAllowed: bool = Field(..., description="Margin trading allowed")
    filters: List[Dict[str, Any]] = Field(..., description="Price, quantity, and other filters")
    permissions: List[str] = Field(..., description="Symbol permissions")

    def get_price_filter(self) -> Optional[Dict[str, Any]]:
        """Get price filter rules."""
        for f in self.filters:
            if f.get("filterType") == "PRICE_FILTER":
                return f
        return None

    def get_lot_size_filter(self) -> Optional[Dict[str, Any]]:
        """Get lot size (quantity) filter rules."""
        for f in self.filters:
            if f.get("filterType") == "LOT_SIZE":
                return f
        return None


class BinanceWebSocketOrderUpdate(BaseModel):
    """
    WebSocket execution report (order update).

    Event type 'executionReport' from user data stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description="Event type: executionReport")
    E: int = Field(..., description="Event timestamp")
    s: str = Field(..., description="Symbol")
    c: str = Field(..., description="Client order ID")
    S: str = Field(..., description="Side: BUY or SELL")
    o: str = Field(..., description="Order type")
    f: str = Field(..., description="Time in force")
    q: str = Field(..., description="Order quantity")
    p: str = Field(..., description="Order price")
    P: str = Field(..., description="Stop price (0.00000000 if not stop order)")
    F: str = Field(..., description="Iceberg quantity")
    g: int = Field(..., description="Order list ID")
    C: str = Field(..., description="Original client order ID (for cancels)")
    x: str = Field(..., description="Execution type: NEW, CANCELED, REPLACED, etc.")
    X: str = Field(..., description="Order status: NEW, PARTIALLY_FILLED, FILLED, etc.")
    r: str = Field(..., description="Order reject reason")
    i: int = Field(..., description="Order ID")
    l: str = Field(..., description="Last executed quantity")
    z: str = Field(..., description="Cumulative filled quantity")
    L: str = Field(..., description="Last executed price")
    n: str = Field(..., description="Commission amount")
    N: Optional[str] = Field(None, description="Commission asset")
    T: int = Field(..., description="Transaction timestamp")
    t: int = Field(..., description="Trade ID (-1 if no trade)")
    I: int = Field(..., description="Ignore field")
    w: bool = Field(..., description="Is order on book")
    m: bool = Field(..., description="Is trade maker side")
    M: bool = Field(..., description="Ignore field")
    O: int = Field(..., description="Order creation timestamp")
    Z: str = Field(..., description="Cumulative quote asset transacted quantity")
    Y: str = Field(..., description="Last quote asset transacted quantity")
    Q: str = Field(..., description="Quote order quantity")
    W: Optional[int] = Field(None, description="Working time when order starts affecting orderbook")
    V: Optional[str] = Field(None, description="Self trade prevention mode: EXPIRE_TAKER, EXPIRE_MAKER, etc.")


class BinanceWebSocketBalance(BaseModel):
    """WebSocket balance update."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    a: str = Field(..., description="Asset")
    f: str = Field(..., description="Free amount")
    l: str = Field(..., description="Locked amount")


class BinanceWebSocketBalanceUpdate(BaseModel):
    """
    WebSocket account update.

    Event type 'outboundAccountPosition' from user data stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description="Event type: outboundAccountPosition")
    E: int = Field(..., description="Event timestamp")
    u: int = Field(..., description="Time of last account update")
    B: List[Dict[str, Any]] = Field(..., description="Balances array")

    def get_balances(self) -> List[BinanceWebSocketBalance]:
        """Get typed balance objects."""
        return [BinanceWebSocketBalance(a=bal["a"], f=bal[""], l=bal["l"]) for bal in self.B]


class BinanceWebSocketDepthUpdate(BaseModel):
    """
    WebSocket orderbook depth update.

    From market data stream depth updates.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description="Event type: depthUpdate")
    E: int = Field(..., description="Event timestamp")
    s: str = Field(..., description="Symbol")
    U: int = Field(..., description="First update ID")
    u: int = Field(..., description="Final update ID")
    b: List[List[str]] = Field(..., description="Bids to update [price, quantity]")
    a: List[List[str]] = Field(..., description="Asks to update [price, quantity]")


class BinanceWebSocketBookTicker(BaseModel):
    """
    WebSocket best bid/ask update.

    Individual book ticker from stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    u: int = Field(..., description="Order book update ID")
    s: str = Field(..., description="Symbol")
    b: str = Field(..., description="Best bid price")
    B: str = Field(..., description="Best bid quantity")
    a: str = Field(..., description="Best ask price")
    A: str = Field(..., description="Best ask quantity")


class BinanceListenKeyResponse(BaseModel):
    """Response from listen key creation/renewal."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    listenKey: str = Field(..., description="The listen key for user data stream")


# =============================================================================
# Response Envelope Types
# =============================================================================


class BinanceSpotBalanceEnvelope(BaseModel):
    """
    Envelope for Binance Spot balance/account responses.

    Centralizes isinstance checks for different response formats:
    - Dict with "balances" key (account info response)
    - List (raw balance array)
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    balances: List[Dict[str, Any]] = Field(default_factory=list, description="List of balance entries")

    @classmethod
    def from_response(cls, response: Union[Dict[str, Any], List[Any]]) -> "BinanceSpotBalanceEnvelope":
        """
        Create envelope from raw API response.

        Handles both account info dict and raw balance list formats.
        """
        if isinstance(response, list):
            # List format - could be list of balances or list containing account info
            if response and isinstance(response[0], dict) and "balances" in response[0]:
                # First element is account info
                return cls(balances=response[0].get("balances", []))
            # Assume it's a raw balance list
            return cls(balances=response)
        # Dict format - response is a dict
        if "balances" in response:
            return cls(balances=response["balances"])
        # Single balance entry
        return cls(balances=[response])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[Dict[str, Any]]:
        """Alias for balances for consistent interface."""
        return self.balances


class BinanceSpotWebSocketBalanceEnvelope(BaseModel):
    """
    Envelope for Binance Spot WebSocket balance update messages.

    Centralizes isinstance checks for outboundAccountPosition events.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    balances: List[Dict[str, Any]] = Field(default_factory=list, description="List of balance updates from 'B' field")

    @classmethod
    def from_update(cls, update: Union[Dict[str, Any], List[Any]]) -> "BinanceSpotWebSocketBalanceEnvelope":
        """
        Create envelope from WebSocket update.

        Handles both single update dict and list of updates.
        """
        if isinstance(update, list):
            # List format - process first update if available
            if update and isinstance(update[0], dict):
                return cls(balances=update[0].get("B", []))
            return cls(balances=[])
        # Dict format - update is a dict
        return cls(balances=update.get("B", []))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[Dict[str, Any]]:
        """Alias for balances for consistent interface."""
        return self.balances


BinanceWebSocketMessage = Union[
    BinanceWebSocketOrderUpdate,
    BinanceWebSocketBalanceUpdate,
    BinanceWebSocketDepthUpdate,
    BinanceWebSocketBookTicker,
    Dict[str, Any],
]
