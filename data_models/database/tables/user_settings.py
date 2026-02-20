"""
User Settings Model - Stores user-level preferences
"""

from typing import Any, Dict

from sqlalchemy import JSON, Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from data_models.database.tables.base import Base


class UserSettings(Base):  # type: ignore[misc,no-any-unimported]
    """User settings and preferences"""

    __tablename__ = "user_settings"

    # Primary key
    user_id = Column(String, primary_key=True, nullable=False)

    # Live testing preferences
    run_live_tests_before_start = Column(Boolean, default=False, nullable=False)
    live_test_efficiency = Column(Boolean, default=True, nullable=False)
    live_test_exchange = Column(Boolean, default=True, nullable=False)
    live_test_cancel_maker = Column(Boolean, default=True, nullable=False)
    live_test_cancel_inverted = Column(Boolean, default=False, nullable=False)
    live_test_execution = Column(Boolean, default=False, nullable=False)

    # Other user preferences
    theme = Column(String, default="dark", nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    language = Column(String, default="en", nullable=False)

    # Flexible JSON storage for additional settings
    preferences = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert user settings to dictionary"""
        return {
            "user_id": self.user_id,
            "run_live_tests_before_start": self.run_live_tests_before_start,
            "live_test_efficiency": self.live_test_efficiency,
            "live_test_exchange": self.live_test_exchange,
            "live_test_cancel_maker": self.live_test_cancel_maker,
            "live_test_cancel_inverted": self.live_test_cancel_inverted,
            "live_test_execution": self.live_test_execution,
            "theme": self.theme,
            "timezone": self.timezone,
            "language": self.language,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_live_test_config(self) -> Dict[str, Any]:
        """Get live testing configuration as a dict"""
        return {
            "enabled": self.run_live_tests_before_start,
            "efficiency": self.live_test_efficiency,
            "exchange": self.live_test_exchange,
            "cancel_maker": self.live_test_cancel_maker,
            "cancel_inverted": self.live_test_cancel_inverted,
            "execution": self.live_test_execution,
        }
