"""
Typed models for engine layer metrics.

These models provide Pydantic validation for engine performance metrics.
"""

from pydantic import Field

from data_models.models.domain.base import StrictBaseModel


class EngineMetrics(StrictBaseModel):
    """Typed engine performance metrics."""

    total_ticks_processed: int = Field(ge=0, description="Total ticks processed")
    successful_arbitrages: int = Field(ge=0, description="Successful arbitrage executions")
    failed_arbitrages: int = Field(ge=0, description="Failed arbitrage attempts")
    average_execution_time_ms: float = Field(ge=0, description="Average execution time")
    network_errors: int = Field(ge=0, description="Network error count")
    rate_limit_errors: int = Field(ge=0, description="Rate limit error count")
    uptime_seconds: float = Field(ge=0, description="Engine uptime in seconds")


__all__ = [
    "EngineMetrics",
]
