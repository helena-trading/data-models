"""
Typed models for broker layer statistics.

These models provide Pydantic validation for broker statistics
and performance metrics.
"""

from typing import Optional

from pydantic import Field

from data_models.models.domain.base import StrictBaseModel


class WebsocketPusherStats(StrictBaseModel):
    """Stats from WebsocketCachePusher.get_statistics()."""

    successful_updates: int = Field(description="Total successful cache updates")
    failed_updates: int = Field(description="Total failed cache updates")
    total_updates: int = Field(description="Total update attempts")
    success_rate: float = Field(description="Success rate percentage (0-100)")
    average_latency_ms: float = Field(description="Average push latency in milliseconds")
    uptime_seconds: float = Field(description="Time since pusher initialization")
    updates_per_second: float = Field(description="Current update rate")


class CancellationResult(StrictBaseModel):
    """Result of a cancellation attempt with rate limit info.

    This dataclass provides structured information about the outcome of a
    cancellation attempt. The broker handles nonce retry logic internally,
    so the engine only sees a simple success/fail result.

    Attributes:
        success: Whether the cancellation succeeded
        order_id: The order ID that was cancelled (or attempted)
        rate_limited: Whether a 429 rate limit error occurred
        backoff_until_ms: Unix timestamp (ms) until which to backoff
    """

    success: bool = Field(description="Whether cancellation succeeded")
    order_id: Optional[str] = Field(default=None, description="Order ID that was cancelled")
    rate_limited: bool = Field(default=False, description="Whether rate limited")
    backoff_until_ms: Optional[int] = Field(default=None, description="Backoff until timestamp (ms)")
    already_cancelled: bool = Field(default=False, description="Order was already cancelled on exchange")


__all__ = [
    "WebsocketPusherStats",
    "CancellationResult",
]
