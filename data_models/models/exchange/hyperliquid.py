"""
Hyperliquid API response models and type definitions.

This module provides type safety and clear data structures for Hyperliquid gateway,
following the same Pydantic pattern as Bybit exchange implementation.

Architecture:
- Typed Pydantic models for all API responses
- Computed fields for common calculations
- Response envelope types for unwrapping API responses

CRITICAL: Hyperliquid uses THREE distinct order ID formats that must NEVER be confused:
1. internal_id: Our tracking ID (e.g., B4512RGUf7121547)
2. hex_cloid: Hex-encoded client order ID for Hyperliquid API (e.g., 0x00000000000000000000019a5ba95db4)
3. oid: Exchange-assigned order ID (e.g., 225674155175)
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

T = TypeVar("T")


class HyperliquidOrderIdentifiers(BaseModel):
    """
    Hyperliquid order identifiers with strict validation.

    This model ensures we ALWAYS know which ID format we're dealing with.
    Each field has format validation to catch bugs at runtime.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    internal_id: str = Field(..., description="Internal tracking ID (B4512RGU... format, never starts with 0x)")
    hex_cloid: str = Field(..., description="Hex client order ID (0x... format, exactly 34 chars = 16 bytes)")
    oid: Optional[str] = Field(None, description="Exchange order ID (numeric string)")

    @field_validator("hex_cloid")
    @classmethod
    def validate_hex_cloid(cls, v: str) -> str:
        """Validate hex_cloid format: must be 0x followed by 32 hex characters (16 bytes per Hyperliquid SDK spec)."""
        if not v.startswith("0x"):
            raise ValueError(f"hex_cloid must start with 0x, got: {v}")
        if len(v) != 34:
            raise ValueError(f"hex_cloid must be exactly 34 characters (0x + 32 hex = 16 bytes), got length {len(v)}: {v}")
        # Validate hex characters
        try:
            int(v, 16)
        except ValueError:
            raise ValueError(f"hex_cloid must contain valid hex characters, got: {v}") from None
        return v

    @field_validator("internal_id")
    @classmethod
    def validate_internal_id(cls, v: str) -> str:
        """Validate internal_id format: must NOT start with 0x (that's hex_cloid format)."""
        if v.startswith("0x"):
            raise ValueError(f"internal_id cannot be hex format (that's hex_cloid), got: {v}")
        if not v:
            raise ValueError("internal_id cannot be empty")
        return v

    @field_validator("oid")
    @classmethod
    def validate_oid(cls, v: Optional[str]) -> Optional[str]:
        """Validate oid format: must be numeric string if present."""
        if v is not None and v != "":
            try:
                int(v)  # Should be parseable as integer
            except ValueError:
                raise ValueError(f"oid must be numeric string, got: {v}") from None
        return v


class HyperliquidIDConverter:
    """
    Helper class for safe ID conversions with validation.

    Provides static methods to convert between ID formats using mapping cache.
    All conversions include format validation to catch bugs immediately.
    """

    @staticmethod
    def to_hex_cloid(internal_id: str, mapping_cache: Any) -> str:
        """
        Convert internal_id to hex_cloid using mapping cache.

        Args:
            internal_id: Internal tracking ID (B4512RGU... format)
            mapping_cache: OrderIDMappingCache for resolution

        Returns:
            hex_cloid: Hex client order ID (0x... format)

        Raises:
            ValueError: If mapping not found or hex_cloid format invalid
        """
        # Already hex? Return as-is (but validate)
        if internal_id.startswith("0x"):
            if len(internal_id) != 66:
                raise ValueError(f"Invalid hex_cloid length: {len(internal_id)} (expected 66)")
            return internal_id

        # Resolve via mapping cache
        mapping = mapping_cache.get_by_client_id(internal_id)
        if not mapping or not mapping.exchange_client_id:
            raise ValueError(
                f"No hex_cloid mapping found for internal_id={internal_id}. "
                "Mapping MUST be stored when order is created. "
                "This indicates either: "
                "1. Order was never created (internal_id invalid), OR "
                "2. Mapping storage failed during order creation, OR "
                "3. Mapping was evicted from cache (LRU eviction)"
            )

        hex_cloid = cast(str, mapping.exchange_client_id)

        # Validate hex_cloid format (Hyperliquid SDK spec: 0x + 32 hex chars = 34 total)
        if not hex_cloid.startswith("0x") or len(hex_cloid) != 34:
            raise ValueError(
                f"Invalid hex_cloid in mapping for {internal_id}: {hex_cloid}. "
                "hex_cloid must be 0x + 32 hex characters (34 total, 16 bytes per Hyperliquid SDK)."
            )

        return hex_cloid

    @staticmethod
    def to_internal_id(hex_cloid: str, mapping_cache: Any) -> str:
        """
        Convert hex_cloid to internal_id using mapping cache (reverse lookup).

        Args:
            hex_cloid: Hex client order ID (0x... format)
            mapping_cache: OrderIDMappingCache for resolution

        Returns:
            internal_id: Internal tracking ID (B4512RGU... format)

        Raises:
            ValueError: If mapping not found or internal_id format invalid
        """
        # Validate input format
        if not hex_cloid.startswith("0x") or len(hex_cloid) != 66:
            raise ValueError(f"Invalid hex_cloid format: {hex_cloid} (must be 0x + 64 hex)")

        # Resolve via mapping cache
        mapping = mapping_cache.get_by_exchange_client_id(hex_cloid)
        if not mapping or not mapping.client_id:
            raise ValueError(
                f"No internal_id mapping found for hex_cloid={hex_cloid}. "
                "This indicates the order came from outside our system or mapping was lost."
            )

        internal_id = cast(str, mapping.client_id)

        # Validate internal_id format
        if internal_id.startswith("0x"):
            raise ValueError(f"Corrupted mapping: internal_id has hex format: {internal_id}")

        return internal_id

    @staticmethod
    def validate_for_cancellation(order_id: str, mapping_cache: Any) -> str:
        """
        Validate and convert order_id to hex_cloid for cancellation.

        Hyperliquid REQUIRES hex_cloid for cancellation - this method ensures
        we ALWAYS send the correct format.

        Args:
            order_id: Either internal_id or hex_cloid
            mapping_cache: OrderIDMappingCache for resolution

        Returns:
            hex_cloid: Validated hex client order ID ready for Hyperliquid API

        Raises:
            ValueError: If conversion fails or format invalid
        """
        if order_id.startswith("0x"):
            # Already hex_cloid - validate format
            if len(order_id) != 66:
                raise ValueError(f"Invalid hex_cloid length: {len(order_id)} (expected 66)")
            return order_id
        else:
            # Internal ID - convert to hex_cloid
            return HyperliquidIDConverter.to_hex_cloid(order_id, mapping_cache)


# ============================================================================
# ORDER RESPONSE MODELS
# ============================================================================


class HyperliquidRestingOrderStatus(BaseModel):
    """Hyperliquid resting order status (order is live on book).

    Response format:
    {
        "resting": {
            "oid": 225674155175,
            "cloid": "0x00000000000000000000019a5ba95db4"
        }
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    oid: Optional[int] = Field(None, description="Exchange order ID")
    cloid: Optional[str] = Field(None, description="Client order ID (hex format)")

    def get_order_id(self) -> str:
        """Get order ID as string."""
        return str(self.oid) if self.oid is not None else ""

    def get_client_id(self) -> str:
        """Get client order ID."""
        return self.cloid or ""


class HyperliquidFilledOrderStatus(BaseModel):
    """Hyperliquid filled order status.

    Response format:
    {
        "filled": {
            "oid": 225674155175,
            "totalSz": "0.01",
            "avgPx": "50000.0"
        }
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    oid: Optional[int] = Field(None, description="Exchange order ID")
    totalSz: str = Field(default="0", description="Total filled size")
    avgPx: str = Field(default="0", description="Average fill price")
    cloid: Optional[str] = Field(None, description="Client order ID")

    def get_order_id(self) -> str:
        """Get order ID as string."""
        return str(self.oid) if self.oid is not None else ""

    def get_filled_qty_decimal(self) -> Decimal:
        """Get filled quantity as Decimal."""
        return Decimal(self.totalSz) if self.totalSz else Decimal("0")

    def get_avg_price_decimal(self) -> Decimal:
        """Get average price as Decimal."""
        return Decimal(self.avgPx) if self.avgPx else Decimal("0")


class HyperliquidOrderStatusResponse(BaseModel):
    """Hyperliquid order status wrapper.

    Handles multiple status formats:
    - {"resting": {...}}  - Order is live on book
    - {"filled": {...}}   - Order is fully filled
    - {"error": "..."}    - Order failed

    Pattern: Provides type-safe access to order status.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    resting: Optional[HyperliquidRestingOrderStatus] = Field(None, description="Resting order info")
    filled: Optional[HyperliquidFilledOrderStatus] = Field(None, description="Filled order info")
    error: Optional[str] = Field(None, description="Error message if order failed")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_resting(self) -> bool:
        """Check if order is resting (live on book)."""
        return self.resting is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is filled."""
        return self.filled is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_error(self) -> bool:
        """Check if order failed with error."""
        return self.error is not None

    def get_order_id(self) -> str:
        """Get order ID from whichever status is present."""
        if self.resting:
            return self.resting.get_order_id()
        elif self.filled:
            return self.filled.get_order_id()
        return ""

    def get_client_id(self) -> str:
        """Get client order ID from whichever status is present."""
        if self.resting:
            return self.resting.get_client_id()
        elif self.filled:
            return self.filled.cloid or ""
        return ""


class HyperliquidOrderResponseData(BaseModel):
    """Hyperliquid order response data wrapper.

    Response format from SDK:
    {
        "statuses": [
            {"resting": {"oid": 123, "cloid": "0x..."}}
        ]
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    statuses: List[HyperliquidOrderStatusResponse] = Field(default_factory=list, description="Order status list")

    def get_first_status(self) -> Optional[HyperliquidOrderStatusResponse]:
        """Get first order status."""
        return self.statuses[0] if self.statuses else None

    def get_order_id(self) -> str:
        """Get order ID from first status."""
        first = self.get_first_status()
        return first.get_order_id() if first else ""

    def has_error(self) -> bool:
        """Check if any status contains an error."""
        return any(s.is_error for s in self.statuses)

    def get_error_message(self) -> Optional[str]:
        """Get error message if present."""
        for s in self.statuses:
            if s.is_error:
                return s.error
        return None


class HyperliquidOrderResponse(BaseModel):
    """Hyperliquid order creation/action response.

    Full response format:
    {
        "response": {
            "type": "order",
            "data": {
                "statuses": [...]
            }
        },
        "status": "ok"
    }

    Pattern: Provides envelope unwrapping and type-safe data access.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    status: str = Field(default="", description="Response status (ok/error)")
    response: Optional[Dict[str, Any]] = Field(None, description="Response envelope")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.status == "ok"

    def get_data(self) -> Optional[HyperliquidOrderResponseData]:
        """Extract and parse order data."""
        if not self.response:
            return None
        data = self.response.get("data", {})
        if isinstance(data, dict):
            return HyperliquidOrderResponseData.model_validate(data)
        return None

    def get_order_id(self) -> str:
        """Get order ID from response."""
        data = self.get_data()
        return data.get_order_id() if data else ""

    def get_error_message(self) -> Optional[str]:
        """Get error message if present."""
        data = self.get_data()
        if data:
            return data.get_error_message()
        return None


# ============================================================================
# POSITION RESPONSE MODELS
# ============================================================================


class HyperliquidPositionInfo(BaseModel):
    """Hyperliquid position info from assetPositions.

    Position format:
    {
        "coin": "BTC",
        "szi": "0.5",
        "entryPx": "50000.0",
        "unrealizedPnl": "500.0",
        "marginUsed": "2500.0",
        "liquidationPx": "45000.0"
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    coin: str = Field(..., description="Asset symbol (e.g., BTC)")
    szi: str = Field(default="0", description="Position size (signed: positive=long, negative=short)")
    entryPx: Optional[str] = Field(None, description="Entry price")
    unrealizedPnl: str = Field(default="0", description="Unrealized PnL")
    marginUsed: str = Field(default="0", description="Margin used for position")
    liquidationPx: Optional[str] = Field(None, description="Liquidation price")
    positionValue: Optional[str] = Field(None, description="Position notional value")
    returnOnEquity: Optional[str] = Field(None, description="Return on equity")
    maxTradeSzs: Optional[List[str]] = Field(None, description="Maximum trade sizes")

    def get_size_decimal(self) -> Decimal:
        """Get position size as Decimal (signed)."""
        return Decimal(self.szi) if self.szi else Decimal("0")

    def get_entry_price_decimal(self) -> Decimal:
        """Get entry price as Decimal."""
        return Decimal(self.entryPx) if self.entryPx else Decimal("0")

    def get_unrealized_pnl_decimal(self) -> Decimal:
        """Get unrealized PnL as Decimal."""
        return Decimal(self.unrealizedPnl) if self.unrealizedPnl else Decimal("0")

    def get_margin_used_decimal(self) -> Decimal:
        """Get margin used as Decimal."""
        return Decimal(self.marginUsed) if self.marginUsed else Decimal("0")

    def get_liquidation_price_decimal(self) -> Optional[Decimal]:
        """Get liquidation price as Decimal (None if not set)."""
        return Decimal(self.liquidationPx) if self.liquidationPx else None

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


class HyperliquidAssetPosition(BaseModel):
    """Hyperliquid asset position wrapper.

    Format from SDK:
    {
        "position": {
            "coin": "BTC",
            "szi": "0.5",
            ...
        }
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    position: HyperliquidPositionInfo = Field(..., description="Position details")


# ============================================================================
# BALANCE/MARGIN RESPONSE MODELS
# ============================================================================


class HyperliquidMarginSummary(BaseModel):
    """Hyperliquid margin summary from user state.

    Format:
    {
        "accountValue": "10000.0",
        "totalMarginUsed": "2500.0",
        "withdrawable": "7500.0",
        "totalRawUsd": "10000.0"
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    accountValue: str = Field(default="0", description="Total account value (equity)")
    totalMarginUsed: str = Field(default="0", description="Total margin used by positions")
    withdrawable: str = Field(default="0", description="Available for withdrawal")
    totalRawUsd: Optional[str] = Field(None, description="Total raw USD value")
    totalNtlPos: Optional[str] = Field(None, description="Total notional position")

    def get_account_value_decimal(self) -> Decimal:
        """Get account value as Decimal."""
        return Decimal(self.accountValue) if self.accountValue else Decimal("0")

    def get_margin_used_decimal(self) -> Decimal:
        """Get total margin used as Decimal."""
        return Decimal(self.totalMarginUsed) if self.totalMarginUsed else Decimal("0")

    def get_withdrawable_decimal(self) -> Decimal:
        """Get withdrawable amount as Decimal."""
        return Decimal(self.withdrawable) if self.withdrawable else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def free_balance(self) -> Decimal:
        """Get free balance (withdrawable)."""
        return self.get_withdrawable_decimal()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def locked_balance(self) -> Decimal:
        """Get locked balance (in positions/margin)."""
        return self.get_account_value_decimal() - self.get_withdrawable_decimal()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def margin_ratio(self) -> Decimal:
        """Calculate margin ratio (margin used / account value)."""
        account_value = self.get_account_value_decimal()
        if account_value > 0:
            return self.get_margin_used_decimal() / account_value
        return Decimal("0")


class HyperliquidUserState(BaseModel):
    """Hyperliquid user state response (positions + balances).

    Full format from SDK user_state():
    {
        "assetPositions": [
            {"position": {...}},
            ...
        ],
        "marginSummary": {
            "accountValue": "10000.0",
            ...
        }
    }

    Pattern: Provides type-safe access to positions and balances.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    assetPositions: List[HyperliquidAssetPosition] = Field(default_factory=list, description="List of positions")
    marginSummary: HyperliquidMarginSummary = Field(
        default_factory=HyperliquidMarginSummary, description="Margin/balance summary"
    )
    crossMarginSummary: Optional[Dict[str, Any]] = Field(None, description="Cross margin info")
    withdrawable: Optional[str] = Field(None, description="Withdrawable amount")

    def get_positions(self) -> List[HyperliquidPositionInfo]:
        """Get list of position info objects."""
        return [ap.position for ap in self.assetPositions]

    def get_position_for_coin(self, coin: str) -> Optional[HyperliquidPositionInfo]:
        """Get position for specific coin."""
        for ap in self.assetPositions:
            if ap.position.coin.upper() == coin.upper():
                return ap.position
        return None

    def get_active_positions(self) -> List[HyperliquidPositionInfo]:
        """Get only positions with non-zero size."""
        return [ap.position for ap in self.assetPositions if ap.position.has_position]


# ============================================================================
# WEBSOCKET UPDATE MODELS
# ============================================================================


class HyperliquidWebSocketOrderUpdate(BaseModel):
    """Hyperliquid WebSocket order update.

    Format:
    {
        "oid": 123,
        "coin": "BTC",
        "side": "B",
        "origSz": "0.01",
        "sz": "0.005",
        "limitPx": "50000.0",
        "cloid": "0x...",
        "timestamp": 1234567890
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    oid: int = Field(..., description="Exchange order ID")
    coin: str = Field(..., description="Asset symbol")
    side: str = Field(..., description="Order side: B=Buy, A=Ask/Sell")
    origSz: str = Field(default="0", description="Original order size")
    sz: str = Field(default="0", description="Remaining size")
    limitPx: Optional[str] = Field(None, description="Limit price")
    cloid: Optional[str] = Field(None, description="Client order ID (hex)")
    timestamp: Optional[int] = Field(None, description="Update timestamp")
    tif: Optional[str] = Field(None, description="Time in force: Gtc, Alo, Ioc")

    def get_order_id(self) -> str:
        """Get order ID as string."""
        return str(self.oid)

    def get_original_size_decimal(self) -> Decimal:
        """Get original size as Decimal."""
        return Decimal(self.origSz) if self.origSz else Decimal("0")

    def get_remaining_size_decimal(self) -> Decimal:
        """Get remaining size as Decimal."""
        return Decimal(self.sz) if self.sz else Decimal("0")

    def get_filled_size_decimal(self) -> Decimal:
        """Get filled size as Decimal."""
        return self.get_original_size_decimal() - self.get_remaining_size_decimal()

    def get_price_decimal(self) -> Decimal:
        """Get limit price as Decimal."""
        return Decimal(self.limitPx) if self.limitPx else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_buy(self) -> bool:
        """Check if buy order."""
        return self.side == "B"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.get_remaining_size_decimal() == 0 and self.get_original_size_decimal() > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        remaining = self.get_remaining_size_decimal()
        original = self.get_original_size_decimal()
        return Decimal("0") < remaining < original

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_post_only(self) -> bool:
        """Check if order is post-only (maker)."""
        return self.tif == "Alo"


class HyperliquidFillUpdate(BaseModel):
    """Hyperliquid fill/execution update.

    Format from userEvents fills:
    {
        "oid": 123,
        "coin": "BTC",
        "side": "B",
        "px": "50000.0",
        "sz": "0.001",
        "time": 1234567890000,
        "tid": 456,
        "fee": "0.05",
        "dir": "Open Long"
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    oid: int = Field(..., description="Order ID")
    coin: str = Field(..., description="Asset symbol")
    side: str = Field(..., description="Trade side: B=Buy, A=Ask/Sell")
    px: str = Field(..., description="Execution price")
    sz: str = Field(..., description="Execution size")
    time: int = Field(..., description="Execution timestamp (ms)")
    tid: Optional[int] = Field(None, description="Trade ID")
    fee: str = Field(default="0", description="Trade fee")
    dir: Optional[str] = Field(None, description="Direction: Open Long, Open Short, Close Long, etc.")
    hash: Optional[str] = Field(None, description="Transaction hash")
    crossed: Optional[bool] = Field(None, description="Whether order crossed the spread")

    def get_order_id(self) -> str:
        """Get order ID as string."""
        return str(self.oid)

    def get_trade_id(self) -> str:
        """Get trade ID as string."""
        return str(self.tid) if self.tid else ""

    def get_price_decimal(self) -> Decimal:
        """Get execution price as Decimal."""
        return Decimal(self.px) if self.px else Decimal("0")

    def get_size_decimal(self) -> Decimal:
        """Get execution size as Decimal."""
        return Decimal(self.sz) if self.sz else Decimal("0")

    def get_fee_decimal(self) -> Decimal:
        """Get fee as Decimal."""
        return Decimal(self.fee) if self.fee else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_buy(self) -> bool:
        """Check if buy trade."""
        return self.side == "B"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_maker(self) -> bool:
        """Check if this was a maker trade (provided liquidity)."""
        return self.crossed is False if self.crossed is not None else False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_opening(self) -> bool:
        """Check if this is an opening trade."""
        return self.dir is not None and "Open" in self.dir


class HyperliquidWebSocketPositionUpdate(BaseModel):
    """Hyperliquid WebSocket position update.

    From userEvents:
    {
        "coin": "BTC",
        "szi": "0.5",
        "entryPx": "50000.0",
        ...
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    coin: str = Field(..., description="Asset symbol")
    szi: str = Field(default="0", description="Position size (signed)")
    entryPx: Optional[str] = Field(None, description="Entry price")
    unrealizedPnl: str = Field(default="0", description="Unrealized PnL")
    marginUsed: str = Field(default="0", description="Margin used")
    liquidationPx: Optional[str] = Field(None, description="Liquidation price")

    def get_size_decimal(self) -> Decimal:
        """Get position size as Decimal."""
        return Decimal(self.szi) if self.szi else Decimal("0")

    def get_entry_price_decimal(self) -> Decimal:
        """Get entry price as Decimal."""
        return Decimal(self.entryPx) if self.entryPx else Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_position(self) -> bool:
        """Check if there is an active position."""
        return self.get_size_decimal() != 0


class HyperliquidUserEventsUpdate(BaseModel):
    """Hyperliquid userEvents WebSocket update.

    Format:
    {
        "fills": [...],
        "positions": [...],
        "funding": [...]
    }
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    fills: List[HyperliquidFillUpdate] = Field(default_factory=list, description="Fill updates")
    positions: List[HyperliquidWebSocketPositionUpdate] = Field(default_factory=list, description="Position updates")
    funding: Optional[List[Dict[str, Any]]] = Field(None, description="Funding updates")

    def has_fills(self) -> bool:
        """Check if update contains fills."""
        return len(self.fills) > 0

    def has_positions(self) -> bool:
        """Check if update contains position changes."""
        return len(self.positions) > 0

    def get_fills_for_order(self, order_id: str) -> List[HyperliquidFillUpdate]:
        """Get fills for specific order ID."""
        return [f for f in self.fills if f.get_order_id() == order_id]
