"""BotParametersManager with group-based access."""

from typing import Any, Callable, Dict, List, Optional

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


class BotParametersManager:
    """
    Bot parameter manager with group-based access.

    Usage:
        params = BotParameters(
            spread=SpreadParameters(...),
            sizing=SizingParameters(...),
        )
        manager = BotParametersManager(params)

        # Access via groups
        premium = manager.spread.target_premium

        # Check if optional feature is enabled
        if manager.is_funding_enabled:
            horizon = manager.funding.horizon_hours
    """

    def __init__(self, params: BotParameters) -> None:
        self._params = params
        self._update_callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}

        # Non-parameter attributes
        self.strategy_type: str = "cross_exchange_arbitrage"
        self.is_graph_latency: bool = False
        self.graph_config: Optional[Dict[str, Any]] = None
        self.contract_list_main: Optional[List[str]] = None
        self.contract_list_sec: Optional[List[str]] = None

        # WebSocket health parameters (system-level, not trading parameters)
        self.websocket_health_threshold: int = 10
        self.websocket_recovery_enabled: bool = True
        self.websocket_max_recovery_attempts: int = 3
        self.websocket_recovery_backoff: List[int] = [60, 120, 240]

        # Circuit breaker configuration (system-level, not trading parameters)
        # Empty dict uses defaults from CircuitBreakerConfig dataclass
        self.circuit_breaker: Dict[str, Any] = {}

        # Graph-specific attributes (set by executor after initialization)
        self.min_spread_threshold: Optional[float] = None
        self._exchanges: Dict[str, Any] = {}

    # =========================================================================
    # Group Accessors
    # =========================================================================

    @property
    def spread(self) -> SpreadParameters:
        """Access spread parameters group."""
        return self._params.spread

    @property
    def sizing(self) -> SizingParameters:
        """Access sizing parameters group."""
        return self._params.sizing

    @property
    def slippage_sizing(self) -> Optional[SlippageSizingParameters]:
        """Access slippage sizing group (None if disabled)."""
        return self._params.slippage_sizing

    @property
    def taker_reference(self) -> Optional[TakerReferenceParameters]:
        """Access taker reference group (None if disabled)."""
        return self._params.taker_reference

    @property
    def funding(self) -> Optional[FundingParameters]:
        """Access funding parameters group (None if disabled)."""
        return self._params.funding

    @property
    def execution(self) -> Optional[ExecutionParameters]:
        """Access execution parameters group (None if disabled)."""
        return self._params.execution

    @property
    def slippage_penalty(self) -> Optional[SlippagePenaltyParameters]:
        """Access slippage penalty group (None if disabled)."""
        return self._params.slippage_penalty

    # =========================================================================
    # Feature Enable Checks
    # =========================================================================

    @property
    def is_slippage_sizing_enabled(self) -> bool:
        """Check if slippage-bounded sizing is enabled."""
        return self._params.is_slippage_sizing_enabled

    @property
    def is_taker_reference_enabled(self) -> bool:
        """Check if taker reference pricing is enabled."""
        return self._params.is_taker_reference_enabled

    @property
    def is_funding_enabled(self) -> bool:
        """Check if funding rate adjustment is enabled."""
        return self._params.is_funding_enabled

    @property
    def is_slippage_penalty_enabled(self) -> bool:
        """Check if slippage penalty is enabled."""
        return self._params.is_slippage_penalty_enabled

    # =========================================================================
    # Safe Accessors with Defaults (for optional groups)
    # =========================================================================

    def get_slippage_budget_bps(self, is_premium: bool) -> float:
        """Get slippage budget for direction, with fallback default."""
        return self._params.get_slippage_budget_bps(is_premium)

    def get_slippage_capture_pct(self, is_premium: bool) -> float:
        """Get slippage capture percentage for direction, with fallback default."""
        return self._params.get_slippage_capture_pct(is_premium)

    def get_taker_timeout_ms(self) -> int:
        """Get taker timeout, with default fallback."""
        return self._params.get_taker_timeout_ms()

    def get_wait_for_fill(self) -> bool:
        """Get wait_for_fill setting, with default fallback."""
        return self._params.get_wait_for_fill()

    def get_accepted_slippage(self) -> float:
        """Get accepted slippage percentage, with default fallback."""
        if self._params.execution:
            return self._params.execution.accepted_slippage
        return 0.5  # Default 0.5%

    def get_slippage_penalty_scale_factor(self) -> float:
        """Get slippage penalty scale factor."""
        return self._params.get_slippage_penalty_scale_factor()

    def get_slippage_penalty_max_bps(self) -> float:
        """Get slippage penalty maximum in basis points."""
        return self._params.get_slippage_penalty_max_bps()

    # =========================================================================
    # Dynamic Updates
    # =========================================================================

    def update_group(self, group_name: str, values: Dict[str, Any]) -> None:
        """Update parameters within a group."""
        if group_name == "spread":
            current = self._params.spread.model_dump()
            current.update(values)
            self._params.spread = SpreadParameters(**current)
        elif group_name == "sizing":
            current = self._params.sizing.model_dump()
            current.update(values)
            self._params.sizing = SizingParameters(**current)
        elif group_name == "slippage_sizing" and self._params.slippage_sizing:
            current = self._params.slippage_sizing.model_dump()
            for key, val in values.items():
                if key in ("premium", "discount") and isinstance(val, dict):
                    current[key].update(val)
                else:
                    current[key] = val
            self._params.slippage_sizing = SlippageSizingParameters(**current)
        elif group_name == "taker_reference" and self._params.taker_reference:
            current = self._params.taker_reference.model_dump()
            current.update(values)
            self._params.taker_reference = TakerReferenceParameters(**current)
        elif group_name == "funding" and self._params.funding:
            current = self._params.funding.model_dump()
            current.update(values)
            self._params.funding = FundingParameters(**current)
        elif group_name == "execution" and self._params.execution:
            current = self._params.execution.model_dump()
            current.update(values)
            self._params.execution = ExecutionParameters(**current)

        for callback in self._update_callbacks.get(group_name, []):
            callback(group_name, values)

    def enable_group(self, group_name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Enable an optional parameter group."""
        config = config or {}

        if group_name == "funding":
            self._params.funding = FundingParameters(**config)
        elif group_name == "taker_reference":
            self._params.taker_reference = TakerReferenceParameters(**config)
        elif group_name == "slippage_sizing":
            premium_config = config.get("premium", {})
            discount_config = config.get("discount", {})
            self._params.slippage_sizing = SlippageSizingParameters(
                premium=(
                    SlippageDirection(**premium_config)
                    if premium_config
                    else SlippageDirection(budget_bps=2.0, capture_pct=0.8)
                ),
                discount=(
                    SlippageDirection(**discount_config)
                    if discount_config
                    else SlippageDirection(budget_bps=5.0, capture_pct=0.95)
                ),
            )
        elif group_name == "execution":
            self._params.execution = ExecutionParameters(**config)
        elif group_name == "slippage_penalty":
            self._params.slippage_penalty = SlippagePenaltyParameters(**config)

    def disable_group(self, group_name: str) -> None:
        """Disable an optional parameter group (set to None)."""
        if group_name == "funding":
            self._params.funding = None
        elif group_name == "taker_reference":
            self._params.taker_reference = None
        elif group_name == "slippage_sizing":
            self._params.slippage_sizing = None
        elif group_name == "execution":
            self._params.execution = None
        elif group_name == "slippage_penalty":
            self._params.slippage_penalty = None

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Export as hierarchical dictionary."""
        return self._params.to_dict()
