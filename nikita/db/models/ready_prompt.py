"""Ready prompt model for unified pipeline (Spec 042).

Pre-built system prompts stored in DB for 0ms agent load time.
Immutable: no updated_at. Updates = deactivate old + insert new.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.user import User


class ReadyPrompt(Base, UUIDMixin):
    """Pre-built system prompt for text/voice agents.

    Immutable by design — no updated_at. When a new prompt is generated,
    the old one is deactivated (is_current=False) and a new row is inserted.
    This preserves full prompt history for debugging.
    """

    __tablename__ = "ready_prompts"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(Text, nullable=False)

    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    pipeline_version: Mapped[str] = mapped_column(Text, nullable=False)
    generation_time_ms: Mapped[float] = mapped_column(Float, nullable=False)

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Only created_at — no updated_at (immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ready_prompts")
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
    )

    __table_args__ = (
        CheckConstraint(
            "platform IN ('text', 'voice')",
            name="check_ready_prompt_platform",
        ),
    )
