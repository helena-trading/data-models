"""Bot parameter container with group-level enable/disable."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .groups import (
    ExecutionParameters,
    FundingParameters,
    SizingParameters,
    SlippagePenaltyParameters,
    SlippageSizingParameters,
    SpreadParameters,
    TakerReferenceParameters,
)


class BotParameters(BaseModel):
    """
    Bot parameters container with clear group semantics.

    Required Groups:
        - spread: Core spread parameters (always required)
        - sizing: Order sizing parameters (always required)

    Optional Groups (None = disabled, configured = enabled):
        - slippage_sizing: Direction-specific slippage bounds
        - taker_reference: Robust taker pricing with depth analysis
        - funding: Funding rate price adjustments
        - execution: Taker order execution behavior

    Usage:
        params = BotParameters(
            spread=SpreadParameters(...),
            sizing=SizingParameters(...),
            funding=None,  # Funding adjustment disabled
            slippage_sizing=SlippageSizingParameters(),  # Enabled with defaults
        )

        # Check if feature is enabled
        if params.funding is not None:
            horizon = params.funding.horizon_hours

        # Or use helper properties
        if params.is_funding_enabled:
            horizon = params.funding.horizon_hours
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # Required groups
    spread: SpreadParameters
    sizing: SizingParameters

    # Optional groups (None = disabled)
    slippage_sizing: Optional[SlippageSizingParameters] = None
    taker_reference: Optional[TakerReferenceParameters] = None
    funding: Optional[FundingParameters] = None
    execution: Optional[ExecutionParameters] = None
    slippage_penalty: Optional[SlippagePenaltyParameters] = None

    # =========================================================================
    # Feature Enable Checks (clean API)
    # =========================================================================

    @property
    def is_slippage_sizing_enabled(self) -> bool:
        """Check if slippage-bounded sizing is enabled."""
        return self.slippage_sizing is not None

    @property
    def is_taker_reference_enabled(self) -> bool:
        """Check if taker reference pricing is enabled."""
        return self.taker_reference is not None

    @property
    def is_funding_enabled(self) -> bool:
        """Check if funding rate adjustment is enabled."""
        return self.funding is not None

    @property
    def is_execution_custom(self) -> bool:
        """Check if custom execution parameters are configured."""
        return self.execution is not None

    @property
    def is_slippage_penalty_enabled(self) -> bool:
        """Check if slippage penalty is enabled."""
        return self.slippage_penalty is not None and self.slippage_penalty.enabled

    # =========================================================================
    # Safe Accessors with Defaults
    # =========================================================================

    def get_slippage_budget_bps(self, is_premium: bool) -> float:
        """Get slippage budget for direction, with fallback default."""
        if self.slippage_sizing is None:
            return 2.0 if is_premium else 5.0
        direction = self.slippage_sizing.premium if is_premium else self.slippage_sizing.discount
        return direction.budget_bps

    def get_slippage_capture_pct(self, is_premium: bool) -> float:
        """Get slippage capture percentage for direction, with fallback default."""
        if self.slippage_sizing is None:
            return 0.8 if is_premium else 0.95
        direction = self.slippage_sizing.premium if is_premium else self.slippage_sizing.discount
        return direction.capture_pct

    def get_funding_horizon_hours(self) -> float:
        """Get funding horizon, returns 0 if disabled."""
        return self.funding.horizon_hours if self.funding else 0.0

    def get_funding_safety_buffer(self) -> float:
        """Get funding safety buffer, returns 0 if disabled."""
        return self.funding.safety_buffer if self.funding else 0.0

    def get_funding_refresh_interval_sec(self) -> int:
        """Get funding refresh interval, returns 300 if disabled."""
        return self.funding.refresh_interval_sec if self.funding else 300

    def get_taker_timeout_ms(self) -> int:
        """Get taker timeout, with default fallback."""
        return self.execution.taker_timeout_ms if self.execution else 5000

    def get_wait_for_fill(self) -> bool:
        """Get wait_for_fill setting, with default fallback."""
        return self.execution.wait_for_fill if self.execution else True

    def get_taker_ref_depth_capture_pct(self) -> float:
        """Get taker reference depth capture percentage."""
        return self.taker_reference.depth_capture_pct if self.taker_reference else 0.03

    def get_taker_ref_levels(self) -> int:
        """Get taker reference orderbook levels."""
        return self.taker_reference.levels if self.taker_reference else 20

    def get_taker_ref_size_floor(self) -> float:
        """Get taker reference size floor."""
        return self.taker_reference.size_floor if self.taker_reference else 2000.0

    def get_taker_ref_size_cap(self) -> float:
        """Get taker reference size cap."""
        return self.taker_reference.size_cap if self.taker_reference else 30000.0

    def get_slippage_penalty_scale_factor(self) -> float:
        """Get slippage penalty scale factor."""
        return self.slippage_penalty.scale_factor if self.slippage_penalty else 0.5

    def get_slippage_penalty_max_bps(self) -> float:
        """Get slippage penalty maximum in basis points."""
        return self.slippage_penalty.max_penalty_bps if self.slippage_penalty else 20.0

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotParameters":
        """Create from dictionary."""
        return cls.model_validate(data)
