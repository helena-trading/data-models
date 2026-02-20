"""Protocol definitions for lifecycle management interfaces.

This module contains Protocol classes that define the expected behavior of
components that can be started, stopped, or shutdown during bot lifecycle.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from data_models.models.parameters import (
    ExecutionParameters,
    FundingParameters,
    SizingParameters,
    SlippagePenaltyParameters,
    SlippageSizingParameters,
    SpreadParameters,
    TakerReferenceParameters,
)
from data_models.models.enums.trading import BotState

# Type alias for cleanup callbacks (used by ShutdownManager for thread pool)
CleanupCallback = Callable[[], None]


@runtime_checkable
class StoppableProtocol(Protocol):
    """Protocol for objects that can be stopped."""

    def stop(self) -> None:
        """Stop the object."""
        ...


@runtime_checkable
class BotProtocol(Protocol):
    """Protocol for bot objects with lifecycle and state methods."""

    @property
    def route(self) -> str:
        """Get the bot route identifier."""
        ...

    def stop_trading(self) -> None:
        """Stop trading activities."""
        ...

    def is_stopped(self) -> bool:
        """Check if the bot is stopped.

        Returns:
            bool: True if bot is stopped, False otherwise
        """
        ...

    def get_bot_state(self) -> Optional[BotState]:
        """Get current bot state.

        Returns:
            Optional[BotState]: Bot state object, None if not available
        """
        ...

    def get_maker_id(self) -> Optional[str]:
        """Get maker exchange identifier.

        Returns:
            Optional[str]: Maker ID, None if not available
        """
        ...

    def get_taker_id(self) -> Optional[str]:
        """Get taker exchange identifier.

        Returns:
            Optional[str]: Taker ID, None if not available
        """
        ...

    def execute_single_cycle(self) -> None:
        """Execute a single trading cycle."""
        ...


@runtime_checkable
class IBotParametersManager(Protocol):
    """Protocol for hierarchical bot parameters manager.

    Defines the typed interface for accessing bot trading parameters
    via hierarchical groups.

    Usage:
        # Access via groups
        premium = params.spread.target_premium
        cap = params.sizing.amount_cap

        # Check if optional feature is enabled
        if params.is_funding_enabled:
            horizon = params.funding.horizon_hours

        # Safe accessors with defaults
        timeout = params.get_taker_timeout_ms()
    """

    # =========================================================================
    # Non-parameter attributes (system-level configuration)
    # =========================================================================

    strategy_type: str
    is_graph_latency: bool
    graph_config: Optional[Dict[str, Any]]
    contract_list_main: Optional[List[str]]
    contract_list_sec: Optional[List[str]]

    # WebSocket health parameters (system-level)
    websocket_health_threshold: int
    websocket_recovery_enabled: bool
    websocket_max_recovery_attempts: int
    websocket_recovery_backoff: List[int]

    # Circuit breaker configuration (system-level)
    circuit_breaker: Dict[str, Any]

    # Graph-specific attributes (set by executor after initialization)
    min_spread_threshold: Optional[float]
    _exchanges: Dict[str, Any]

    # =========================================================================
    # Group Accessors (required groups)
    # =========================================================================

    @property
    def spread(self) -> SpreadParameters:
        """Access spread parameters group."""
        ...

    @property
    def sizing(self) -> SizingParameters:
        """Access sizing parameters group."""
        ...

    # =========================================================================
    # Group Accessors (optional groups - None if disabled)
    # =========================================================================

    @property
    def slippage_sizing(self) -> Optional[SlippageSizingParameters]:
        """Access slippage sizing group (None if disabled)."""
        ...

    @property
    def taker_reference(self) -> Optional[TakerReferenceParameters]:
        """Access taker reference group (None if disabled)."""
        ...

    @property
    def funding(self) -> Optional[FundingParameters]:
        """Access funding parameters group (None if disabled)."""
        ...

    @property
    def execution(self) -> Optional[ExecutionParameters]:
        """Access execution parameters group (None if disabled)."""
        ...

    @property
    def slippage_penalty(self) -> Optional[SlippagePenaltyParameters]:
        """Access slippage penalty group (None if disabled)."""
        ...

    # =========================================================================
    # Feature Enable Checks
    # =========================================================================

    @property
    def is_slippage_sizing_enabled(self) -> bool:
        """Check if slippage-bounded sizing is enabled."""
        ...

    @property
    def is_taker_reference_enabled(self) -> bool:
        """Check if taker reference pricing is enabled."""
        ...

    @property
    def is_funding_enabled(self) -> bool:
        """Check if funding rate adjustment is enabled."""
        ...

    @property
    def is_slippage_penalty_enabled(self) -> bool:
        """Check if slippage penalty is enabled."""
        ...

    # =========================================================================
    # Safe Accessors with Defaults (for optional groups)
    # =========================================================================

    def get_slippage_budget_bps(self, is_premium: bool) -> float:
        """Get slippage budget for direction, with fallback default.

        Args:
            is_premium: True for premium direction, False for discount

        Returns:
            Slippage budget in basis points
        """
        ...

    def get_slippage_capture_pct(self, is_premium: bool) -> float:
        """Get slippage capture percentage for direction, with fallback default.

        Args:
            is_premium: True for premium direction, False for discount

        Returns:
            Capture percentage (0.0-1.0)
        """
        ...

    def get_taker_timeout_ms(self) -> int:
        """Get taker timeout, with default fallback.

        Returns:
            Timeout in milliseconds
        """
        ...

    def get_wait_for_fill(self) -> bool:
        """Get wait_for_fill setting, with default fallback.

        Returns:
            Whether to wait for taker fill
        """
        ...

    def get_slippage_penalty_scale_factor(self) -> float:
        """Get slippage penalty scale factor.

        Returns:
            Scale factor (0.1-2.0), default 0.5
        """
        ...

    def get_slippage_penalty_max_bps(self) -> float:
        """Get slippage penalty maximum in basis points.

        Returns:
            Maximum penalty in bps (0-100), default 20.0
        """
        ...

    def get_accepted_slippage(self) -> float:
        """Get accepted slippage percentage, with default fallback.

        Returns:
            Accepted slippage percentage (default 0.5%)
        """
        ...

    # =========================================================================
    # Dynamic Updates
    # =========================================================================

    def update_group(self, group_name: str, values: Dict[str, Any]) -> None:
        """Update parameters within a group.

        Args:
            group_name: Name of the group ('spread', 'sizing', etc.)
            values: Dictionary of parameter values to update
        """
        ...

    def enable_group(self, group_name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Enable an optional parameter group.

        Args:
            group_name: Name of the optional group
            config: Optional configuration for the group
        """
        ...

    def disable_group(self, group_name: str) -> None:
        """Disable an optional parameter group (set to None).

        Args:
            group_name: Name of the optional group
        """
        ...

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Export as hierarchical dictionary.

        Returns:
            Dictionary representation of all parameters
        """
        ...
