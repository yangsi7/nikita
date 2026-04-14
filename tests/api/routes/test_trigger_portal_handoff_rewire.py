"""Regression tests for _trigger_portal_handoff rewire — Spec 213 PR 213-3.

Verifies that the rewired _trigger_portal_handoff calls PortalOnboardingFacade
to generate/cache backstory scenarios before delegating to HandoffManager.

Existing handoff contracts are preserved — public interface unchanged.
Only the internal path changes: facade now runs before HandoffManager.

Per .claude/rules/testing.md:
  - Non-empty fixtures where function iterates a result
  - Every test_* has at least one assert
  - Patch source module, NOT importer
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
TELEGRAM_ID = 12345678


class TestTriggerPortalHandoffFacadeIntegration:
    """_trigger_portal_handoff now calls PortalOnboardingFacade.process()."""

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

        with (
            patch(
                "nikita.api.routes.onboarding.PortalOnboardingFacade"
            ) as MockFacade,
            patch(
                "nikita.api.routes.onboarding.HandoffManager"
            ) as MockHandoff,
            patch(
                "nikita.api.routes.onboarding.get_session_maker"
            ) as MockSessionMaker,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.return_value = []  # empty = degraded path OK
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.error = None
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_maker = MagicMock()
            mock_maker.return_value = mock_session
            MockSessionMaker.return_value = mock_maker

            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user

            await _trigger_portal_handoff(
                user_id=USER_ID,
                user_repo=mock_user_repo,
                drug_tolerance=3,
            )

            mock_facade_inst.process.assert_awaited_once()
            # First positional arg is user_id
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

        with (
            patch(
                "nikita.api.routes.onboarding.PortalOnboardingFacade"
            ) as MockFacade,
            patch(
                "nikita.api.routes.onboarding.HandoffManager"
            ) as MockHandoff,
            patch(
                "nikita.api.routes.onboarding.get_session_maker"
            ) as MockSessionMaker,
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

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_maker = MagicMock()
            mock_maker.return_value = mock_session
            MockSessionMaker.return_value = mock_maker

            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user

            # Should NOT raise — facade errors are non-blocking
            await _trigger_portal_handoff(
                user_id=USER_ID,
                user_repo=mock_user_repo,
                drug_tolerance=3,
            )

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

        with (
            patch(
                "nikita.api.routes.onboarding.PortalOnboardingFacade"
            ) as MockFacade,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo.set_pending_handoff = AsyncMock()

            await _trigger_portal_handoff(
                user_id=USER_ID,
                user_repo=mock_user_repo,
                drug_tolerance=3,
            )

            # Facade should NOT be instantiated on deferred path
            MockFacade.assert_not_called()

    @pytest.mark.asyncio
    async def test_facade_session_is_fresh_not_request_scoped(self):
        """Facade receives a fresh session from get_session_maker(), not request session."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = TELEGRAM_ID
        mock_user.phone = None
        mock_user.onboarding_profile = {"city": "Berlin", "social_scene": "techno"}

        with (
            patch(
                "nikita.api.routes.onboarding.PortalOnboardingFacade"
            ) as MockFacade,
            patch(
                "nikita.api.routes.onboarding.HandoffManager"
            ) as MockHandoff,
            patch(
                "nikita.api.routes.onboarding.get_session_maker"
            ) as MockSessionMaker,
        ):
            mock_facade_inst = AsyncMock()
            mock_facade_inst.process.return_value = []
            MockFacade.return_value = mock_facade_inst

            mock_result = MagicMock()
            mock_result.success = True
            mock_handoff_inst = AsyncMock()
            mock_handoff_inst.execute_handoff.return_value = mock_result
            MockHandoff.return_value = mock_handoff_inst

            mock_inner_session = AsyncMock()
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_inner_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_maker = MagicMock()
            mock_maker.return_value = mock_session_ctx
            MockSessionMaker.return_value = mock_maker

            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user

            await _trigger_portal_handoff(
                user_id=USER_ID,
                user_repo=mock_user_repo,
                drug_tolerance=3,
            )

            # get_session_maker was called (fresh session opened for facade)
            MockSessionMaker.assert_called_once()
            # Facade received the inner session from the context manager
            process_call = mock_facade_inst.process.call_args
            # Third positional arg is session
            assert process_call[0][2] is mock_inner_session


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

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user
        mock_user_repo.set_pending_handoff = AsyncMock()

        with patch("nikita.api.routes.onboarding.PortalOnboardingFacade"):
            await _trigger_portal_handoff(
                user_id=USER_ID,
                user_repo=mock_user_repo,
                drug_tolerance=3,
            )

        mock_user_repo.set_pending_handoff.assert_awaited_once_with(USER_ID, True)

    @pytest.mark.asyncio
    async def test_user_not_found_returns_gracefully(self):
        """User not found: function returns without raising."""
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None  # user not found

        # Must NOT raise
        await _trigger_portal_handoff(
            user_id=USER_ID,
            user_repo=mock_user_repo,
            drug_tolerance=3,
        )

        assert mock_user_repo.get.await_count == 1
