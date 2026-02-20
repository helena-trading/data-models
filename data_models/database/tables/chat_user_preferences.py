"""Chat user preferences model for storing user-specific chat settings."""

from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

from data_models.database.tables.base import Base


class ChatUserPreferences(Base):  # type: ignore[misc,no-any-unimported]
    """Model for storing user-specific chat preferences.

    Stores user preferences for chat interface including LLM provider,
    context window size, display preferences, and data retention policies.

    Note: Foreign key to users table not implemented as users table doesn't exist.
    user_id is stored as VARCHAR for flexibility.
    """

    __tablename__ = "chat_user_preferences"

    # Primary key (user_id)
    user_id = Column(String(50), primary_key=True, nullable=False)

    # LLM preferences
    default_provider = Column(String(20), default="claude", nullable=False)  # 'claude' or 'openai'
    max_context_messages = Column(Integer, default=50, nullable=False)  # Context window size

    # Display preferences
    auto_save = Column(Boolean, default=True, nullable=False)
    show_token_usage = Column(Boolean, default=True, nullable=False)
    show_tool_details = Column(Boolean, default=True, nullable=False)

    # Data retention
    conversation_retention_days = Column(Integer, default=90, nullable=False)  # Auto-archive after N days

    # Notification preferences
    enable_notifications = Column(Boolean, default=False, nullable=False)

    # Flexible preferences (for future extensibility)
    preferences = Column(JSON, default=dict, nullable=False)

    # Timestamps
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary for API responses.

        Returns:
            Dictionary with all preference fields
        """
        return {
            "user_id": self.user_id,
            "default_provider": self.default_provider,
            "max_context_messages": self.max_context_messages,
            "auto_save": self.auto_save,
            "show_token_usage": self.show_token_usage,
            "show_tool_details": self.show_tool_details,
            "conversation_retention_days": self.conversation_retention_days,
            "enable_notifications": self.enable_notifications,
            "preferences": self.preferences,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """Get default preference values.

        Returns:
            Dictionary with default values for all preferences
        """
        return {
            "default_provider": "claude",
            "max_context_messages": 50,
            "auto_save": True,
            "show_token_usage": True,
            "show_tool_details": True,
            "conversation_retention_days": 90,
            "enable_notifications": False,
            "preferences": {},
        }

    def validate(self) -> bool:
        """Validate preference values.

        Returns:
            True if all values are valid, False otherwise
        """
        # Validate max_context_messages range
        if self.max_context_messages is not None and not 10 <= self.max_context_messages <= 100:
            return False

        # Validate provider
        if self.default_provider is not None and self.default_provider not in ["claude", "openai"]:
            return False

        # Validate retention days
        if self.conversation_retention_days is not None and self.conversation_retention_days < 1:
            return False

        return True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ChatUserPreferences(user_id={self.user_id}, "
            f"provider={self.default_provider}, "
            f"max_context={self.max_context_messages})>"
        )
