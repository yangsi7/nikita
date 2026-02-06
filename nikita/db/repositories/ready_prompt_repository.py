"""ReadyPrompt repository for pre-built prompt operations (Spec 042)."""

from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.ready_prompt import ReadyPrompt
from nikita.db.repositories.base import BaseRepository


class ReadyPromptRepository(BaseRepository[ReadyPrompt]):
    """Repository for ReadyPrompt entity.

    Manages pre-built system prompts with atomic set_current
    (deactivate old + insert new in single transaction).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReadyPrompt)

    async def get_current(
        self,
        user_id: UUID,
        platform: str,
    ) -> ReadyPrompt | None:
        """Get the current active prompt for a user/platform.

        Args:
            user_id: Owner user UUID.
            platform: 'text' or 'voice'.

        Returns:
            The current ReadyPrompt or None.
        """
        stmt = (
            select(ReadyPrompt)
            .where(
                ReadyPrompt.user_id == user_id,
                ReadyPrompt.platform == platform,
                ReadyPrompt.is_current.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_current(
        self,
        user_id: UUID,
        platform: str,
        prompt_text: str,
        token_count: int,
        pipeline_version: str,
        generation_time_ms: float,
        context_snapshot: dict[str, Any] | None = None,
        conversation_id: UUID | None = None,
    ) -> ReadyPrompt:
        """Atomically deactivate old prompt and insert new one.

        Within the same transaction:
        1. UPDATE is_current=False for all matching (user_id, platform)
        2. INSERT new prompt with is_current=True

        Args:
            user_id: Owner user UUID.
            platform: 'text' or 'voice'.
            prompt_text: The generated prompt text.
            token_count: Token count of the prompt.
            pipeline_version: Pipeline version string.
            generation_time_ms: Time to generate in ms.
            context_snapshot: Optional context JSONB.
            conversation_id: Optional conversation UUID.

        Returns:
            The newly created ReadyPrompt.
        """
        # Step 1: Deactivate all current prompts for this user/platform
        deactivate_stmt = (
            update(ReadyPrompt)
            .where(
                ReadyPrompt.user_id == user_id,
                ReadyPrompt.platform == platform,
                ReadyPrompt.is_current.is_(True),
            )
            .values(is_current=False)
        )
        await self.session.execute(deactivate_stmt)

        # Step 2: Insert new prompt
        new_prompt = ReadyPrompt(
            user_id=user_id,
            platform=platform,
            prompt_text=prompt_text,
            token_count=token_count,
            context_snapshot=context_snapshot,
            pipeline_version=pipeline_version,
            generation_time_ms=generation_time_ms,
            is_current=True,
            conversation_id=conversation_id,
        )
        self.session.add(new_prompt)
        await self.session.flush()
        await self.session.refresh(new_prompt)
        return new_prompt

    async def get_history(
        self,
        user_id: UUID,
        platform: str | None = None,
        limit: int = 10,
    ) -> list[ReadyPrompt]:
        """Get prompt history for a user.

        Args:
            user_id: Owner user UUID.
            platform: Optional filter by platform.
            limit: Max results.

        Returns:
            List of ReadyPrompt records ordered by created_at DESC.
        """
        stmt = (
            select(ReadyPrompt)
            .where(ReadyPrompt.user_id == user_id)
            .order_by(ReadyPrompt.created_at.desc())
            .limit(limit)
        )

        if platform is not None:
            stmt = stmt.where(ReadyPrompt.platform == platform)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
