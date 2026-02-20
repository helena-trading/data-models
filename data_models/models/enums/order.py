"""
Order-related enums.

Centralized definitions for order side, status, and type enums.
These are the INTERNAL (canonical) enums used throughout the application.
Exchange-specific enum values are handled by converters in the gateway layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class OrderSide(Enum):
    """Order direction from the exchange perspective."""

    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str | "OrderSide" | None) -> "OrderSide":
        """Convert string to OrderSide enum.

        Handles string input from external sources (JSON, exchange APIs).
        """
        if not value:
            return cls.BUY
        if isinstance(value, str):
            value_lower = value.lower()
            for side in cls:
                if side.value == value_lower:
                    return side
            return cls.UNKNOWN
        # Already OrderSide
        return value


class OrderStatus(Enum):
    """Status of an order as reported by the exchange."""

    NEW = "new"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"
    UNKNOWN = "unknown"


class OrderType(Enum):
    """Type of order to be executed by the exchange."""

    LIMIT = "limit"
    MARKET = "market"
    POST_ONLY = "post_only"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"
    TAKE_PROFIT_MARKET = "take_profit_market"
    TRAILING_STOP = "trailing_stop"
    IOC = "ioc"
    FOK = "fok"

    @classmethod
    def from_string(cls, value: str | "OrderType" | None) -> "OrderType":
        """Convert string to OrderType enum.

        Handles string input from external sources (JSON, exchange APIs).
        """
        if not value:
            return cls.LIMIT
        if isinstance(value, str):
            value_lower = value.lower()
            for order_type in cls:
                if order_type.value == value_lower:
                    return order_type
            return cls.LIMIT
        # Already OrderType
        return value


class OrderRequestStatus(Enum):
    """Status constants for order request tracking."""

    SUCCESS = "success"
    PENDING = "pending"
    ACCEPTED = "accepted"
    TIMEOUT_ERROR = "timeout_error"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    UNKNOWN_REJECTION = "unknown_rejection"
    CRITICAL_ERROR = "critical_error"
    INTERNAL_ERROR = "internal_error"
    PRICE_FILTER_REJECTION = "price_filter_rejection"
    POST_ONLY_REJECTED = "post_only_rejected"
    LIMIT_MAKER_REJECTED = "limit_maker_rejected"
    WEBSOCKET_NOT_CONNECTED = "websocket_not_connected"
    RATE_LIMIT_ERROR = "rate_limit_error"


# ============================================================================
# EXCHANGE MAPPING FUNCTIONS
# ============================================================================

# Status mapping from various exchanges to standardized enum values
STATUS_MAPPING: Dict[str, OrderStatus] = {
    # Binance
    "NEW": OrderStatus.NEW,
    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
    "FILLED": OrderStatus.FILLED,
    "CANCELED": OrderStatus.CANCELED,
    "PENDING_CANCEL": OrderStatus.CANCELED,
    "REJECTED": OrderStatus.REJECTED,
    "EXPIRED": OrderStatus.EXPIRED,
    # Bybit
    "Created": OrderStatus.NEW,
    "New": OrderStatus.NEW,
    "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
    "Filled": OrderStatus.FILLED,
    "Cancelled": OrderStatus.CANCELED,
    "PendingCancel": OrderStatus.CANCELED,
    "Rejected": OrderStatus.REJECTED,
    # OKX
    "live": OrderStatus.OPEN,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELED,
    # Hyperliquid
    "open": OrderStatus.OPEN,
    "closed": OrderStatus.FILLED,
    "cancelled": OrderStatus.CANCELED,
    # Common lowercase (entries not already defined above)
    "new": OrderStatus.NEW,
    "rejected": OrderStatus.REJECTED,
    "expired": OrderStatus.EXPIRED,
}

# Side mapping from various exchanges to standardized enum values
SIDE_MAPPING: Dict[str, OrderSide] = {
    "BUY": OrderSide.BUY,
    "SELL": OrderSide.SELL,
    "buy": OrderSide.BUY,
    "sell": OrderSide.SELL,
    "Buy": OrderSide.BUY,
    "Sell": OrderSide.SELL,
    "b": OrderSide.BUY,
    "s": OrderSide.SELL,
    "1": OrderSide.BUY,
    "-1": OrderSide.SELL,
}

# Order type mapping from various exchanges to standardized enum values
ORDER_TYPE_MAPPING: Dict[str, OrderType] = {
    "LIMIT": OrderType.LIMIT,
    "MARKET": OrderType.MARKET,
    "POST_ONLY": OrderType.POST_ONLY,
    "STOP": OrderType.STOP,
    "STOP_LIMIT": OrderType.STOP_LIMIT,
    "STOP_MARKET": OrderType.STOP_MARKET,
    "TAKE_PROFIT": OrderType.TAKE_PROFIT,
    "TAKE_PROFIT_LIMIT": OrderType.TAKE_PROFIT_LIMIT,
    "TAKE_PROFIT_MARKET": OrderType.TAKE_PROFIT_MARKET,
    "IOC": OrderType.IOC,
    "FOK": OrderType.FOK,
    # Lowercase variants
    "limit": OrderType.LIMIT,
    "market": OrderType.MARKET,
    "post_only": OrderType.POST_ONLY,
    "stop": OrderType.STOP,
    "stop_limit": OrderType.STOP_LIMIT,
    "stop_market": OrderType.STOP_MARKET,
    "take_profit": OrderType.TAKE_PROFIT,
    "take_profit_limit": OrderType.TAKE_PROFIT_LIMIT,
    "take_profit_market": OrderType.TAKE_PROFIT_MARKET,
    "ioc": OrderType.IOC,
    "fok": OrderType.FOK,
}


def normalize_side(value: str | OrderSide | None) -> OrderSide:
    """Convert exchange-specific side value to OrderSide enum.

    Handles string input from external sources (JSON, exchange APIs).
    """
    if not value:
        return OrderSide.BUY
    if isinstance(value, str):
        return SIDE_MAPPING.get(value.strip(), OrderSide.BUY)
    # Already OrderSide
    return value


def normalize_status(value: str | OrderStatus | None) -> OrderStatus:
    """Convert exchange-specific status value to OrderStatus enum.

    Handles string input from external sources (JSON, exchange APIs).
    """
    if not value:
        return OrderStatus.NEW
    if isinstance(value, str):
        return STATUS_MAPPING.get(value.strip(), OrderStatus.UNKNOWN)
    # Already OrderStatus
    return value


def normalize_order_type(value: str | OrderType | None) -> OrderType:
    """Convert exchange-specific order type value to OrderType enum.

    Handles string input from external sources (JSON, exchange APIs).
    """
    if not value:
        return OrderType.LIMIT
    if isinstance(value, str):
        return ORDER_TYPE_MAPPING.get(value.strip(), OrderType.LIMIT)
    # Already OrderType
    return value


__all__ = [
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "OrderRequestStatus",
    "normalize_side",
    "normalize_status",
    "normalize_order_type",
    "STATUS_MAPPING",
    "SIDE_MAPPING",
    "ORDER_TYPE_MAPPING",
]
