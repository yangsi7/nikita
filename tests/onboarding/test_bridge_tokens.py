"""Tests for `nikita.onboarding.bridge_tokens` (Spec 214 FR-11c T1.2).

The new `generate_portal_bridge_url` helper lives in `nikita/onboarding/`
and is DISTINCT from the legacy `generate_portal_bridge_url` in
`nikita/platforms/telegram/utils.py`. The two MUST stay separate:
- legacy (utils.py): post-OTP zero-click bridge via auth_bridge_tokens
  (5-min TTL, route /auth/bridge?token=), used by /onboard.
- new (onboarding.bridge_tokens): FR-11c Telegram→portal routing via
  portal_bridge_tokens (24h/1h TTL, route /onboarding/auth?bridge=).

Callers import by fully qualified module path so grep-reviews can
disambiguate.
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.bridge_tokens import generate_portal_bridge_url


class TestBareUrl:
    """AC-T1.2.1 / AC-11c.12: E1 new-user URL has no query params."""

    @pytest.mark.asyncio
    async def test_bare_url_for_none_user_id(self) -> None:
        """user_id=None → exact match `{portal_url}/onboarding/auth`."""
        with patch(
            "nikita.onboarding.bridge_tokens.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://portal.example.com"
            url = await generate_portal_bridge_url(user_id=None, reason=None)

        assert url == "https://portal.example.com/onboarding/auth"
        # AC-11c.12: exact regex match, zero query params / path segments
        assert re.fullmatch(
            r"^https://portal\.example\.com/onboarding/auth$", url
        )

    @pytest.mark.asyncio
    async def test_bare_url_uses_settings_portal_url(self) -> None:
        """Different portal_url → different URL."""
        with patch(
            "nikita.onboarding.bridge_tokens.get_settings"
        ) as mock_settings:
            mock_settings.return_value.portal_url = "https://nikita-mygirl.com"
            url = await generate_portal_bridge_url(user_id=None, reason=None)

        assert url == "https://nikita-mygirl.com/onboarding/auth"


class TestTokenUrl:
    """AC-T1.2.2: with user_id+reason, mint + ?bridge= URL."""

    @pytest.mark.asyncio
    async def test_url_with_user_id_mints_and_returns_bridge_param(
        self,
    ) -> None:
        """user_id + reason → mints token, returns ?bridge=<token>."""
        user_id = str(uuid4())

        mock_repo = AsyncMock()
        mock_repo.mint.return_value = "fake-token-abc123"

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session

        with (
            patch(
                "nikita.onboarding.bridge_tokens.get_settings"
            ) as mock_settings,
            patch(
                "nikita.onboarding.bridge_tokens.get_session_maker"
            ) as mock_sm,
            patch(
                "nikita.onboarding.bridge_tokens.PortalBridgeTokenRepository",
                return_value=mock_repo,
            ),
        ):
            mock_settings.return_value.portal_url = "https://portal.example.com"
            mock_sm.return_value = lambda: mock_session_ctx

            url = await generate_portal_bridge_url(
                user_id=user_id, reason="resume"
            )

        assert url == (
            "https://portal.example.com/onboarding/auth?bridge=fake-token-abc123"
        )
        mock_repo.mint.assert_awaited_once()
        # User-id arg is a UUID instance, reason passed through
        call_args = mock_repo.mint.call_args
        passed_uid, passed_reason = call_args.args
        assert str(passed_uid) == user_id
        assert passed_reason == "resume"
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_url_for_re_onboard_reason(self) -> None:
        user_id = str(uuid4())
        mock_repo = AsyncMock()
        mock_repo.mint.return_value = "tkn"

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session

        with (
            patch(
                "nikita.onboarding.bridge_tokens.get_settings"
            ) as mock_settings,
            patch(
                "nikita.onboarding.bridge_tokens.get_session_maker"
            ) as mock_sm,
            patch(
                "nikita.onboarding.bridge_tokens.PortalBridgeTokenRepository",
                return_value=mock_repo,
            ),
        ):
            mock_settings.return_value.portal_url = "https://p.example.com"
            mock_sm.return_value = lambda: mock_session_ctx

            url = await generate_portal_bridge_url(
                user_id=user_id, reason="re-onboard"
            )

        assert url.endswith("?bridge=tkn")
        _, passed_reason = mock_repo.mint.call_args.args
        assert passed_reason == "re-onboard"

    @pytest.mark.asyncio
    async def test_user_id_without_reason_raises(self) -> None:
        """user_id provided but reason=None is invalid (defensive)."""
        with pytest.raises(ValueError):
            await generate_portal_bridge_url(user_id=str(uuid4()), reason=None)

    @pytest.mark.asyncio
    async def test_reason_without_user_id_raises(self) -> None:
        """reason provided but user_id=None is invalid (defensive)."""
        with pytest.raises(ValueError):
            await generate_portal_bridge_url(user_id=None, reason="resume")
