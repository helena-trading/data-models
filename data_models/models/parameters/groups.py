"""Hierarchical parameter group models with Pydantic validation.

All spread/percentage parameters are in percentage format:
- 0.20 = 0.20% = 20 basis points
- 1.00 = 1.00% = 100 basis points
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ===========================================================================
# Required Groups (always present)
# ===========================================================================


class SpreadParameters(BaseModel):
    """Core spread parameters for market-making.

    All values in percentage format where 0.25 = 0.25% = 25 basis points.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    target_premium: float = Field(
        ...,
        ge=-5.0,
        le=5.0,
        description="Target spread for premium direction (buying on maker). Can be negative for exits.",
    )
    target_discount: float = Field(
        ...,
        ge=-5.0,
        le=5.0,
        description="Target spread for discount direction (selling on maker). Can be negative for exits.",
    )
    taker_spread: float = Field(
        ...,
        ge=0.001,
        le=1.0,
        description="Additional spread threshold for aggressive taker orders",
    )
    max_target_deviation: float = Field(
        ...,
        ge=0.001,
        le=0.1,
        description="Cancel maker if price moves beyond this threshold",
    )
    max_size_deviation: float = Field(
        default=30.0,
        ge=0.0,
        le=100.0,
        description="Cancel maker if taker liquidity changes beyond this % threshold (default 30%)",
    )


class SizingParameters(BaseModel):
    """Order sizing parameters."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    amount_cap: float = Field(
        ...,
        gt=0,
        le=1_000_000.0,
        description="Maximum trade amount in USD (cap for dynamic sizing)",
    )
    amount_floor: float = Field(
        ...,
        gt=0,
        le=1_000_000.0,
        description="Minimum trade amount in USD (floor for dynamic sizing)",
    )
    max_notional_premium: float = Field(
        ...,
        ge=0,
        le=10_000_000.0,
        description="Maximum notional position for premium direction",
    )
    max_notional_discount: float = Field(
        ...,
        ge=0,
        le=10_000_000.0,
        description="Maximum notional position for discount direction",
    )
    min_dist_maker: float = Field(
        default=100.0,
        ge=0.001,
        le=10_000.0,
        description="Minimum distance for maker orders in quote currency",
    )
    is_dollar_amt: bool = Field(
        default=True,
        description="Whether trade amounts are in quote currency (USD) or base currency",
    )

    @model_validator(mode="after")
    def validate_floor_not_exceeds_cap(self) -> "SizingParameters":
        if self.amount_floor > self.amount_cap:
            raise ValueError(f"amount_floor ({self.amount_floor}) cannot exceed amount_cap ({self.amount_cap})")
        return self


# ===========================================================================
# Optional Groups (None = disabled, configured = enabled)
# ===========================================================================


class SlippageDirection(BaseModel):
    """Slippage parameters for a single direction (premium or discount)."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    budget_bps: float = Field(
        ...,
        ge=0.1,
        le=100.0,
        description="Maximum acceptable slippage in basis points",
    )
    capture_pct: float = Field(
        ...,
        ge=0.1,
        le=1.0,
        description="Percentage of liquidity within budget to capture",
    )


class SlippageSizingParameters(BaseModel):
    """Direction-specific slippage-bounded sizing parameters.

    When this group is configured, order sizing uses slippage budget
    instead of fixed depth capture percentage.

    Premium = conservative (accumulating position)
    Discount = aggressive (exiting position)
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    premium: SlippageDirection = Field(
        default_factory=lambda: SlippageDirection(budget_bps=2.0, capture_pct=0.8),
        description="Slippage config for premium (conservative, accumulating)",
    )
    discount: SlippageDirection = Field(
        default_factory=lambda: SlippageDirection(budget_bps=5.0, capture_pct=0.95),
        description="Slippage config for discount (aggressive, exiting)",
    )


class TakerReferenceParameters(BaseModel):
    """Robust taker reference pricing parameters.

    When configured, uses VWAP-based taker pricing with depth checks
    instead of simple BBO prices.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    depth_capture_pct: float = Field(
        default=0.03,
        ge=0.001,
        le=1.0,
        description="Percentage of available depth to capture for sizing",
    )
    levels: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Number of orderbook levels to consider",
    )
    size_floor: float = Field(
        default=2000.0,
        ge=10.0,
        le=1_000_000.0,
        description="Minimum order size from depth calculation in USD",
    )
    size_cap: float = Field(
        default=30000.0,
        ge=10.0,
        le=1_000_000.0,
        description="Maximum order size from depth calculation in USD",
    )

    @model_validator(mode="after")
    def validate_floor_not_exceeds_cap(self) -> "TakerReferenceParameters":
        if self.size_floor > self.size_cap:
            raise ValueError(f"size_floor ({self.size_floor}) cannot exceed size_cap ({self.size_cap})")
        return self


class FundingParameters(BaseModel):
    """Funding rate adjustment parameters.

    When configured, adjusts quote prices based on expected funding
    costs/benefits over the holding horizon.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    horizon_hours: float = Field(
        default=8.0,
        ge=0.5,
        le=48.0,
        description="Hours to project funding costs for price adjustment",
    )
    safety_buffer: float = Field(
        default=0.0,
        ge=0.0,
        le=0.01,
        description="Safety buffer for funding rate (decimal, e.g., 0.0001 = 1bp)",
    )
    refresh_interval_sec: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="How often to refresh funding rates",
    )


class ExecutionParameters(BaseModel):
    """Order execution behavior parameters.

    When configured, controls taker order execution timing and orderbook staleness.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    wait_for_fill: bool = Field(
        default=True,
        description="Wait for taker order to fill completely before processing",
    )
    taker_timeout_ms: int = Field(
        default=5000,
        ge=100,
        le=60000,
        description="Taker order timeout in milliseconds",
    )
    accepted_slippage: float = Field(
        default=0.5,
        ge=0.01,
        le=5.0,
        description="Accepted slippage percentage for taker order price adjustment",
    )
    maker_staleness_threshold_ms: int = Field(
        default=2000,
        ge=100,
        le=30000,
        description="Maximum age in ms for maker orderbook before considered stale",
    )
    taker_staleness_threshold_ms: int = Field(
        default=2000,
        ge=100,
        le=30000,
        description="Maximum age in ms for taker orderbook before considered stale",
    )


class SlippagePenaltyParameters(BaseModel):
    """Parameters for slippage-based cost penalty.

    When configured, historical slippage is treated as an additional cost
    (like fees) and deducted from net profitability calculations.

    Formula: penalty_bps = min(max(0, ema_slippage_bps) * scale_factor, max_penalty_bps)

    Only adverse slippage (worse than expected) is penalized.
    Favorable slippage (better than expected) returns 0 penalty.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable slippage penalty as an additional fee in spread calculations",
    )
    scale_factor: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Multiply historical slippage by this factor (0.5 = 10 bps slippage → 5 bps penalty)",
    )
    max_penalty_bps: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Maximum penalty in basis points (cap to prevent extreme adjustments)",
    )
