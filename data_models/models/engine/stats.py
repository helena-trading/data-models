"""
Typed models for engine layer statistics.

These models provide Pydantic validation for engine statistics
and health monitoring data.
"""

from typing import Dict

from pydantic import Field

from data_models.models.domain.base import StrictBaseModel


class WebsocketHealthSummary(StrictBaseModel):
    """Health summary from WebSocketHealthService.get_health_summary()."""

    unhealthy_counts: Dict[str, int] = Field(description="Count of unhealthy checks per exchange")
    recovery_attempts: Dict[str, int] = Field(description="Recovery attempt count per exchange")
    recovery_in_progress: Dict[str, bool] = Field(description="Recovery in progress flag per exchange")
    failure_reasons: Dict[str, str] = Field(description="Last failure reason per exchange")


class SignalServiceStats(StrictBaseModel):
    """Stats from SignalService.get_stats()."""

    mode: str = Field(description="Signal service mode")
    pending_predictions: int = Field(description="Number of pending predictions")
    max_pending: int = Field(description="Maximum pending predictions allowed")
    ev_threshold_bps: float = Field(description="Expected value threshold in bps")
    db_logging_enabled: bool = Field(description="Whether database logging is enabled")
    fill_model_version: str = Field(description="Fill model version identifier")


class FillDetectorStats(StrictBaseModel):
    """Stats from FillSignalDetector.get_stats()."""

    maker_fills_detected: int = Field(default=0, description="Maker fills detected")
    taker_fills_detected: int = Field(default=0, description="Taker fills detected")
    partial_fills_detected: int = Field(default=0, description="Partial fills detected")
    fill_signals_published: int = Field(default=0, description="Fill signals published")
    orders_currently_tracked: int = Field(description="Orders currently being tracked")


__all__ = [
    "WebsocketHealthSummary",
    "SignalServiceStats",
    "FillDetectorStats",
]
