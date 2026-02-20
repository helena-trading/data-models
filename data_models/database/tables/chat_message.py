"""Chat message model for storing individual messages within conversations."""

from typing import Any, Dict

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from data_models.database.tables.base import Base


class ChatMessage(Base):  # type: ignore[misc,no-any-unimported]
    """Model for storing individual chat messages.

    Each message belongs to a conversation and contains the message content,
    role (user/assistant/system), and optional tool execution data.
    """

    __tablename__ = "chat_messages"

    # Primary key (auto-increment)
    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False)

    # Foreign key to conversation
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    role = Column(
        String(20),
        nullable=False,
    )  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)

    # AI/Tool execution data (optional, for assistant messages)
    tool_calls = Column(JSON, nullable=True)  # Array of tool executions
    model = Column(String(50), nullable=True)  # LLM model used (e.g., 'claude-3-5-sonnet-20241022')
    tokens_used = Column(Integer, nullable=True)  # Token count for cost tracking

    # Flexible metadata
    custom_metadata = Column(JSON, default=dict, nullable=False)

    # Relationship to conversation (for ORM convenience)
    conversation = relationship("ChatConversation", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for API responses.

        Returns:
            Dictionary with all message fields
        """
        return {
            "id": self.id,
            "conversation_id": str(self.conversation_id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "metadata": self.custom_metadata,
        }

    def to_dict_minimal(self) -> Dict[str, Any]:
        """Convert to dictionary with minimal fields (excludes tool_calls for performance).

        Returns:
            Dictionary with core message fields only
        """
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def get_preview(self, max_length: int = 200) -> str:
        """Get preview text of message content.

        Args:
            max_length: Maximum length of preview text

        Returns:
            Truncated message content
        """
        content_str = str(self.content)
        if len(content_str) <= max_length:
            return content_str
        return content_str[:max_length] + "..."

    def __repr__(self) -> str:
        """String representation for debugging."""
        preview = self.get_preview(50)
        return (
            f"<ChatMessage(id={self.id}, conversation_id={self.conversation_id}, " f"role={self.role}, content={preview!r})>"
        )
