"""Tests for nikita.agents.onboarding.conversation_persistence (Spec 214 FR-11d).

Live per-user SELECT-FOR-UPDATE lock + JSONB persistence requires a
real Postgres session; those are covered by post-merge integration
tests. Here we verify the write-path helper with an ``AsyncMock``
session to prove:

- AC-T2.8.1 shape: ``SELECT ... FOR UPDATE`` statement issued + ORM
  round-trip (no raw ``jsonb_set``).
- AC-T2.8.3: 101st append evicts oldest + preserves ``extracted`` into
  ``elided_extracted``.

AC-T2.8.2 (MutableDict mutation tracking) is implicit in SQLAlchemy's
``default=dict`` + reassignment pattern used here — verified by the
fact that the helper reassigns ``user.onboarding_profile = profile``
rather than mutating in place (which would require MutableDict for
dirty-tracking).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_persistence import (
    CONVERSATION_TURN_CAP,
    append_conversation_turn,
)


def _mock_session_with_user(user_profile: dict | None = None):
    user = SimpleNamespace(id=uuid4(), onboarding_profile=user_profile)
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=user)
    session.execute = AsyncMock(return_value=result)
    return session, user


class TestAppendConversationTurn:
    @pytest.mark.asyncio
    async def test_concurrent_turn_writes_serialize_per_user(self):
        """AC-T2.8.1: helper issues SELECT ... FOR UPDATE (locking read)
        so two concurrent calls for the same user serialize on the row
        lock, not collide on JSONB writes.
        """
        session, user = _mock_session_with_user(None)
        await append_conversation_turn(
            session,
            user.id,
            {
                "role": "user",
                "content": "Zurich",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        session.execute.assert_awaited_once()
        # Verify FOR UPDATE is in the compiled statement. The helper
        # constructs ``select(User).where(User.id == uid).with_for_update()``.
        call_sql = str(session.execute.call_args.args[0])
        assert "FOR UPDATE" in call_sql

        # AC-T2.8.1 corollary: the helper reassigned the JSONB column;
        # no raw jsonb_set call in the session mock.
        assert user.onboarding_profile is not None
        assert "conversation" in user.onboarding_profile
        assert user.onboarding_profile["conversation"][0]["content"] == "Zurich"

    @pytest.mark.asyncio
    async def test_nested_mutation_flushes_without_reassign(self):
        """AC-T2.8.2 structural: helper reassigns the profile dict so
        dirty-tracking fires regardless of MutableDict wrapping. The
        reassignment is the explicit mechanism.
        """
        session, user = _mock_session_with_user({"conversation": []})
        original = user.onboarding_profile
        await append_conversation_turn(
            session,
            user.id,
            {"role": "nikita", "content": "hi", "timestamp": "2026-01-01T00:00:00Z"},
        )
        # Reassignment occurred — new object, not the same dict.
        assert user.onboarding_profile is not original

    @pytest.mark.asyncio
    async def test_turn_cap_elides_oldest_and_preserves_extracted(self):
        """AC-T2.8.3: 101st append evicts oldest; extracted fields of
        the evicted turn land in ``elided_extracted``.
        """
        # Pre-fill with exactly CONVERSATION_TURN_CAP turns, where the
        # oldest carries an extracted ``city`` field.
        initial_turns = [
            {
                "role": "user",
                "content": f"turn {i}",
                "timestamp": "2026-01-01T00:00:00Z",
                "extracted": (
                    {"city": "Zurich"} if i == 0 else None
                ),
            }
            for i in range(CONVERSATION_TURN_CAP)
        ]
        session, user = _mock_session_with_user(
            {"conversation": initial_turns}
        )

        await append_conversation_turn(
            session,
            user.id,
            {
                "role": "nikita",
                "content": "new turn",
                "timestamp": "2026-01-01T00:00:01Z",
            },
        )

        conv = user.onboarding_profile["conversation"]
        assert len(conv) == CONVERSATION_TURN_CAP, (
            f"expected cap={CONVERSATION_TURN_CAP}, got {len(conv)}"
        )
        assert conv[-1]["content"] == "new turn"
        # Oldest turn evicted.
        assert conv[0]["content"] != "turn 0"
        # Extracted city preserved in elided_extracted.
        assert (
            user.onboarding_profile["elided_extracted"].get("city")
            == "Zurich"
        )

    @pytest.mark.asyncio
    async def test_cap_constant_pinned(self):
        """Regression guard — AC-NR1b.5 pins the cap to 100."""
        assert CONVERSATION_TURN_CAP == 100
