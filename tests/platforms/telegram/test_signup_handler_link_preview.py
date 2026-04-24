"""Spec 215 PR-F1b T016 — Testing H1: Telegram link-preview disabled.

The Telegram link-preview crawler will GET the action_link to render an embed,
burning the single-use token before the user can tap. Bot MUST set
`disable_web_page_preview=True` on the `send_message`/keyboard call whenever
the message body contains the magic-link `action_link`.

Tests:
- AC-1: FR-5 magic-link send asserts disable_web_page_preview=True
- AC-2 (NEGATIVE control): FR-2 welcome reply does NOT force
  disable_web_page_preview (default off)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from nikita.platforms.telegram.signup_handler import SignupHandler


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
    supabase = MagicMock()
    supabase.auth.sign_in_with_otp = AsyncMock(return_value=MagicMock(status_code=200))
    verify_response = MagicMock()
    verify_response.user = MagicMock()
    verify_response.user.id = "550e8400-e29b-41d4-a716-446655440000"
    supabase.auth.verify_otp = AsyncMock(return_value=verify_response)
    return supabase


@pytest.fixture
def mock_admin_endpoint() -> AsyncMock:
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
# AC-1 — FR-5 path: disable_web_page_preview=True is mandatory
# ---------------------------------------------------------------------------


class TestMagicLinkLinkPreviewDisabled:
    @pytest.mark.asyncio
    async def test_fr5_magic_link_send_disables_web_page_preview(
        self, handler, mock_bot, mock_repo
    ):
        """AC-5.3 + Testing H1 + NFR-Sec-1: every magic-link Telegram message
        MUST set disable_web_page_preview=True so the link-preview crawler does
        not burn the single-use token."""
        existing = MagicMock()
        existing.signup_state = "code_sent"
        existing.email = "player@example.com"
        existing.attempts = 0
        existing.expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        mock_repo.get.return_value = existing

        await handler.handle_code(
            telegram_id=123, chat_id=456, text="123456"
        )

        # Either send_message or send_message_with_keyboard was called for the link;
        # whichever was used MUST have disable_web_page_preview=True
        link_send_calls = []
        for call in mock_bot.send_message.await_args_list:
            link_send_calls.append(("send_message", call))
        for call in mock_bot.send_message_with_keyboard.await_args_list:
            link_send_calls.append(("send_message_with_keyboard", call))

        assert link_send_calls, "Bot must send the magic-link message"

        # Find the call that contains the action_link
        link_call = None
        for kind, call in link_send_calls:
            kw = call.kwargs
            text = kw.get("text", "")
            keyboard = kw.get("keyboard", [])
            if "supabase.example.com" in text or any(
                "supabase.example.com" in (btn.get("url") or "")
                for row in keyboard
                for btn in row
            ):
                link_call = (kind, call)
                break
            # Heuristic: keyboards generally indicate the link CTA
            if kind == "send_message_with_keyboard":
                link_call = (kind, call)

        assert link_call is not None, "Magic-link message not found in bot calls"
        assert link_call[1].kwargs.get("disable_web_page_preview") is True, (
            f"FR-5 magic-link {link_call[0]} MUST pass "
            "disable_web_page_preview=True (Testing H1, NFR-Sec-1)"
        )


# ---------------------------------------------------------------------------
# AC-2 — NEGATIVE control: FR-2 welcome does NOT force disable_web_page_preview
# ---------------------------------------------------------------------------


class TestWelcomeDoesNotForceDisablePreview:
    @pytest.mark.asyncio
    async def test_fr2_welcome_does_not_force_disable_web_page_preview(
        self, handler, mock_bot
    ):
        """NEGATIVE control: the FR-2 welcome message does not contain a
        magic-link, so it should not force disable_web_page_preview=True.

        This guards against an over-eager rule like "always disable previews"
        that would mask the FR-5 path slipping through without the flag."""
        await handler.handle_welcome(telegram_id=123, chat_id=456)

        mock_bot.send_message.assert_awaited_once()
        kw = mock_bot.send_message.call_args.kwargs
        # NEGATIVE control: True is reserved for magic-link sends. Welcome
        # SHOULD NOT pass True. (False or absent are both acceptable.)
        assert kw.get("disable_web_page_preview") is not True, (
            "FR-2 welcome message must NOT force disable_web_page_preview=True"
            " (negative control for Testing H1)"
        )
