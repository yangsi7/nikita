"""Conversation-related database models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.context import ConversationThread, NikitaThought
    from nikita.db.models.generated_prompt import GeneratedPrompt
    from nikita.db.models.scheduled_event import ScheduledEvent
    from nikita.db.models.user import User


class Conversation(Base, UUIDMixin, TimestampMixin):
    """
    Conversation session storage.

    Stores both text (Telegram) and voice (ElevenLabs) conversations
    with their messages, analysis, and scoring.
    """

    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Platform and type
    platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # 'telegram' | 'voice'

    # Messages as JSONB array
    # Format: [{role: str, content: str, timestamp: str, analysis?: dict}]
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Scoring
    score_delta: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Game state at conversation time
    is_boss_fight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chapter_at_time: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Voice-specific fields
    elevenlabs_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Post-processing pipeline fields (spec 012)
    status: Mapped[str] = mapped_column(
        Text,
        default="active",
        nullable=False,
    )  # 'active' | 'processing' | 'processed' | 'failed'
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )  # Spec 031 T4.1: For stuck detection (>30 min = stuck)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Extracted data from post-processing
    extracted_entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_tone: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # 'positive' | 'neutral' | 'negative'

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    embeddings: Mapped[list["MessageEmbedding"]] = relationship(
        "MessageEmbedding",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    threads: Mapped[list["ConversationThread"]] = relationship(
        "ConversationThread",
        back_populates="source_conversation",
    )
    generated_thoughts: Mapped[list["NikitaThought"]] = relationship(
        "NikitaThought",
        back_populates="source_conversation",
    )
    generated_prompts: Mapped[list["GeneratedPrompt"]] = relationship(
        "GeneratedPrompt",
        back_populates="conversation",
    )
    scheduled_events: Mapped[list["ScheduledEvent"]] = relationship(
        "ScheduledEvent",
        back_populates="source_conversation",
    )

    def add_message(
        self,
        role: str,
        content: str,
        analysis: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if analysis:
            message["analysis"] = analysis
        # Defensive: ensure messages is a list (may be None for new objects)
        current_messages = self.messages if self.messages is not None else []
        # Use assignment (triggers SQLAlchemy dirty flag) instead of mutation (ignored)
        self.messages = [*current_messages, message]

    @property
    def message_count(self) -> int:
        """Get total number of messages."""
        return len(self.messages) if self.messages else 0


class MessageEmbedding(Base, UUIDMixin):
    """
    Vector embeddings for semantic search.

    Stores embeddings for individual messages to enable
    semantic search and memory retrieval.
    """

    __tablename__ = "message_embeddings"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Message content and embedding
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),  # OpenAI text-embedding-3-small dimension
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'user' | 'nikita'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="embeddings",
    )
