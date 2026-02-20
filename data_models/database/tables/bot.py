"""
Bot Management Models for managing multiple bot instances
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates

from data_models.database.tables.base import Base
from data_models.models.enums.strategy import StrategyType


class BotStatus(PyEnum):
    """Bot status enumeration"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class LogLevel(PyEnum):
    """Log level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def _validate_cross_arb_config(config: Dict[str, Any]) -> None:
    """Validate cross-arbitrage bot configuration."""
    required_fields = ("contract_list_main", "contract_list_sec", "exchanges", "parameters")
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(config["contract_list_main"], list) or not config["contract_list_main"]:
        raise ValueError("contract_list_main must be a non-empty list")
    if not isinstance(config["contract_list_sec"], list) or not config["contract_list_sec"]:
        raise ValueError("contract_list_sec must be a non-empty list")

    exchanges = config.get("exchanges", {})
    if not isinstance(exchanges, dict):
        raise ValueError("exchanges must be an object")
    if "maker" not in exchanges or "taker" not in exchanges:
        raise ValueError("Config must specify both maker and taker exchanges")

    if not isinstance(config.get("parameters"), dict):
        raise ValueError("parameters must be a dictionary")


def _validate_graph_config(config: Dict[str, Any]) -> None:
    """Validate graph-arbitrage bot configuration."""
    if "graph_config" not in config:
        raise ValueError("Missing required field: graph_config")

    graph_config = config["graph_config"]
    if not isinstance(graph_config, dict):
        raise ValueError("graph_config must be an object")
    if "exchanges" not in graph_config:
        raise ValueError("graph_config must contain exchanges")

    exchanges = graph_config.get("exchanges")
    if not isinstance(exchanges, list) or len(exchanges) < 2:
        raise ValueError("graph_config.exchanges must be a list with at least 2 exchanges")

    for idx, exchange in enumerate(exchanges):
        if not isinstance(exchange, dict):
            raise ValueError(f"graph_config.exchanges[{idx}] must be a dictionary")
        if "id" not in exchange:
            raise ValueError(f"graph_config.exchanges[{idx}] missing required field: id")
        if "contracts" not in exchange:
            raise ValueError(f"graph_config.exchanges[{idx}] missing required field: contracts")
        if not isinstance(exchange["contracts"], list) or not exchange["contracts"]:
            raise ValueError(f"graph_config.exchanges[{idx}].contracts must be a non-empty list")


def _validate_monitoring_config(config: Dict[str, Any]) -> None:
    """Validate monitoring bot configuration."""
    if "monitors" not in config:
        raise ValueError("Missing required field: monitors")

    monitors_config = config["monitors"]
    if not isinstance(monitors_config, dict):
        raise ValueError("monitors must be a dictionary")
    if not monitors_config.get("enabled", False):
        raise ValueError("monitors.enabled must be true for monitoring strategy")

    supported_monitor_types = ("accounts", "public_market_data", "graph_opportunity")
    has_monitor_type = False
    for monitor_type in supported_monitor_types:
        monitor_cfg = monitors_config.get(monitor_type)
        if monitor_cfg is None:
            continue
        if not isinstance(monitor_cfg, dict):
            raise ValueError(f"monitors.{monitor_type} must be a dictionary")
        if monitor_cfg.get("enabled", False):
            has_monitor_type = True
            if "refresh_interval" in monitor_cfg:
                interval = monitor_cfg["refresh_interval"]
                if not isinstance(interval, int) or interval <= 0:
                    raise ValueError(f"{monitor_type}.refresh_interval must be a positive integer")

    if not has_monitor_type:
        raise ValueError(
            "At least one monitor type must be enabled. "
            f"Available types: {', '.join(supported_monitor_types)}"
        )

    exchanges = config.get("exchanges", [])
    if exchanges and len(exchanges) > 0:
        raise ValueError("Monitoring strategy should have empty exchanges array (loads from database)")


def _validate_strategy_config(strategy_type: str, config: Dict[str, Any]) -> None:
    """Validate strategy config without depending on bot-core runtime imports."""
    if strategy_type == StrategyType.CROSS_ARB.value:
        _validate_cross_arb_config(config)
        return
    if strategy_type == StrategyType.GRAPH_ARBITRAGE.value:
        _validate_graph_config(config)
        return
    if strategy_type == StrategyType.MONITORING.value:
        _validate_monitoring_config(config)
        return
    valid_strategies = [s.value for s in StrategyType]
    raise ValueError(f"Unknown strategy: {strategy_type}. Valid strategies: {valid_strategies}")


class Bot(Base):  # type: ignore[misc,no-any-unimported]
    """Model for bot configurations and status"""

    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    strategy_type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False)
    status = Column(String(20), default="stopped")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_started_at = Column(DateTime(timezone=True))
    last_stopped_at = Column(DateTime(timezone=True))
    pid = Column(Integer)
    container_id = Column(String(100))
    error_message = Column(Text)
    tags = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Relationships
    runs = relationship("BotRun", back_populates="bot", cascade="all, delete-orphan")
    activity_logs = relationship("BotActivityLog", back_populates="bot", cascade="all, delete-orphan")
    bot_accounts = relationship("BotAccount", back_populates="bot", cascade="all, delete-orphan")
    # NOTE: health_status_reports relationship removed - cross-DB reference not supported
    # health_status_reports = relationship("BotHealthStatus", back_populates="bot", cascade="all, delete-orphan")

    @validates("config")
    def validate_config(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bot configuration based on strategy type

        The validation is delegated to the StrategyRegistry which knows
        the specific requirements for each strategy type.
        """
        # Note: We need the strategy_type to validate, but it might not be set yet
        # during object construction. We'll validate in validate_strategy_config instead.
        return value

    @validates("strategy_type")
    def validate_strategy_type(self, key: str, value: str) -> str:
        """Validate and normalize strategy type to valid StrategyType enum value.

        This also handles one-time data migration from legacy names:
        - 'cross_exchange_arbitrage' -> 'cross_arb'
        """
        # Normalize legacy strategy names (data migration)
        value = self._normalize_strategy_type(value)

        try:
            # This will raise ValueError if not a valid StrategyType
            StrategyType(value)
        except ValueError as e:
            valid_strategies = [s.value for s in StrategyType]
            raise ValueError(f"Unknown strategy type: {value}. Valid strategies: {valid_strategies}") from e
        return value

    @validates("tags")
    def validate_tags(self, key: str, value: List[str]) -> List[str]:
        """Validate and normalize tags: lowercase, trimmed, deduplicated, sorted."""
        if not isinstance(value, list):
            raise ValueError("tags must be a list")
        normalized = []
        seen: set[str] = set()
        for tag in value:
            if not isinstance(tag, str):
                raise ValueError("Each tag must be a string")
            tag = tag.strip().lower()
            if not tag:
                continue
            if tag not in seen:
                seen.add(tag)
                normalized.append(tag)
        return sorted(normalized)

    def validate_strategy_config(self) -> None:
        """Validate config matches the strategy requirements

        This should be called after both strategy_type and config are set.
        """
        if self.strategy_type and self.config:
            # Normalize legacy strategy names before validation
            strategy_type = self._normalize_strategy_type(str(self.strategy_type))
            _validate_strategy_config(strategy_type, self.config)

    @staticmethod
    def _normalize_strategy_type(value: str) -> str:
        """Normalize legacy strategy type names to current canonical names."""
        legacy_mapping = {
            "cross_exchange_arbitrage": StrategyType.CROSS_ARB.value,
        }
        return legacy_mapping.get(value, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert bot to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "strategy_type": self.strategy_type,
            "config": self.config,
            "status": self.status,
            # Always include milliseconds for HFT precision analysis
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(timespec="milliseconds") if self.updated_at else None,
            "last_started_at": (self.last_started_at.isoformat(timespec="milliseconds") if self.last_started_at else None),
            "last_stopped_at": (self.last_stopped_at.isoformat(timespec="milliseconds") if self.last_stopped_at else None),
            "pid": self.pid,
            "container_id": self.container_id,
            "error_message": self.error_message,
            "tags": self.tags or [],
            "bot_accounts": [{"account_id": ba.account_id, "role": ba.role} for ba in (self.bot_accounts or [])],
        }


class BotRun(Base):  # type: ignore[misc,no-any-unimported]
    """Model for bot execution history.

    Note: Stats (total_orders, total_trades, total_pnl, error_count) are stored
    in the bot_run_stats table in the analytics database, NOT in this table.
    This avoids duplication and ensures stats are always read from the source of truth.
    """

    __tablename__ = "bot_runs"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    stopped_at = Column(DateTime(timezone=True))
    stop_reason = Column(String(100))
    config_snapshot = Column(JSONB)
    # NOTE: total_orders, total_trades, total_pnl, error_count columns removed
    # Stats are now stored exclusively in bot_run_stats (analytics DB)

    # Relationships
    bot = relationship("Bot", back_populates="runs")
    activity_logs = relationship("BotActivityLog", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert run to dictionary.

        Note: Stats fields (total_orders, total_trades, total_pnl, error_count)
        are NOT included here. They must be fetched from bot_run_stats table
        in the analytics database and merged by the API layer.
        """
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            # Always include milliseconds for HFT precision analysis
            "started_at": self.started_at.isoformat(timespec="milliseconds") if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat(timespec="milliseconds") if self.stopped_at else None,
            "stop_reason": self.stop_reason,
            "duration_seconds": (
                (self.stopped_at - self.started_at).total_seconds() if self.stopped_at and self.started_at else None
            ),
        }


class BotActivityLog(Base):  # type: ignore[misc,no-any-unimported]
    """Model for bot activity logs"""

    __tablename__ = "bot_activity_logs"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=True)
    level: Mapped[LogLevel] = Column(Enum(LogLevel), nullable=False)  # type: ignore[assignment]
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    bot = relationship("Bot", back_populates="activity_logs")
    run = relationship("BotRun", back_populates="activity_logs")

    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary"""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "run_id": self.run_id,
            "level": self.level.value if self.level else None,
            "message": self.message,
            # Always include milliseconds for HFT precision analysis
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
        }
