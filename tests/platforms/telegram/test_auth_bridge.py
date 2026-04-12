"""Tests for shared portal bridge URL utility.

GH #233: Extracted from duplicated code in message_handler.py and otp_handler.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_generate_portal_bridge_url_returns_none_on_error():
    """generate_portal_bridge_url returns None when an exception occurs."""
    with patch(
        "nikita.platforms.telegram.auth_bridge.get_settings",
        side_effect=Exception("Settings unavailable"),
    ):
        from nikita.platforms.telegram.auth_bridge import (
            generate_portal_bridge_url,
        )

        url = await generate_portal_bridge_url(str(uuid4()))

    assert url is None


@pytest.mark.asyncio
async def test_generate_portal_bridge_url_default_redirect():
    """Default redirect_path is '/onboarding'."""
    from nikita.platforms.telegram.auth_bridge import generate_portal_bridge_url
    import inspect

    sig = inspect.signature(generate_portal_bridge_url)
    assert sig.parameters["redirect_path"].default == "/onboarding"


@pytest.mark.asyncio
async def test_message_handler_delegates_to_shared_utility():
    """message_handler._generate_portal_bridge_url delegates to shared utility."""
    from nikita.platforms.telegram.message_handler import MessageHandler

    handler = MessageHandler.__new__(MessageHandler)

    with patch(
        "nikita.platforms.telegram.auth_bridge.generate_portal_bridge_url",
        new_callable=AsyncMock,
        return_value="https://portal.test/auth/bridge?token=abc",
    ) as mock_fn:
        result = await handler._generate_portal_bridge_url("user-123", "/test")

    mock_fn.assert_awaited_once_with("user-123", "/test")
    assert result == "https://portal.test/auth/bridge?token=abc"


@pytest.mark.asyncio
async def test_otp_handler_delegates_to_shared_utility():
    """otp_handler._generate_portal_bridge_url delegates to shared utility."""
    from nikita.platforms.telegram.otp_handler import OTPVerificationHandler

    handler = OTPVerificationHandler.__new__(OTPVerificationHandler)

    with patch(
        "nikita.platforms.telegram.auth_bridge.generate_portal_bridge_url",
        new_callable=AsyncMock,
        return_value="https://portal.test/auth/bridge?token=xyz",
    ) as mock_fn:
        result = await handler._generate_portal_bridge_url("user-456")

    mock_fn.assert_awaited_once_with("user-456", "/onboarding")
    assert result == "https://portal.test/auth/bridge?token=xyz"
