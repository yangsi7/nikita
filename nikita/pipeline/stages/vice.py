"""Vice profile update stage (Spec 114, GE-006).

Non-critical: analyzes last conversation exchange, updates vice_preferences.
Skipped when vice_pipeline_enabled=False (safe rollout gate).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ViceStage(BaseStage):
    """Analyze last exchange for vice signals and update vice_preferences.

    Non-critical — failure does not stop the pipeline.
    Gated by settings.vice_pipeline_enabled (default False).
    """

    name = "vice"
    is_critical = False
    timeout_seconds = 45.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Analyze last user+nikita exchange for vice signals."""
        from nikita.config.settings import get_settings

        settings = get_settings()
        if not settings.vice_pipeline_enabled:
            return {"skipped": True, "reason": "vice_pipeline_disabled"}

        # Extract last (user, nikita) exchange from conversation messages
        messages = []
        if ctx.conversation is not None and hasattr(ctx.conversation, "messages"):
            messages = ctx.conversation.messages or []

        user_message, nikita_response = _extract_last_exchange(messages)
        if not user_message or not nikita_response:
            logger.info("[VICE] Insufficient messages for analysis, skipping")
            return {"skipped": True, "reason": "insufficient_messages"}

        from nikita.engine.vice.service import ViceService

        # ViceService() takes no args — ViceScorer manages its own session internally
        vice_service = ViceService()
        result = await vice_service.process_conversation(
            user_id=ctx.user_id,
            user_message=user_message,
            nikita_message=nikita_response,  # NOTE: parameter is nikita_message, not nikita_response
            conversation_id=ctx.conversation_id,
            chapter=ctx.chapter,
        )
        logger.info(
            "[VICE] Vice analysis: discovered=%d updated=%d",
            result.get("discovered", 0),
            result.get("updated", 0),
        )
        return result


def _extract_last_exchange(messages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Return the last (user_message, nikita_response) pair from messages.

    Iterates in reverse to find a user+nikita consecutive pair.
    Returns (None, None) if no such pair exists.
    """
    i = len(messages) - 1
    while i > 0:
        curr = messages[i]
        prev = messages[i - 1]
        curr_role = curr.get("role", "")
        prev_role = prev.get("role", "")
        if curr_role == "nikita" and prev_role == "user":
            user_content = prev.get("content", "")
            nikita_content = curr.get("content", "")
            if user_content and nikita_content:
                return str(user_content), str(nikita_content)
        i -= 1
    return None, None
