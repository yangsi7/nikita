"""Tests for asyncpg session-poison prevention in _run_completion_side_effects (GH #624).

Root cause: seed_vices_from_profile raises a DB exception inside a swallowed
except-Exception block in _run_completion_side_effects. The exception is logged
as "non-fatal" but the session's asyncpg transaction is now in FAILED state.
The route handler then commits the session (via get_async_session), which raises
InFailedSQLTransactionError and poisons the pool connection for subsequent requests.

Fix: call `await session.rollback()` inside the swallowed-exception block so the
session is clean even when seed_vices fails, allowing the outer commit to succeed.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.exc import IntegrityError


class TestCompletionSideEffectsRollback:
    """_run_completion_side_effects must rollback on seed_vices failure (GH #624)."""

    @pytest.fixture
    def mock_session(self):
        """A mock AsyncSession."""
        session = AsyncMock()
        session.rollback = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        user.onboarding_status = "in_progress"
        return user

    @pytest.fixture
    def mock_state(self):
        from nikita.agents.onboarding.v2.state import WizardSlotsV2, WizardStateV2, Phase
        slots = WizardSlotsV2()
        return WizardStateV2(slots=slots, phase=Phase.phase2)

    @pytest.mark.asyncio
    async def test_session_rollback_called_when_seed_vices_fails(
        self, mock_session, mock_user, mock_state
    ):
        """When seed_vices_from_profile raises a DB exception, session.rollback()
        must be called so the transaction is clean (GH #624).

        Without the fix, the exception is swallowed but the asyncpg transaction
        stays FAILED, poisoning the pool connection.
        """
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        mock_user_repo = AsyncMock()

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)  # No existing profile
        mock_profile_repo.create_profile = AsyncMock()

        db_error = IntegrityError("seed_vices failed", {}, None)

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                side_effect=db_error,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
        ):
            # Should NOT raise — seed_vices failure is non-fatal
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # profile and game activation should still complete
        mock_profile_repo.create_profile.assert_awaited_once()
        mock_user_repo.update_onboarding_status.assert_awaited_once_with(
            mock_user.id, "completed"
        )
        mock_user_repo.activate_game.assert_awaited_once_with(mock_user.id)

        # rollback MUST be called after the swallowed seed_vices exception (GH #624)
        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_rollback_when_seed_vices_succeeds(
        self, mock_session, mock_user, mock_state
    ):
        """When seed_vices succeeds, no rollback should be called."""
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        mock_user_repo = AsyncMock()

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                new_callable=AsyncMock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # No rollback on happy path
        mock_session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idempotency_guard_skips_on_existing_profile(
        self, mock_session, mock_user, mock_state
    ):
        """If profile already exists, skip all side effects (idempotency guard)."""
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        mock_user_repo = AsyncMock()
        existing_profile = MagicMock()  # non-None

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=existing_profile)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        mock_user_repo.update_onboarding_status.assert_not_awaited()
        mock_session.rollback.assert_not_awaited()
