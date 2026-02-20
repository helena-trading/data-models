"""
SQLAlchemy model for admin users (credentials database).
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, text

from data_models.database.tables.base import Base


class AdminUser(Base):  # type: ignore[misc,no-any-unimported]
    """Admin user model for dashboard authentication."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))

    __table_args__ = (Index("idx_admin_users_username", "username"),)
