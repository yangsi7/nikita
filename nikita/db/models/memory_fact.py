"""Memory fact model for unified pipeline (Spec 042)."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.user import User


class MemoryFact(Base, UUIDMixin, TimestampMixin):
    """Semantic memory fact stored with pgVector embedding.

    Supabase-native pgVector storage for semantic memory.
    Three graph types: user (personal facts), relationship (user-Nikita),
    nikita (Nikita's world state).
    """

    __tablename__ = "memory_facts"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    graph_type: Mapped[str] = mapped_column(Text, nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # pgVector 1536-dim embedding (OpenAI text-embedding-3-small)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    # Python attr "fact_metadata" maps to DB column "metadata"
    # (avoids clash with SQLAlchemy Base.metadata)
    fact_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Self-referential: points to the fact that replaced this one
    superseded_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("memory_facts.id", ondelete="SET NULL"),
        nullable=True,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memory_facts")
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
    )

    __table_args__ = (
        CheckConstraint(
            "graph_type IN ('user', 'relationship', 'nikita')",
            name="check_memory_fact_graph_type",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="check_memory_fact_confidence_range",
        ),
    )
