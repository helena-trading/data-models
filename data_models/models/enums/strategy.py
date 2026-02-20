"""
Strategy type enums for Helena Bot.

Provides type-safe identifiers for all supported trading strategies.
These enums are the single source of truth for strategy naming across the codebase.

Usage:
from data_models.models.enums.strategy import StrategyType

    # Use enum values directly (no strings!)
    if bot.strategy_type == StrategyType.CROSS_ARB:
        # Cross-exchange arbitrage logic
"""

from enum import StrEnum
from typing import List


class StrategyType(StrEnum):
    """
    Supported trading strategy identifiers.

    These are the canonical strategy names used throughout the codebase.
    The database and API use these identifiers for configuration.

    Naming Convention:
    - Descriptive names with snake_case
    - These are the ONLY valid values - no aliases or legacy names
    """

    # Trading Strategies
    CROSS_ARB = "cross_arb"
    GRAPH_ARBITRAGE = "graph_arbitrage"

    # Non-Trading Strategies
    MONITORING = "monitoring"

    @classmethod
    def all(cls) -> List["StrategyType"]:
        """Return all supported strategies."""
        return list(cls)

    @classmethod
    def trading_strategies(cls) -> List["StrategyType"]:
        """Return all trading strategies (that execute trades)."""
        return [cls.CROSS_ARB, cls.GRAPH_ARBITRAGE]

    @classmethod
    def non_trading_strategies(cls) -> List["StrategyType"]:
        """Return all non-trading strategies (monitoring, etc.)."""
        return [cls.MONITORING]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "StrategyType",
]
