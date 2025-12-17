"""
Mock Agent Helper for E2E Tests

Provides mock responses for the text agent to avoid real Anthropic API calls
during E2E testing. This saves API costs and makes tests deterministic.

Usage in tests:
    with MockAgentHelper.patch_generate_response("Hello!"):
        response = await simulator.send_message("Hi", telegram_id)
        # Agent will return "Hello!" instead of calling LLM

For CI/CD, always use mocked responses.
For manual testing, can use real agent (costs API credits).
"""

import os
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch


@dataclass
class MockAgentResponse:
    """Mock response configuration."""
    response: str
    delay_seconds: float = 0.0
    should_respond: bool = True
    skip_reason: Optional[str] = None


class MockAgentHelper:
    """Helper for mocking the text agent in E2E tests.

    Patches nikita.agents.text.handler.generate_response to return
    predetermined responses without calling the Anthropic API.
    """

    # Standard mock responses for different scenarios
    RESPONSES = {
        "greeting": "Hey babe! I was just thinking about you. What's up? 💕",
        "default": "I'm here for you, always. What's going on?",
        "game_over": "Our story has ended. The game is over.",
        "rate_limit": "Whoa slow down, give me a sec to breathe! 😅",
        "error": "I'm having a moment... let me gather my thoughts.",
        "welcome": "Perfect! You're all set up. I'm so excited to get to know you! 💕",
        "otp_invalid": "Hmm, that doesn't look right. Try the 6-digit code again?",
        "otp_expired": "That code has expired. Let's try again - I'll send you a new one!",
        "not_registered": "You need to register first. Send /start to begin.",
    }

    @classmethod
    @contextmanager
    def patch_generate_response(
        cls,
        response_text: Optional[str] = None,
        delay_seconds: float = 0.0,
    ):
        """Patch generate_response to return a mock response.

        Args:
            response_text: Text to return. Defaults to standard greeting.
            delay_seconds: Optional delay before returning (simulates processing).

        Usage:
            with MockAgentHelper.patch_generate_response("Hi there!"):
                # Any code that calls generate_response will get "Hi there!"
                ...
        """
        import asyncio

        response = response_text or cls.RESPONSES["default"]

        async def mock_generate(*args, **kwargs) -> str:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            return response

        with patch(
            "nikita.agents.text.handler.generate_response",
            new=mock_generate,
        ):
            yield

    @classmethod
    @contextmanager
    def patch_message_handler(
        cls,
        response_text: Optional[str] = None,
    ):
        """Patch the entire message handler to return a mock response.

        This is a higher-level patch that skips all handler logic.
        Use for testing webhook routing, not message handling.
        """
        response = response_text or cls.RESPONSES["default"]

        async def mock_handle(*args, **kwargs) -> None:
            # The handler doesn't return anything - it sends via bot
            pass

        with patch(
            "nikita.platforms.telegram.message_handler.MessageHandler.handle",
            new=mock_handle,
        ):
            yield

    @classmethod
    def create_mock_deps(
        cls,
        user_id: str = "test-user-id",
        telegram_id: int = 999888777,
        game_status: str = "active",
        chapter: int = 1,
        relationship_score: float = 50.0,
    ) -> MagicMock:
        """Create mock NikitaDeps for testing.

        Returns a MagicMock configured with standard user state.
        """
        import uuid

        deps = MagicMock()

        # Mock user
        deps.user = MagicMock()
        deps.user.id = uuid.UUID(user_id) if user_id != "test-user-id" else uuid.uuid4()
        deps.user.telegram_id = telegram_id
        deps.user.game_status = game_status
        deps.user.chapter = chapter
        deps.user.relationship_score = relationship_score

        # Mock conversation
        deps.conversation = MagicMock()
        deps.conversation.id = uuid.uuid4()

        # Mock memory client
        deps.memory = AsyncMock()
        deps.memory.get_context_for_prompt = AsyncMock(return_value="")
        deps.memory.add_user_fact = AsyncMock()

        # Mock session
        deps.session = AsyncMock()

        return deps

    @classmethod
    @contextmanager
    def patch_get_nikita_agent_for_user(
        cls,
        mock_deps: Optional[MagicMock] = None,
    ):
        """Patch get_nikita_agent_for_user to return mock agent and deps.

        Useful for testing code that calls get_nikita_agent_for_user directly.
        """
        async def mock_get_agent(user_id):
            agent = AsyncMock()
            deps = mock_deps or cls.create_mock_deps()
            return agent, deps

        with patch(
            "nikita.agents.text.handler.get_nikita_agent_for_user",
            new=mock_get_agent,
        ):
            yield


# ==================== Environment-Aware Mock Configuration ====================

def is_mock_mode() -> bool:
    """Check if E2E tests should use mocked agent responses.

    Returns True if:
    - E2E_MOCK_MODE env var is set to "true"
    - Running in CI (CI env var is set)
    - ANTHROPIC_API_KEY is not set
    """
    if os.getenv("E2E_MOCK_MODE", "").lower() == "true":
        return True
    if os.getenv("CI"):
        return True
    if not os.getenv("ANTHROPIC_API_KEY"):
        return True
    return False


def get_mock_response_for_message(message: str) -> str:
    """Get appropriate mock response based on message content.

    Used when mock mode is enabled to provide contextual responses.
    """
    message_lower = message.lower()

    if message_lower.startswith("/start"):
        return "Hey there! I'm Nikita. What's your email so we can get started?"

    if "@" in message and "." in message:  # Looks like email
        return "Perfect! Check your email for a 6-digit code."

    if message.isdigit() and len(message) == 6:  # OTP code
        return MockAgentHelper.RESPONSES["welcome"]

    if any(word in message_lower for word in ["hi", "hello", "hey"]):
        return MockAgentHelper.RESPONSES["greeting"]

    return MockAgentHelper.RESPONSES["default"]
