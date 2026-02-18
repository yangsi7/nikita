"""Conflict details DB persistence (Spec 057).

Load/save conflict_details JSONB from/to users table.
Used by message_handler (real-time scoring) and pipeline (post-processing).
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def load_conflict_details(
    user_id: UUID,
    session: AsyncSession,
) -> dict[str, Any] | None:
    """Load conflict_details JSONB from users table.

    Args:
        user_id: User's UUID.
        session: Async DB session.

    Returns:
        conflict_details dict or None if not set.
    """
    from nikita.db.models.user import User

    result = await session.execute(
        select(User.conflict_details).where(User.id == user_id)
    )
    row = result.scalar_one_or_none()
    return row if row else None


async def save_conflict_details(
    user_id: UUID,
    details: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Write conflict_details JSONB to users table.

    Args:
        user_id: User's UUID.
        details: ConflictDetails as dict (from .to_jsonb()).
        session: Async DB session.
    """
    from nikita.db.models.user import User

    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(conflict_details=details)
    )
    await session.flush()

    logger.info(
        f"[CONFLICT] Saved conflict_details for user {user_id}: "
        f"temp={details.get('temperature', 0):.1f}, zone={details.get('zone', 'calm')}"
    )
