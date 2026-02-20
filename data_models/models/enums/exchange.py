"""
Exchange and TradeType enums for Helena Bot.

Provides type-safe identifiers for all supported exchanges and trade types.
These enums are the single source of truth for exchange naming across the codebase.

Usage:
from data_models.models.enums.exchange import ExchangeName, TradeType

    # Use enum values directly (no strings!)
    if gateway.exchange_name == ExchangeName.HYPERLIQUID:
        # Hyperliquid-specific logic

    # Get trade type for an exchange
    trade_type = get_trade_type(ExchangeName.BINANCE_SPOT)  # TradeType.SPOT
"""

from enum import StrEnum
from typing import List


class ExchangeName(StrEnum):
    """
    Supported exchange identifiers.

    These are the canonical exchange names used throughout the codebase.
    The gateway layer uses these identifiers for routing and configuration.

    Naming Convention:
    - Base exchange name for single-type exchanges: HYPERLIQUID, BYBIT
    - Exchange + type suffix for multi-type exchanges: BINANCE_SPOT, BINANCE_FUTURES
    """

    # CEX Spot
    BINANCE_SPOT = "binance_spot"
    RIPIO_TRADE = "ripio_trade"

    # CEX Futures
    BINANCE_FUTURES = "binance_futures"
    BYBIT = "bybit"

    # DEX Spot
    LIGHTER_SPOT = "lighter_spot"

    # DEX Futures
    HYPERLIQUID = "hyperliquid"
    LIGHTER = "lighter"

    @classmethod
    def all(cls) -> List["ExchangeName"]:
        """Return all supported exchanges."""
        return list(cls)

    @classmethod
    def spot_exchanges(cls) -> List["ExchangeName"]:
        """Return all spot exchanges."""
        return [cls.BINANCE_SPOT, cls.RIPIO_TRADE, cls.LIGHTER_SPOT]

    @classmethod
    def futures_exchanges(cls) -> List["ExchangeName"]:
        """Return all futures exchanges."""
        return [cls.BINANCE_FUTURES, cls.BYBIT, cls.HYPERLIQUID, cls.LIGHTER]


class TradeType(StrEnum):
    """
    Trading type for exchange accounts.

    Determines whether an exchange account trades spot or futures/perpetual markets.
    """

    SPOT = "spot"
    FUTURES = "futures"


# =============================================================================
# EXCHANGE TO TRADE TYPE MAPPING
# =============================================================================

EXCHANGE_TRADE_TYPE: dict[ExchangeName, TradeType] = {
    # Spot exchanges
    ExchangeName.BINANCE_SPOT: TradeType.SPOT,
    ExchangeName.RIPIO_TRADE: TradeType.SPOT,
    ExchangeName.LIGHTER_SPOT: TradeType.SPOT,
    # Futures exchanges
    ExchangeName.BINANCE_FUTURES: TradeType.FUTURES,
    ExchangeName.BYBIT: TradeType.FUTURES,
    ExchangeName.HYPERLIQUID: TradeType.FUTURES,
    ExchangeName.LIGHTER: TradeType.FUTURES,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_trade_type(exchange: ExchangeName) -> TradeType:
    """
    Get the trade type for an exchange.

    Args:
        exchange: Exchange enum value

    Returns:
        TradeType for the exchange

    Raises:
        KeyError: If exchange is not in mapping (should never happen)
    """
    return EXCHANGE_TRADE_TYPE[exchange]


def is_spot_exchange(exchange: ExchangeName) -> bool:
    """Check if exchange is a spot exchange."""
    return get_trade_type(exchange) == TradeType.SPOT


def is_futures_exchange(exchange: ExchangeName) -> bool:
    """Check if exchange is a futures exchange."""
    return get_trade_type(exchange) == TradeType.FUTURES


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "ExchangeName",
    "TradeType",
    # Mapping
    "EXCHANGE_TRADE_TYPE",
    # Functions
    "get_trade_type",
    "is_spot_exchange",
    "is_futures_exchange",
]
