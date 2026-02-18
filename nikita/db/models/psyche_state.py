"""SQLAlchemy model for psyche_states table (Spec 056 T2).

Stores one PsycheState JSONB per user, upserted by the psyche agent.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base, TimestampMixin, UUIDMixin


class PsycheStateRecord(Base, UUIDMixin, TimestampMixin):
    """Persisted psyche state for a user.

    One row per user (user_id UNIQUE). Upserted by daily batch job
    or on-demand trigger analysis. State stored as JSONB matching
    PsycheState Pydantic model schema.
    """

    __tablename__ = "psyche_states"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    state: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="'{}'",
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="sonnet",
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    def __repr__(self) -> str:
        return (
            f"<PsycheStateRecord user_id={self.user_id} "
            f"model={self.model} tokens={self.token_count}>"
        )
