"""Generated prompt logging model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.user import User


class GeneratedPrompt(Base, UUIDMixin):
    """
    Generated prompt logging for admin debugging.

    Logs all AI-generated prompts with timing, token count,
    and context snapshots for transparency and debugging.
    """

    __tablename__ = "generated_prompts"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Prompt content
    prompt_content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generation_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    meta_prompt_template: Mapped[str] = mapped_column(String(100), nullable=False)

    # Platform identifier (text or voice) - Spec 035
    platform: Mapped[str] = mapped_column(String(10), nullable=False, default="text")

    # Context snapshot (JSONB for flexible debugging)
    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generated_prompts")
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        back_populates="generated_prompts",
    )
