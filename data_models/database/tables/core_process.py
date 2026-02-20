"""Core process configuration model.

Stores persisted runtime configuration for long-running non-bot services
managed by the API (for example, market-data-hub).
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB

from data_models.database.tables.base import Base


class CoreProcessConfig(Base):  # type: ignore[misc,no-any-unimported]
    """Persisted configuration for a managed core process."""

    __tablename__ = "core_process_configs"

    process_key = Column(String(100), primary_key=True, nullable=False)
    name = Column(String(120), nullable=False)
    config = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_key": self.process_key,
            "name": self.name,
            "config": self.config or {},
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(timespec="milliseconds") if self.updated_at else None,
        }
