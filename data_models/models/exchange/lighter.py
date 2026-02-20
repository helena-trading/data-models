"""
Lighter API response models and type definitions.

This module provides type safety and clear data structures for Lighter gateway,
following the same Pydantic pattern as other exchange implementations.

Architecture:
- Typed Pydantic models for all API responses
- Computed fields for common calculations
- Response envelope types for unwrapping API responses

CRITICAL: Lighter uses integer order_index as order ID and market_id for routing.
- Order IDs are integers (order_index)
- Only LIMIT orders with Time-In-Force (TIF)
- TIF values: POST_ONLY=2, IOC=0, GTT=1
- USDC is universal quote currency
- Cross-margin only
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field

T = TypeVar("T")


# ============================================================================
# ORDER RESPONSE MODELS
# ============================================================================


class LighterOrderResponse(BaseModel):
    """Lighter order response from REST API or SDK.

    Handles multiple field name variants (SDK vs raw API):
    - order_index / index / order_id
    - market_id / market_index
    - initial_base_amount / base_amount / amount
    - is_ask / is_buy

    Response format from SDK:
    {
        "order_index": 123,
        "market_id": 0,
        "is_ask": true,
        "limit_price": "88000.50",
        "initial_base_amount": "0.001",
        "filled_base_amount": "0",
        "status": "open",
        "time_in_force": 2,
        "client_order_index": 12345678
    }

    Pattern: Provides type-safe access to order data.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    # Order identification - multiple field names supported
    order_index: Optional[int] = Field(None, description="Order index (exchange ID)")
    index: Optional[int] = Field(None, description="Alternative order index field")
    order_id: Optional[int] = Field(None, description="Alternative order ID field")

    # Market identification
    market_id: Optional[int] = Field(None, description="Market ID for routing")
    market_index: Optional[int] = Field(None, description="Alternative market ID field")

    # Side - Lighter uses is_ask (True=SELL, False=BUY)
    is_ask: Optional[bool] = Field(None, description="True=SELL, False=BUY")
    is_buy: Optional[bool] = Field(None, description="True=BUY (alternative to is_ask)")

    # Price and amounts - may be strings or scaled integers
    price: Optional[str] = Field(None, description="Order price")
    limit_price: Optional[str] = Field(None, description="Alternative price field")

    initial_base_amount: Optional[str] = Field(None, description="Original order size")
    base_amount: Optional[str] = Field(None, description="Alternative size field")
    amount: Optional[str] = Field(None, description="Alternative size field")

    filled_base_amount: Optional[str] = Field(None, description="Filled size")
    filled_amount: Optional[str] = Field(None, description="Alternative filled field")

    # Order metadata
    status: str = Field(default="", description="Order status string")
    time_in_force: int = Field(default=1, description="TIF: 0=IOC, 1=GTT, 2=POST_ONLY")
    client_order_index: Optional[int] = Field(None, description="Client order index")
    timestamp: Optional[int] = Field(None, description="Order timestamp")
    expiry: Optional[int] = Field(None, description="Order expiry time")
    reduce_only: bool = Field(default=False, description="Reduce only flag")

    # TIF constants
    TIF_IOC: int = 0
    TIF_GTT: int = 1
    TIF_POST_ONLY: int = 2

    def get_order_index(self) -> int:
        """Get order index (exchange ID), preferring order_index field."""
        return self.order_index or self.index or self.order_id or 0

    def get_market_id(self) -> int:
        """Get market ID."""
        return self.market_id or self.market_index or 0

    def get_is_buy(self) -> bool:
        """Get buy side, handling both is_ask and is_buy fields."""
        if self.is_ask is not None:
            return not self.is_ask  # is_ask=True means SELL
        return self.is_buy if self.is_buy is not None else True

    def get_price_decimal(self) -> Decimal:
        """Get price as Decimal."""
        raw = self.price or self.limit_price or "0"
        return Decimal(str(raw)) if raw else Decimal("0")

    def get_amount_decimal(self) -> Decimal:
        """Get original order size as Decimal."""
        raw = self.initial_base_amount or self.base_amount or self.amount or "0"
        return Decimal(str(raw)) if raw else Decimal("0")

    def get_filled_amount_decimal(self) -> Decimal:
        """Get filled amount as Decimal."""
        raw = self.filled_base_amount or self.filled_amount or "0"
        return Decimal(str(raw)) if raw else Decimal("0")

    def get_remaining_amount_decimal(self) -> Decimal:
        """Get remaining unfilled amount as Decimal."""
        return self.get_amount_decimal() - self.get_filled_amount_decimal()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_post_only(self) -> bool:
        """Check if order is post-only (maker)."""
        return self.time_in_force == self.TIF_POST_ONLY

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_ioc(self) -> bool:
        """Check if order is immediate-or-cancel."""
        return self.time_in_force == self.TIF_IOC

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_open(self) -> bool:
        """Check if order is open."""
        return self.status.lower() in ("open", "new", "")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return "filled" in self.status.lower() and "partial" not in self.status.lower()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return "cancel" in self.status.lower()


class LighterOrderEnvelope(BaseModel):
    """Lighter order response envelope.

    Wraps order data that may be nested under 'order' key.

    Response format:
    {
        "order": {...order_data...}
    }
    OR
    {...order_data directly...}
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    order: Optional[LighterOrderResponse] = Field(None, description="Nested order data")
    code: Optional[int] = Field(None, description="Response code (200=success)")
    success: Optional[bool] = Field(None, description="Success flag")
    message: Optional[str] = Field(None, description="Response message")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.code == 200 or self.success is True


class LighterOrderListResponse(BaseModel):
    """Lighter order list response.

    Format:
    {
        "orders": [
            {...order...},
            ...
        ]
    }
    OR direct list [...]
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    orders: List[LighterOrderResponse] = Field(default_factory=list, description="List of orders")

    @classmethod
    def from_response(cls, data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> "LighterOrderListResponse":
        """Create from raw response, handling list or dict format."""
        if isinstance(data, list):
            orders = [LighterOrderResponse.model_validate(o) for o in data]
            return cls(orders=orders)
        elif isinstance(data, dict) and "orders" in data:
            orders = [LighterOrderResponse.model_validate(o) for o in data.get("orders", [])]
            return cls(orders=orders)
        return cls(orders=[])


# ============================================================================
# CANCEL RESPONSE MODELS
# ============================================================================


class LighterCancelResponse(BaseModel):
    """Lighter cancel order response.

    Response format:
    {
        "code": 200,
        "success": true,
        "status": "cancelled",
        "message": ""
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    code: int = Field(default=0, description="Response code (200=success)")
    success: bool = Field(default=False, description="Success flag")
    status: str = Field(default="", description="Result status")
    message: str = Field(default="", description="Response message")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if cancellation was successful."""
        return self.code == 200 or self.success

    @computed_field  # type: ignore[prop-decorator]
    @property
    def already_cancelled(self) -> bool:
        """Check if order was already cancelled."""
        status_lower = self.status.lower()
        return "already" in status_lower and "cancel" in status_lower

    @computed_field  # type: ignore[prop-decorator]
    @property
    def already_filled(self) -> bool:
        """Check if order was already filled."""
        return "filled" in self.status.lower()


# ============================================================================
# POSITION RESPONSE MODELS
# ============================================================================


class LighterPositionResponse(BaseModel):
    """Lighter position response.

    Handles two formats:
    - WebSocket: ``size`` (signed), ``entry_price``, ``mark_price``
    - REST SDK (AccountPosition): ``position`` (unsigned) + ``sign``,
      ``avg_entry_price``, ``position_value``

    Note: Lighter uses cross-margin, so leverage is derived.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    market_id: Optional[int] = Field(None, description="Market ID")
    market: Optional[int] = Field(None, description="Alternative market field")

    # WebSocket format fields
    size: str = Field(default="0", description="Position size (signed) - WebSocket format")
    entry_price: str = Field(default="0", description="Entry price - WebSocket format")
    mark_price: str = Field(default="0", description="Current mark price - WebSocket format")

    # REST SDK format fields (AccountPosition model)
    position: str = Field(default="0", description="Position size (unsigned) - REST format")
    sign: int = Field(default=0, description="Position direction: 1=long, -1=short, 0=none - REST format")
    avg_entry_price: str = Field(default="0", description="Average entry price - REST format")
    position_value: str = Field(default="0", description="Position notional value - REST format")
    allocated_margin: str = Field(default="0", description="Allocated margin - REST format")

    # Common fields
    liquidation_price: str = Field(default="0", description="Liquidation price")
    unrealized_pnl: str = Field(default="0", description="Unrealized PnL")
    margin: str = Field(default="0", description="Margin used")
    notional: str = Field(default="0", description="Position notional value")
    leverage: Optional[str] = Field(None, description="Effective leverage")

    def get_market_id(self) -> int:
        """Get market ID."""
        return self.market_id or self.market or 0

    def get_size_decimal(self) -> Decimal:
        """Get position size as Decimal (signed).

        WebSocket sends ``size`` already signed.
        REST SDK sends ``position`` (unsigned) with ``sign`` for direction.
        """
        ws_size = Decimal(self.size) if self.size else Decimal("0")
        if ws_size != 0:
            return ws_size

        rest_position = Decimal(self.position) if self.position else Decimal("0")
        if rest_position != 0 and self.sign != 0:
            return rest_position * self.sign

        return Decimal("0")

    def get_entry_price_decimal(self) -> Decimal:
        """Get entry price as Decimal.

        WebSocket uses ``entry_price``, REST SDK uses ``avg_entry_price``.
        """
        ws_price = Decimal(self.entry_price) if self.entry_price else Decimal("0")
        if ws_price != 0:
            return ws_price
        return Decimal(self.avg_entry_price) if self.avg_entry_price else Decimal("0")

    def get_mark_price_decimal(self) -> Decimal:
        """Get mark price as Decimal.

        WebSocket sends ``mark_price`` directly.
        REST SDK has no mark_price — derive from ``position_value / position``.
        """
        ws_price = Decimal(self.mark_price) if self.mark_price else Decimal("0")
        if ws_price != 0:
            return ws_price
        pos_val = Decimal(self.position_value) if self.position_value else Decimal("0")
        pos_size = Decimal(self.position) if self.position else Decimal("0")
        if pos_val != 0 and pos_size != 0:
            return abs(pos_val / pos_size)
        return Decimal("0")

    def get_liquidation_price_decimal(self) -> Decimal:
        """Get liquidation price as Decimal."""
        return Decimal(self.liquidation_price) if self.liquidation_price else Decimal("0")

    def get_unrealized_pnl_decimal(self) -> Decimal:
        """Get unrealized PnL as Decimal."""
        return Decimal(self.unrealized_pnl) if self.unrealized_pnl else Decimal("0")

    def get_margin_decimal(self) -> Decimal:
        """Get margin used as Decimal."""
        return Decimal(self.margin) if self.margin else Decimal("0")

    def get_notional_decimal(self) -> Decimal:
        """Get notional value as Decimal."""
        return Decimal(self.notional) if self.notional else Decimal("0")

    def get_leverage_decimal(self) -> Optional[Decimal]:
        """Get leverage as Decimal, or calculate from margin/notional."""
        if self.leverage:
            return Decimal(self.leverage)
        # Calculate from margin and notional if available
        margin = self.get_margin_decimal()
        notional = self.get_notional_decimal()
        if margin > 0 and notional > 0:
            return notional / margin
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.get_size_decimal() > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.get_size_decimal() < 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_position(self) -> bool:
        """Check if there is an active position."""
        return self.get_size_decimal() != 0


# ============================================================================
# BALANCE RESPONSE MODELS
# ============================================================================


class LighterBalanceResponse(BaseModel):
    """Lighter balance response.

    Lighter uses single USDC balance for all trading.

    Balance format:
    {
        "free": "10000.0",
        "locked": "2500.0",
        "total": "12500.0"
    }
    OR simple numeric:
    "10000.0"
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    free: str = Field(default="0", description="Available balance")
    locked: str = Field(default="0", description="Locked in positions/orders")
    total: str = Field(default="0", description="Total balance")

    def get_free_decimal(self) -> Decimal:
        """Get free balance as Decimal."""
        return Decimal(self.free) if self.free else Decimal("0")

    def get_locked_decimal(self) -> Decimal:
        """Get locked balance as Decimal."""
        return Decimal(self.locked) if self.locked else Decimal("0")

    def get_total_decimal(self) -> Decimal:
        """Get total balance as Decimal."""
        if self.total and self.total != "0":
            return Decimal(self.total)
        # Calculate from free + locked
        return self.get_free_decimal() + self.get_locked_decimal()

    @classmethod
    def from_value(cls, value: Union[str, int, float, Dict[str, Any]]) -> "LighterBalanceResponse":
        """Create from various input formats."""
        if isinstance(value, dict):
            return cls.model_validate(value)
        # Simple numeric value - treat as total/free
        total_str = str(value)
        return cls(free=total_str, locked="0", total=total_str)


# ============================================================================
# ACCOUNT RESPONSE MODELS
# ============================================================================


class LighterAccountResponse(BaseModel):
    """Lighter account info response (balance + positions).

    Account format:
    {
        "balance": {
            "free": "10000.0",
            "locked": "2500.0",
            "total": "12500.0"
        },
        "positions": [
            {...position...},
            ...
        ]
    }
    OR:
    {
        "usdc_balance": {...},
        "active_positions": [...]
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    # Balance - multiple field names
    balance: Optional[Dict[str, Any]] = Field(None, description="Balance info")
    usdc_balance: Optional[Dict[str, Any]] = Field(None, description="Alternative balance field")

    # Positions - multiple field names
    positions: Optional[List[Dict[str, Any]]] = Field(None, description="Position list")
    active_positions: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative position field")

    # Account metadata
    account_id: Optional[int] = Field(None, description="Account index")
    account_index: Optional[int] = Field(None, description="Alternative account ID field")

    def get_balance(self) -> LighterBalanceResponse:
        """Get parsed balance."""
        raw = self.balance or self.usdc_balance
        if raw:
            if isinstance(raw, dict):
                return LighterBalanceResponse.model_validate(raw)
            return LighterBalanceResponse.from_value(raw)
        return LighterBalanceResponse()

    def get_positions(self) -> List[LighterPositionResponse]:
        """Get parsed positions."""
        raw_list = self.positions or self.active_positions or []

        # Handle dict format (market_id -> position)
        if isinstance(raw_list, dict):
            raw_list = list(raw_list.values())

        positions = []
        for raw in raw_list:
            try:
                pos = LighterPositionResponse.model_validate(raw)
                if pos.has_position:
                    positions.append(pos)
            except Exception:
                continue

        return positions

    def get_account_id(self) -> int:
        """Get account ID."""
        return self.account_id or self.account_index or 0


# ============================================================================
# WEBSOCKET UPDATE MODELS
# ============================================================================


class LighterWebSocketOrderUpdate(BaseModel):
    """Lighter WebSocket order update from account_all_orders channel.

    CRITICAL: Lighter WebSocket uses DIFFERENT field names from REST API:
    - price (not limit_price)
    - initial_base_amount (not amount)
    - filled_base_amount (not filled_amount)
    - is_ask (not is_buy) - inverted!
    - market_index (not market_id)

    Actual WebSocket format:
    {
        "order_index": 562951041666264,
        "client_order_index": 40757949625456,
        "market_index": 1,
        "is_ask": true,
        "price": "91354.3",
        "initial_base_amount": "0.00219",
        "filled_base_amount": "0.00219",
        "remaining_base_amount": "0.00000",
        "status": "filled",
        "time_in_force": "good-till-time",
        "timestamp": 1767568015
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    # Primary fields (actual WebSocket format)
    order_index: Optional[int] = Field(None, description="Order index (exchange ID)")
    index: Optional[int] = Field(None, description="Alternative order index")
    market_index: Optional[int] = Field(None, description="Market index (WebSocket format)")
    market_id: int = Field(default=0, description="Market ID (fallback)")
    is_ask: Optional[bool] = Field(None, description="True=SELL, False=BUY (WebSocket)")
    is_buy: Optional[bool] = Field(None, description="True=BUY, False=SELL (fallback)")
    price: Optional[str] = Field(None, description="Price (WebSocket format)")
    limit_price: str = Field(default="0", description="Limit price (fallback)")
    initial_base_amount: Optional[str] = Field(None, description="Order amount (WebSocket)")
    amount: str = Field(default="0", description="Order amount (fallback)")
    filled_base_amount: Optional[str] = Field(None, description="Filled amount (WebSocket)")
    filled_amount: str = Field(default="0", description="Filled amount (fallback)")
    filled_quote_amount: Optional[str] = Field(None, description="Filled quote amount (for avg price calc)")
    remaining_base_amount: Optional[str] = Field(None, description="Remaining amount")
    status: str = Field(default="", description="Order status")
    time_in_force: Optional[str] = Field(None, description="TIF as string or int")
    client_order_index: Optional[int] = Field(None, description="Client order index")
    timestamp: Optional[int] = Field(None, description="Update timestamp")

    def get_order_index(self) -> int:
        """Get order index."""
        return self.order_index or self.index or 0

    def get_market_id(self) -> int:
        """Get market ID from either field."""
        return self.market_index or self.market_id or 0

    @property
    def is_buy_order(self) -> bool:
        """Get if order is buy (handles is_ask inversion)."""
        if self.is_ask is not None:
            return not self.is_ask  # is_ask=True means SELL
        return self.is_buy if self.is_buy is not None else True

    def get_price_decimal(self) -> Decimal:
        """Get limit price as Decimal (handles both formats)."""
        raw = self.price or self.limit_price or "0"
        return Decimal(raw) if raw else Decimal("0")

    def get_amount_decimal(self) -> Decimal:
        """Get order amount as Decimal (handles both formats)."""
        raw = self.initial_base_amount or self.amount or "0"
        return Decimal(raw) if raw else Decimal("0")

    def get_filled_amount_decimal(self) -> Decimal:
        """Get filled amount as Decimal (handles both formats)."""
        raw = self.filled_base_amount or self.filled_amount or "0"
        return Decimal(raw) if raw else Decimal("0")

    def get_filled_quote_amount_decimal(self) -> Decimal:
        """Get filled quote amount as Decimal."""
        if self.filled_quote_amount:
            return Decimal(self.filled_quote_amount)
        return Decimal("0")

    def get_avg_price_decimal(self) -> Decimal:
        """Calculate average execution price from filled amounts.

        avg_price = filled_quote_amount / filled_base_amount

        This gives us the ACTUAL executed price, not the limit price sent.
        Critical for accurate spread/PnL calculations.

        Returns:
            Average fill price, or Decimal("0") if no fills or missing data
        """
        filled_base = self.get_filled_amount_decimal()
        filled_quote = self.get_filled_quote_amount_decimal()

        if filled_base > 0 and filled_quote > 0:
            return filled_quote / filled_base
        return Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_open(self) -> bool:
        """Check if order is open."""
        return self.status.lower() in ("open", "new", "")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return "filled" in self.status.lower() and "partial" not in self.status.lower()


class LighterWebSocketPositionUpdate(BaseModel):
    """Lighter WebSocket position update from account_all channel.

    Format:
    {
        "market_id": 0,
        "size": "0.5",
        "entry_price": "50000.0",
        "mark_price": "50500.0",
        "unrealized_pnl": "250.0"
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    market_id: int = Field(default=0, description="Market ID")
    size: str = Field(default="0", description="Position size (signed)")
    entry_price: str = Field(default="0", description="Entry price")
    mark_price: str = Field(default="0", description="Mark price")
    unrealized_pnl: str = Field(default="0", description="Unrealized PnL")
    liquidation_price: str = Field(default="0", description="Liquidation price")

    def get_size_decimal(self) -> Decimal:
        """Get position size as Decimal."""
        return Decimal(self.size) if self.size else Decimal("0")

    def get_entry_price_decimal(self) -> Decimal:
        """Get entry price as Decimal."""
        return Decimal(self.entry_price) if self.entry_price else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_position(self) -> bool:
        """Check if there is an active position."""
        return self.get_size_decimal() != 0


class LighterWebSocketBalanceUpdate(BaseModel):
    """Lighter WebSocket balance update from account_all channel.

    Format:
    {
        "free": "10000.0",
        "locked": "2500.0",
        "total": "12500.0"
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    free: str = Field(default="0", description="Available balance")
    locked: str = Field(default="0", description="Locked balance")
    total: str = Field(default="0", description="Total balance")

    def get_free_decimal(self) -> Decimal:
        """Get free balance as Decimal."""
        return Decimal(self.free) if self.free else Decimal("0")

    def get_locked_decimal(self) -> Decimal:
        """Get locked balance as Decimal."""
        return Decimal(self.locked) if self.locked else Decimal("0")

    def get_total_decimal(self) -> Decimal:
        """Get total balance as Decimal."""
        if self.total and self.total != "0":
            return Decimal(self.total)
        return self.get_free_decimal() + self.get_locked_decimal()


class LighterAccountUpdate(BaseModel):
    """Lighter WebSocket account update combining balance and positions.

    From account_all channel:
    {
        "channel": "account_all:123",
        "balance": {...},
        "positions": [...],
        ...
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    channel: str = Field(default="", description="WebSocket channel")
    balance: Optional[Dict[str, Any]] = Field(None, description="Balance update")
    usdc_balance: Optional[Dict[str, Any]] = Field(None, description="Alternative balance")
    positions: Optional[List[Dict[str, Any]]] = Field(None, description="Position updates")
    active_positions: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative positions")

    def get_balance(self) -> Optional[LighterWebSocketBalanceUpdate]:
        """Get parsed balance update."""
        raw = self.balance or self.usdc_balance
        if raw and isinstance(raw, dict):
            return LighterWebSocketBalanceUpdate.model_validate(raw)
        return None

    def get_positions(self) -> List[LighterWebSocketPositionUpdate]:
        """Get parsed position updates."""
        raw_list = self.positions or self.active_positions or []

        if isinstance(raw_list, dict):
            raw_list = list(raw_list.values())

        positions = []
        for raw in raw_list:
            try:
                pos = LighterWebSocketPositionUpdate.model_validate(raw)
                positions.append(pos)
            except Exception:
                continue

        return positions

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_balance(self) -> bool:
        """Check if update contains balance."""
        return self.balance is not None or self.usdc_balance is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_positions(self) -> bool:
        """Check if update contains positions."""
        return bool(self.positions or self.active_positions)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_position_update(self) -> bool:
        """Check if this is a position update message."""
        return self.channel.startswith("account_all:") and self.has_positions

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_balance_update(self) -> bool:
        """Check if this is a balance update message."""
        return self.channel.startswith("account_all:") and self.has_balance
