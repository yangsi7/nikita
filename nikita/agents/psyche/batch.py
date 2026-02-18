"""Batch orchestration for daily psyche state generation (Spec 056 T10).

Runs at 5AM UTC via pg_cron. Generates PsycheState for all active users
using the configured model (Sonnet default). Per-user isolation ensures
one failure doesn't block others.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from nikita.agents.psyche import is_psyche_agent_enabled

logger = logging.getLogger(__name__)

# Per-user timeout for psyche generation (AC-1.4)
USER_TIMEOUT_SECONDS = 30


async def run_psyche_batch() -> dict[str, Any]:
    """Run psyche batch job for all active users.

    Gets active users, loads 48h context per user, generates
    PsycheState, and upserts to DB. Per-user try/except for
    failure isolation (AC-1.5).

    Returns:
        Summary dict: {processed: int, failed: int, skipped: int, errors: list[str]}
    """
    if not is_psyche_agent_enabled():
        logger.info("[PSYCHE-BATCH] Feature flag OFF, skipping batch")
        return {"processed": 0, "failed": 0, "skipped": 0, "errors": []}

    from nikita.agents.psyche.agent import generate_psyche_state
    from nikita.agents.psyche.deps import PsycheDeps
    from nikita.db.database import get_session_maker
    from nikita.db.repositories.psyche_state_repository import PsycheStateRepository
    from nikita.db.repositories.user_repository import UserRepository

    session_maker = get_session_maker()
    processed = 0
    failed = 0
    skipped = 0
    errors: list[str] = []

    async with session_maker() as session:
        user_repo = UserRepository(session)
        active_users = await user_repo.get_active_users_for_decay()

        logger.info(
            "[PSYCHE-BATCH] Starting batch for %d active users", len(active_users)
        )

        for user in active_users:
            try:
                # Load 48h context
                deps = await _build_deps(session, user)

                # Generate with timeout (AC-1.4)
                state, token_count = await asyncio.wait_for(
                    generate_psyche_state(deps),
                    timeout=USER_TIMEOUT_SECONDS,
                )

                # Upsert to DB
                psyche_repo = PsycheStateRepository(session)
                await psyche_repo.upsert(
                    user_id=user.id,
                    state=state.model_dump(),
                    model="sonnet",
                    token_count=token_count,
                )
                await session.commit()

                logger.info(
                    "[PSYCHE-BATCH] model=sonnet tokens=%d user_id=%s tier=batch",
                    token_count,
                    str(user.id),
                )
                processed += 1

            except asyncio.TimeoutError:
                error_msg = f"User {user.id}: timeout after {USER_TIMEOUT_SECONDS}s"
                errors.append(error_msg)
                failed += 1
                logger.warning("[PSYCHE-BATCH] %s", error_msg)
                await session.rollback()

            except Exception as e:
                error_msg = f"User {user.id}: {type(e).__name__}: {e}"
                errors.append(error_msg)
                failed += 1
                logger.warning("[PSYCHE-BATCH] %s", error_msg)
                await session.rollback()

    logger.info(
        "[PSYCHE-BATCH] Complete: processed=%d failed=%d skipped=%d",
        processed,
        failed,
        skipped,
    )

    return {
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors[:10],  # Cap at 10 errors
    }


async def _build_deps(session, user) -> "PsycheDeps":
    """Build PsycheDeps from 48h of user data.

    Args:
        session: Database session.
        user: User model.

    Returns:
        PsycheDeps populated with recent context.
    """
    from nikita.agents.psyche.deps import PsycheDeps

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    score_history: list[dict] = []
    emotional_states: list[dict] = []
    life_events: list[dict] = []
    npc_interactions: list[dict] = []

    # Load score history
    try:
        from nikita.db.repositories.score_history_repository import (
            ScoreHistoryRepository,
        )

        score_repo = ScoreHistoryRepository(session)
        history = await score_repo.get_recent(user_id=user.id, limit=20)
        score_history = [
            {
                "score": float(h.score),
                "event_type": h.event_type,
                "created_at": str(h.created_at),
            }
            for h in history
            if h.created_at and h.created_at >= cutoff
        ]
    except Exception as e:
        logger.debug("[PSYCHE-BATCH] Score history load failed: %s", e)

    # Load emotional states from recent conversations
    try:
        from nikita.db.repositories.conversation_repository import (
            ConversationRepository,
        )

        conv_repo = ConversationRepository(session)
        convs = await conv_repo.get_processed_conversations(
            user_id=user.id, days=2, limit=10
        )
        emotional_states = [
            {
                "tone": c.emotional_tone or "neutral",
                "summary": c.summary or "",
                "created_at": str(c.started_at),
            }
            for c in convs
        ]
    except Exception as e:
        logger.debug("[PSYCHE-BATCH] Emotional states load failed: %s", e)

    return PsycheDeps(
        user_id=user.id,
        score_history=score_history,
        emotional_states=emotional_states,
        life_events=life_events,
        npc_interactions=npc_interactions,
        current_chapter=user.chapter or 1,
    )
