"""
Typed models for graph engine component statistics.

These models provide Pydantic validation for graph engine
statistics, optimization metrics, and performance data.
"""

from typing import Dict, List, Optional

from pydantic import Field

from data_models.models.domain.base import StrictBaseModel

# =============================================================================
# Graph Builder Stats
# =============================================================================


class GraphBuilderStats(StrictBaseModel):
    """Stats from GraphBuilder.get_graph_stats()."""

    nodes: int = Field(description="Number of nodes in graph")
    edges: int = Field(description="Number of edges in graph")
    exchanges: int = Field(default=0, description="Number of unique exchanges")
    pairs: int = Field(default=0, description="Number of unique trading pairs")


# =============================================================================
# Optimizer Stats
# =============================================================================


class OptimizerStats(StrictBaseModel):
    """Stats from SimpleOptimizer for optimization and performance metrics.

    Used by both get_optimization_stats() and get_performance_metrics().
    """

    optimization_count: int = Field(description="Total optimizations performed")
    last_best_spread: Optional[float] = Field(description="Last best spread found")
    optimizer_type: str = Field(description="Type of optimizer")
    algorithm: str = Field(description="Algorithm used for optimization")


# =============================================================================
# Opportunity Finder Stats
# =============================================================================


class OpportunitySearchStats(StrictBaseModel):
    """Stats from OpportunityFinder.get_search_stats()."""

    total_opportunities_found: int = Field(description="Total opportunities found")
    last_search_count: int = Field(description="Opportunities found in last search")
    finder_version: str = Field(description="Finder version identifier")


# =============================================================================
# Path State Manager Stats
# =============================================================================


class PathMetricsDetail(StrictBaseModel):
    """Detail for a single path in PathStateManager."""

    path_id: str = Field(description="Unique path identifier")
    state: str = Field(description="Current bot state name")
    opportunities_found: int = Field(description="Opportunities found for this path")
    orders_placed: int = Field(description="Orders placed for this path")
    orders_filled: int = Field(description="Orders filled for this path")
    volume: float = Field(description="Total volume for this path")
    profit: float = Field(description="Total profit for this path")


class PathStateMetrics(StrictBaseModel):
    """Stats from PathStateManager.get_metrics_summary()."""

    max_concurrent_paths: int = Field(description="Maximum concurrent paths allowed")
    active_paths: int = Field(description="Currently active paths")
    active_with_orders: int = Field(description="Active paths with pending orders")
    total_created: int = Field(description="Total paths created")
    total_completed: int = Field(description="Total paths completed")
    total_failed: int = Field(description="Total paths failed")
    active_paths_detail: List[PathMetricsDetail] = Field(description="Detailed metrics per active path")


# =============================================================================
# Graph Metrics Collector Stats
# =============================================================================


class TimingStats(StrictBaseModel):
    """Timing statistics for performance metrics."""

    mean: float = Field(default=0.0, description="Mean time in ms")
    median: float = Field(default=0.0, description="Median time in ms")
    min: float = Field(default=0.0, description="Minimum time in ms")
    max: float = Field(default=0.0, description="Maximum time in ms")
    p95: float = Field(default=0.0, description="95th percentile")
    p99: float = Field(default=0.0, description="99th percentile")


class OpportunityStats(StrictBaseModel):
    """Opportunity statistics in performance summary."""

    total_found: int = Field(description="Total opportunities found")
    total_executed: int = Field(description="Total opportunities executed")
    total_completed: int = Field(description="Total opportunities completed")
    total_failed: int = Field(description="Total opportunities failed")
    success_rate: float = Field(description="Overall success rate")
    active: int = Field(description="Currently active opportunities")


class ExecutionStats(StrictBaseModel):
    """Execution statistics in performance summary."""

    total_volume: float = Field(description="Total volume executed")
    total_profit: float = Field(description="Total profit realized")
    avg_profit_per_trade: float = Field(description="Average profit per completed trade")


class PerformanceTimingStats(StrictBaseModel):
    """Performance timing statistics."""

    tick_times_ms: TimingStats = Field(description="Tick processing times")
    order_latencies_ms: TimingStats = Field(description="Order latency times")
    execution_times_ms: TimingStats = Field(description="Execution times")


class ExchangePerformanceStats(StrictBaseModel):
    """Per-exchange performance statistics."""

    success_rate: float = Field(description="Success rate for this exchange")
    avg_latency_ms: float = Field(description="Average latency in ms")
    total_orders: int = Field(description="Total orders for this exchange")


class GraphAnalysisStats(StrictBaseModel):
    """Graph analysis statistics."""

    avg_nodes: float = Field(description="Average nodes analyzed")
    avg_opportunities_per_analysis: float = Field(description="Average opportunities found per analysis")
    analyses_performed: int = Field(description="Total analyses performed")


class GraphPerformanceSummary(StrictBaseModel):
    """Stats from GraphMetricsCollector.get_performance_summary()."""

    opportunities: OpportunityStats = Field(description="Opportunity statistics")
    execution: ExecutionStats = Field(description="Execution statistics")
    performance: PerformanceTimingStats = Field(description="Performance timing")
    exchanges: Dict[str, ExchangePerformanceStats] = Field(description="Per-exchange performance")
    graph_analysis: GraphAnalysisStats = Field(description="Graph analysis stats")
    path_types: Dict[str, int] = Field(description="Path type counts")


# =============================================================================
# Opportunity Manager Stats
# =============================================================================


class OpportunityManagerMetrics(StrictBaseModel):
    """Stats from OpportunityManager.get_performance_metrics()."""

    engine_type: str = Field(description="Engine type identifier")
    architecture: str = Field(description="Architecture type")
    optimization_count: int = Field(description="Total optimizations performed")
    last_best_spread: Optional[float] = Field(description="Last best spread found")
    optimizer_type: str = Field(description="Optimizer type used")
    algorithm: str = Field(description="Algorithm used")
    heat_tracker: Optional[Dict[str, int]] = Field(default=None, description="Heat tracker metrics if enabled")
    heat_tracking_enabled: bool = Field(description="Whether heat tracking is enabled")
    slippage_tracker: Optional[Dict[str, int]] = Field(default=None, description="Slippage tracker metrics if enabled")
    slippage_tracking_enabled: bool = Field(description="Whether slippage tracking is enabled")


# =============================================================================
# Graph Engine Stats
# =============================================================================


class GraphTickEngineStats(StrictBaseModel):
    """Stats from TickGraphMarketMakingEngine.get_engine_performance_stats()."""

    tick_count: int = Field(description="Total ticks processed")
    opportunities_executed: int = Field(description="Opportunities executed")
    failed_opportunities: int = Field(description="Failed opportunities")
    avg_tick_time_ms: float = Field(description="Average tick processing time")
    uptime_seconds: float = Field(description="Engine uptime in seconds")


__all__ = [
    # Graph Builder
    "GraphBuilderStats",
    # Optimizer
    "OptimizerStats",
    # Opportunity Finder
    "OpportunitySearchStats",
    # Path State Manager
    "PathMetricsDetail",
    "PathStateMetrics",
    # Graph Metrics Collector
    "TimingStats",
    "OpportunityStats",
    "ExecutionStats",
    "PerformanceTimingStats",
    "ExchangePerformanceStats",
    "GraphAnalysisStats",
    "GraphPerformanceSummary",
    # Opportunity Manager
    "OpportunityManagerMetrics",
    # Graph Engine
    "GraphTickEngineStats",
]
