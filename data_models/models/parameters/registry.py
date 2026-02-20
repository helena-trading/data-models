"""Parameter groups registry - single source of truth for all parameter definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

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


class ParameterType(str, Enum):
    """Supported parameter types."""

    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"


@dataclass
class ParameterDefinition:
    """Definition for a single parameter within a group."""

    name: str
    type: ParameterType
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default: Any = None


@dataclass
class ParameterGroupDefinition:
    """Definition for a parameter group."""

    name: str
    description: str
    model_class: Type[BaseModel]
    is_required: bool
    parameters: List[ParameterDefinition] = field(default_factory=list)
    subgroups: Optional[Dict[str, "ParameterGroupDefinition"]] = None


# ===========================================================================
# Parameter Group Definitions (Single Source of Truth)
# ===========================================================================

PARAMETER_GROUPS: Dict[str, ParameterGroupDefinition] = {
    "spread": ParameterGroupDefinition(
        name="spread",
        description="Core spread parameters for market-making quotes",
        model_class=SpreadParameters,
        is_required=True,
        parameters=[
            ParameterDefinition(
                name="target_premium",
                type=ParameterType.FLOAT,
                description="Target spread for premium direction (can be negative for exits)",
                min_value=-5.0,
                max_value=5.0,
                default=0.15,
            ),
            ParameterDefinition(
                name="target_discount",
                type=ParameterType.FLOAT,
                description="Target spread for discount direction (can be negative for exits)",
                min_value=-5.0,
                max_value=5.0,
                default=0.15,
            ),
            ParameterDefinition(
                name="taker_spread",
                type=ParameterType.FLOAT,
                description="Additional spread threshold for aggressive taker orders",
                min_value=0.001,
                max_value=1.0,
                default=0.05,
            ),
            ParameterDefinition(
                name="max_target_deviation",
                type=ParameterType.FLOAT,
                description="Cancel maker if price moves beyond this threshold",
                min_value=0.001,
                max_value=0.1,
                default=0.01,
            ),
        ],
    ),
    "sizing": ParameterGroupDefinition(
        name="sizing",
        description="Order sizing parameters",
        model_class=SizingParameters,
        is_required=True,
        parameters=[
            ParameterDefinition(
                name="amount_cap",
                type=ParameterType.FLOAT,
                description="Maximum trade amount in USD",
                min_value=1.0,
                max_value=1_000_000.0,
                default=300.0,
            ),
            ParameterDefinition(
                name="amount_floor",
                type=ParameterType.FLOAT,
                description="Minimum trade amount in USD",
                min_value=1.0,
                max_value=1_000_000.0,
                default=300.0,
            ),
            ParameterDefinition(
                name="max_notional_premium",
                type=ParameterType.FLOAT,
                description="Maximum notional position for premium direction",
                min_value=100.0,
                max_value=10_000_000.0,
                default=100_000.0,
            ),
            ParameterDefinition(
                name="max_notional_discount",
                type=ParameterType.FLOAT,
                description="Maximum notional position for discount direction",
                min_value=100.0,
                max_value=10_000_000.0,
                default=100_000.0,
            ),
            ParameterDefinition(
                name="min_dist_maker",
                type=ParameterType.FLOAT,
                description="Minimum distance for maker orders in quote currency",
                min_value=0.001,
                max_value=10_000.0,
                default=100.0,
            ),
            ParameterDefinition(
                name="is_dollar_amt",
                type=ParameterType.BOOL,
                description="Whether trade amounts are in quote currency (USD) or base currency",
                default=True,
            ),
        ],
    ),
    "slippage_sizing": ParameterGroupDefinition(
        name="slippage_sizing",
        description="Direction-specific slippage-bounded sizing (None = disabled)",
        model_class=SlippageSizingParameters,
        is_required=False,
        parameters=[],
        subgroups={
            "premium": ParameterGroupDefinition(
                name="premium",
                description="Slippage config for premium direction (conservative)",
                model_class=SlippageDirection,
                is_required=True,
                parameters=[
                    ParameterDefinition(
                        name="budget_bps",
                        type=ParameterType.FLOAT,
                        description="Max acceptable slippage in basis points",
                        min_value=0.1,
                        max_value=100.0,
                        default=2.0,
                    ),
                    ParameterDefinition(
                        name="capture_pct",
                        type=ParameterType.FLOAT,
                        description="Percentage of liquidity to capture within budget",
                        min_value=0.1,
                        max_value=1.0,
                        default=0.8,
                    ),
                ],
            ),
            "discount": ParameterGroupDefinition(
                name="discount",
                description="Slippage config for discount direction (aggressive)",
                model_class=SlippageDirection,
                is_required=True,
                parameters=[
                    ParameterDefinition(
                        name="budget_bps",
                        type=ParameterType.FLOAT,
                        description="Max acceptable slippage in basis points",
                        min_value=0.1,
                        max_value=100.0,
                        default=5.0,
                    ),
                    ParameterDefinition(
                        name="capture_pct",
                        type=ParameterType.FLOAT,
                        description="Percentage of liquidity to capture within budget",
                        min_value=0.1,
                        max_value=1.0,
                        default=0.95,
                    ),
                ],
            ),
        },
    ),
    "taker_reference": ParameterGroupDefinition(
        name="taker_reference",
        description="Robust taker reference pricing with depth analysis (None = disabled)",
        model_class=TakerReferenceParameters,
        is_required=False,
        parameters=[
            ParameterDefinition(
                name="depth_capture_pct",
                type=ParameterType.FLOAT,
                description="Percentage of available depth to capture",
                min_value=0.001,
                max_value=1.0,
                default=0.03,
            ),
            ParameterDefinition(
                name="levels",
                type=ParameterType.INT,
                description="Number of orderbook levels to consider",
                min_value=1,
                max_value=50,
                default=20,
            ),
            ParameterDefinition(
                name="size_floor",
                type=ParameterType.FLOAT,
                description="Minimum order size from depth calculation in USD",
                min_value=10.0,
                max_value=1_000_000.0,
                default=2000.0,
            ),
            ParameterDefinition(
                name="size_cap",
                type=ParameterType.FLOAT,
                description="Maximum order size from depth calculation in USD",
                min_value=10.0,
                max_value=1_000_000.0,
                default=30000.0,
            ),
        ],
    ),
    "funding": ParameterGroupDefinition(
        name="funding",
        description="Funding rate adjustment parameters (None = disabled)",
        model_class=FundingParameters,
        is_required=False,
        parameters=[
            ParameterDefinition(
                name="horizon_hours",
                type=ParameterType.FLOAT,
                description="Hours to project funding costs",
                min_value=0.5,
                max_value=48.0,
                default=8.0,
            ),
            ParameterDefinition(
                name="safety_buffer",
                type=ParameterType.FLOAT,
                description="Safety buffer for funding rate as decimal",
                min_value=0.0,
                max_value=0.01,
                default=0.0,
            ),
            ParameterDefinition(
                name="refresh_interval_sec",
                type=ParameterType.INT,
                description="How often to refresh funding rates in seconds",
                min_value=60,
                max_value=3600,
                default=300,
            ),
        ],
    ),
    "execution": ParameterGroupDefinition(
        name="execution",
        description="Order execution behavior parameters",
        model_class=ExecutionParameters,
        is_required=False,
        parameters=[
            ParameterDefinition(
                name="wait_for_fill",
                type=ParameterType.BOOL,
                description="Wait for taker order to fill completely",
                default=True,
            ),
            ParameterDefinition(
                name="taker_timeout_ms",
                type=ParameterType.INT,
                description="Taker order timeout in milliseconds",
                min_value=100,
                max_value=60000,
                default=5000,
            ),
            ParameterDefinition(
                name="maker_staleness_threshold_ms",
                type=ParameterType.INT,
                description="Maximum age in ms for maker orderbook before considered stale",
                min_value=100,
                max_value=30000,
                default=2000,
            ),
            ParameterDefinition(
                name="taker_staleness_threshold_ms",
                type=ParameterType.INT,
                description="Maximum age in ms for taker orderbook before considered stale",
                min_value=100,
                max_value=30000,
                default=2000,
            ),
        ],
    ),
    "slippage_penalty": ParameterGroupDefinition(
        name="slippage_penalty",
        description="Slippage-based cost penalty for spread calculations",
        model_class=SlippagePenaltyParameters,
        is_required=False,
        parameters=[
            ParameterDefinition(
                name="enabled",
                type=ParameterType.BOOL,
                description="Enable slippage penalty as additional fee",
                default=False,
            ),
            ParameterDefinition(
                name="scale_factor",
                type=ParameterType.FLOAT,
                description="Multiply historical slippage by this factor (0.5 = 10bps slippage → 5bps penalty)",
                min_value=0.1,
                max_value=2.0,
                default=0.5,
            ),
            ParameterDefinition(
                name="max_penalty_bps",
                type=ParameterType.FLOAT,
                description="Maximum penalty in basis points (cap)",
                min_value=0.0,
                max_value=100.0,
                default=20.0,
            ),
        ],
    ),
}


def get_group_names() -> List[str]:
    """Get all parameter group names."""
    return list(PARAMETER_GROUPS.keys())


def get_required_groups() -> List[str]:
    """Get names of required parameter groups."""
    return [name for name, group in PARAMETER_GROUPS.items() if group.is_required]


def get_optional_groups() -> List[str]:
    """Get names of optional parameter groups."""
    return [name for name, group in PARAMETER_GROUPS.items() if not group.is_required]


def get_parameter_definition(group_name: str, param_name: str) -> Optional[ParameterDefinition]:
    """Get a specific parameter definition.

    Args:
        group_name: Name of the parameter group
        param_name: Name of the parameter within the group

    Returns:
        ParameterDefinition if found, None otherwise
    """
    group = PARAMETER_GROUPS.get(group_name)
    if not group:
        return None

    for param in group.parameters:
        if param.name == param_name:
            return param

    # Check subgroups
    if group.subgroups:
        for subgroup_name, subgroup in group.subgroups.items():
            for param in subgroup.parameters:
                if param.name == param_name:
                    return param

    return None


def validate_parameter_value(
    group_name: str,
    param_name: str,
    value: Any,
) -> tuple[bool, Optional[str]]:
    """Validate a parameter value against its definition.

    Args:
        group_name: Name of the parameter group
        param_name: Name of the parameter
        value: Value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    definition = get_parameter_definition(group_name, param_name)
    if not definition:
        return False, f"Unknown parameter: {group_name}.{param_name}"

    # Type validation
    typed_value: Union[float, int, bool, str]
    try:
        if definition.type == ParameterType.FLOAT:
            typed_value = float(value)
        elif definition.type == ParameterType.INT:
            typed_value = int(value)
        elif definition.type == ParameterType.BOOL:
            typed_value = bool(value)
        else:
            typed_value = str(value)
    except (TypeError, ValueError) as e:
        return False, f"Invalid {definition.type.value} value: {e}"

    # Range validation for numeric types
    if definition.type in (ParameterType.FLOAT, ParameterType.INT) and isinstance(typed_value, (int, float)):
        if definition.min_value is not None and typed_value < definition.min_value:
            return False, f"Value {typed_value} is below minimum {definition.min_value}"
        if definition.max_value is not None and typed_value > definition.max_value:
            return False, f"Value {typed_value} is above maximum {definition.max_value}"

    return True, None
