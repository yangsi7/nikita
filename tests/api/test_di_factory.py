"""Tests for build_message_handler factory function.

Verifies that:
- build_message_handler constructs a fully-initialized MessageHandler
- All repositories are non-None after construction
- Services (rate_limiter, response_delivery, text_agent_handler) are non-None
- The bot argument is wired through correctly
- get_message_handler delegates to build_message_handler

AC Coverage: AC-1 through AC-4 (build_message_handler factory extraction).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.message_handler import MessageHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> AsyncMock:
    """Return an AsyncMock that satisfies AsyncSession's interface."""
    return AsyncMock(spec=AsyncSession)


def _make_bot() -> MagicMock:
    """Return a MagicMock that satisfies TelegramBot's interface."""
    return MagicMock(spec=TelegramBot)


# ---------------------------------------------------------------------------
# Test: build_message_handler
# ---------------------------------------------------------------------------


class TestBuildMessageHandler:
    """Unit tests for the build_message_handler factory."""

    @pytest.mark.asyncio
    async def test_build_message_handler_returns_handler(self):
        """AC-1: build_message_handler returns a MessageHandler instance."""
        from nikita.api.routes.telegram import build_message_handler

        session = _make_session()
        bot = _make_bot()

        handler = await build_message_handler(session=session, bot=bot)

        assert isinstance(handler, MessageHandler)

    @pytest.mark.asyncio
    async def test_build_message_handler_all_repos_initialized(self):
        """AC-2: All 5 repositories are constructed and non-None."""
        from nikita.api.routes.telegram import build_message_handler

        session = _make_session()
        bot = _make_bot()

        handler = await build_message_handler(session=session, bot=bot)

        # MessageHandler stores repos under these attribute names (see __init__)
        assert handler.user_repository is not None
        assert handler.conversation_repo is not None
        assert handler.profile_repo is not None
        assert handler.backstory_repo is not None
        assert handler.metrics_repo is not None

    @pytest.mark.asyncio
    async def test_build_message_handler_services_initialized(self):
        """AC-3: rate_limiter, response_delivery, and text_agent_handler are non-None."""
        from nikita.api.routes.telegram import build_message_handler

        session = _make_session()
        bot = _make_bot()

        handler = await build_message_handler(session=session, bot=bot)

        assert handler.rate_limiter is not None
        assert handler.response_delivery is not None
        assert handler.text_agent_handler is not None

    @pytest.mark.asyncio
    async def test_build_message_handler_bot_passed(self):
        """AC-4: The bot argument is wired into the handler."""
        from nikita.api.routes.telegram import build_message_handler

        session = _make_session()
        bot = _make_bot()

        handler = await build_message_handler(session=session, bot=bot)

        assert handler.bot is bot

    @pytest.mark.asyncio
    async def test_get_message_handler_uses_factory(self):
        """get_message_handler delegates construction to build_message_handler."""
        from nikita.api.routes.telegram import get_message_handler

        session = _make_session()
        bot = _make_bot()
        sentinel = MagicMock(spec=MessageHandler)

        with patch(
            "nikita.api.routes.telegram.build_message_handler",
            new=AsyncMock(return_value=sentinel),
        ) as mock_factory:
            result = await get_message_handler(bot=bot, session=session)

        mock_factory.assert_awaited_once_with(session=session, bot=bot)
        assert result is sentinel
