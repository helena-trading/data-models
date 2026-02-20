"""Market-data-hub configuration model."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from data_models.database.tables.base import Base


class MarketDataHubConfig(Base):  # type: ignore[misc,no-any-unimported]
    """Persisted configuration for an instance of market-data-hub."""

    __tablename__ = "market_data_hubs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    process_type = Column(String(80), nullable=False, default="market_data_hub", server_default="market_data_hub")
    config = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "process_type": self.process_type,
            "config": self.config or {},
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(timespec="milliseconds") if self.updated_at else None,
        }
