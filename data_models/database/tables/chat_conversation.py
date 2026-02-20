"""Chat conversation model for storing conversation metadata and summaries."""

from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from data_models.database.tables.base import Base


class ChatConversation(Base):  # type: ignore[misc,no-any-unimported]
    """Model for storing chat conversation metadata.

    Stores conversation metadata including title, creation time, summary,
    and aggregated metrics. Related messages are stored in ChatMessage table.

    Note: Foreign key to users table not implemented as users table doesn't exist.
    user_id is stored as VARCHAR for flexibility.
    """

    __tablename__ = "chat_conversations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    # User identifier (no FK constraint - no users table exists)
    user_id = Column(String(50), nullable=False, index=True)

    # Conversation metadata
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)  # AI-generated summary
    custom_metadata = Column(JSON, default=dict, nullable=False)  # Flexible metadata (tags, categories, etc.)

    # Status flags
    is_archived = Column(Boolean, default=False, nullable=False, index=True)

    # Aggregated metrics
    message_count = Column(Integer, default=0, nullable=False)

    # Timestamps (automatic)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to messages (for ORM convenience)
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for API responses.

        Returns:
            Dictionary with all conversation fields
        """
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "summary": self.summary,
            "metadata": self.custom_metadata,
            "is_archived": self.is_archived,
            "message_count": self.message_count,
        }

    def to_dict_with_preview(self, last_message_preview: Optional[str] = None) -> Dict[str, Any]:
        """Convert to dictionary with last message preview.

        Args:
            last_message_preview: Preview text of last message (first 200 chars)

        Returns:
            Dictionary with conversation fields plus last_message_preview
        """
        data = self.to_dict()
        data["last_message_preview"] = last_message_preview
        return data

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ChatConversation(id={self.id}, user_id={self.user_id}, "
            f"title={self.title[:50]}, messages={self.message_count})>"
        )
