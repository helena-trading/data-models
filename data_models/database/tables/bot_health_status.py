"""Bot health event model for logging health issues.

This table stores health EVENTS (issues/anomalies), not continuous status.
Events are logged when something goes wrong, not on every health check.

Event types:
- websocket_disconnected: WebSocket connection lost
- websocket_error: WebSocket error occurred
- websocket_reconnected: WebSocket reconnected after disconnection
- high_rest_ratio: REST fallback ratio exceeded threshold (>15%)
- high_error_rate: Error count exceeded threshold
- engine_unhealthy: Engine status changed to unhealthy
- engine_recovered: Engine status recovered to healthy
- websocket_unhealthy: WebSocket status changed to unhealthy
- websocket_failed: WebSocket status changed to failed
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb
from sqlalchemy import (
    ARRAY,
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import func

from data_models.database.tables.base import Base

# Valid event types for health logging
HEALTH_EVENT_TYPES = [
    "websocket_disconnected",
    "websocket_error",
    "websocket_reconnected",
    "websocket_unhealthy",
    "websocket_failed",
    "high_rest_ratio",
    "high_error_rate",
    "engine_unhealthy",
    "engine_recovered",
]


class BotHealthStatus(Base):  # type: ignore[misc,no-any-unimported]
    """Health event records - logged only when issues occur."""

    __tablename__ = "bot_health_status"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to bots table (nullable to handle cross-database references)
    # NOTE: Bots table is in credentials DB, health_status is in analytics DB
    bot_id = Column(Integer, nullable=False)  # Removed ForeignKey - cross-DB reference not supported

    # Event type - what triggered this log entry
    event_type = Column(String(50), nullable=False, default="unknown")

    # Timestamp of health event
    reported_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.current_timestamp(),
    )

    # Overall WebSocket status at time of event
    websocket_status = Column(String(50), nullable=False, default="unknown")

    # WebSocket metrics
    reconnect_count = Column(Integer, default=0)
    last_heartbeat = Column(DateTime(timezone=True))
    uptime_seconds = Column(Integer, default=0)
    last_error = Column(Text)

    # Per-exchange health status (JSON)
    exchanges_health = Column(JSON)

    # Engine health metrics
    engine_status = Column(String(50), default="healthy")
    last_tick = Column(DateTime(timezone=True))
    ticks_per_second = Column(Numeric(10, 2))
    queued_orders = Column(Integer, default=0)

    # Performance metrics (last period)
    orders_last_minute = Column(Integer, default=0)
    trades_last_minute = Column(Integer, default=0)
    errors_last_minute = Column(Integer, default=0)

    # Latency metrics (milliseconds)
    tick_processing_latency_ms = Column(Integer)
    order_placement_latency_ms = Column(Integer)
    websocket_roundtrip_ms = Column(Integer)

    # Route tracking
    active_routes: Mapped[List[str]] = Column(ARRAY(String), default=lambda: [])  # type: ignore[assignment]
    route_statistics = Column(JSON)

    # NOTE: Relationship removed - bot_id is a logical reference only (cross-DB)
    # bot = relationship("Bot", back_populates="health_status_reports")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "websocket_status IN ('healthy', 'connected', 'unhealthy', 'disconnected', 'error', 'failed', 'unknown')",
            name="check_websocket_status",
        ),
        CheckConstraint(
            "event_type IN ('websocket_disconnected', 'websocket_error', 'websocket_reconnected', "
            "'websocket_unhealthy', 'websocket_failed', "
            "'high_rest_ratio', 'high_error_rate', 'engine_unhealthy', 'engine_recovered', 'unknown')",
            name="check_event_type",
        ),
        Index("idx_bot_health_status_bot_id", "bot_id"),
        Index("idx_bot_health_status_reported_at", "reported_at", postgresql_using="btree"),
        Index(
            "idx_bot_health_status_bot_id_reported_at",
            "bot_id",
            "reported_at",
            postgresql_using="btree",
        ),
        Index("idx_bot_health_status_event_type", "event_type"),
    )

    def __repr__(self) -> str:
        return (
            "<BotHealthStatus("
            f"bot_id={self.bot_id}, "
            f"event_type={self.event_type}, "
            f"websocket_status={self.websocket_status}, "
            f"reported_at={self.reported_at}"
            ")>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "event_type": self.event_type,
            # Always include milliseconds for HFT precision analysis
            "reported_at": self.reported_at.isoformat(timespec="milliseconds") if self.reported_at else None,
            "websocket_status": self.websocket_status,
            "reconnect_count": self.reconnect_count,
            "last_heartbeat": (self.last_heartbeat.isoformat(timespec="milliseconds") if self.last_heartbeat else None),
            "uptime_seconds": self.uptime_seconds,
            "last_error": self.last_error,
            "exchanges_health": self.exchanges_health,
            "engine_status": self.engine_status,
            "last_tick": self.last_tick.isoformat(timespec="milliseconds") if self.last_tick else None,
            "ticks_per_second": (float(self.ticks_per_second) if self.ticks_per_second else None),
            "queued_orders": self.queued_orders,
            "orders_last_minute": self.orders_last_minute,
            "trades_last_minute": self.trades_last_minute,
            "errors_last_minute": self.errors_last_minute,
            "tick_processing_latency_ms": self.tick_processing_latency_ms,
            "order_placement_latency_ms": self.order_placement_latency_ms,
            "websocket_roundtrip_ms": self.websocket_roundtrip_ms,
            "active_routes": self.active_routes or [],
            "route_statistics": self.route_statistics or {},
        }

    @classmethod
    def from_event(
        cls,
        bot_id: int,
        event_type: str,
        websocket_status: str = "unknown",
        engine_status: str = "healthy",
        last_error: Optional[str] = None,
        reconnect_count: int = 0,
        uptime_seconds: int = 0,
        exchanges_health: Optional[Dict[str, Any]] = None,
        rest_fallback_ratio: Optional[float] = None,
        errors_last_minute: int = 0,
    ) -> "BotHealthStatus":
        """Create a health event record.

        Args:
            bot_id: Bot ID
            event_type: Type of event (see HEALTH_EVENT_TYPES)
            websocket_status: Current WebSocket status
            engine_status: Current engine status
            last_error: Error message if applicable
            reconnect_count: Number of reconnections
            uptime_seconds: Bot uptime in seconds
            exchanges_health: Per-exchange health data
            rest_fallback_ratio: REST fallback ratio (for high_rest_ratio events)
            errors_last_minute: Error count (for high_error_rate events)
        """
        return cls(
            bot_id=bot_id,
            event_type=event_type,
            websocket_status=websocket_status,
            engine_status=engine_status,
            last_error=last_error,
            reconnect_count=reconnect_count,
            uptime_seconds=uptime_seconds,
            exchanges_health=exchanges_health,
            errors_last_minute=errors_last_minute,
        )

    @staticmethod
    def batch_insert_query() -> str:
        """Get batch insert query for multiple health event records."""
        return """
            INSERT INTO bot_health_status (
                bot_id, event_type, reported_at, websocket_status, reconnect_count,
                last_heartbeat, uptime_seconds, last_error, exchanges_health,
                engine_status, last_tick, ticks_per_second, queued_orders,
                orders_last_minute, trades_last_minute, errors_last_minute,
                tick_processing_latency_ms, order_placement_latency_ms,
                websocket_roundtrip_ms, active_routes, route_statistics
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_insert_query(self) -> tuple[str, tuple[Any, ...]]:
        """Generate INSERT query parameters for this health event."""
        return (
            self.batch_insert_query(),
            (
                self.bot_id,
                self.event_type or "unknown",
                self.reported_at if self.reported_at else datetime.now(timezone.utc),
                self.websocket_status,
                self.reconnect_count,
                self.last_heartbeat,
                self.uptime_seconds,
                self.last_error,
                Jsonb(self.exchanges_health) if self.exchanges_health is not None else None,
                self.engine_status,
                self.last_tick,
                self.ticks_per_second,
                self.queued_orders,
                self.orders_last_minute,
                self.trades_last_minute,
                self.errors_last_minute,
                self.tick_processing_latency_ms,
                self.order_placement_latency_ms,
                self.websocket_roundtrip_ms,
                self.active_routes,
                Jsonb(self.route_statistics) if self.route_statistics is not None else None,
            ),
        )

    @classmethod
    def from_health_report(cls, bot_id: int, event_type: str, health_data: Dict[str, Any]) -> "BotHealthStatus":
        """Create instance from health report data with event type.

        Args:
            bot_id: Bot ID
            event_type: Type of health event that triggered this record
            health_data: Full health data from HealthReporter
        """
        # Extract WebSocket health
        ws_health = health_data.get("websocket_health", {})

        # Extract engine health
        engine_health = health_data.get("engine_health", {})

        # Extract performance metrics
        performance = health_data.get("performance", {})
        latency = performance.get("latency_ms", {})

        # Extract route information
        route_data = health_data.get("routes", {})
        active_routes = [r for r, stats in route_data.items() if stats.get("is_active", False)]

        return cls(
            bot_id=bot_id,
            event_type=event_type,
            websocket_status=ws_health.get("status", "unknown"),
            reconnect_count=ws_health.get("reconnect_count", 0),
            last_heartbeat=ws_health.get("last_heartbeat"),
            uptime_seconds=ws_health.get("uptime_seconds", 0),
            last_error=ws_health.get("last_error"),
            exchanges_health=ws_health.get("exchanges"),
            engine_status=engine_health.get("status", "healthy"),
            last_tick=engine_health.get("last_tick"),
            ticks_per_second=engine_health.get("ticks_per_second"),
            queued_orders=engine_health.get("queued_orders", 0),
            orders_last_minute=performance.get("orders_last_minute", 0),
            trades_last_minute=performance.get("trades_last_minute", 0),
            errors_last_minute=performance.get("errors_last_minute", 0),
            tick_processing_latency_ms=latency.get("tick_processing"),
            order_placement_latency_ms=latency.get("order_placement"),
            websocket_roundtrip_ms=latency.get("websocket_roundtrip"),
            active_routes=active_routes,
            route_statistics=route_data,
        )
