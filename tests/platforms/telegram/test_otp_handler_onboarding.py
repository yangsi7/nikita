"""Tests for OTP handler portal-first onboarding (Spec 081 + GH #187).

Tests verify the bridge URL generation and portal redirect flow
that replaces the broken magic link approach (PKCE mismatch fix).

AC Coverage: AC-1.1, AC-1.2, AC-1.3, AC-1.4 (Spec 081)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.platforms.telegram.otp_handler import OTPVerificationHandler


class TestGeneratePortalBridgeUrl:
    """Tests for _generate_portal_bridge_url() method (GH #187).

    Replaces TestGeneratePortalMagicLink — the old magic link approach
    failed due to PKCE code_verifier mismatch.
    """

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth."""
        return AsyncMock()

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_telegram_auth, mock_bot):
        """Create handler with mocked deps."""
        return OTPVerificationHandler(
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_bridge_url_success_returns_portal_url(self, handler):
        """Returns portal bridge URL with token parameter."""
        mock_bridge = MagicMock()
        mock_bridge.token = "test-bridge-token-abc123"

        mock_repo = AsyncMock()
        mock_repo.create_token.return_value = mock_bridge

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        with (
            patch(
                "nikita.platforms.telegram.otp_handler.get_settings"
            ) as mock_settings,
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.auth_bridge_repository.AuthBridgeRepository",
                return_value=mock_repo,
            ),
        ):
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            result = await handler._generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
                redirect_path="/onboarding",
            )

        assert result is not None
        assert "portal.vercel.app/auth/bridge" in result
        assert "token=test-bridge-token-abc123" in result

    @pytest.mark.asyncio
    async def test_bridge_url_returns_none_on_error(self, handler):
        """Returns None on any failure (doesn't raise)."""
        with (
            patch("nikita.platforms.telegram.otp_handler.get_settings") as mock_settings,
            patch(
                "nikita.db.database.get_session_maker",
                side_effect=Exception("DB unavailable"),
            ),
        ):
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            result = await handler._generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
                redirect_path="/onboarding",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_bridge_url_uses_default_portal_url(self, handler):
        """Uses default portal URL when settings.portal_url is None."""
        mock_bridge = MagicMock()
        mock_bridge.token = "tok789"

        mock_repo = AsyncMock()
        mock_repo.create_token.return_value = mock_bridge

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.platforms.telegram.otp_handler.get_settings") as mock_settings,
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.auth_bridge_repository.AuthBridgeRepository",
                return_value=mock_repo,
            ),
        ):
            mock_settings.return_value.portal_url = None
            result = await handler._generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
            )

        assert result is not None
        assert "portal-phi-orcin.vercel.app" in result


class TestOfferOnboardingChoice:
    """Tests for the revised _offer_onboarding_choice() with portal redirect."""

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth."""
        return AsyncMock()

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_telegram_auth, mock_bot):
        """Create handler."""
        return OTPVerificationHandler(
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_sends_single_url_button_with_bridge_url(
        self, handler, mock_bot
    ):
        """AC-1.1: After OTP, sends single URL button 'Enter Nikita's World' with bridge URL."""
        handler._generate_portal_bridge_url = AsyncMock(
            return_value="https://portal.vercel.app/auth/bridge?token=abc123"
        )
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        mock_bot.send_message_with_keyboard.assert_awaited_once()
        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get(
            "keyboard"
        )
        assert len(keyboard) == 1, "Should have exactly 1 button row"
        assert len(keyboard[0]) == 1, "Should have exactly 1 button"
        button = keyboard[0][0]
        assert "url" in button, "Button should be a URL button"
        assert "callback_data" not in button, "Should NOT have callback_data"
        assert "Enter" in button["text"] or "Nikita" in button["text"]
        assert "auth/bridge" in button["url"]

    @pytest.mark.asyncio
    async def test_falls_back_to_login_url_when_bridge_fails(
        self, handler, mock_bot
    ):
        """AC-1.4: Falls back to portal_url/login?next=/onboarding when bridge URL returns None."""
        handler._generate_portal_bridge_url = AsyncMock(return_value=None)
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get(
            "keyboard"
        )
        button = keyboard[0][0]
        assert "login" in button["url"], (
            f"Fallback URL should contain 'login', got: {button['url']}"
        )

    @pytest.mark.asyncio
    async def test_message_text_matches_spec_copy(self, handler, mock_bot):
        """AC-1.1: Message text includes spec copy about entering Nikita's world."""
        handler._generate_portal_bridge_url = AsyncMock(
            return_value="https://portal.vercel.app/auth/bridge?token=xyz"
        )
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert "You're in" in text, (
            f"Should contain 'You're in', got: {text[:100]}"
        )

    @pytest.mark.asyncio
    async def test_no_voice_or_text_buttons(self, handler, mock_bot):
        """AC-1.1: Voice call and text chat buttons are removed."""
        handler._generate_portal_bridge_url = AsyncMock(
            return_value="https://portal.vercel.app/auth/bridge?token=xyz"
        )
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = (
                "https://portal.vercel.app"
            )
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get(
            "keyboard"
        )
        all_buttons = [btn for row in keyboard for btn in row]
        for btn in all_buttons:
            text = btn.get("text", "")
            assert "Voice" not in text, "Voice button should be removed"
            assert "Text Chat" not in text, "Text Chat button should be removed"
            assert "callback_data" not in btn, "No callback buttons should exist"
