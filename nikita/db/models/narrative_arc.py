"""User Narrative Arc Model (Spec 035).

Stores multi-conversation storylines that develop over time.
Each user can have up to 2 active arcs at a time.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base

if TYPE_CHECKING:
    from nikita.db.models.user import User


class UserNarrativeArc(Base):
    """A multi-conversation narrative arc for a specific user.

    Created by NarrativeArcSystem during post-processing.
    Arcs progress through stages: setup → rising → climax → falling → resolved.
    """

    __tablename__ = "user_narrative_arcs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stage: Mapped[str] = mapped_column(
        String(20), nullable=False, default="setup"
    )
    stage_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversations_in_arc: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    max_conversations: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    current_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    involved_characters: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    emotional_impact: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="narrative_arcs")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for context loading."""
        return {
            "id": str(self.id),
            "name": self.template_name,
            "category": self.category,
            "stage": self.current_stage,
            "description": self.current_description,
            "characters": self.involved_characters,
            "conversations": self.conversations_in_arc,
            "max_conversations": self.max_conversations,
            "emotional_impact": self.emotional_impact,
        }

    def should_advance(self) -> bool:
        """Check if arc should advance to next stage based on conversation count."""
        if self.current_stage == "resolved":
            return False

        # Advance after certain percentage of max conversations
        stage_thresholds = {
            "setup": 0.2,  # 20% - move to rising
            "rising": 0.5,  # 50% - move to climax
            "climax": 0.7,  # 70% - move to falling
            "falling": 0.9,  # 90% - move to resolved
        }

        threshold = stage_thresholds.get(self.current_stage, 1.0)
        progress = self.conversations_in_arc / max(self.max_conversations, 1)
        return progress >= threshold

    def advance_stage(self) -> bool:
        """Advance to the next stage.

        Returns:
            True if stage was advanced, False if already resolved.
        """
        stage_order = ["setup", "rising", "climax", "falling", "resolved"]

        try:
            current_idx = stage_order.index(self.current_stage)
        except ValueError:
            return False

        if current_idx < len(stage_order) - 1:
            self.current_stage = stage_order[current_idx + 1]
            if self.current_stage == "resolved":
                self.resolved_at = datetime.now(UTC)
                self.is_active = False
            return True
        return False

    def __repr__(self) -> str:
        return f"<UserNarrativeArc {self.template_name} ({self.current_stage}) for user {self.user_id}>"
