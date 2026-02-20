"""
SQLAlchemy model for encrypted credentials
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET

from data_models.database.tables.base import Base


class EncryptedCredential(Base):  # type: ignore[misc,no-any-unimported]
    """Encrypted credential storage model"""

    __tablename__ = "encrypted_credentials"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    credential_type = Column(String(50), nullable=False)  # 'api_key', 'api_secret', 'passphrase'
    encrypted_value = Column(Text, nullable=False)
    encryption_metadata = Column(JSON, nullable=False)  # {algorithm, key_id, iv, auth_tag, version}
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    last_accessed_at = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)

    # Relationships (removed back_populates to avoid circular dependency)

    # Constraints
    __table_args__ = (
        UniqueConstraint("account_id", "credential_type", name="uq_account_credential_type"),
        Index("idx_encrypted_credentials_account_id", "account_id"),
        Index("idx_encrypted_credentials_last_accessed", "last_accessed_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "credential_type": self.credential_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "last_accessed_at": (self.last_accessed_at.isoformat() if self.last_accessed_at else None),
            "access_count": self.access_count,
        }


class CredentialAuditLog(Base):  # type: ignore[misc,no-any-unimported]
    """Audit log for credential access.

    Note: This model is stored in the CREDENTIALS database (security-critical).
    bot_id stored as plain Integer (no foreign key) due to dual-database segregation.
    """

    __tablename__ = "credential_audit_log"

    id = Column(Integer, primary_key=True)
    credential_id = Column(Integer, ForeignKey("encrypted_credentials.id", ondelete="SET NULL"))
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"))
    action = Column(String(50), nullable=False)  # 'create', 'read', 'update', 'delete', 'rotate'
    bot_id = Column(Integer, nullable=True)  # Plain integer, no FK (cross-database reference)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    ip_address = Column(INET)  # PostgreSQL INET type for IP addresses
    user_agent = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    audit_metadata = Column(JSON)  # Additional context

    # Indexes
    __table_args__ = (
        Index("idx_credential_audit_log_timestamp", "timestamp"),
        Index("idx_credential_audit_log_account_id", "account_id"),
        Index("idx_credential_audit_log_bot_id", "bot_id"),
        Index("idx_credential_audit_log_action", "action"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "credential_id": self.credential_id,
            "account_id": self.account_id,
            "action": self.action,
            "bot_id": self.bot_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.audit_metadata,
        }
