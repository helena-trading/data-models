"""
Type-safe trading pair representation.

This module provides:
- TradingPair: Immutable, validated trading pair (e.g., BTC_USDT)
- ensure_trading_pair: Helper to convert str or TradingPair to TradingPair

CRITICAL: This represents the INTERNAL format only.
Exchange-specific formats are handled by SymbolAdapters in gateways.

Internal format: BASE_QUOTE (e.g., BTC_USDT, ETH_USDT, SOL_USDT)
- Always uppercase
- Always underscore separator
- Gateways convert to/from exchange formats (BTCUSDT, BTC-USDT, etc.)

Examples:
    >>> pair = TradingPair("BTC_USDT")
    >>> pair.base
    'BTC'
    >>> pair.quote
    'USDT'
    >>> str(pair)
    'BTC_USDT'

    >>> TradingPair.from_parts("eth", "usdt")
    TradingPair(ETH_USDT)

    >>> ensure_trading_pair("SOL_USDT")
    TradingPair(SOL_USDT)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TradingPair:
    """
    Type-safe internal trading pair format (e.g., BTC_USDT).

    CRITICAL: This represents the INTERNAL format only.
    Exchange-specific formats are handled by SymbolAdapters in gateways.

    This is a frozen dataclass for:
    - Immutability (safe to use as dict keys, share across threads)
    - Hashability (can be used in sets and as dict keys)
    - Type safety (mypy catches misuse at compile time)

    Attributes:
        value: The trading pair string in BASE_QUOTE format (e.g., "BTC_USDT")

    Examples:
        - "BTC_USDT" (Bitcoin/USDT)
        - "ETH_USDT" (Ethereum/USDT)
        - "SOL_USDT" (Solana/USDT)
    """

    value: str

    def __post_init__(self) -> None:
        """Validate trading pair format on creation."""
        if not self._is_valid_format(self.value):
            raise ValueError(f"Invalid trading pair format: {self.value}. " f"Expected BASE_QUOTE (e.g., BTC_USDT)")

    @staticmethod
    def _is_valid_format(value: str) -> bool:
        """
        Check if value is valid internal trading pair format.

        Valid format:
        - Contains exactly one underscore
        - BASE and QUOTE are non-empty
        - BASE and QUOTE are uppercase
        """
        if "_" not in value:
            return False

        parts = value.split("_")
        if len(parts) != 2:
            return False

        base, quote = parts
        return len(base) >= 1 and len(quote) >= 1 and base.isupper() and quote.isupper() and base.isalnum() and quote.isalnum()

    @property
    def base(self) -> str:
        """
        Base currency (e.g., 'BTC' from 'BTC_USDT').

        Returns:
            The base currency portion of the trading pair
        """
        return self.value.split("_")[0]

    @property
    def quote(self) -> str:
        """
        Quote currency (e.g., 'USDT' from 'BTC_USDT').

        Returns:
            The quote currency portion of the trading pair
        """
        return self.value.split("_")[1]

    def __str__(self) -> str:
        """Return the raw trading pair value for logging and string contexts."""
        return self.value

    def __repr__(self) -> str:
        """Return a debug representation showing the type."""
        return f"TradingPair({self.value})"

    def __hash__(self) -> int:
        """Support using as dictionary key."""
        return hash(self.value)

    @classmethod
    def from_parts(cls, base: str, quote: str) -> "TradingPair":
        """
        Create trading pair from base and quote currencies.

        Args:
            base: Base currency (e.g., "BTC", "btc")
            quote: Quote currency (e.g., "USDT", "usdt")

        Returns:
            TradingPair instance with uppercase formatting

        Example:
            >>> TradingPair.from_parts("btc", "usdt")
            TradingPair(BTC_USDT)
        """
        return cls(f"{base.upper()}_{quote.upper()}")


def ensure_trading_pair(value: str | TradingPair) -> TradingPair:
    """
    Convert string or TradingPair to TradingPair.

    This helper eliminates the pattern:
        `value if isinstance(value, TradingPair) else TradingPair(value)`

    Args:
        value: A trading pair string or TradingPair instance

    Returns:
        TradingPair instance

    Example:
        >>> ensure_trading_pair("BTC_USDT")
        TradingPair(BTC_USDT)
        >>> ensure_trading_pair(TradingPair("ETH_USDT"))
        TradingPair(ETH_USDT)
    """
    if isinstance(value, TradingPair):
        return value
    return TradingPair(value)


__all__ = [
    "TradingPair",
    "ensure_trading_pair",
]
