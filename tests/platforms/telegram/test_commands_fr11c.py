"""Tests for FR-11c `_handle_start` vanilla-branch rewrite (Spec 214 T1.3-5).

The legacy 3-branch start handler is replaced: every vanilla `/start`
now routes to the portal via a bare URL (E1) or a bridge-token URL
(E3-E6). The payload branch (E7, `/start <code>`) is unchanged; its
regression coverage lives in `test_commands.py::TestHandleStartWithPayload`.

ACs covered:
  - AC-T1.3.1 (AC-11c.1, E1): unknown telegram_id → bare URL button.
  - AC-T1.3.2 (AC-11c.2, E2/E8): onboarded + active → welcome-back text only.
  - AC-T1.3.3 (AC-11c.3, E3/E4): game_over/won → reset + re-onboard (1h) bridge.
  - AC-T1.3.4 (AC-11c.4+AC-11c.5, E5/E6): pending/in_progress/limbo → resume (24h).
  - AC-T1.3.5 (AC-11c.9): DI guard raises RuntimeError (not assert).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.models.user import User
from nikita.platforms.telegram.commands import CommandHandler


def _msg(text: str, telegram_id: int = 123456789) -> dict:
    return {
        "message_id": 1,
        "from": {"id": telegram_id, "first_name": "Alex"},
        "chat": {"id": telegram_id, "type": "private"},
        "text": text,
    }


def _user(
    *,
    onboarding_status: str = "completed",
    game_status: str = "active",
    has_profile: bool = True,
) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.telegram_id = 123456789
    u.chapter = 1
    u.relationship_score = Decimal("50")
    u.onboarding_status = onboarding_status
    u.game_status = game_status
    # Stash helper flag on the mock for the fixture to key the profile
    # repo's mocked return.
    u._has_profile = has_profile
    return u


@pytest.fixture
def mock_user_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_telegram_auth() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_message_with_keyboard = AsyncMock()
    return bot


@pytest.fixture
def mock_profile_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def handler(
    mock_user_repository: AsyncMock,
    mock_telegram_auth: AsyncMock,
    mock_bot: AsyncMock,
    mock_profile_repository: AsyncMock,
) -> CommandHandler:
    """CommandHandler wired with the FR-11c-required profile_repository."""
    return CommandHandler(
        user_repository=mock_user_repository,
        telegram_auth=mock_telegram_auth,
        bot=mock_bot,
        profile_repository=mock_profile_repository,
    )


class TestE1UnknownUser:
    """AC-T1.3.1 / AC-11c.1: new user → bare portal URL."""

    @pytest.mark.asyncio
    async def test_unknown_user_sends_bare_portal_url_button(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        mock_user_repository.get_by_telegram_id.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://portal.example/onboarding/auth"),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        # E1: helper called with user_id=None + reason=None (bare path)
        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs.get("user_id") is None
        assert kwargs.get("reason") is None

        # Single URL button, no extra DB writes, no email prompt
        mock_bot.send_message_with_keyboard.assert_awaited_once()
        mock_bot.send_message.assert_not_called()
        button = mock_bot.send_message_with_keyboard.call_args.kwargs["keyboard"][0][0]
        assert button["url"] == "https://portal.example/onboarding/auth"

    @pytest.mark.asyncio
    async def test_unknown_user_no_placeholder_db_row(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        """AC-11c.1: MUST NOT create a users row or any placeholder state."""
        mock_user_repository.get_by_telegram_id.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth"),
        ):
            await handler.handle(_msg("/start"))

        # The only read is get_by_telegram_id. No create / upsert calls.
        mock_user_repository.get_by_telegram_id.assert_awaited_once()
        mock_user_repository.create.assert_not_called() if hasattr(
            mock_user_repository, "create"
        ) else None
        for attr in ("create_user", "create", "insert", "update", "reset_game_state"):
            method = getattr(mock_user_repository, attr, None)
            if method is not None:
                method.assert_not_called()


class TestE2OnboardedActive:
    """AC-T1.3.2 / AC-11c.2: onboarded + active → welcome-back, no button."""

    @pytest.mark.asyncio
    async def test_onboarded_active_returns_welcome_back_only(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="completed", game_status="active")
        mock_user_repository.get_by_telegram_id.return_value = user
        mock_profile_repository.get.return_value = MagicMock()  # profile present

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        # No bridge generated, no keyboard, just a text message.
        mock_gen.assert_not_awaited()
        mock_bot.send_message_with_keyboard.assert_not_called()
        mock_bot.send_message.assert_awaited_once()
        text = mock_bot.send_message.call_args.kwargs["text"].lower()
        assert "again" in text or "back" in text
        # No state mutations.
        mock_user_repository.reset_game_state.assert_not_called()


class TestE3E4GameOverOrWon:
    """AC-T1.3.3 / AC-11c.3: game_over/won → reset + re-onboard bridge (1h)."""

    @pytest.mark.asyncio
    async def test_game_over_resets_and_sends_re_onboard_bridge(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="completed", game_status="game_over")
        mock_user_repository.get_by_telegram_id.return_value = user
        mock_profile_repository.get.return_value = MagicMock()

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=t1"),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        mock_user_repository.reset_game_state.assert_awaited_once_with(user.id)
        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["user_id"] == str(user.id)
        assert kwargs["reason"] == "re-onboard"
        mock_bot.send_message_with_keyboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_won_resets_and_sends_re_onboard_bridge(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="completed", game_status="won")
        mock_user_repository.get_by_telegram_id.return_value = user
        mock_profile_repository.get.return_value = MagicMock()

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=t2"),
        ):
            await handler.handle(_msg("/start"))

        mock_user_repository.reset_game_state.assert_awaited_once_with(user.id)


class TestE5E6PendingOrLimbo:
    """AC-T1.3.4 / AC-11c.4 + AC-11c.5: pending/in_progress/limbo → resume (24h)."""

    @pytest.mark.asyncio
    async def test_pending_routes_to_resume_bridge(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="pending", game_status="active")
        mock_user_repository.get_by_telegram_id.return_value = user
        mock_profile_repository.get.return_value = None  # may be partial / null

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=t3"),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["reason"] == "resume"
        mock_user_repository.reset_game_state.assert_not_called()
        # Copy includes the "pick this up" framing.
        mock_bot.send_message_with_keyboard.assert_awaited_once()
        text = mock_bot.send_message_with_keyboard.call_args.kwargs["text"].lower()
        assert "pick" in text or "left off" in text or "where" in text

    @pytest.mark.asyncio
    async def test_in_progress_routes_to_resume_bridge(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="in_progress", game_status="active")
        mock_user_repository.get_by_telegram_id.return_value = user
        mock_profile_repository.get.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=t4"),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        _, kwargs = mock_gen.call_args
        assert kwargs["reason"] == "resume"

    @pytest.mark.asyncio
    async def test_limbo_user_row_no_profile_routes_to_resume(
        self,
        handler: CommandHandler,
        mock_user_repository: AsyncMock,
        mock_profile_repository: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        """E6 limbo: users row exists but profile is absent.

        AC-11c.5: treat as resume path, NOT fresh-onboard Q&A.
        """
        user = _user(onboarding_status="completed", game_status="active")
        mock_user_repository.get_by_telegram_id.return_value = user
        # Critical: profile absent
        mock_profile_repository.get.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=t5"),
        ) as mock_gen:
            await handler.handle(_msg("/start"))

        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["reason"] == "resume"
        mock_user_repository.reset_game_state.assert_not_called()


class TestDIGuards:
    """AC-T1.3.5 / AC-11c.9: RuntimeError (not assert) on missing deps."""

    @pytest.mark.asyncio
    async def test_missing_profile_repository_raises_runtime_error(
        self,
        mock_user_repository: AsyncMock,
        mock_telegram_auth: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        """Vanilla /start path with a known user requires profile_repository."""
        handler = CommandHandler(
            user_repository=mock_user_repository,
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
            profile_repository=None,  # DI misconfig
        )
        mock_user_repository.get_by_telegram_id.return_value = _user()

        with pytest.raises(RuntimeError, match="profile_repository"):
            await handler.handle(_msg("/start"))


class TestNoLegacyOnboardingReferences:
    """AC-11c.10 (scoped): no OnboardingHandler imports/attrs on commands.py.

    Stronger variant lives in `test_wiring.py::test_no_onboarding_handler_references`
    in T1.6, but this test guards the command module itself.
    """

    def test_commands_module_has_no_onboarding_handler_symbol(self) -> None:
        import nikita.platforms.telegram.commands as commands_mod

        assert not hasattr(commands_mod, "OnboardingHandler")
        assert not hasattr(commands_mod, "OnboardingStateRepository")
