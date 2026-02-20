"""
Ripio Trade API Response Models

Typed models for Ripio Trade API responses to replace Dict[str, Any] usage.
These models provide type safety and better IDE support.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

# Generic type variable for envelope payloads
T = TypeVar("T")


class RipioOrderResponse(BaseModel):
    """
    Ripio Trade order response model.

    Used for both REST order creation responses and order query responses.
    """

    # Use extra="ignore" - WebSocket order updates may contain undocumented fields
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str = Field(..., description="Order ID assigned by exchange")
    pair: str = Field(..., description="Trading pair (e.g., 'BTC_USDC')")
    side: str = Field(..., description="Order side: 'buy' or 'sell'")
    status: str = Field(
        ...,
        description="Order status: pending, open, partially_filled, filled, cancelled, rejected, expired",
    )

    @field_validator("id", "pair", "side", "status", mode="before")
    @classmethod
    def convert_str_fields(cls, v: Any) -> str:
        """Convert fields to string (WebSocket may send integers for id)."""
        if v is None:
            return ""
        return str(v)

    type: Optional[str] = Field(None, description="Order type: 'limit' or 'market' (not in creation response)")
    price: Optional[str] = Field(None, description="Order price (not in creation response)")
    amount: Optional[str] = Field(None, description="Requested order amount (use requested_amount instead)")
    filled: Optional[str] = Field(None, description="Amount already filled (use executed_amount instead)")
    external_id: Optional[str] = Field(None, description="Client-provided order ID")
    post_only: Optional[bool] = Field(None, description="Post-only order flag")
    fill_or_kill: Optional[bool] = Field(None, description="Fill-or-kill order flag")
    tax_amount: Optional[Union[str, int, float]] = Field(None, description="Tax amount for the order")
    fee: Optional[Union[str, int, float]] = Field(None, description="Trading fee for the order")
    total_value: Optional[Union[str, int, float]] = Field(None, description="Total value of the order")
    update_date: Optional[str] = Field(None, description="ISO format update timestamp (alternative to updated_at)")
    triggered: Optional[bool] = Field(None, description="Whether stop order has been triggered")
    distance: Optional[Union[str, int, float]] = Field(None, description="Distance for stop orders")
    stop_limit_price: Optional[Union[str, int, float]] = Field(None, description="Stop limit price")
    transactions: Optional[List[Dict[str, Any]]] = Field(None, description="List of order transactions")
    created_at: Optional[str] = Field(None, description="ISO format creation timestamp")
    updated_at: Optional[str] = Field(None, description="ISO format update timestamp")
    average_price: Optional[str] = Field(None, description="Average fill price")
    average_execution_price: Optional[str] = Field(None, description="Average execution price for partial fills")

    @field_validator("price", "amount", "filled", "average_price", "average_execution_price", mode="before")
    @classmethod
    def convert_numeric_to_str(cls, v: Any) -> Optional[str]:
        """Convert numeric values to strings (WebSocket may send floats/ints)."""
        if v is None:
            return None
        return str(v)

    requested_amount: Optional[Union[str, int, float]] = Field(None, description="Original requested amount")
    requested_value: Optional[Union[str, int, float]] = Field(None, description="Original requested value")
    executed_amount: Optional[Union[str, int, float]] = Field(None, description="Total executed amount")
    executed_value: Optional[Union[str, int, float]] = Field(None, description="Total executed value")
    create_date: Optional[Union[int, str]] = Field(None, description="Unix timestamp or ISO date string")
    remaining_amount: Optional[Union[str, int, float]] = Field(
        None, description="Remaining amount to be filled (from API response)"
    )
    remaining_value: Optional[Union[str, int, float]] = Field(
        None, description="Remaining value to be filled (from API response)"
    )

    @field_validator(
        "remaining_amount",
        "remaining_value",
        "requested_amount",
        "requested_value",
        "executed_amount",
        "executed_value",
        mode="before",
    )
    @classmethod
    def convert_to_string(cls, v: Any) -> Optional[str]:
        """Convert numeric values to strings."""
        if v is None:
            return None
        return str(v)

    @computed_field
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "filled"

    @computed_field
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in ["pending", "open", "partially_filled"]

    @computed_field
    def calculated_remaining(self) -> float:
        """Calculate remaining unfilled amount from amount and filled."""
        if self.amount is None:
            raise ValueError("Cannot calculate remaining amount: 'amount' field is None")
        total = float(self.amount)
        filled = float(self.filled) if self.filled else 0.0
        return max(0.0, total - filled)

    def get_timestamp(self) -> int:
        """Get timestamp in milliseconds, handling multiple formats."""
        # Check if create_date exists
        if self.create_date:
            # If it's already an int, return it
            if isinstance(self.create_date, int):
                return self.create_date
            # If it's a string, try to parse it
            if isinstance(self.create_date, str):
                # First check if it's a string representation of an int
                if self.create_date.isdigit():
                    return int(self.create_date)
                # It's an ISO date string, parse it
                try:
                    dt = datetime.fromisoformat(self.create_date.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except Exception:
                    pass

        # Parse ISO format created_at
        if self.created_at:
            try:
                dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except Exception:
                pass

        return 0


class RipioOrderbookEntry(BaseModel):
    """Single orderbook level for Ripio Trade."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    price: float = Field(..., description="Price level")
    amount: float = Field(..., description="Amount at this level")

    @classmethod
    def from_list(cls, entry: List[Union[str, float]]) -> "RipioOrderbookEntry":
        """Create from list format [price, amount]."""
        return cls(price=float(entry[0]), amount=float(entry[1]))


class RipioOrderbookResponse(BaseModel):
    """
    Ripio Trade orderbook response.

    Used for both REST and WebSocket orderbook data.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    asks: List[List[Union[str, float]]] = Field(..., description="List of [price, amount] ask levels")
    bids: List[List[Union[str, float]]] = Field(..., description="List of [price, amount] bid levels")
    pair: Optional[str] = Field(None, description="Trading pair (for WebSocket)")
    timestamp: Optional[int] = Field(None, description="Timestamp in milliseconds")

    def get_bid_entries(self) -> List[RipioOrderbookEntry]:
        """Convert bid lists to typed entries."""
        return [RipioOrderbookEntry.from_list(bid) for bid in self.bids]

    def get_ask_entries(self) -> List[RipioOrderbookEntry]:
        """Convert ask lists to typed entries."""
        return [RipioOrderbookEntry.from_list(ask) for ask in self.asks]

    @computed_field
    def best_bid(self) -> Optional[RipioOrderbookEntry]:
        """Get best (highest) bid."""
        if self.bids:
            return RipioOrderbookEntry.from_list(self.bids[0])
        return None

    @computed_field
    def best_ask(self) -> Optional[RipioOrderbookEntry]:
        """Get best (lowest) ask."""
        if self.asks:
            return RipioOrderbookEntry.from_list(self.asks[0])
        return None


class RipioBalance(BaseModel):
    """Account balance for a single currency."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    currency: str = Field(..., description="Currency code (e.g., 'BTC', 'USDC')")
    available: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Balance locked in orders")
    total: str = Field(..., description="Total balance")

    @computed_field
    def available_float(self) -> float:
        """Get available balance as float."""
        return float(self.available)

    @computed_field
    def locked_float(self) -> float:
        """Get locked balance as float."""
        return float(self.locked)

    @computed_field
    def total_float(self) -> float:
        """Get total balance as float."""
        return float(self.total)


class RipioAccountResponse(BaseModel):
    """
    Ripio Trade account/balance response.

    Used for REST /accounts endpoint.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    balances: List[Dict[str, Any]] = Field(..., description="Raw balance data")

    def get_balances(self) -> List[RipioBalance]:
        """Get typed balance objects."""
        return [
            RipioBalance(
                currency=bal["currency"],
                available=bal["available"],
                locked=bal["locked"],
                total=bal["total"],
            )
            for bal in self.balances
        ]

    def get_balance(self, currency: str) -> Optional[RipioBalance]:
        """Get balance for specific currency."""
        for bal in self.balances:
            if bal["currency"] == currency:
                return RipioBalance(
                    currency=bal["currency"],
                    available=bal["available"],
                    locked=bal["locked"],
                    total=bal["total"],
                )
        return None


class RipioTicket(BaseModel):
    """Authentication ticket response."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ticket: str = Field(..., description="Authentication ticket string")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")

    @computed_field
    def is_expired(self) -> bool:
        """Check if ticket is expired."""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(expires.tzinfo) > expires
        except Exception:
            return False


class RipioAuthResponse(BaseModel):
    """Authentication response containing ticket."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    data: Dict[str, Any] = Field(..., description="Contains ticket information")

    def get_ticket(self) -> RipioTicket:
        """Extract ticket from response."""
        return RipioTicket(
            ticket=self.data["ticket"],
            expires_at=self.data.get("expires_at"),
            ttl=self.data.get("ttl"),
        )


# WebSocket Message Models


class RipioWebSocketOrderUpdate(BaseModel):
    """
    WebSocket order status update.

    Event type 'order_status' from user data stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: str = Field(..., description="Event type: 'order_status'")
    data: Dict[str, Any] = Field(..., description="Order data (same format as REST response)")

    def to_order_response(self) -> RipioOrderResponse:
        """Convert to order response model."""
        return RipioOrderResponse(**self.data)


class RipioWebSocketOrderbook(BaseModel):
    """
    WebSocket orderbook update.

    Event type 'orderbook' from market data stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: str = Field(..., description="Event type: 'orderbook'")
    data: Dict[str, Any] = Field(..., description="Orderbook data")

    def to_orderbook_response(self) -> RipioOrderbookResponse:
        """Convert to orderbook response model."""
        return RipioOrderbookResponse(
            asks=self.data.get("asks", []),
            bids=self.data.get("bids", []),
            pair=self.data.get("pair"),
            timestamp=self.data.get("timestamp"),
        )


class RipioWebSocketAuth(BaseModel):
    """WebSocket authentication message."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event: str = Field(..., description="Event name: 'auth'")
    data: Dict[str, Any] = Field(..., description="Auth data containing ticket")

    @classmethod
    def create_auth_message(cls, ticket: str) -> Dict[str, Any]:
        """Create authentication message for WebSocket."""
        return {"event": "auth", "data": {"ticket": ticket}}


class RipioWebSocketSubscription(BaseModel):
    """WebSocket subscription message."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event: str = Field(..., description="Event name: 'subscribe'")
    channels: List[str] = Field(..., description="Channel names to subscribe")

    @classmethod
    def create_subscription(cls, channels: List[str]) -> Dict[str, Any]:
        """Create subscription message for WebSocket."""
        return {"event": "subscribe", "channels": channels}


class RipioWebSocketPong(BaseModel):
    """WebSocket pong response."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: str = Field(..., description="Message type: 'pong'")
    timestamp: Optional[int] = Field(None, description="Server timestamp")


# Type alias for WebSocket messages
RipioWebSocketMessage = Union[
    RipioWebSocketOrderUpdate,
    RipioWebSocketOrderbook,
    RipioWebSocketPong,
    Dict[str, Any],  # Fallback for unknown message types
]


# API Error Response Models


class RipioErrorDetail(BaseModel):
    """Single error detail."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field("", description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class RipioErrorResponse(BaseModel):
    """
    Ripio Trade API error response.

    Standard error format for all API endpoints.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    error: str = Field(..., description="Main error message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of detailed errors")
    status_code: Optional[int] = Field(None, description="HTTP status code")

    def get_error_details(self) -> List[RipioErrorDetail]:
        """Get typed error detail objects."""
        if not self.errors:
            return []
        return [
            RipioErrorDetail(
                field=err.get("field"),
                message=err.get("message", ""),
                code=err.get("code"),
            )
            for err in self.errors
        ]

    @computed_field
    def is_rate_limit(self) -> bool:
        """Check if this is a rate limit error."""
        return self.status_code == 429 or "rate limit" in self.error.lower()

    @computed_field
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.status_code in [401, 403] or "unauthorized" in self.error.lower()


# =============================================================================
# Response Envelope Types
# =============================================================================


class RipioBalanceEnvelope(BaseModel, Generic[T]):
    """
    Envelope for Ripio Trade balance/account responses.

    Centralizes isinstance checks for different response formats:
    - API: {"data": [...]} or {"data": {"balances": [...]}}
    - V2 API: {"balances": [...]}
    - Direct list format
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    balances: List[T] = Field(default_factory=list, description="List of balance entries")

    @classmethod
    def from_response(cls, response: Union[Dict[str, Any], List[Any]]) -> "RipioBalanceEnvelope[T]":
        """
        Create envelope from raw API response.

        Handles V2, and direct list formats.
        """
        if isinstance(response, list):
            return cls(balances=response)

        # Dict format - extract balance list from various structures
        # First check for data key
        data = response.get("data", response)

        # If data is a dict, check for balances key
        if isinstance(data, dict):
            return cls(balances=data.get("balances", []))
        if isinstance(data, list):
            return cls(balances=data)

        # Fallback to direct balances key (V2 API)
        return cls(balances=response.get("balances", []))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[T]:
        """Alias for balances for consistent interface."""
        return self.balances


class RipioWebSocketBalanceEnvelope(BaseModel, Generic[T]):
    """
    Envelope for Ripio Trade WebSocket balance update messages.

    Centralizes isinstance checks for balance updates.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    balance_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted balance data from update")
    is_multi_balance: bool = Field(default=False, description="Whether this contains multiple balances")

    @classmethod
    def from_update(cls, update: Union[Dict[str, Any], List[Any]]) -> "RipioWebSocketBalanceEnvelope[T]":
        """
        Create envelope from WebSocket update.

        Handles both single update dict and list of updates.
        Ripio WS wraps private topic data in "body", not "data".
        """
        if isinstance(update, list):
            # List format - process first update if available
            if update and isinstance(update[0], dict):
                inner = update[0]
                balance_data = inner.get("body", inner.get("data", inner))
                is_multi = "balances" in balance_data if isinstance(balance_data, dict) else False
                return cls(balance_data=balance_data if isinstance(balance_data, dict) else {}, is_multi_balance=is_multi)
            return cls(balance_data={}, is_multi_balance=False)

        # Dict format - extract balance data (Ripio uses "body", fallback to "data")
        balance_data = update.get("body", update.get("data", update))
        is_multi = "balances" in balance_data if isinstance(balance_data, dict) else False
        return cls(balance_data=balance_data if isinstance(balance_data, dict) else {}, is_multi_balance=is_multi)

    @property
    def has_currency(self) -> bool:
        """Check if this is a single currency update."""
        return "currency" in self.balance_data or "currency_code" in self.balance_data

    @property
    def has_balances(self) -> bool:
        """Check if this contains multiple balances."""
        return self.is_multi_balance
