"""Per-user-serialized JSONB write path for /converse conversation turns.

Spec 214 FR-11d — AC-T2.8.1/2/3. Uses ``SELECT ... FOR UPDATE`` inside
a transaction to guarantee that two concurrent ``/converse`` calls for
the SAME user serialize cleanly on the user row and no turn is lost.

Pattern per tech-spec §2.3 step 8 and per PR #317 / PR #319 precedents
(raw ``jsonb_set`` caused double-encoded JSONB land-mines; the ORM
round-trip + ``MutableDict.as_mutable`` path is the durable fix).

Elision (AC-T2.8.3): when ``profile["conversation"]`` exceeds
``CONVERSATION_TURN_CAP`` (100 turns), the OLDEST turn is dropped AND
any ``extracted`` fields it carried are merged into
``profile["elided_extracted"]`` so the agent does not lose the field
signal. This preserves the invariant that the cumulative extracted
profile is monotonically non-decreasing.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import User


# Conversation turn cap — per AC-NR1b.5 / tech-spec §10 open-question 3.
CONVERSATION_TURN_CAP: int = 100


async def append_conversation_turn(
    session: AsyncSession, user_id: UUID, new_turn: dict[str, Any]
) -> None:
    """Append one turn to ``users.onboarding_profile["conversation"]``.

    Flow:
    1. ``SELECT ... FOR UPDATE`` locks the user row.
    2. Defensive-copy the JSONB dict so the ORM treats it as a new value
       (avoids MutableDict tracking flakiness on deep mutations).
    3. Append the turn; elide oldest if over cap.
    4. Reassign ``user.onboarding_profile = profile`` so SQLAlchemy
       dirty-tracking fires on commit.

    Caller owns the transaction boundary so it can batch this with the
    idempotency-cache PUT and the spend-ledger UPDATE atomically.
    """
    stmt = select(User).where(User.id == user_id).with_for_update()
    result = await session.execute(stmt)
    user = result.scalar_one()

    # Defensive copy: mutate a local dict, then reassign to trigger
    # dirty tracking (works with or without MutableDict wrapping).
    profile: dict[str, Any] = dict(user.onboarding_profile or {})
    conversation: list[dict[str, Any]] = list(profile.get("conversation", []))
    elided_extracted: dict[str, Any] = dict(profile.get("elided_extracted", {}))

    conversation.append(new_turn)

    # Elide oldest if over cap — preserve extracted fields.
    if len(conversation) > CONVERSATION_TURN_CAP:
        oldest = conversation.pop(0)
        extracted = oldest.get("extracted") or {}
        for key, value in extracted.items():
            # Last-write-wins; the newer extraction already lives later
            # in the conversation list.
            if key not in elided_extracted:
                elided_extracted[key] = value

    profile["conversation"] = conversation
    profile["elided_extracted"] = elided_extracted
    user.onboarding_profile = profile


__all__ = [
    "CONVERSATION_TURN_CAP",
    "append_conversation_turn",
]
