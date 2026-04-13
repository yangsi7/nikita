"""Tests for telegram utils — extracted shared helpers (GH #233).

`generate_portal_bridge_url` was previously duplicated across otp_handler.py
and message_handler.py. After extraction it lives in
`nikita.platforms.telegram.utils` as a module-public free function.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGeneratePortalBridgeUrl:
    """Direct tests for the extracted free function (GH #233)."""

    @pytest.mark.asyncio
    async def test_returns_bridge_url_with_token_on_success(self):
        """Returns portal bridge URL with token query param for a valid user."""
        from nikita.platforms.telegram.utils import generate_portal_bridge_url

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
                "nikita.platforms.telegram.utils.get_settings"
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
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            result = await generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
                redirect_path="/onboarding",
            )

        assert result is not None
        assert "portal.vercel.app/auth/bridge" in result
        assert "token=test-bridge-token-abc123" in result

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        """Catches all exceptions and returns None (caller handles fallback)."""
        from nikita.platforms.telegram.utils import generate_portal_bridge_url

        with (
            patch(
                "nikita.platforms.telegram.utils.get_settings"
            ) as mock_settings,
            patch(
                "nikita.db.database.get_session_maker",
                side_effect=Exception("DB unavailable"),
            ),
        ):
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            result = await generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
                redirect_path="/onboarding",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_default_portal_url_when_setting_is_none(self):
        """Falls back to the hardcoded default portal URL when setting unset."""
        from nikita.platforms.telegram.utils import generate_portal_bridge_url

        mock_bridge = MagicMock()
        mock_bridge.token = "fallback-token"

        mock_repo = AsyncMock()
        mock_repo.create_token.return_value = mock_bridge

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        with (
            patch(
                "nikita.platforms.telegram.utils.get_settings"
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
            mock_settings.return_value.portal_url = None
            result = await generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
            )

        assert result is not None
        assert "portal-phi-orcin.vercel.app" in result

    @pytest.mark.asyncio
    async def test_default_redirect_path_is_onboarding(self):
        """Default redirect_path is /onboarding — preserves prior signature."""
        from nikita.platforms.telegram.utils import generate_portal_bridge_url

        mock_bridge = MagicMock()
        mock_bridge.token = "default-redirect-token"

        mock_repo = AsyncMock()
        mock_repo.create_token.return_value = mock_bridge

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        with (
            patch(
                "nikita.platforms.telegram.utils.get_settings"
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
            mock_settings.return_value.portal_url = "https://portal.vercel.app"
            # Call without explicit redirect_path — asserts default arg present.
            await generate_portal_bridge_url(
                user_id="550e8400-e29b-41d4-a716-446655440000",
            )

        from uuid import UUID
        mock_repo.create_token.assert_awaited_once_with(
            UUID("550e8400-e29b-41d4-a716-446655440000"), "/onboarding"
        )
