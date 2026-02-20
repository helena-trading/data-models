"""Versioned contracts for runtime <-> control-plane communication."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RUNTIME_CONTROL_PLANE_CONTRACT_VERSION = "runtime-control-plane.v1"
RuntimeStatus = Literal["starting", "running", "stopping", "stopped", "error"]


class RuntimeContractBase(BaseModel):
    """Base model for runtime/control-plane payloads."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    contract_version: str = Field(default=RUNTIME_CONTROL_PLANE_CONTRACT_VERSION)
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    sent_at: Optional[str] = None


class RuntimeStartResultContract(RuntimeContractBase):
    """Contract for runtime start responses."""

    container_id: str
    started_at: str
    status: RuntimeStatus


class RuntimeLogsResultContract(RuntimeContractBase):
    """Contract for runtime container log responses."""

    success: bool
    logs: Optional[Any] = None
    error: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None


class RuntimeVersionResultContract(RuntimeContractBase):
    """Contract for runtime version metadata responses."""

    success: bool
    version_info: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    error: Optional[str] = None


class RuntimeInitErrorReportContract(RuntimeContractBase):
    """Contract for runtime initialization/runtime fatal error callbacks."""

    error_message: str = "Unknown error"


class RuntimeHealthWebsocketContract(BaseModel):
    """WebSocket-specific health payload."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    status: str = "unknown"
    reconnect_count: int = Field(default=0, ge=0)
    last_heartbeat: Optional[str] = None
    uptime_seconds: int = Field(default=0, ge=0)
    last_error: Optional[str] = None
    exchanges: Optional[Dict[str, Any]] = None
    gateway_health_cache_metrics: Optional[Dict[str, Any]] = None


class RuntimeHealthEngineContract(BaseModel):
    """Engine-specific health payload."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    status: str = "healthy"
    last_tick: Optional[str] = None
    ticks_per_second: float = Field(default=0.0, ge=0.0)
    queued_orders: int = Field(default=0, ge=0)


class RuntimeHealthLatencyContract(BaseModel):
    """Latency metrics payload."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    tick_processing: Optional[int] = Field(default=None, ge=0)
    order_placement: Optional[int] = Field(default=None, ge=0)
    websocket_roundtrip: Optional[int] = Field(default=None, ge=0)


class RuntimeHealthRestFallbackContract(BaseModel):
    """REST fallback health payload."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    count_last_minute: int = Field(default=0, ge=0)
    total_requests_last_minute: int = Field(default=0, ge=0)
    rest_ratio: float = Field(default=0.0, ge=0.0)
    exchange_rest_fallbacks: Optional[Dict[str, Any]] = None


class RuntimeHealthPerformanceContract(BaseModel):
    """Performance metrics payload."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)
    orders_last_minute: int = Field(default=0, ge=0)
    trades_last_minute: int = Field(default=0, ge=0)
    errors_last_minute: int = Field(default=0, ge=0)
    latency_ms: RuntimeHealthLatencyContract = Field(default_factory=RuntimeHealthLatencyContract)
    rest_fallback: RuntimeHealthRestFallbackContract = Field(default_factory=RuntimeHealthRestFallbackContract)


class RuntimeHealthReportContract(RuntimeContractBase):
    """Contract for runtime health reporting callbacks."""

    websocket_health: RuntimeHealthWebsocketContract = Field(default_factory=RuntimeHealthWebsocketContract)
    engine_health: RuntimeHealthEngineContract = Field(default_factory=RuntimeHealthEngineContract)
    performance: RuntimeHealthPerformanceContract = Field(default_factory=RuntimeHealthPerformanceContract)
    routes: Dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = Field(default=60, ge=1)

__all__ = [
    "RUNTIME_CONTROL_PLANE_CONTRACT_VERSION",
    "RuntimeStatus",
    "RuntimeStartResultContract",
    "RuntimeLogsResultContract",
    "RuntimeVersionResultContract",
    "RuntimeInitErrorReportContract",
    "RuntimeHealthWebsocketContract",
    "RuntimeHealthEngineContract",
    "RuntimeHealthLatencyContract",
    "RuntimeHealthRestFallbackContract",
    "RuntimeHealthPerformanceContract",
    "RuntimeHealthReportContract",
]
