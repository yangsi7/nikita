"""Regression tests for _trigger_portal_handoff rewire — Spec 213 PR 213-3/4.

PR 213-3: Verifies _trigger_portal_handoff calls PortalOnboardingFacade.process().
PR 213-4: FR-14 — user_repo param REMOVED; function now opens its own session.

All tests updated to new signature: (user_id, drug_tolerance).
UserRepository is mocked via patching get_session_maker + UserRepository.

Per .claude/rules/testing.md:
  - Every test_* has at least one assert
  - Non-empty fixtures for iterator/worker paths
  - Patch source module, NOT importer
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
TELEGRAM_ID = 12345678


def _make_mock_session_maker(mock_user: MagicMock) -> tuple[MagicMock, AsyncMock, AsyncMock]:
    """Build a mock session_maker stack for _trigger_portal_handoff tests.

    FR-14: _trigger_portal_handoff calls get_session_maker() twice:
      1. session_maker = get_session_maker()          → mock_session_maker
         async with session_maker() as fresh_session: → mock_session_maker() →
         mock_fresh_session_ctx → yields mock_fresh_session
      2. async with get_session_maker()() as facade:  → mock_session_maker() →
         mock_facade_session_ctx → yields mock_facade_session

    Both calls reach mock_session_maker.side_effect which alternates contexts.

    IMPORTANT: side_effect is set on mock_session_maker itself (not .return_value)
    so that each mock_session_maker() call gets a distinct context manager.

    Returns:
        (mock_session_maker, mock_fresh_session, mock_facade_session)
        mock_fresh_session = session for user lookup + early writes
        mock_facade_session = session passed to PortalOnboardingFacade.process()
    """
    mock_fresh_session = AsyncMock()
    mock_fresh_session.commit = AsyncMock()
    mock_fresh_session_ctx = AsyncMock()
    mock_fresh_session_ctx.__aenter__ = AsyncMock(return_value=mock_fresh_session)
    mock_fresh_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_facade_session = AsyncMock()
    mock_facade_session.commit = AsyncMock()
    mock_facade_session_ctx = AsyncMock()
    mock_facade_session_ctx.__aenter__ = AsyncMock(return_value=mock_facade_session)
    mock_facade_session_ctx.__aexit__ = AsyncMock(return_value=False)

    # side_effect on mock_session_maker itself: each call() returns a different ctx
    call_count = [0]

    def _make_session_ctx():
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_fresh_session_ctx  # first call: user lookup session
        return mock_facade_session_ctx  # subsequent calls: facade session

    mock_session_maker = MagicMock(side_effect=_make_session_ctx)

    return mock_session_maker, mock_fresh_session, mock_facade_session


class TestTriggerPortalHandoffFacadeIntegration:
    """_trigger_portal_handoff calls PortalOnboardingFacade.process() (PR 213-3 regression)."""

    @pytest.mark.asyncio
    async def test_facade_called_when_telegram_id_present(self):
        """Facade.process() is called when user has telegram_id (normal path)."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {
            "city": "Berlin",
            "social_scene": "techno",
            "darkness_level": 3,
        }

        mock_session_maker, mock_fresh_session, mock_facade_session = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.HandoffManager") as MockHandoff,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.return_value = []
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.error = None
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            mock_facade_inst.process.assert_awaited_once()
            call_args = mock_facade_inst.process.call_args
            assert call_args[0][0] == USER_ID

    @pytest.mark.asyncio
    async def test_facade_failure_does_not_block_handoff(self):
        """Facade error is non-blocking — handoff still proceeds."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {"city": "Berlin", "social_scene": "techno"}

        mock_session_maker, _, _ = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.HandoffManager") as MockHandoff,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.side_effect = RuntimeError("LLM exploded")
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.error = None
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            MockUserRepo.return_value = mock_repo_inst

            # Should NOT raise — facade errors are non-blocking
            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            # Handoff still called despite facade failure
            mock_handoff_inst.execute_handoff.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_facade_skipped_when_no_telegram_id(self):
        """When user has no telegram_id, facade is NOT called (deferred path)."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = None
        mock_user.phone = None
        mock_user.onboarding_profile = {}

        mock_session_maker, _, _ = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            # Facade should NOT be instantiated on deferred path
            MockFacade.assert_not_called()

    @pytest.mark.asyncio
    async def test_facade_session_is_fresh_not_request_scoped(self):
        """FR-14: facade receives a fresh session, not a request-scoped one."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {"city": "Berlin", "social_scene": "techno"}

        mock_session_maker, mock_fresh_session, mock_facade_session = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.HandoffManager") as MockHandoff,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.return_value = []
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            MockUserRepo.return_value = mock_repo_inst

            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            # get_session_maker was called (fresh session opened)
            mock_session_maker.assert_called()
            # Facade.process was called with user_id as first arg
            process_call = mock_facade_inst.process.call_args
            assert process_call[0][0] == USER_ID


class TestTriggerPortalHandoffPreservesPublicInterface:
    """Existing public behaviour of _trigger_portal_handoff is unchanged."""

    @pytest.mark.asyncio
    async def test_deferred_handoff_when_no_telegram_id(self):
        """User without telegram_id gets pending_handoff=True set (existing behaviour)."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = None
        mock_user.phone = None
        mock_user.onboarding_profile = {}

        mock_session_maker, _, _ = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade"),
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

        mock_repo_inst.set_pending_handoff.assert_awaited_once_with(USER_ID, True)

    @pytest.mark.asyncio
    async def test_user_not_found_returns_gracefully(self):
        """User not found: function returns without raising."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_session_maker, _, _ = _make_mock_session_maker(MagicMock())

        with (
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None  # user not found
            MockUserRepo.return_value = mock_repo_inst

            # Must NOT raise
            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

        assert mock_repo_inst.get.await_count == 1


class TestTriggerPortalHandoffSessionCommit:
    """N-02 regression: facade_session.commit() must be awaited.

    SQLAlchemy 2.x AsyncSession.__aexit__ calls close() without implicit commit.
    Writes inside _bootstrap_pipeline (pipeline_state transitions) are silently
    rolled back unless an explicit commit is issued after facade.process().
    """

    @pytest.mark.asyncio
    async def test_trigger_portal_handoff_commits_session_on_success(self):
        """facade_session.commit() is awaited after facade.process() succeeds.

        N-02 regression: SQLAlchemy 2.x AsyncSession.__aexit__ calls close()
        without implicit commit. Writes inside _bootstrap_pipeline (pipeline_state
        transitions) are silently rolled back unless explicit commit is issued.

        Mock tracing note: _trigger_portal_handoff calls get_session_maker() twice:
          1. Line 868: `session_maker = get_session_maker()` → mock_session_maker
             `async with session_maker() as fresh_session:` — uses
             mock_session_maker.return_value directly as async context manager.
          2. Line 930: `async with get_session_maker()() as facade_session:` —
             calls mock_session_maker.return_value() which triggers side_effect
             → returns mock_fresh_session_ctx → __aenter__ yields mock_fresh_session.
        So `facade_session` = mock_fresh_session. Commit assertion targets
        mock_fresh_session (the object yielded to the facade path).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {
            "city": "Berlin",
            "social_scene": "techno",
            "darkness_level": 3,
        }

        mock_session_maker, mock_fresh_session, mock_facade_session = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.HandoffManager") as MockHandoff,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.return_value = []
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.error = None
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            MockUserRepo.return_value = mock_repo_inst

            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            # facade_session = mock_facade_session (2nd call to mock_session_maker).
            # commit() must be awaited to persist pipeline_state='ready' (N-02 regression).
            mock_facade_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_trigger_portal_handoff_commits_session_on_facade_error(self):
        """facade_session.commit() is awaited even when facade.process() raises.

        _bootstrap_pipeline writes pipeline_state='failed' before re-raising.
        That write must be committed so it survives session close.

        Mock tracing note: same as test_trigger_portal_handoff_commits_session_on_success —
        facade_session = mock_fresh_session (yielded by mock_fresh_session_ctx).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {"city": "Berlin", "social_scene": "techno"}

        mock_session_maker, mock_fresh_session, mock_facade_session = _make_mock_session_maker(mock_user)

        with (
            patch("nikita.api.routes.onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.onboarding.HandoffManager") as MockHandoff,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.side_effect = RuntimeError("LLM exploded")
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.error = None
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = mock_user
            MockUserRepo.return_value = mock_repo_inst

            # Should NOT raise — facade errors are non-blocking
            await _trigger_portal_handoff(user_id=USER_ID, drug_tolerance=3)

            # facade_session = mock_facade_session (2nd call to mock_session_maker).
            # commit() must be awaited even on error to persist pipeline_state='failed'.
            mock_facade_session.commit.assert_awaited_once()
            # Handoff still proceeds despite facade failure
            mock_handoff_inst.execute_handoff.assert_awaited_once()
