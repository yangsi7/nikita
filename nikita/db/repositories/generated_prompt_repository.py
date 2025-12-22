"""GeneratedPrompt repository for prompt logging operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.generated_prompt import GeneratedPrompt
from nikita.db.repositories.base import BaseRepository


class GeneratedPromptRepository(BaseRepository[GeneratedPrompt]):
    """Repository for GeneratedPrompt entity.

    Handles logging of AI-generated prompts for admin debugging.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize GeneratedPromptRepository."""
        super().__init__(session, GeneratedPrompt)

    async def create_log(
        self,
        user_id: UUID,
        prompt_content: str,
        token_count: int,
        generation_time_ms: float,
        meta_prompt_template: str,
        conversation_id: UUID | None = None,
        context_snapshot: dict[str, Any] | None = None,
    ) -> GeneratedPrompt:
        """Create a new prompt log entry.

        Args:
            user_id: The user's UUID.
            prompt_content: The generated prompt text.
            token_count: Number of tokens in the prompt.
            generation_time_ms: Time taken to generate in milliseconds.
            meta_prompt_template: Template used for generation.
            conversation_id: Optional conversation UUID.
            context_snapshot: Optional context data as JSONB.

        Returns:
            Created GeneratedPrompt entity.
        """
        prompt_log = GeneratedPrompt(
            user_id=user_id,
            conversation_id=conversation_id,
            prompt_content=prompt_content,
            token_count=token_count,
            generation_time_ms=generation_time_ms,
            meta_prompt_template=meta_prompt_template,
            context_snapshot=context_snapshot,
            created_at=datetime.utcnow(),
        )

        self.session.add(prompt_log)
        await self.session.flush()

        return prompt_log

    async def get_by_user_id(
        self, user_id: UUID, limit: int = 50
    ) -> list[GeneratedPrompt]:
        """Get recent prompts for a user.

        Args:
            user_id: The user's UUID.
            limit: Maximum number of prompts to return.

        Returns:
            List of GeneratedPrompt records ordered by created_at DESC.
        """
        stmt = (
            select(GeneratedPrompt)
            .where(GeneratedPrompt.user_id == user_id)
            .order_by(GeneratedPrompt.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_template(
        self, template: str, limit: int = 50
    ) -> list[GeneratedPrompt]:
        """Get recent prompts by template type.

        Args:
            template: Template name to filter by.
            limit: Maximum number of prompts to return.

        Returns:
            List of GeneratedPrompt records ordered by created_at DESC.
        """
        stmt = (
            select(GeneratedPrompt)
            .where(GeneratedPrompt.meta_prompt_template == template)
            .order_by(GeneratedPrompt.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_by_user_id(
        self, user_id: UUID, limit: int = 10
    ) -> list[GeneratedPrompt]:
        """Get recent prompts for a user (for admin debugging).

        Args:
            user_id: The user's UUID.
            limit: Maximum number of prompts to return (default 10, max 50).

        Returns:
            List of GeneratedPrompt records ordered by created_at DESC.
            Returns empty list for non-existent user_id.
        """
        # Clamp limit to valid range
        limit = max(1, min(limit, 50))

        stmt = (
            select(GeneratedPrompt)
            .where(GeneratedPrompt.user_id == user_id)
            .order_by(GeneratedPrompt.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_user_id(self, user_id: UUID) -> GeneratedPrompt | None:
        """Get the most recent prompt for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Most recent GeneratedPrompt or None if no prompts exist.
        """
        stmt = (
            select(GeneratedPrompt)
            .where(GeneratedPrompt.user_id == user_id)
            .order_by(GeneratedPrompt.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
