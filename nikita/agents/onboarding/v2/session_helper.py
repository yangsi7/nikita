"""Spec 218 Slice 218-2 — sticky-flag session helper (R1 + R11).

`migration_or_init_v2_session(user_id, session)` resolves the v1/v2 path
for a single user's onboarding session per plan R11 sticky-flag invariant:

  1. Read `users.onboarding_profile` JSONB.
  2. If `state_version` already stamped → honor stamp (sticky).
  3. Else evaluate `settings.is_wizard_v2_enabled_for_user(user_id)` and
     stamp the JSONB with `"v2"` or `"v1"` immediately.

Returns `(use_v2: bool, profile: dict)`. The caller dispatches to the
v2 handler when `use_v2` is True, else the legacy v1 path.

Per plan R1: this helper MUST be called BEFORE any persistence call in
the /answer route handler. Persisting via the v2 path before evaluating
the flag would double-write and corrupt the sticky-flag invariant.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.settings import get_settings
from nikita.db.repositories.user_repository import UserRepository


STATE_VERSION_KEY: str = "state_version"
"""Key inside ``users.onboarding_profile`` JSONB storing the sticky stamp.

Values: ``"v1"`` or ``"v2"``. Absence ⇒ fresh session (evaluate flag).
"""


async def migration_or_init_v2_session(
    user_id: UUID,
    session: AsyncSession,
) -> tuple[bool, dict[str, Any]]:
    """Resolve v2 vs v1 path for a single user's onboarding session.

    Sticky-flag invariant (plan R11): once stamped, the session honors
    its stamp regardless of subsequent flag flips. Mid-session migration
    is forbidden (would break state schema continuity).

    Returns:
        ``(use_v2, profile)`` where ``profile`` is the persisted JSONB
        dict (already stamped if fresh).
    """
    repo = UserRepository(session)
    user = await repo.get(user_id)
    if user is None:
        # Caller is expected to handle the missing-user case (404). We
        # return a safe v1 default so the caller's existing v1 code path
        # produces the familiar "User not found" error.
        return False, {}

    profile: dict[str, Any] = user.onboarding_profile or {}
    stamped = profile.get(STATE_VERSION_KEY)

    if stamped in ("v1", "v2"):
        # Sticky: honor existing stamp regardless of current flag.
        return stamped == "v2", profile

    # Fresh session — evaluate flag once and stamp immediately.
    settings = get_settings()
    use_v2 = settings.is_wizard_v2_enabled_for_user(str(user_id))
    new_stamp = "v2" if use_v2 else "v1"

    await repo.update_onboarding_profile(
        user_id=user_id,
        profile_updates={STATE_VERSION_KEY: new_stamp},
    )
    profile = {**profile, STATE_VERSION_KEY: new_stamp}
    return use_v2, profile


__all__ = ["STATE_VERSION_KEY", "migration_or_init_v2_session"]
