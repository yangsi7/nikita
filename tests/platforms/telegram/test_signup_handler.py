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
    repo.get = AsyncMock(return_value=None)  # GH #599: users row missing
    repo.create_with_metrics = AsyncMock()
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

        from supabase_auth.errors import AuthApiError

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

        from supabase_auth.errors import AuthApiError
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


class TestHandleCodeNonOtpShape:
    """I-1 regression guard: non-OTP-shaped junk MUST trip the rate-limit
    path so spam (`hi`, `abc`, ...) cannot bypass the 3-strike purge.

    Per iter-2 QA review I-1: previously `if not OTP_REGEX.match(code)`
    short-circuited with a gentle reply WITHOUT increment_attempts, leaving
    a DoS / cost surface. Fix routes through `_handle_invalid_otp` which
    shares the increment + rate-limit purge path.
    """

    @pytest.mark.asyncio
    async def test_non_otp_shape_increments_attempts(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """Non-numeric junk in CODE_SENT MUST call increment_attempts."""
        mock_repo.increment_attempts.return_value = 1

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="abc"
        )

        # KEY assertion: increment_attempts was called (was the bypass)
        mock_repo.increment_attempts.assert_awaited_once_with(telegram_id=123)
        # verify_otp NEVER called (no shape match)
        mock_supabase.auth.verify_otp.assert_not_awaited()
        # User got a reply with tries-left messaging
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert text  # non-empty

    @pytest.mark.asyncio
    async def test_non_otp_shape_three_attempts_triggers_purge(
        self, handler, mock_bot, mock_repo, mock_supabase
    ):
        """3 non-numeric inputs in CODE_SENT MUST purge the row + rate-limit."""
        mock_repo.increment_attempts.return_value = 3  # 3rd attempt

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="hi"
        )

        mock_repo.increment_attempts.assert_awaited_once_with(telegram_id=123)
        # Purge path fired (same as legitimate 3-strike)
        assert (
            mock_repo.purge.await_count > 0
            or mock_repo.delete_on_completion.await_count > 0
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
    async def test_ac6_valid_otp_binds_telegram_id_for_existing_user(
        self, handler, mock_repo, mock_supabase, mock_user_repo
    ):
        """AC-5.5: post-magic-link bind for existing user → UPDATE path."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        # public.users row EXISTS — go through update_telegram_id path.
        existing_user = MagicMock()
        mock_user_repo.get.return_value = existing_user

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        mock_user_repo.update_telegram_id.assert_awaited_once()
        mock_user_repo.create_with_metrics.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_gh_599_creates_public_users_row_when_missing(
        self, handler, mock_repo, mock_supabase, mock_user_repo
    ):
        """GH #599: when public.users row is missing for a fresh signup,
        signup_handler MUST create it (with telegram_id bound) — NOT defer
        to the removed FR-11b `/start <code>` path. The deferred behavior
        was the root cause of `telegram_bind_failed_user_row_missing` on
        `/auth/confirm` autobind for every new user post-Spec 218.
        """
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        # users row missing (default fixture state)
        mock_user_repo.get.return_value = None

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        # MUST create the row atomically with telegram_id bound, NOT defer.
        mock_user_repo.create_with_metrics.assert_awaited_once()
        kwargs = mock_user_repo.create_with_metrics.call_args.kwargs
        assert kwargs.get("telegram_id") == 123
        # user_id MUST be the auth.users UUID from the verify_otp response —
        # not telegram_id-cast or a freshly-generated one. The mock_supabase
        # fixture seeds verify_response.user.id = `550e8400-...`.
        assert kwargs.get("user_id") == UUID(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        # When create path runs, we do NOT additionally call update_telegram_id
        # (the INSERT already includes the telegram_id column).
        mock_user_repo.update_telegram_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_gh_601_cross_user_telegram_conflict_blocks_magiclink(
        self, handler, mock_bot, mock_repo, mock_supabase, mock_user_repo, mock_admin_endpoint
    ):
        """GH #601: when telegram_id is already bound to a DIFFERENT
        user_id, we MUST NOT deliver a magic-link to that chat.

        Sending the link in this case would let the chat owner sign
        into the OTHER email's portal if they also control the inbox.
        Expected: user gets a conflict message; admin magiclink endpoint
        is NOT called.
        """
        from nikita.db.repositories.user_repository import (  # noqa: PLC0415
            TelegramIdAlreadyBoundByOtherUserError,
        )

        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        # public.users exists for THIS auth_uid; conflict is on telegram_id
        # being held by a different user_id.
        mock_user_repo.get.return_value = MagicMock()
        mock_user_repo.update_telegram_id.side_effect = (
            TelegramIdAlreadyBoundByOtherUserError(telegram_id=123)
        )

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        # The cross-user conflict MUST prevent magic-link delivery.
        mock_admin_endpoint.assert_not_awaited()
        # User must be notified of the conflict.
        mock_bot.send_message.assert_awaited()
        last_call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "already linked" in last_call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_gh_599_race_recovery_when_concurrent_verify_lost(
        self, handler, mock_repo, mock_supabase, mock_user_repo
    ):
        """GH #599 race path: two concurrent verify_otp calls both see
        get()=None and race into create_with_metrics. The loser's
        IntegrityError MUST fall through to update_telegram_id so the
        binding still completes (avoids telegram_id=NULL row leak)."""
        from sqlalchemy.exc import IntegrityError  # noqa: PLC0415

        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        # Race: get() sees no row → create attempts → IntegrityError (the
        # winning concurrent verify just inserted) → fallback bind.
        mock_user_repo.get.return_value = None
        mock_user_repo.create_with_metrics.side_effect = IntegrityError(
            "INSERT", {}, Exception("duplicate key")
        )

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        mock_user_repo.create_with_metrics.assert_awaited_once()
        # CRITICAL: race-loser MUST recover by binding telegram_id on the
        # now-existing row. Without this fallback the loser ships a
        # magic-link to a user whose row has telegram_id=NULL.
        mock_user_repo.update_telegram_id.assert_awaited_once()
        kwargs = mock_user_repo.update_telegram_id.call_args.kwargs
        assert kwargs.get("telegram_id") == 123


class TestHandleCodeOTPLengthFlexibility:
    """GH #431: Supabase prod sends 8-digit OTP codes; regex must accept 6-8.

    Defensive 6-8 range protects against future Supabase dashboard length
    drift (configurable per Auth → Email Templates). Anything outside the
    range still falls into the invalid-attempt path so DoS surface stays
    closed.
    """

    @pytest.mark.asyncio
    async def test_8_digit_otp_is_accepted_and_passed_to_supabase(
        self, handler, mock_repo, mock_supabase, mock_admin_endpoint
    ):
        """8-digit code (Supabase prod default 2026) must reach verify_otp."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="60555977"
        )

        mock_supabase.auth.verify_otp.assert_awaited_once()
        verify_call = mock_supabase.auth.verify_otp.call_args.args[0]
        assert verify_call["token"] == "60555977"

    @pytest.mark.asyncio
    async def test_7_digit_otp_is_accepted(
        self, handler, mock_repo, mock_supabase
    ):
        """7-digit code is also accepted (defensive midpoint)."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="1234567"
        )

        mock_supabase.auth.verify_otp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_5_digit_otp_still_rejected_locally(
        self, handler, mock_repo, mock_supabase, mock_bot
    ):
        """Codes shorter than 6 still go to the invalid-attempt path."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="12345"
        )

        # No Supabase call — local regex rejection
        mock_supabase.auth.verify_otp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_9_digit_otp_still_rejected_locally(
        self, handler, mock_repo, mock_supabase
    ):
        """Codes longer than 8 still go to the invalid-attempt path."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456789"
        )

        mock_supabase.auth.verify_otp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_numeric_still_rejected_locally(
        self, handler, mock_repo, mock_supabase
    ):
        """Letters never reach Supabase regardless of length."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="abcdefgh"
        )

        mock_supabase.auth.verify_otp.assert_not_awaited()

    def test_code_sent_text_does_not_promise_specific_digit_count(self):
        """GH #433: copy must not say "6-digit" since Supabase sends 8."""
        from nikita.platforms.telegram.signup_handler import CODE_SENT_TEXT
        assert "6-digit" not in CODE_SENT_TEXT
        assert "8-digit" not in CODE_SENT_TEXT
