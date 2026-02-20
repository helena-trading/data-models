"""Bot parameter system for Helena Bot.

This package provides a clean parameter structure with:
- Required groups: spread, sizing
- Optional groups: slippage_sizing, taker_reference, funding, execution

Optional groups use None to indicate disabled state.

Usage:
    from data_models.models.parameters import (
        BotParameters,
        BotParametersManager,
        SpreadParameters,
        SizingParameters,
        get_default_parameters,
    )

    # Create parameters
    params = BotParameters(
        spread=SpreadParameters(
            target_premium=0.20,
            target_discount=0.15,
            taker_spread=0.05,
            max_target_deviation=0.01,
        ),
        sizing=SizingParameters(
            amount_cap=500,
            amount_floor=100,
            max_notional_premium=50000,
            max_notional_discount=50000,
        ),
        # Optional groups - None means disabled
        taker_reference=None,
        funding=None,
    )

    # Create manager for engine use
    manager = BotParametersManager(params)

    # Access parameters
    premium = manager.spread.target_premium

    # Check if feature is enabled
    if manager.is_funding_enabled:
        horizon = manager.funding.horizon_hours
"""

from .container import BotParameters
from .defaults import (
    get_default_execution,
    get_default_funding,
    get_default_parameters,
    get_default_sizing,
    get_default_slippage_penalty,
    get_default_slippage_sizing,
    get_default_spread,
    get_default_taker_reference,
    get_minimal_parameters,
)
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
from .manager import BotParametersManager
from .registry import (
    PARAMETER_GROUPS,
    ParameterDefinition,
    ParameterGroupDefinition,
    ParameterType,
    get_group_names,
    get_optional_groups,
    get_parameter_definition,
    get_required_groups,
    validate_parameter_value,
)

__all__ = [
    # Container
    "BotParameters",
    # Groups
    "SpreadParameters",
    "SizingParameters",
    "SlippageDirection",
    "SlippagePenaltyParameters",
    "SlippageSizingParameters",
    "TakerReferenceParameters",
    "FundingParameters",
    "ExecutionParameters",
    # Manager
    "BotParametersManager",
    # Defaults
    "get_default_parameters",
    "get_minimal_parameters",
    "get_default_spread",
    "get_default_sizing",
    "get_default_slippage_penalty",
    "get_default_slippage_sizing",
    "get_default_taker_reference",
    "get_default_funding",
    "get_default_execution",
    # Registry
    "PARAMETER_GROUPS",
    "ParameterDefinition",
    "ParameterGroupDefinition",
    "ParameterType",
    "get_group_names",
    "get_required_groups",
    "get_optional_groups",
    "get_parameter_definition",
    "validate_parameter_value",
]
