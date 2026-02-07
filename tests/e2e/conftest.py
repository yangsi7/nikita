"""
E2E Test Configuration and Fixtures

Provides Playwright browser fixtures and test utilities for
end-to-end testing of the Telegram authentication and message flows.

Fixture Categories:
- Session-scoped: URLs, config (shared across all tests)
- Function-scoped: test data, webhook simulator (isolated per test)
- Cleanup: database cleanup after tests
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

# Note: playwright needs to be installed: pip install playwright pytest-playwright
# Then: playwright install chromium

from tests.e2e.helpers.telegram_helper import (
    TelegramWebhookSimulator,
    WebhookTestData,
    generate_test_telegram_id,
    generate_test_email,
)
from tests.e2e.helpers.mock_agent_helper import MockAgentHelper, is_mock_mode


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Get the backend API URL."""
    return os.getenv(
        "NIKITA_BACKEND_URL",
        "https://nikita-api-1040094048579.us-central1.run.app"
    )


@pytest.fixture(scope="session")
def webhook_url(backend_url: str) -> str:
    """Get the webhook endpoint URL."""
    return f"{backend_url}/api/v1/telegram/webhook"


@pytest.fixture(scope="session")
def auth_confirm_url(backend_url: str) -> str:
    """Get the auth confirm endpoint URL."""
    return f"{backend_url}/api/v1/telegram/auth/confirm"


@pytest.fixture(scope="session")
def supabase_url() -> str:
    """Get Supabase URL for magic link verification."""
    return os.getenv(
        "SUPABASE_URL",
        "https://vlvlwmolfdpzdfmtipji.supabase.co"
    )


@pytest.fixture(scope="session")
def test_email() -> str:
    """Get the test email address."""
    return os.getenv("TEST_EMAIL", "nikita.e2e.test@gmail.com")


@pytest.fixture(scope="session")
def test_telegram_id() -> int:
    """Get the test Telegram ID."""
    return int(os.getenv("TEST_TELEGRAM_ID", "999999999"))


# Browser fixtures - use pytest-playwright's built-in fixtures
# or define custom ones for async usage

@pytest.fixture
async def browser_context():
    """Create a browser context for a single test."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) E2E-Test"
        )
        yield context
        await browser.close()


@pytest.fixture
async def page(browser_context):
    """Create a page for a single test."""
    page = await browser_context.new_page()
    yield page
    await page.close()


# ==================== Webhook Test Fixtures ====================


@pytest.fixture
def test_app():
    """Create a minimal FastAPI test app with mocked telegram deps.

    Uses ASGI transport so E2E tests run in-process without needing
    the real Cloud Run endpoint or webhook secret. Follows the same
    mock pattern as tests/api/routes/test_telegram.py.
    """
    with patch("nikita.api.routes.telegram.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.telegram_webhook_secret = None  # Disable 403
        mock_get_settings.return_value = mock_settings

        from fastapi import FastAPI
        from nikita.platforms.telegram.bot import TelegramBot
        from nikita.api.routes.telegram import (
            create_telegram_router,
            get_command_handler,
            get_message_handler,
            get_onboarding_handler,
            get_otp_handler,
            get_registration_handler,
            _get_bot_from_state,
        )
        from nikita.db.dependencies import (
            get_user_repo,
            get_pending_registration_repo,
            get_profile_repo,
            get_onboarding_state_repo,
        )

        app = FastAPI()

        # Mock bot
        bot = MagicMock(spec=TelegramBot)
        bot.send_message = AsyncMock(return_value={"ok": True})
        app.state.telegram_bot = bot

        # Mock all handler dependencies
        mock_cmd = AsyncMock()
        mock_cmd.handle = AsyncMock()

        mock_msg = AsyncMock()
        mock_msg.handle = AsyncMock()

        mock_onboarding = MagicMock()
        mock_onboarding.handle = AsyncMock()
        mock_onboarding.start = AsyncMock()
        mock_onboarding.has_incomplete_onboarding = AsyncMock(return_value=None)

        mock_otp = MagicMock()
        mock_otp.handle = AsyncMock(return_value=True)

        mock_reg = AsyncMock()
        mock_reg.handle = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=None)
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)

        mock_pending_repo = AsyncMock()
        mock_pending_repo.get_by_telegram_id = AsyncMock(return_value=None)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get = AsyncMock(return_value=None)

        mock_onboarding_repo = AsyncMock()
        mock_onboarding_repo.get = AsyncMock(return_value=None)
        mock_onboarding_repo.get_or_create = AsyncMock(return_value=None)

        # Override dependencies
        app.dependency_overrides[get_command_handler] = lambda: mock_cmd
        app.dependency_overrides[get_message_handler] = lambda: mock_msg
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_onboarding
        app.dependency_overrides[get_otp_handler] = lambda: mock_otp
        app.dependency_overrides[get_registration_handler] = lambda: mock_reg
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
        app.dependency_overrides[get_pending_registration_repo] = lambda: mock_pending_repo
        app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
        app.dependency_overrides[get_onboarding_state_repo] = lambda: mock_onboarding_repo
        app.dependency_overrides[_get_bot_from_state] = lambda: bot

        # Include telegram router
        router = create_telegram_router(bot=bot)
        app.include_router(router, prefix="/api/v1/telegram")

        yield app


@pytest.fixture
def webhook_simulator(test_app) -> TelegramWebhookSimulator:
    """Create a webhook simulator using in-process ASGI transport."""
    return TelegramWebhookSimulator(app=test_app)


@pytest.fixture
def unique_telegram_id() -> int:
    """Generate a unique Telegram ID for this test.

    Uses the 900M-999M range to avoid collision with real users.
    Each test gets a fresh ID to ensure isolation.
    """
    return generate_test_telegram_id()


@pytest.fixture
def unique_test_email(unique_telegram_id: int) -> str:
    """Generate a unique test email based on Telegram ID."""
    return generate_test_email(unique_telegram_id)


@pytest.fixture
def test_data() -> WebhookTestData:
    """Create complete test data for a webhook test.

    Returns a WebhookTestData instance with unique telegram_id, email, and chat_id.
    """
    return WebhookTestData.create()


# ==================== Mock Mode Fixtures ====================


@pytest.fixture
def mock_agent():
    """Context manager fixture for mocking the agent response.

    Usage in test:
        def test_something(mock_agent):
            with mock_agent("Hello from Nikita!"):
                # Test code here
    """
    return MockAgentHelper.patch_generate_response


@pytest.fixture
def mock_mode() -> bool:
    """Check if tests should run in mock mode (no real API calls)."""
    return is_mock_mode()


# ==================== Database Cleanup Fixtures ====================


@pytest.fixture
async def cleanup_pending_registration(unique_telegram_id: int):
    """Cleanup pending registration after test.

    NOTE: This fixture uses Supabase MCP tools in Claude Code context.
    In CI/CD, cleanup happens via the Supabase Python client.
    """
    yield unique_telegram_id

    # Cleanup SQL for pending_registrations
    cleanup_sql = f"""
        DELETE FROM pending_registrations
        WHERE telegram_id = {unique_telegram_id};
    """
    # In Claude Code: mcp__supabase__execute_sql({"query": cleanup_sql})
    # In CI/CD: supabase_client.rpc("execute_sql", {"query": cleanup_sql})
    #
    # For now, tests are responsible for their own cleanup or
    # can call this fixture explicitly.


@pytest.fixture
async def cleanup_test_user(unique_telegram_id: int):
    """Cleanup test user after test.

    Removes user_metrics and users records for the test telegram_id.
    """
    yield unique_telegram_id

    # Cleanup SQL for users (cascades to user_metrics via FK)
    cleanup_sql = f"""
        DELETE FROM users
        WHERE telegram_id = {unique_telegram_id};
    """
    # See cleanup_pending_registration for execution notes
