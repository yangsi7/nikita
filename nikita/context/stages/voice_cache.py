"""Voice cache invalidation stage for pipeline.

Stage 7.7 in the post-processing pipeline. Invalidates cached voice
prompt for text-voice consistency (Spec 031 T2.1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext


class VoiceCacheStage(PipelineStage[UUID, None]):
    """Stage 7.7: Invalidate voice cache.

    Called after text post-processing to ensure voice-text consistency.
    The next voice call will regenerate the prompt with fresh context.

    Non-critical: Pipeline continues if this stage fails.
    """

    name = "voice_cache"
    is_critical = False
    timeout_seconds = 5.0
    max_retries = 1

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize VoiceCacheStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy import to avoid circular dependency
        from nikita.db.repositories.user_repository import UserRepository

        self._user_repo = UserRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        user_id: UUID,
    ) -> None:
        """Execute voice cache invalidation.

        Args:
            context: Pipeline context with conversation data.
            user_id: User ID to invalidate cache for.

        Returns:
            None on success.

        Note:
            This stage catches and logs errors internally rather than
            raising them, since cache invalidation is non-critical.
            The next voice call will simply use stale context.
        """
        try:
            await self._user_repo.invalidate_voice_cache(user_id)
            self._logger.info(
                "voice_cache_invalidated",
                user_id=str(user_id),
            )
        except ValueError as e:
            # User not found - log warning but don't fail stage
            self._logger.warning(
                "voice_cache_user_not_found",
                user_id=str(user_id),
                error=str(e),
            )
        except Exception as e:
            # Unexpected error - log warning but don't fail stage
            self._logger.warning(
                "voice_cache_invalidation_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )

        return None
