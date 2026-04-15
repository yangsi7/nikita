"""Tests for phone-conditional handoff routing (Spec 212 PR C, T021).

Verifies _trigger_portal_handoff routes correctly:
- Voice branch: user.phone present + telegram_id present -> execute_handoff_with_voice_callback
- Telegram branch: user.phone absent + telegram_id present -> execute_handoff
- Pending branch: telegram_id absent -> early-return with pending_handoff=True
- Voice-callback exception -> Telegram fallback called
- Structured log keys present on every branch

Failing until T022/T023 (implementation) are committed.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.onboarding.handoff import HandoffResult
from nikita.onboarding.models import UserOnboardingProfile


def _make_user(
    *,
    user_id: UUID | None = None,
    telegram_id: int | None = 123456789,
    phone: str | None = None,
) -> MagicMock:
    """Build a mock User ORM object."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.telegram_id = telegram_id
    user.phone = phone
    user.onboarding_profile = {"darkness_level": 3}
    return user


def _make_success_result(user_id: UUID) -> HandoffResult:
    """Build a successful HandoffResult stub."""
    return HandoffResult(
        success=True,
        user_id=user_id,
        first_message_sent=False,
        nikita_callback_initiated=True,
    )


def _make_session_maker_for_user(mock_user: MagicMock) -> MagicMock:
    """Build a mock session_maker and UserRepository for FR-14 tests.

    FR-14 (PR 213-4): _trigger_portal_handoff no longer accepts user_repo.
    It calls get_session_maker() to open its own sessions. Tests must patch
    get_session_maker + UserRepository at source module.

    Returns mock_session_maker suitable for:
      patch("nikita.api.routes.onboarding.get_session_maker",
            return_value=mock_session_maker)

    The returned session_maker creates two distinct async sessions:
      1. fresh_session  — for user lookup (session_maker() call 1)
      2. facade_session — for PortalOnboardingFacade.process() (call 2)
    """
    def _make_ctx():
        session = AsyncMock()
        session.commit = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    call_count = [0]

    def _side_effect():
        call_count[0] += 1
        return _make_ctx()

    return MagicMock(side_effect=_side_effect)


class TestVoiceBranch:
    """User has phone + telegram_id -> execute_handoff_with_voice_callback."""

    @pytest.mark.asyncio
    async def test_voice_branch_calls_voice_callback(self, caplog):
        """Voice branch: execute_handoff_with_voice_callback is called when phone present.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=111222333, phone="+41791234567")

        mock_session_maker = _make_session_maker_for_user(user)
        mock_handoff_result = _make_success_result(user_id)

        with (
            patch("nikita.api.routes.onboarding.HandoffManager") as mock_hm_cls,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            mock_hm = mock_hm_cls.return_value
            mock_hm.execute_handoff_with_voice_callback = AsyncMock(
                return_value=mock_handoff_result
            )
            mock_hm.execute_handoff = AsyncMock()

            with caplog.at_level(logging.INFO, logger="nikita.api.routes.onboarding"):
                await _trigger_portal_handoff(
                    user_id=user_id,
                    drug_tolerance=3,
                )

        mock_hm.execute_handoff_with_voice_callback.assert_awaited_once()
        mock_hm.execute_handoff.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_voice_branch_structured_log(self, caplog):
        """Voice branch: structured log contains branch=voice, phone_present=True.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=111222333, phone="+41791234567")

        mock_session_maker = _make_session_maker_for_user(user)
        mock_handoff_result = _make_success_result(user_id)

        with (
            patch("nikita.api.routes.onboarding.HandoffManager") as mock_hm_cls,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            MockUserRepo.return_value = mock_repo_inst

            mock_hm = mock_hm_cls.return_value
            mock_hm.execute_handoff_with_voice_callback = AsyncMock(
                return_value=mock_handoff_result
            )
            mock_hm.execute_handoff = AsyncMock()

            with caplog.at_level(logging.DEBUG, logger="nikita.api.routes.onboarding"):
                await _trigger_portal_handoff(
                    user_id=user_id,
                    drug_tolerance=3,
                )

        # Verify structured log keys
        log_records = [r for r in caplog.records if hasattr(r, "event")]
        branch_records = [r for r in log_records if getattr(r, "event", "") == "portal_handoff.branch"]
        assert branch_records, "Expected portal_handoff.branch log record"
        rec = branch_records[0]
        assert rec.branch == "voice"
        assert rec.phone_present is True
        assert rec.telegram_present is True
        assert str(user_id) == rec.user_id


class TestTelegramBranch:
    """User has NO phone + has telegram_id -> existing execute_handoff."""

    @pytest.mark.asyncio
    async def test_telegram_branch_calls_execute_handoff(self, caplog):
        """Telegram branch: execute_handoff is called when phone absent.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=999888777, phone=None)

        mock_session_maker = _make_session_maker_for_user(user)
        mock_handoff_result = HandoffResult(
            success=True,
            user_id=user_id,
            first_message_sent=True,
        )

        with (
            patch("nikita.api.routes.onboarding.HandoffManager") as mock_hm_cls,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            MockUserRepo.return_value = mock_repo_inst

            mock_hm = mock_hm_cls.return_value
            mock_hm.execute_handoff = AsyncMock(return_value=mock_handoff_result)
            mock_hm.execute_handoff_with_voice_callback = AsyncMock()

            with caplog.at_level(logging.INFO, logger="nikita.api.routes.onboarding"):
                await _trigger_portal_handoff(
                    user_id=user_id,
                    drug_tolerance=2,
                )

        mock_hm.execute_handoff.assert_awaited_once()
        mock_hm.execute_handoff_with_voice_callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_telegram_branch_structured_log(self, caplog):
        """Telegram branch: structured log contains branch=telegram, phone_present=False.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=999888777, phone=None)

        mock_session_maker = _make_session_maker_for_user(user)
        mock_handoff_result = HandoffResult(
            success=True,
            user_id=user_id,
            first_message_sent=True,
        )

        with (
            patch("nikita.api.routes.onboarding.HandoffManager") as mock_hm_cls,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            MockUserRepo.return_value = mock_repo_inst

            mock_hm = mock_hm_cls.return_value
            mock_hm.execute_handoff = AsyncMock(return_value=mock_handoff_result)
            mock_hm.execute_handoff_with_voice_callback = AsyncMock()

            with caplog.at_level(logging.DEBUG, logger="nikita.api.routes.onboarding"):
                await _trigger_portal_handoff(
                    user_id=user_id,
                    drug_tolerance=2,
                )

        log_records = [r for r in caplog.records if hasattr(r, "event")]
        branch_records = [r for r in log_records if getattr(r, "event", "") == "portal_handoff.branch"]
        assert branch_records, "Expected portal_handoff.branch log record"
        rec = branch_records[0]
        assert rec.branch == "telegram"
        assert rec.phone_present is False
        assert rec.telegram_present is True


class TestPendingBranch:
    """User has NO telegram_id -> early-return with pending_handoff=True."""

    @pytest.mark.asyncio
    async def test_pending_branch_sets_flag(self, caplog):
        """Pending branch: set_pending_handoff called when telegram_id absent.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=None, phone=None)

        mock_session_maker = _make_session_maker_for_user(user)

        with (
            patch("nikita.api.routes.onboarding.HandoffManager") as mock_hm_cls,
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            mock_hm = mock_hm_cls.return_value
            mock_hm.execute_handoff = AsyncMock()
            mock_hm.execute_handoff_with_voice_callback = AsyncMock()

            await _trigger_portal_handoff(
                user_id=user_id,
                drug_tolerance=1,
            )

        mock_repo_inst.set_pending_handoff.assert_awaited_once_with(user_id, True)
        mock_hm.execute_handoff.assert_not_awaited()
        mock_hm.execute_handoff_with_voice_callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pending_branch_structured_log(self, caplog):
        """Pending branch: structured log contains branch=pending.

        FR-14: uses get_session_maker + UserRepository mocks (no user_repo param).
        """
        from nikita.api.routes.onboarding import _trigger_portal_handoff

        user_id = uuid4()
        user = _make_user(user_id=user_id, telegram_id=None, phone=None)

        mock_session_maker = _make_session_maker_for_user(user)

        with (
            patch("nikita.api.routes.onboarding.HandoffManager"),
            patch("nikita.api.routes.onboarding.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get = AsyncMock(return_value=user)
            mock_repo_inst.set_pending_handoff = AsyncMock()
            MockUserRepo.return_value = mock_repo_inst

            with caplog.at_level(logging.DEBUG, logger="nikita.api.routes.onboarding"):
                await _trigger_portal_handoff(
                    user_id=user_id,
                    drug_tolerance=1,
                )

        log_records = [r for r in caplog.records if hasattr(r, "event")]
        branch_records = [r for r in log_records if getattr(r, "event", "") == "portal_handoff.branch"]
        assert branch_records, "Expected portal_handoff.branch log record for pending"
        rec = branch_records[0]
        assert rec.branch == "pending"
        assert rec.phone_present is False
        assert rec.telegram_present is False


class TestVoiceCallbackFallback:
    """execute_handoff_with_voice_callback raises -> Telegram fallback is queued."""

    @pytest.mark.asyncio
    async def test_voice_failure_falls_back_to_telegram(self):
        """When initiate_nikita_callback raises, execute_handoff Telegram fallback is called."""
        from nikita.onboarding.handoff import HandoffManager

        manager = HandoffManager()
        user_id = uuid4()
        telegram_id = 555444333
        phone_number = "+41791234567"
        profile = UserOnboardingProfile(darkness_level=3)

        fallback_result = HandoffResult(
            success=True,
            user_id=user_id,
            first_message_sent=True,
        )

        with patch.object(
            manager,
            "initiate_nikita_callback",
            new_callable=AsyncMock,
            side_effect=RuntimeError("ElevenLabs unreachable"),
        ), patch.object(
            manager,
            "execute_handoff",
            new_callable=AsyncMock,
            return_value=fallback_result,
        ) as mock_execute_handoff, patch(
            "nikita.onboarding.handoff.generate_and_store_social_circle",
            new_callable=AsyncMock,
        ):
            result = await manager.execute_handoff_with_voice_callback(
                user_id=user_id,
                telegram_id=telegram_id,
                phone_number=phone_number,
                profile=profile,
            )

        # Telegram fallback must have been called
        mock_execute_handoff.assert_awaited_once()
        call_kwargs = mock_execute_handoff.call_args
        assert call_kwargs.kwargs.get("user_id") == user_id or call_kwargs.args[0] == user_id
        assert call_kwargs.kwargs.get("telegram_id") == telegram_id or telegram_id in call_kwargs.args

    @pytest.mark.asyncio
    async def test_voice_failure_outcome_log(self, caplog):
        """When voice callback fails, portal_handoff.voice_callback outcome=failure is logged."""
        from nikita.onboarding.handoff import HandoffManager

        manager = HandoffManager()
        user_id = uuid4()
        profile = UserOnboardingProfile(darkness_level=2)

        fallback_result = HandoffResult(
            success=True,
            user_id=user_id,
            first_message_sent=True,
        )

        with patch.object(
            manager,
            "initiate_nikita_callback",
            new_callable=AsyncMock,
            side_effect=ConnectionError("timeout"),
        ), patch.object(
            manager,
            "execute_handoff",
            new_callable=AsyncMock,
            return_value=fallback_result,
        ), patch(
            "nikita.onboarding.handoff.generate_and_store_social_circle",
            new_callable=AsyncMock,
        ):
            with caplog.at_level(logging.WARNING, logger="nikita.onboarding.handoff"):
                await manager.execute_handoff_with_voice_callback(
                    user_id=user_id,
                    telegram_id=444333222,
                    phone_number="+41791234567",
                    profile=profile,
                )

        log_records = [r for r in caplog.records if hasattr(r, "event")]
        outcome_records = [
            r for r in log_records
            if getattr(r, "event", "") == "portal_handoff.voice_callback"
            and getattr(r, "outcome", "") == "failure"
        ]
        assert outcome_records, "Expected portal_handoff.voice_callback outcome=failure log"
        rec = outcome_records[0]
        assert rec.error_class == "ConnectionError"
        assert str(user_id) == rec.user_id
