"""
Data models for the graph-based arbitrage engine.

Pydantic models for graph arbitrage opportunities, configuration, and tolerance settings.
"""

from enum import Enum
from typing import Dict, List, NamedTuple, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from data_models.models.enums.trading import BotState


class RawOpportunity(NamedTuple):
    """Lightweight representation of a graph opportunity (source, target, spread).

    Used as intermediate data structure during opportunity discovery before
    building full GraphOpportunity objects. NamedTuple for performance and hashability.
    """

    source: str
    """Source node ID (format: exchange:pair:role:side)"""

    target: str
    """Target node ID (format: exchange:pair:role:side)"""

    spread: float
    """Net spread/profitability as decimal (e.g., 0.001 = 10 bps)"""


class ExchangeCapabilities(BaseModel):
    """
    Defines exchange role capabilities for graph arbitrage.

    Controls which exchanges can act as makers (limit orders) vs takers (market-taking orders)
    in the graph engine. Used for debugging specific exchange behaviors and production risk management.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    exchange_name: str = Field(..., description="Exchange identifier (e.g., 'binance_futures', 'bybit')")
    can_be_maker: bool = Field(default=True, description="Whether exchange can place maker (limit) orders")
    can_be_taker: bool = Field(default=True, description="Whether exchange can take (execute against) orders")


class SensitivityMode(Enum):
    """Bot sensitivity modes for opportunity switching."""

    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class GraphNode(BaseModel):
    """Represents a node in the arbitrage graph (exchange-pair combination)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    node_id: str = Field(..., description="Format: exchange_name:PAIR")
    exchange_name: str = Field(..., description="Exchange name")
    pair: str = Field(..., description="Trading pair")
    trade_type: str = Field(default="spot", description="Trade type: spot or futures")

    def __str__(self) -> str:
        return self.node_id

    @classmethod
    def from_id(cls, node_id: str) -> "GraphNode":
        """Create a GraphNode from its ID string."""
        parts = node_id.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid node ID format: {node_id}")

        exchange_name, pair = parts
        return cls(node_id=node_id, exchange_name=exchange_name, pair=pair)


class GraphEdge(BaseModel):
    """Represents an edge in the arbitrage graph (arbitrage opportunity)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    source_node: str = Field(..., description="Source node ID")
    target_node: str = Field(..., description="Target node ID")
    weight: float = Field(..., description="Net spread (profit potential)")
    edge_type: str = Field(..., description="Edge type: same-pair or cross-pair")
    volume_limit: Optional[float] = Field(None, description="Maximum volume for this edge")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread_percentage(self) -> float:
        """Return spread as a percentage."""
        return self.weight * 100


class GraphOpportunity(BaseModel):
    """Represents a complete arbitrage opportunity (path through the graph)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    path: List[str] = Field(..., description="Node IDs in sequence")
    raw_spread: float = Field(..., description="Raw market spread (no fees deducted)")
    total_fees: float = Field(..., description="Total maker + taker fees")
    net_profitability: float = Field(..., description="Net profit after fees (used for ranking)")
    path_type: str = Field(..., description="Path type: direct or chained")
    edge_weights: List[float] = Field(default_factory=list, description="Weights for each edge")
    required_volume: Optional[float] = Field(None, description="Required volume for opportunity")
    estimated_profit: Optional[float] = Field(None, description="Estimated profit in USD")
    # Unwinding metadata (set during position unwinding)
    unwind_value: Optional[float] = Field(None, description="USD value of position being unwound")
    position_key: Optional[str] = Field(None, description="Key identifying the position being unwound")

    # Heat tracking metadata (set during opportunity discovery)
    heat_score: float = Field(default=1.0, description="Current spread vs historical average (>1.0 = hot market)")
    consistency_score: float = Field(default=0.5, description="How consistently this market produces good spreads (0-1)")

    # Slippage tracking metadata (set during opportunity discovery)
    slippage_score: float = Field(default=1.0, description="Execution quality score (0=high slippage, 1=low slippage)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source(self) -> str:
        """Get the source node of the path."""
        return self.path[0] if self.path else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def target(self) -> str:
        """Get the target node of the path."""
        return self.path[-1] if self.path else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def length(self) -> int:
        """Get the number of edges in the path."""
        return len(self.path) - 1 if len(self.path) > 1 else 0

    def is_direct(self) -> bool:
        """Check if this is a direct (single-edge) opportunity."""
        return self.length == 1

    def is_triangular(self) -> bool:
        """Check if this is a triangular arbitrage opportunity."""
        return self.length == 3 and self.path[0] == self.path[-1]


class GraphConfig(BaseModel):
    """Configuration for graph-based arbitrage mode."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    enabled: bool = Field(default=False, description="Enable graph arbitrage mode")
    max_concurrent_paths: int = Field(default=50, description="Maximum concurrent path executions")
    path_types: List[str] = Field(default_factory=lambda: ["direct"], description="Allowed path types")
    refresh_interval_ms: int = Field(default=100, description="Graph refresh interval in milliseconds")
    max_path_length: int = Field(default=3, description="Maximum edges in a path")
    enable_triangular: bool = Field(default=False, description="Enable triangular arbitrage")
    enable_cross_pair: bool = Field(default=False, description="Enable cross-pair arbitrage")

    # Performance tuning
    cache_ttl_ms: int = Field(default=100, description="Orderbook cache time-to-live")
    incremental_updates: bool = Field(default=True, description="Use incremental updates")

    # Risk management
    conflict_resolution: str = Field(default="skip", description="Conflict resolution: skip or queue")

    @model_validator(mode="after")
    def validate_config(self) -> "GraphConfig":
        """Validate configuration values."""
        if self.max_concurrent_paths <= 0:
            raise ValueError("max_concurrent_paths must be positive")
        if self.refresh_interval_ms <= 0:
            raise ValueError("refresh_interval_ms must be positive")
        if not self.path_types:
            raise ValueError("path_types cannot be empty")
        return self


class GraphToleranceConfig(BaseModel):
    """
    Configuration for graph arbitrage tolerance system.

    Controls when to cancel orders and switch opportunities based on
    spread changes, better opportunities, and time-based thresholds.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Spread degradation thresholds (in basis points)
    spread_degradation_tolerance_bps: float = Field(
        default=10.0, description="Cancel maker order if spread drops by this many basis points"
    )
    target_spread_bps: float = Field(
        default=5.0,
        description="Target spread for metrics/logging only (NOT a filter - market-making bot trades ALL spreads)",
    )

    # Opportunity switching thresholds (in basis points)
    better_opportunity_threshold_bps: float = Field(
        default=20.0, description="Minimum spread improvement required to consider switching opportunities"
    )
    switch_penalty_by_state: Dict[BotState, float] = Field(
        default_factory=lambda: {
            BotState.START: 0.0,  # No penalty when idle
            BotState.CREATING_MAKER: 10.0,  # Small penalty when creating order
            BotState.MAKER_LIVE: 20.0,  # Higher penalty when order is live in market
        },
        description="Additional threshold required based on current execution state",
    )

    # Time-based thresholds (in milliseconds)
    opportunity_persistence_ms: int = Field(
        default=100, description="Opportunity must exist for this long before acting on it"
    )
    maker_fill_timeout_ms: int = Field(default=5000, description="Maximum time to wait for maker order fill before cancelling")
    cooldown_after_cancel_ms: int = Field(
        default=500, description="Cooldown period before re-entering same opportunity after cancellation"
    )
    spread_check_interval_ms: int = Field(default=50, description="How often to check spread degradation for active orders")

    # Sensitivity mode and multipliers
    sensitivity_mode: SensitivityMode = Field(
        default=SensitivityMode.BALANCED, description="Overall sensitivity mode for the bot"
    )
    sensitivity_multipliers: Dict[SensitivityMode, float] = Field(
        default_factory=lambda: {
            SensitivityMode.AGGRESSIVE: 0.5,  # Half all thresholds
            SensitivityMode.BALANCED: 1.0,  # Normal thresholds
            SensitivityMode.CONSERVATIVE: 2.0,  # Double all thresholds
        },
        description="Multipliers applied to all thresholds based on sensitivity mode",
    )

    # Advanced parameters
    max_consecutive_cancellations: int = Field(
        default=3, description="Maximum consecutive cancellations before increasing thresholds"
    )
    dynamic_threshold_adjustment: bool = Field(
        default=True, description="Enable automatic threshold adjustment based on performance"
    )
    threshold_increase_factor: float = Field(
        default=1.2, description="Factor to increase thresholds after excessive cancellations"
    )
    threshold_decay_time_ms: int = Field(
        default=60000, description="Time for increased thresholds to decay back to normal (1 minute)"
    )

    def get_effective_spread_degradation_tolerance(self) -> float:
        """Get spread degradation tolerance adjusted for sensitivity mode."""
        multiplier = self.sensitivity_multipliers[self.sensitivity_mode]
        return self.spread_degradation_tolerance_bps * multiplier

    def get_effective_switch_threshold(self, current_state: BotState) -> float:
        """
        Get opportunity switch threshold adjusted for sensitivity and state.

        Args:
          current_state: Current bot execution state

        Returns:
          Effective threshold in basis points
        """
        base_threshold = self.better_opportunity_threshold_bps
        state_penalty = self.switch_penalty_by_state.get(current_state, 0.0)
        multiplier = self.sensitivity_multipliers[self.sensitivity_mode]

        return (base_threshold + state_penalty) * multiplier

    def get_effective_persistence_ms(self) -> int:
        """Get persistence requirement adjusted for sensitivity mode."""
        multiplier = self.sensitivity_multipliers[self.sensitivity_mode]
        return int(self.opportunity_persistence_ms * multiplier)

    def should_cancel_for_spread_degradation(self, original_spread_bps: float, current_spread_bps: float) -> bool:
        """
        Check if order should be cancelled due to spread degradation.

        Args:
          original_spread_bps: Original spread when order was placed
          current_spread_bps: Current spread

        Returns:
          True if order should be cancelled
        """
        degradation = original_spread_bps - current_spread_bps
        tolerance = self.get_effective_spread_degradation_tolerance()

        # MARKET-MAKING: Only cancel if degraded beyond tolerance
        # We continue trading even below target_spread_bps
        # as that's just a profitability target, NOT a filter
        if current_spread_bps < self.target_spread_bps:
            # Log but don't cancel - we're a market maker
            pass  # Could add logging here if needed

        return degradation > tolerance

    def should_switch_opportunity(self, current_spread_bps: float, new_spread_bps: float, current_state: BotState) -> bool:
        """
        Check if bot should switch to a new opportunity.

        Args:
          current_spread_bps: Spread of current opportunity
          new_spread_bps: Spread of new opportunity
          current_state: Current execution state

        Returns:
          True if should switch to new opportunity
        """
        improvement = new_spread_bps - current_spread_bps
        threshold = self.get_effective_switch_threshold(current_state)

        return improvement > threshold

    @classmethod
    def from_sensitivity_mode(cls, mode: SensitivityMode) -> "GraphToleranceConfig":
        """
        Create config with preset values for a sensitivity mode.

        Args:
          mode: Desired sensitivity mode

        Returns:
          Configured GraphToleranceConfig instance
        """
        config = cls(sensitivity_mode=mode)

        if mode == SensitivityMode.AGGRESSIVE:
            # Aggressive: Quick to cancel, quick to switch
            config.spread_degradation_tolerance_bps = 5.0
            config.better_opportunity_threshold_bps = 10.0
            config.opportunity_persistence_ms = 50
            config.maker_fill_timeout_ms = 3000

        elif mode == SensitivityMode.CONSERVATIVE:
            # Conservative: Slow to cancel, slow to switch
            config.spread_degradation_tolerance_bps = 20.0
            config.better_opportunity_threshold_bps = 40.0
            config.opportunity_persistence_ms = 200
            config.maker_fill_timeout_ms = 10000

        # BALANCED uses default values

        return config


__all__ = [
    "ExchangeCapabilities",
    "RawOpportunity",
    "SensitivityMode",
    "GraphNode",
    "GraphEdge",
    "GraphOpportunity",
    "GraphConfig",
    "GraphToleranceConfig",
]
