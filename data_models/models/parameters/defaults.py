"""Default parameter values and factory functions."""

from .container import BotParameters
from .groups import (
    ExecutionParameters,
    FundingParameters,
    SizingParameters,
    SlippageDirection,
    SlippagePenaltyParameters,
    SlippageSizingParameters,
    SpreadParameters,
    TakerReferenceParameters,
)


def get_default_spread() -> SpreadParameters:
    """Get default spread parameters."""
    return SpreadParameters(
        target_premium=0.15,
        target_discount=0.15,
        taker_spread=0.05,
        max_target_deviation=0.01,
    )


def get_default_sizing() -> SizingParameters:
    """Get default sizing parameters."""
    return SizingParameters(
        amount_cap=300.0,
        amount_floor=300.0,
        max_notional_premium=100_000.0,
        max_notional_discount=100_000.0,
        min_dist_maker=100.0,
        is_dollar_amt=True,
    )


def get_default_slippage_sizing() -> SlippageSizingParameters:
    """Get default slippage sizing parameters."""
    return SlippageSizingParameters(
        premium=SlippageDirection(budget_bps=2.0, capture_pct=0.8),
        discount=SlippageDirection(budget_bps=5.0, capture_pct=0.95),
    )


def get_default_taker_reference() -> TakerReferenceParameters:
    """Get default taker reference parameters."""
    return TakerReferenceParameters(
        depth_capture_pct=0.03,
        levels=20,
        size_floor=2000.0,
        size_cap=30000.0,
    )


def get_default_funding() -> FundingParameters:
    """Get default funding parameters."""
    return FundingParameters(
        horizon_hours=8.0,
        safety_buffer=0.0,
        refresh_interval_sec=300,
    )


def get_default_execution() -> ExecutionParameters:
    """Get default execution parameters."""
    return ExecutionParameters(
        wait_for_fill=True,
        taker_timeout_ms=5000,
    )


def get_default_slippage_penalty() -> SlippagePenaltyParameters:
    """Get default slippage penalty parameters.

    Disabled by default (opt-in feature).
    When enabled, adds historical slippage as a cost in spread calculations.
    """
    return SlippagePenaltyParameters(
        enabled=False,  # Opt-in feature
        scale_factor=0.5,  # 10 bps slippage → 5 bps penalty
        max_penalty_bps=20.0,  # Cap at 20 bps
    )


def get_default_parameters(
    *,
    enable_slippage_sizing: bool = True,
    enable_taker_reference: bool = True,
    enable_funding: bool = False,
    enable_execution: bool = True,
) -> BotParameters:
    """Get default hierarchical parameters with optional feature flags.

    Args:
        enable_slippage_sizing: Enable slippage-bounded sizing
        enable_taker_reference: Enable robust taker reference pricing
        enable_funding: Enable funding rate adjustment
        enable_execution: Enable custom execution parameters

    Returns:
        BotParameters with sensible defaults
    """
    return BotParameters(
        spread=get_default_spread(),
        sizing=get_default_sizing(),
        slippage_sizing=get_default_slippage_sizing() if enable_slippage_sizing else None,
        taker_reference=get_default_taker_reference() if enable_taker_reference else None,
        funding=get_default_funding() if enable_funding else None,
        execution=get_default_execution() if enable_execution else None,
    )


def get_minimal_parameters(
    *,
    target_premium: float = 0.15,
    target_discount: float = 0.15,
    amount_cap: float = 300.0,
) -> BotParameters:
    """Get minimal parameters with only required groups.

    Useful for testing or simple configurations where optional
    features are not needed.

    Args:
        target_premium: Target spread for premium direction
        target_discount: Target spread for discount direction
        amount_cap: Maximum trade amount in USD

    Returns:
        BotParameters with only required groups configured
    """
    return BotParameters(
        spread=SpreadParameters(
            target_premium=target_premium,
            target_discount=target_discount,
            taker_spread=0.05,
            max_target_deviation=0.01,
        ),
        sizing=SizingParameters(
            amount_cap=amount_cap,
            amount_floor=min(amount_cap, 100.0),
            max_notional_premium=100_000.0,
            max_notional_discount=100_000.0,
        ),
        slippage_sizing=None,
        taker_reference=None,
        funding=None,
        execution=None,
    )
