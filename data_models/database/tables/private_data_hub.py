"""Private-data-hub configuration models."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from data_models.database.tables.base import Base


class PrivateDataHubConfig(Base):  # type: ignore[misc,no-any-unimported]
    """Persisted configuration for an instance of private-data-hub."""

    __tablename__ = "private_data_hubs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    process_type = Column(String(80), nullable=False, default="private_data_hub", server_default="private_data_hub")
    config = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tracked_accounts = relationship(
        "PrivateDataHubTrackedAccount",
        back_populates="hub",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "process_type": self.process_type,
            "config": self.config or {},
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(timespec="milliseconds") if self.updated_at else None,
            "tracked_account_count": len(self.tracked_accounts) if self.tracked_accounts else 0,
        }


class PrivateDataHubTrackedAccount(Base):  # type: ignore[misc,no-any-unimported]
    """Tracked account entry for a private-data-hub instance."""

    __tablename__ = "private_data_hub_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hub_id = Column(Integer, ForeignKey("private_data_hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    contracts = Column(JSONB, nullable=False, default=list, server_default="[]")
    account_metadata = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("hub_id", "account_id", name="uq_private_data_hub_account"),)

    hub = relationship("PrivateDataHubConfig", back_populates="tracked_accounts")
    account = relationship("Account")

    def to_dict(self) -> Dict[str, Any]:
        account_obj = self.account
        return {
            "id": self.id,
            "hub_id": self.hub_id,
            "account_id": self.account_id,
            "enabled": bool(self.enabled),
            "metadata": self.account_metadata or {},
            "exchange": account_obj.exchange if account_obj else None,
            "account_name": account_obj.name if account_obj else None,
            "account_active": bool(account_obj.is_active) if account_obj else None,
            "created_at": self.created_at.isoformat(timespec="milliseconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(timespec="milliseconds") if self.updated_at else None,
        }
