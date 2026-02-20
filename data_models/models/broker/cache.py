"""
Typed models for broker layer operations.

These models provide Pydantic validation for broker communication,
cache statistics, and market data structures.
"""

from typing import Dict, List, Optional

from pydantic import Field

from data_models.models.domain.base import StrictBaseModel

# =============================================================================
# Opportunity Data Models
# =============================================================================


class SerializedOpportunity(StrictBaseModel):
    """Serialized representation of a GraphOpportunity for caching.

    This model represents the pre-serialized form of opportunities stored
    in the opportunity cache for fast reads by the command panel.
    """

    path: List[str] = Field(description="Path nodes [source, target]")
    maker_exchange: Optional[str] = Field(default=None, description="Maker exchange name")
    maker_contract: Optional[str] = Field(default=None, description="Maker contract symbol")
    maker_side: Optional[str] = Field(default=None, description="Maker order side (BUY/SELL)")
    taker_exchange: Optional[str] = Field(default=None, description="Taker exchange name")
    taker_contract: Optional[str] = Field(default=None, description="Taker contract symbol")
    taker_side: Optional[str] = Field(default=None, description="Taker order side (BUY/SELL)")
    raw_spread_pct: float = Field(description="Raw spread percentage")
    total_fees_pct: float = Field(description="Total fees percentage")
    net_profitability_pct: float = Field(description="Net profitability percentage")
    heat_score: float = Field(description="Heat score (0-1)")
    consistency_score: float = Field(description="Consistency score (0-1)")
    slippage_score: float = Field(description="Slippage score (0-1)")


class DiscoveryStats(StrictBaseModel):
    """Statistics from an opportunity discovery cycle.

    Contains timing metrics and counts from the graph traversal
    and opportunity finding process.
    """

    # From OpportunityDiscoverer
    graph_time_ms: float = Field(default=0.0, description="Time to build/update graph (ms)")
    edge_time_ms: float = Field(default=0.0, description="Time to update edge weights (ms)")
    find_time_ms: float = Field(default=0.0, description="Time to find opportunities (ms)")
    total_time_ms: float = Field(default=0.0, description="Total discovery time (ms)")
    opportunities_found: int = Field(default=0, description="Number of opportunities found")

    # From OpportunityManager (merged stats)
    total_opportunities: int = Field(default=0, description="Total opportunities before filtering")
    unwind_capable: int = Field(default=0, description="Opportunities capable of unwinding positions")
    position_safe: int = Field(default=0, description="Opportunities safe for position limits")


class BrokerOrderRequest(StrictBaseModel):
    """Typed order request for broker layer."""

    exchange: str = Field(description="Target exchange")
    symbol: str = Field(description="Trading pair symbol")
    side: str = Field(description="Order side (BUY/SELL)")
    order_type: str = Field(description="Order type (LIMIT/MARKET/POST_ONLY)")
    quantity: float = Field(gt=0, description="Order quantity")
    price: Optional[float] = Field(default=None, description="Order price (required for limit orders)")
    client_id: Optional[str] = Field(default=None, description="Client order ID")


class BrokerOrderResponse(StrictBaseModel):
    """Typed order response from broker layer."""

    success: bool = Field(description="Whether order was successful")
    order_id: Optional[str] = Field(default=None, description="Exchange order ID")
    client_id: Optional[str] = Field(default=None, description="Client order ID")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    exchange: str = Field(description="Exchange that processed the order")


class MarketDataSnapshot(StrictBaseModel):
    """Typed market data snapshot."""

    exchange: str = Field(description="Exchange name")
    symbol: str = Field(description="Trading pair symbol")
    best_bid: float = Field(gt=0, description="Best bid price")
    best_ask: float = Field(gt=0, description="Best ask price")
    bid_size: float = Field(ge=0, description="Best bid size")
    ask_size: float = Field(ge=0, description="Best ask size")
    timestamp: int = Field(description="Data timestamp")
    is_stale: bool = Field(default=False, description="Whether data is stale")


class BrokerStatusUpdate(StrictBaseModel):
    """Typed status update from broker operations."""

    exchange: str = Field(description="Exchange name")
    operation: str = Field(description="Operation type")
    status: str = Field(description="Operation status")
    timestamp: int = Field(description="Update timestamp")
    details: Optional[Dict[str, str]] = Field(default=None, description="Additional details")


class LoggedOrderData(StrictBaseModel):
    """Typed data for order logging in status brokers."""

    order_id: str = Field(description="Order ID")
    symbol: str = Field(description="Trading symbol")
    side: str = Field(description="Order side")
    quantity: float = Field(description="Order quantity")
    price: Optional[float] = Field(default=None, description="Order price")
    status: str = Field(description="Order status")
    timestamp: int = Field(description="Last update timestamp")


# =============================================================================
# Cache Stats Models - Typed returns for get_stats()/get_metrics() methods
# =============================================================================


class GenericCacheStats(StrictBaseModel):
    """Stats returned by GenericCache.get_metrics() / CacheMetrics.get_stats()."""

    updates_count: int = Field(description="Total update operations")
    reads_count: int = Field(description="Total read operations")
    cache_hits: int = Field(description="Successful cache lookups")
    cache_misses: int = Field(description="Failed cache lookups")
    hit_rate: float = Field(description="Cache hit rate as percentage")
    updates_per_minute: float = Field(description="Update rate per minute")
    uptime_seconds: float = Field(description="Cache uptime in seconds")
    active_entries: int = Field(description="Current number of cached entries")
    evictions_count: int = Field(description="Total evictions performed")
    max_entries: int = Field(description="Maximum cache capacity")
    memory_utilization: float = Field(description="Memory utilization percentage")


class PositionCacheStats(StrictBaseModel):
    """Stats returned by CentralizedPositionCache.get_stats()."""

    # Position metrics
    cached_positions: int = Field(description="Number of cached positions")
    total_updates: int = Field(description="Total position updates")
    total_reads: int = Field(description="Total position reads")
    cache_hits: int = Field(description="Position cache hits")
    cache_misses: int = Field(description="Position cache misses")
    hit_rate: float = Field(description="Position hit rate (0-1)")
    evictions: int = Field(description="Position evictions")
    updates_per_sec: float = Field(description="Position updates per second")
    reads_per_sec: float = Field(description="Position reads per second")

    # Balance metrics
    cached_balances: int = Field(description="Number of cached balances")
    balance_updates: int = Field(description="Total balance updates")
    balance_reads: int = Field(description="Total balance reads")
    balance_cache_hits: int = Field(description="Balance cache hits")
    balance_cache_misses: int = Field(description="Balance cache misses")
    balance_hit_rate: float = Field(description="Balance hit rate (0-1)")
    balance_evictions: int = Field(description="Balance evictions")
    balance_updates_per_sec: float = Field(description="Balance updates per second")
    balance_reads_per_sec: float = Field(description="Balance reads per second")

    # Overall
    runtime_seconds: float = Field(description="Cache runtime in seconds")


class OrderCacheStats(StrictBaseModel):
    """Stats returned by CentralizedOrderCache.get_stats()."""

    active_orders: int = Field(description="Number of active orders in cache")
    terminal_orders: int = Field(description="Number of terminal orders in cache")
    total_orders: int = Field(description="Total orders (active + terminal)")
    total_updates: int = Field(description="Total order updates processed")
    total_reads: int = Field(description="Total read operations")
    cache_hits: int = Field(description="Successful cache lookups")
    cache_misses: int = Field(description="Failed cache lookups")
    hit_rate: float = Field(description="Cache hit rate (0-1)")
    active_evictions: int = Field(description="Active order evictions")
    terminal_cleanups: int = Field(description="Terminal order cleanups")
    updates_per_sec: float = Field(description="Updates per second")
    reads_per_sec: float = Field(description="Reads per second")
    runtime_seconds: float = Field(description="Cache runtime in seconds")
    exchange_id_reverse_mappings: int = Field(description="Number of exchange ID reverse mappings")


class RequestCacheStats(StrictBaseModel):
    """Stats returned by CentralizedRequestCache.get_stats()."""

    total_entries: int = Field(description="Total number of request entries in cache")
    active_entries: int = Field(description="Number of non-terminal request entries")
    total_creates: int = Field(description="Total request creation operations")
    total_transitions: int = Field(description="Total state transitions applied")
    total_reads: int = Field(description="Total read operations")
    cache_hits: int = Field(description="Successful cache lookups")
    cache_misses: int = Field(description="Failed cache lookups")
    hit_rate: float = Field(description="Cache hit rate (0-1)")
    transition_rejections: int = Field(description="Invalid state transitions rejected")
    expired_cleanups: int = Field(description="Expired entries removed by cleanup")
    runtime_seconds: float = Field(description="Cache runtime in seconds")
    entries_by_state: Dict[str, int] = Field(description="Current entry count by request state")


class OrderbookCacheStats(StrictBaseModel):
    """Stats returned by CentralizedOrderbookCache.get_metrics()."""

    updates_count: int = Field(description="Total orderbook updates")
    reads_count: int = Field(description="Total read operations")
    cache_hits: int = Field(description="Successful cache lookups")
    cache_misses: int = Field(description="Failed cache lookups (not_found + stale)")
    cache_misses_not_found: int = Field(description="Orderbook missing from cache")
    cache_misses_stale: int = Field(description="Staleness rejections")
    hit_rate: float = Field(description="Cache hit rate percentage")
    updates_per_second: float = Field(description="Current update rate")
    uptime_seconds: float = Field(description="Cache uptime in seconds")
    active_orderbooks: int = Field(description="Number of cached orderbooks")
    evictions_count: int = Field(description="Total evictions performed")
    max_entries: int = Field(description="Maximum cache capacity")
    memory_utilization: float = Field(description="Memory utilization percentage")
    exchange_updates: Dict[str, int] = Field(description="Per-exchange update counts")
    exchange_reads: Dict[str, int] = Field(description="Per-exchange read counts")


class OpportunityCacheStats(StrictBaseModel):
    """Stats returned by CentralizedOpportunityCache.get_stats()."""

    thread_count: int = Field(description="Number of tracked threads")
    threads: List[str] = Field(description="List of thread IDs")
    updates_count: int = Field(description="Total updates")
    reads_count: int = Field(description="Total reads")
    updates_per_sec: float = Field(description="Updates per second")
    reads_per_sec: float = Field(description="Reads per second")
    runtime_seconds: float = Field(description="Cache runtime in seconds")


# =============================================================================
# Phase 1: Broker Stats Models - Orderbook Cache
# =============================================================================


class OrderbookMemoryStats(StrictBaseModel):
    """Stats from CentralizedOrderbookCache.get_memory_stats()."""

    current_entries: int = Field(description="Current number of cached orderbooks")
    max_entries: int = Field(description="Maximum allowed entries before eviction")
    memory_utilization: float = Field(description="Percentage of capacity used")
    evictions_count: int = Field(description="Total number of evictions performed")
    evictions_per_hour: float = Field(description="Rate of evictions per hour")
    lru_key: Optional[str] = Field(default=None, description="Least recently used cache key")
    mru_key: Optional[str] = Field(default=None, description="Most recently used cache key")


class MetricsDetail(StrictBaseModel):
    """Metrics breakdown for a cache dimension (exchange, contract, or pair).

    Used for per-exchange and per-contract statistics in orderbook cache.
    Tracks cache performance including hit/miss counts, hit rate, and miss categorization.
    """

    updates: int = Field(description="Total updates for this dimension")
    hits: int = Field(description="Cache hits for this dimension")
    misses: int = Field(description="Cache misses for this dimension")
    hit_rate: float = Field(description="Hit rate percentage")
    miss_not_found: int = Field(default=0, description="Misses due to key not found")
    miss_no_timestamp: int = Field(default=0, description="Misses due to no timestamp")
    miss_stale: int = Field(default=0, description="Misses due to stale data")


# Type aliases for backward compatibility
ExchangeMetricsDetail = MetricsDetail
ContractMetricsDetail = MetricsDetail


class ExchangeContractMetricsDetail(StrictBaseModel):
    """Per exchange:contract pair metrics."""

    updates: int = Field(description="Total updates for this pair")
    hits: int = Field(description="Cache hits for this pair")
    misses: int = Field(description="Cache misses for this pair")
    hit_rate: float = Field(description="Hit rate percentage")


class OrderbookOverallStats(StrictBaseModel):
    """Overall orderbook cache performance metrics."""

    updates_count: int = Field(description="Total orderbook updates")
    reads_count: int = Field(description="Total read operations")
    cache_hits: int = Field(description="Successful cache lookups")
    cache_misses: int = Field(description="Failed cache lookups")
    hit_rate: float = Field(description="Cache hit rate percentage")
    updates_per_second: float = Field(description="Current update rate")
    uptime_seconds: float = Field(description="Cache uptime in seconds")
    active_orderbooks: int = Field(description="Number of cached orderbooks")
    evictions_count: int = Field(description="Total evictions performed")
    max_entries: int = Field(description="Maximum cache capacity")
    memory_utilization: float = Field(description="Memory utilization percentage")


class OrderbookRollingStats(StrictBaseModel):
    """Rolling window statistics for orderbook cache."""

    window_seconds: int = Field(description="Rolling window size in seconds")
    updates: int = Field(description="Updates in window")
    hits: int = Field(description="Hits in window")
    misses: int = Field(description="Misses in window")
    hit_rate: float = Field(description="Hit rate in window")


class OrderbookCacheStatistics(StrictBaseModel):
    """Comprehensive stats from CentralizedOrderbookCache.get_cache_statistics()."""

    overall: OrderbookOverallStats = Field(description="Overall cache performance")
    by_exchange: Dict[str, MetricsDetail] = Field(description="Stats by exchange")
    by_contract: Dict[str, MetricsDetail] = Field(description="Stats by contract")
    by_exchange_contract: Dict[str, ExchangeContractMetricsDetail] = Field(description="Top 10 exchange:contract pairs")
    rolling: OrderbookRollingStats = Field(description="Rolling window averages")


# =============================================================================
# Phase 1: Broker Stats Models - Order Cache
# =============================================================================


class ExchangeCallbackHealth(StrictBaseModel):
    """Health status for a single exchange's callbacks."""

    last_update_seconds_ago: float = Field(description="Seconds since last update")
    status: str = Field(description="Status: healthy | stale | dead")


class CallbackHealthSummary(StrictBaseModel):
    """Per-exchange callback health from CentralizedOrderCache.get_callback_health_summary()."""

    exchanges: Dict[str, ExchangeCallbackHealth] = Field(description="Health by exchange")


__all__ = [
    "BrokerOrderRequest",
    "BrokerOrderResponse",
    "MarketDataSnapshot",
    "BrokerStatusUpdate",
    "LoggedOrderData",
    # Cache stats models (typed returns for get_stats()/get_metrics())
    "GenericCacheStats",
    "PositionCacheStats",
    "OrderCacheStats",
    "RequestCacheStats",
    "OrderbookCacheStats",
    "OpportunityCacheStats",
    # Phase 1: Orderbook cache stats
    "OrderbookMemoryStats",
    "MetricsDetail",
    "ExchangeMetricsDetail",  # Alias for MetricsDetail (backward compatibility)
    "ContractMetricsDetail",  # Alias for MetricsDetail (backward compatibility)
    "ExchangeContractMetricsDetail",
    "OrderbookOverallStats",
    "OrderbookRollingStats",
    "OrderbookCacheStatistics",
    # Phase 1: Order cache callback health
    "ExchangeCallbackHealth",
    "CallbackHealthSummary",
]
