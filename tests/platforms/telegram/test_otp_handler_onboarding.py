"""Tests for OTP handler portal-first onboarding (Spec 081).

Tests verify the magic link generation and portal redirect flow
that replaces the voice/text onboarding choice after OTP verification.

AC Coverage: AC-1.1, AC-1.2, AC-1.3, AC-1.4 (Spec 081)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.platforms.telegram.otp_handler import OTPVerificationHandler


class TestGeneratePortalMagicLink:
    """Tests for _generate_portal_magic_link() method."""

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth with Supabase admin API."""
        auth = AsyncMock()
        # Mock the admin.get_user_by_id response
        mock_user_response = MagicMock()
        mock_user_response.user.email = "player@example.com"
        auth.supabase.auth.admin.get_user_by_id = AsyncMock(
            return_value=mock_user_response
        )
        # Mock the admin.generate_link response
        mock_link_response = MagicMock()
        mock_link_response.properties.action_link = (
            "https://supabase.co/auth/v1/verify?token=abc123&type=magiclink"
            "&redirect_to=https://portal.vercel.app/auth/callback?next=/onboarding"
        )
        auth.supabase.auth.admin.generate_link = AsyncMock(
            return_value=mock_link_response
        )
        return auth

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
    async def test_magic_link_success_returns_action_link(self, handler):
        """AC-1.2: Magic link generation returns action_link URL from Supabase."""
        result = await handler._generate_portal_magic_link(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            redirect_path="/onboarding",
        )
        assert result is not None
        assert "token=abc123" in result
        assert "redirect_to=" in result

    @pytest.mark.asyncio
    async def test_magic_link_calls_get_user_for_email(
        self, handler, mock_telegram_auth
    ):
        """AC-1.3: Looks up email via admin.get_user_by_id before generating link."""
        await handler._generate_portal_magic_link(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            redirect_path="/onboarding",
        )
        mock_telegram_auth.supabase.auth.admin.get_user_by_id.assert_awaited_once_with(
            "550e8400-e29b-41d4-a716-446655440000"
        )

    @pytest.mark.asyncio
    async def test_magic_link_calls_generate_link_with_magiclink_type(
        self, handler, mock_telegram_auth
    ):
        """AC-1.3: Calls admin.generate_link with type=magiclink and correct email."""
        await handler._generate_portal_magic_link(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            redirect_path="/onboarding",
        )
        mock_telegram_auth.supabase.auth.admin.generate_link.assert_awaited_once()
        call_args = (
            mock_telegram_auth.supabase.auth.admin.generate_link.call_args
        )
        link_params = call_args[0][0]  # First positional arg (dict)
        assert link_params["type"] == "magiclink"
        assert link_params["email"] == "player@example.com"
        assert "/onboarding" in link_params["options"]["redirect_to"]

    @pytest.mark.asyncio
    async def test_magic_link_returns_none_on_no_email(self, handler, mock_telegram_auth):
        """AC-1.4: Returns None gracefully when user has no email."""
        mock_user_response = MagicMock()
        mock_user_response.user.email = None
        mock_telegram_auth.supabase.auth.admin.get_user_by_id = AsyncMock(
            return_value=mock_user_response
        )
        result = await handler._generate_portal_magic_link(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            redirect_path="/onboarding",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_magic_link_returns_none_on_supabase_error(
        self, handler, mock_telegram_auth
    ):
        """AC-1.4: Returns None on Supabase API error (doesn't raise)."""
        mock_telegram_auth.supabase.auth.admin.get_user_by_id = AsyncMock(
            side_effect=Exception("Supabase unavailable")
        )
        result = await handler._generate_portal_magic_link(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            redirect_path="/onboarding",
        )
        assert result is None


class TestOfferOnboardingChoice:
    """Tests for the revised _offer_onboarding_choice() with portal redirect."""

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth."""
        auth = AsyncMock()
        mock_user_response = MagicMock()
        mock_user_response.user.email = "player@example.com"
        auth.supabase.auth.admin.get_user_by_id = AsyncMock(
            return_value=mock_user_response
        )
        mock_link_response = MagicMock()
        mock_link_response.properties.action_link = "https://supabase.co/auth/v1/verify?token=xyz"
        auth.supabase.auth.admin.generate_link = AsyncMock(
            return_value=mock_link_response
        )
        return auth

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_telegram_auth, mock_bot):
        """Create handler."""
        return OTPVerificationHandler(
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_sends_single_url_button_with_magic_link(self, handler, mock_bot):
        """AC-1.1: After OTP, sends single URL button 'Enter Nikita's World' with magic link."""
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        mock_bot.send_message_with_keyboard.assert_awaited_once()
        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get("keyboard")
        # Should be a single button row with URL (not callback_data)
        assert len(keyboard) == 1, "Should have exactly 1 button row"
        assert len(keyboard[0]) == 1, "Should have exactly 1 button"
        button = keyboard[0][0]
        assert "url" in button, "Button should be a URL button"
        assert "callback_data" not in button, "Should NOT have callback_data"
        assert "Enter" in button["text"] or "Nikita" in button["text"]

    @pytest.mark.asyncio
    async def test_falls_back_to_login_url_when_magic_link_fails(
        self, handler, mock_bot, mock_telegram_auth
    ):
        """AC-1.4: Falls back to portal_url/login?next=/onboarding when magic link returns None."""
        # Make magic link generation fail
        mock_telegram_auth.supabase.auth.admin.get_user_by_id = AsyncMock(
            side_effect=Exception("Supabase down")
        )
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get("keyboard")
        button = keyboard[0][0]
        assert "login" in button["url"], f"Fallback URL should contain 'login', got: {button['url']}"

    @pytest.mark.asyncio
    async def test_message_text_matches_spec_copy(self, handler, mock_bot):
        """AC-1.1: Message text includes spec copy about entering Nikita's world."""
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert "You're in" in text, f"Should contain 'You're in', got: {text[:100]}"

    @pytest.mark.asyncio
    async def test_no_voice_or_text_buttons(self, handler, mock_bot):
        """AC-1.1: Voice call and text chat buttons are removed."""
        with patch(
            "nikita.platforms.telegram.otp_handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            await handler._offer_onboarding_choice(
                chat_id=12345,
                user_id="550e8400-e29b-41d4-a716-446655440000",
                telegram_id=67890,
            )

        call_kwargs = mock_bot.send_message_with_keyboard.call_args
        keyboard = call_kwargs.kwargs.get("keyboard") or call_kwargs[1].get("keyboard")
        all_buttons = [btn for row in keyboard for btn in row]
        for btn in all_buttons:
            text = btn.get("text", "")
            assert "Voice" not in text, "Voice button should be removed"
            assert "Text Chat" not in text, "Text Chat button should be removed"
            assert "callback_data" not in btn, "No callback buttons should exist"
