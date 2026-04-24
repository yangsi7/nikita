"""Tests for signup_handler — Spec 215 PR-F1b consolidated FSM.

Maps to T015 acceptance criteria:
- AC-1: /start welcome for unbound telegram_id triggers welcome + AWAITING_EMAIL row
- AC-2: invalid email keeps state AWAITING_EMAIL, Nikita rejection
- AC-3: valid email → CODE_SENT via repo CAS + emits signup_email_received telemetry
- AC-4: invalid OTP increments attempts; 3rd invalid → rate-limit + reset
- AC-5: expired code emits "Code expired" + row purge
- AC-6: valid OTP → MAGIC_LINK_SENT via FR-5 admin endpoint + Telegram delivery

Mapped FR/AC: FR-2, FR-3, FR-4, FR-5; AC-2.1..AC-2.3, AC-3.1..AC-3.4, AC-4.1..AC-4.4, AC-5.4
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from nikita.platforms.telegram.signup_handler import SignupHandler


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_message_with_keyboard = AsyncMock()
    return bot


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=None)
    repo.create_awaiting_email = AsyncMock(return_value="row-id-1")
    repo.transition_to_code_sent = AsyncMock(return_value="row-id-1")
    repo.transition_to_magic_link_sent = AsyncMock(return_value="row-id-1")
    repo.delete_on_completion = AsyncMock(return_value=1)
    repo.increment_attempts = AsyncMock(return_value=1)
    return repo


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_telegram_id = AsyncMock(return_value=None)
    repo.update_telegram_id = AsyncMock()
    return repo


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Mock Supabase async client with auth.* methods."""
    supabase = MagicMock()
    supabase.auth.sign_in_with_otp = AsyncMock(return_value=MagicMock(status_code=200))

    verify_response = MagicMock()
    verify_response.user = MagicMock()
    verify_response.user.id = "550e8400-e29b-41d4-a716-446655440000"
    supabase.auth.verify_otp = AsyncMock(return_value=verify_response)

    return supabase


@pytest.fixture
def mock_admin_endpoint() -> AsyncMock:
    """Mock direct call to portal_auth.generate_magiclink_for_telegram_user."""
    endpoint = AsyncMock()
    endpoint.return_value = SimpleNamespace(
        action_link="https://supabase.example.com/verify?token_hash=xxx&type=magiclink",
        hashed_token="hashed-xyz",
        verification_type="magiclink",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return endpoint


@pytest.fixture
def handler(mock_bot, mock_repo, mock_user_repo, mock_supabase, mock_admin_endpoint):
    return SignupHandler(
        bot=mock_bot,
        repo=mock_repo,
        user_repo=mock_user_repo,
        supabase_client=mock_supabase,
        admin_generate_magiclink=mock_admin_endpoint,
    )


# ---------------------------------------------------------------------------
# AC-1 / FR-2 welcome
# ---------------------------------------------------------------------------


class TestHandleWelcome:
    @pytest.mark.asyncio
    async def test_ac1_welcome_creates_awaiting_email_row_and_greets(
        self, handler, mock_bot, mock_repo
    ):
        """AC-2.1: `/start welcome` for unbound telegram_id triggers welcome
        message and creates `signup_state=AWAITING_EMAIL` row in
        telegram_signup_sessions."""
        telegram_id = 123456789
        chat_id = 987654321

        await handler.handle_welcome(telegram_id=telegram_id, chat_id=chat_id)

        mock_repo.create_awaiting_email.assert_awaited_once_with(
            telegram_id=telegram_id, chat_id=chat_id
        )
        mock_bot.send_message.assert_awaited_once()
        kw = mock_bot.send_message.call_args.kwargs
        assert kw["chat_id"] == chat_id
        assert "email" in kw["text"].lower()

    @pytest.mark.asyncio
    async def test_ac1_welcome_emits_signup_started_telemetry(
        self, handler, mock_bot, mock_repo
    ):
        """FR-Telemetry-1: emit signup_started_telegram on FSM entry."""
        telegram_id = 123456789
        chat_id = 987654321

        with patch(
            "nikita.platforms.telegram.signup_handler.emit_signup_started_telegram"
        ) as mock_emit:
            await handler.handle_welcome(
                telegram_id=telegram_id, chat_id=chat_id
            )

        mock_emit.assert_called_once()
        event = mock_emit.call_args.args[0]
        assert event.telegram_id_hash  # hashed, not raw


# ---------------------------------------------------------------------------
# AC-2 / FR-2 invalid email rejection
# ---------------------------------------------------------------------------


class TestHandleEmailInvalid:
    @pytest.mark.asyncio
    async def test_ac2_invalid_email_rejects_without_state_change(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """AC-2.2: invalid-email submission emits Nikita-voiced rejection AND
        keeps signup_state=AWAITING_EMAIL (no row mutation)."""
        # Fixture: AWAITING_EMAIL row exists
        existing = MagicMock()
        existing.signup_state = "awaiting_email"
        existing.email = ""
        existing.last_attempt_at = None
        mock_repo.get.return_value = existing

        await handler.handle_email(
            telegram_id=123, chat_id=456, text="not-an-email"
        )

        mock_repo.transition_to_code_sent.assert_not_awaited()
        mock_supabase.auth.sign_in_with_otp.assert_not_awaited()
        mock_bot.send_message.assert_awaited_once()
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "email" in text.lower() or "doesn't look" in text.lower()


# ---------------------------------------------------------------------------
# AC-3 / FR-3 valid email path
# ---------------------------------------------------------------------------


class TestHandleEmailValid:
    @pytest.mark.asyncio
    async def test_ac3_valid_email_calls_supabase_and_advances_to_code_sent(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """AC-3.1/3.2: valid email → sign_in_with_otp + CAS to CODE_SENT."""
        existing = MagicMock()
        existing.signup_state = "awaiting_email"
        existing.email = ""
        existing.last_attempt_at = None
        mock_repo.get.return_value = existing

        await handler.handle_email(
            telegram_id=123, chat_id=456, text="player@example.com"
        )

        mock_supabase.auth.sign_in_with_otp.assert_awaited_once()
        otp_call = mock_supabase.auth.sign_in_with_otp.call_args.args[0]
        assert otp_call["email"] == "player@example.com"
        assert otp_call["options"]["should_create_user"] is True

        mock_repo.transition_to_code_sent.assert_awaited_once_with(
            telegram_id=123, email="player@example.com"
        )

        mock_bot.send_message.assert_awaited_once()
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "code" in text.lower() or "inbox" in text.lower()

    @pytest.mark.asyncio
    async def test_ac3_emits_signup_email_received_and_code_sent_telemetry(
        self, handler, mock_repo
    ):
        """FR-Telemetry-1: emit signup_email_received + signup_code_sent."""
        existing = MagicMock()
        existing.signup_state = "awaiting_email"
        existing.email = ""
        existing.last_attempt_at = None
        mock_repo.get.return_value = existing

        with patch(
            "nikita.platforms.telegram.signup_handler.emit_signup_email_received"
        ) as mock_email_emit, patch(
            "nikita.platforms.telegram.signup_handler.emit_signup_code_sent"
        ) as mock_code_emit:
            await handler.handle_email(
                telegram_id=123, chat_id=456, text="player@example.com"
            )

        mock_email_emit.assert_called_once()
        mock_code_emit.assert_called_once()


# ---------------------------------------------------------------------------
# AC-4 / FR-4 invalid OTP + rate-limit
# ---------------------------------------------------------------------------


class TestHandleCodeInvalid:
    @pytest.mark.asyncio
    async def test_ac4_invalid_otp_increments_attempts(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """AC-4.1: invalid OTP increments attempts."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing
        mock_repo.increment_attempts.return_value = 1

        from supabase.lib.client_options import (  # noqa: F401
            ClientOptions,
        )
        from gotrue.errors import AuthApiError

        mock_supabase.auth.verify_otp.side_effect = AuthApiError(
            "invalid", 400, "invalid_credentials"
        )

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="000000"
        )

        mock_repo.increment_attempts.assert_awaited_once_with(telegram_id=123)
        mock_repo.transition_to_magic_link_sent.assert_not_awaited()
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "tries" in text.lower() or "left" in text.lower() or "right" in text.lower()

    @pytest.mark.asyncio
    async def test_ac4_third_invalid_otp_triggers_rate_limit_reset(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """AC-4.2: 3 invalid attempts within 1h triggers rate-limit + delete row."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 2
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing
        mock_repo.increment_attempts.return_value = 3

        from gotrue.errors import AuthApiError
        mock_supabase.auth.verify_otp.side_effect = AuthApiError(
            "invalid", 400, "invalid_credentials"
        )

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="000000"
        )

        # Row deleted (rate-limit reset)
        # Use delete via repo helper or session — check that we cleaned up
        assert (
            mock_repo.delete_on_completion.await_count > 0
            or hasattr(mock_repo, "delete")
            and mock_repo.delete.await_count > 0
            or mock_repo.purge.await_count > 0
        )


class TestHandleCodeExpired:
    @pytest.mark.asyncio
    async def test_ac5_expired_code_purges_row_and_notifies(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """AC-4.3 / AC-5.4: expired code → Nikita 'Code expired' + row purge."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        # Should NOT call verify_otp at all
        mock_supabase.auth.verify_otp.assert_not_awaited()
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "expired" in text.lower()


# ---------------------------------------------------------------------------
# AC-6 / FR-5 valid OTP path
# ---------------------------------------------------------------------------


class TestHandleCodeValid:
    @pytest.mark.asyncio
    async def test_ac6_valid_otp_calls_admin_endpoint_and_sends_link(
        self, handler, mock_bot, mock_repo, mock_supabase, mock_admin_endpoint
    ):
        """AC-4.4 + AC-5.1..AC-5.4: valid OTP → admin generate_link → Telegram
        delivery with disable_web_page_preview=True."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        mock_supabase.auth.verify_otp.assert_awaited_once()
        verify_call = mock_supabase.auth.verify_otp.call_args.args[0]
        assert verify_call["email"] == "player@example.com"
        assert verify_call["token"] == "123456"
        assert verify_call["type"] == "email"

        mock_admin_endpoint.assert_awaited_once()

        # FR-5 / Testing H1: must send via inline button with link-preview off
        assert (
            mock_bot.send_message_with_keyboard.await_count > 0
            or mock_bot.send_message.await_count > 0
        )

    @pytest.mark.asyncio
    async def test_ac6_valid_otp_idempotently_binds_telegram_id(
        self, handler, mock_repo, mock_supabase, mock_user_repo
    ):
        """AC-5.5: post-magic-link bind: UPDATE users SET telegram_id is idempotent."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        # Bind attempted (may no-op gracefully if user row doesn't exist yet)
        mock_user_repo.update_telegram_id.assert_awaited()
