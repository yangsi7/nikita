"""Tests for FR-11c pre-onboard gate in MessageHandler (Spec 214 T1.5).

Covers AC-11c.7 (E9 free text pre-onboard → bridge nudge; pipeline
`process_message` NOT called) and AC-11c.8 (E10 email-shaped text
pre-onboard → in-character "no email here" nudge + bridge; no OTP).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.models.user import User
from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramMessage


def _build_message(
    telegram_id: int = 123456789,
    text: str = "hi",
) -> TelegramMessage:
    """Build a TelegramMessage fixture."""
    # TelegramMessage is a pydantic model; build via dict.
    return TelegramMessage.model_validate(
        {
            "message_id": 42,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": telegram_id, "type": "private"},
            "text": text,
            "date": 1_700_000_000,
        }
    )


def _user(
    *,
    onboarding_status: str = "completed",
    telegram_id: int = 123456789,
    game_status: str = "active",
) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.telegram_id = telegram_id
    u.chapter = 1
    u.relationship_score = Decimal("50")
    u.onboarding_status = onboarding_status
    u.game_status = game_status
    u.pending_handoff = False
    return u


@pytest.fixture
def mock_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_message_with_keyboard = AsyncMock()
    bot.send_chat_action = AsyncMock()
    return bot


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    repo = AsyncMock()
    # Force the non-locking fallback path to avoid lock acquire noise.
    repo.get_by_telegram_id_for_update.side_effect = Exception("no lock in tests")
    return repo


@pytest.fixture
def handler(mock_user_repo: AsyncMock, mock_bot: AsyncMock) -> MessageHandler:
    """MessageHandler with the bare minimum dependencies."""
    text_agent = AsyncMock()
    delivery = AsyncMock()
    convo_repo = AsyncMock()
    convo_repo.session = AsyncMock()

    profile_repo = AsyncMock()
    backstory_repo = AsyncMock()

    return MessageHandler(
        user_repository=mock_user_repo,
        conversation_repository=convo_repo,
        text_agent_handler=text_agent,
        response_delivery=delivery,
        bot=mock_bot,
        profile_repository=profile_repo,
        backstory_repository=backstory_repo,
    )


class TestFreeTextPreOnboard:
    """AC-T1.5.1 / AC-11c.7: free text pre-onboard → nudge + short-circuit."""

    @pytest.mark.asyncio
    async def test_pre_onboard_free_text_sends_nudge_and_skips_pipeline(
        self,
        handler: MessageHandler,
        mock_user_repo: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="pending")
        mock_user_repo.get_by_telegram_id.return_value = user

        with patch(
            "nikita.platforms.telegram.message_handler.generate_portal_bridge_url",
            new=AsyncMock(
                return_value="https://p.example/onboarding/auth?bridge=xx"
            ),
        ) as mock_gen:
            await handler.handle(_build_message(text="hey what's up"))

        # Bridge nudge fired with reason='resume'
        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["reason"] == "resume"

        # A keyboard button was sent (bridge nudge)
        mock_bot.send_message_with_keyboard.assert_awaited_once()

        # Pipeline not invoked: no typing indicator, no agent call.
        handler.text_agent_handler.process_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_profile_free_text_sends_nudge(
        self,
        handler: MessageHandler,
        mock_user_repo: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        """Limbo (status=completed but profile=None) also short-circuits."""
        user = _user(onboarding_status="completed")
        mock_user_repo.get_by_telegram_id.return_value = user
        handler.profile_repo.get_by_user_id.return_value = None

        with patch(
            "nikita.platforms.telegram.message_handler.generate_portal_bridge_url",
            new=AsyncMock(
                return_value="https://p.example/onboarding/auth?bridge=yy"
            ),
        ):
            await handler.handle(_build_message(text="anyone there"))

        mock_bot.send_message_with_keyboard.assert_awaited_once()
        handler.text_agent_handler.process_message.assert_not_called()


class TestEmailTextPreOnboard:
    """AC-T1.5.2 / AC-11c.8: email-shaped text → 'no email here' nudge."""

    @pytest.mark.asyncio
    async def test_email_shaped_text_sends_no_email_here_nudge(
        self,
        handler: MessageHandler,
        mock_user_repo: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="pending")
        mock_user_repo.get_by_telegram_id.return_value = user

        with patch(
            "nikita.platforms.telegram.message_handler.generate_portal_bridge_url",
            new=AsyncMock(
                return_value="https://p.example/onboarding/auth?bridge=zz"
            ),
        ):
            await handler.handle(
                _build_message(text="alex@example.com")
            )

        # Email-specific copy (distinct from generic free-text nudge)
        mock_bot.send_message_with_keyboard.assert_awaited_once()
        call_kwargs = mock_bot.send_message_with_keyboard.call_args.kwargs
        text = call_kwargs["text"].lower()
        # Must signal "email is in the wrong place" in-character.
        assert "email" in text or "inbox" in text or "door" in text

        # No OTP flow kicked off.
        # There's no direct `telegram_auth` on MessageHandler; assert the
        # pipeline is not invoked.
        handler.text_agent_handler.process_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_pre_onboard_bypasses_normal_pipeline(
        self,
        handler: MessageHandler,
        mock_user_repo: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="pending")
        mock_user_repo.get_by_telegram_id.return_value = user

        with patch(
            "nikita.platforms.telegram.message_handler.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth?bridge=ab"),
        ):
            await handler.handle(
                _build_message(text="nikita.fan@gmail.com")
            )

        handler.text_agent_handler.process_message.assert_not_called()


class TestCompletedUserUnaffected:
    """Pre-onboard gate MUST NOT fire for fully-onboarded users."""

    @pytest.mark.asyncio
    async def test_onboarded_user_free_text_does_not_send_bridge(
        self,
        handler: MessageHandler,
        mock_user_repo: AsyncMock,
        mock_bot: AsyncMock,
    ) -> None:
        user = _user(onboarding_status="completed")
        mock_user_repo.get_by_telegram_id.return_value = user
        handler.profile_repo.get_by_user_id.return_value = MagicMock()

        with patch(
            "nikita.platforms.telegram.message_handler.generate_portal_bridge_url",
            new=AsyncMock(),
        ) as mock_gen:
            # Don't fully drive the rest of the pipeline; just assert the
            # gate doesn't fire. We do this by inspecting send_message_with_keyboard
            # absence after a failed downstream (expected; pipeline has heavy deps).
            try:
                await handler.handle(_build_message(text="hi there"))
            except Exception:
                # Downstream pipeline may fail under mocked deps; gate
                # behavior is what we test.
                pass

        # The bridge generator must NOT have been called at all.
        mock_gen.assert_not_awaited()
