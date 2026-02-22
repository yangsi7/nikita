"""VoiceCallRepository for voice call persistence (Spec 072 G3).

Handles CRUD operations for VoiceCall records.
Follows the pattern established by ReadyPromptRepository and UserRepository.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.voice_call import VoiceCall
from nikita.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class VoiceCallRepository(BaseRepository[VoiceCall]):
    """Repository for VoiceCall entity.

    Provides voice call persistence with session-based deduplication
    and user-scoped queries for cross-modality context loading.

    Example:
        async with session_maker() as session:
            repo = VoiceCallRepository(session)
            call = await repo.create_new_call(
                user_id=user_id,
                elevenlabs_session_id=session_id,
                started_at=datetime.now(timezone.utc),
            )
            await session.commit()
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize VoiceCallRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__(session, VoiceCall)

    async def create_new_call(
        self,
        user_id: UUID,
        elevenlabs_session_id: str | None = None,
        started_at: datetime | None = None,
        transcript: str | None = None,
        summary: str | None = None,
        ended_at: datetime | None = None,
        duration_seconds: int | None = None,
        score_delta: Decimal | None = None,
    ) -> VoiceCall:
        """Create a new VoiceCall record.

        Convenience method that builds and persists a VoiceCall instance
        with the given parameters. Automatically sets started_at to now
        if not provided.

        Args:
            user_id: UUID of the user who initiated the call.
            elevenlabs_session_id: ElevenLabs session/conversation ID.
            started_at: Call start timestamp (defaults to now).
            transcript: Full call transcript text.
            summary: LLM-generated summary of the call.
            ended_at: Call end timestamp.
            duration_seconds: Total call duration in seconds.
            score_delta: Score change resulting from this call.

        Returns:
            Created and flushed VoiceCall instance.
        """
        call = VoiceCall(
            user_id=user_id,
            elevenlabs_session_id=elevenlabs_session_id,
            started_at=started_at or datetime.now(timezone.utc),
            transcript=transcript,
            summary=summary,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            score_delta=score_delta,
        )
        self.session.add(call)
        await self.session.flush()
        await self.session.refresh(call)

        logger.info(
            f"[VOICE_CALL] Created VoiceCall: user={user_id}, "
            f"session={elevenlabs_session_id}"
        )
        return call

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[VoiceCall]:
        """Get voice calls for a user, most recent first.

        Args:
            user_id: User UUID to query.
            limit: Maximum number of records to return (default 20).

        Returns:
            List of VoiceCall records ordered by started_at DESC.
        """
        stmt = (
            select(VoiceCall)
            .where(VoiceCall.user_id == user_id)
            .order_by(VoiceCall.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_id(
        self,
        elevenlabs_session_id: str,
    ) -> VoiceCall | None:
        """Get a VoiceCall by its ElevenLabs session ID.

        Used for deduplication and post-call enrichment (adding transcript,
        summary, score_delta after the call ends).

        Args:
            elevenlabs_session_id: ElevenLabs conversation/session ID.

        Returns:
            VoiceCall if found, None otherwise.
        """
        stmt = (
            select(VoiceCall)
            .where(VoiceCall.elevenlabs_session_id == elevenlabs_session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
