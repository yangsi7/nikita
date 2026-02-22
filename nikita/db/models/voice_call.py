"""VoiceCall database model (Spec 072 G3).

Persists voice call sessions for analytics and cross-modality context.

MIGRATION SQL (apply via Supabase dashboard — do NOT run automatically):

    CREATE TABLE voice_calls (
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      user_id UUID NOT NULL REFERENCES users(id),
      elevenlabs_session_id TEXT,
      started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      ended_at TIMESTAMPTZ,
      duration_seconds INT,
      transcript TEXT,
      summary TEXT,
      score_delta DECIMAL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX idx_voice_calls_user_id ON voice_calls(user_id);
    ALTER TABLE voice_calls ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "voice_calls_service_role_only" ON voice_calls
      FOR ALL USING (auth.role() = 'service_role');
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base

if TYPE_CHECKING:
    from nikita.db.models.user import User


class VoiceCall(Base):
    """Voice call session record.

    Tracks each ElevenLabs voice call session with:
    - Session metadata (IDs, timestamps)
    - Call content (transcript, summary)
    - Scoring outcome (score_delta)

    Supports:
    - Cross-modality context (text agent can read voice call history)
    - Analytics (call duration, frequency)
    - Memory enrichment (summaries stored for future context)
    """

    __tablename__ = "voice_calls"

    # Primary key (DB-generated UUID)
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    # Foreign key to users table
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ElevenLabs session identifier (for deduplication and transcript lookup)
    elevenlabs_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Call timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Call content
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scoring outcome
    score_delta: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return (
            f"VoiceCall(id={self.id}, user_id={self.user_id}, "
            f"session={self.elevenlabs_session_id}, duration={self.duration_seconds}s)"
        )
