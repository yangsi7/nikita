"""Adversarial/gap scenario tests for Telegram webhook and rate limiter (GH #145).

Covers: empty messages, very long messages, unicode/emoji, whitespace-only,
webhook secret validation, and rate limiter edge cases. All tests fully mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.rate_limiter import (
    InMemoryCache,
    RateLimiter,
    RateLimitResult,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_update(text: str | None, update_id: int = 1, telegram_id: int = 99999) -> dict:
    """Build a minimal Telegram webhook update payload."""
    msg: dict = {
        "message_id": 1,
        "date": 1700000000,
        "from": {"id": telegram_id, "is_bot": False, "first_name": "Test"},
        "chat": {"id": telegram_id, "type": "private"},
    }
    if text is not None:
        msg["text"] = text
    return {"update_id": update_id, "message": msg}


# ---------------------------------------------------------------------------
# Webhook security tests
# ---------------------------------------------------------------------------


class TestWebhookSecretValidation:
    """SEC-01: Webhook secret header validation."""

    @pytest.fixture(autouse=True)
    def clear_dedup_cache(self):
        """Clear dedup cache so each test gets clean state."""
        import nikita.api.routes.telegram as tg_module
        tg_module._UPDATE_ID_CACHE.clear()
        yield
        tg_module._UPDATE_ID_CACHE.clear()

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock(spec=TelegramBot)
        bot.send_message = AsyncMock(return_value={"ok": True})
        return bot

    def _build_app(self, mock_bot, webhook_secret: str | None):
        """Build a FastAPI test app with a specific webhook_secret setting."""
        from nikita.api.routes.telegram import (
            create_telegram_router,
            get_command_handler,
            get_message_handler,
            get_onboarding_handler,
            get_otp_handler,
            get_registration_handler,
        )
        from nikita.db.database import get_async_session
        from nikita.db.dependencies import (
            get_user_repo,
            get_pending_registration_repo,
            get_profile_repo,
            get_onboarding_state_repo,
        )

        app = FastAPI()
        app.state.telegram_bot = mock_bot

        mock_handler = AsyncMock()
        mock_handler.handle = AsyncMock()

        app.dependency_overrides[get_command_handler] = lambda: mock_handler
        app.dependency_overrides[get_message_handler] = lambda: mock_handler
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_handler
        app.dependency_overrides[get_otp_handler] = lambda: mock_handler
        app.dependency_overrides[get_registration_handler] = lambda: mock_handler
        app.dependency_overrides[get_user_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_pending_registration_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_profile_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_onboarding_state_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_async_session] = lambda: AsyncMock()

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    def test_missing_secret_header_rejected(self, mock_bot):
        """Webhook without X-Telegram-Bot-Api-Secret-Token header is 403."""
        with patch("nikita.api.routes.telegram.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = "real-secret-123"
            mock_gs.return_value = mock_settings

            # Also mock the rate limiter to not hit DB
            with patch("nikita.api.routes.telegram.DatabaseRateLimiter") as mock_rl_cls:
                mock_rl = MagicMock()
                mock_rl.check_by_telegram_id = AsyncMock(
                    return_value=RateLimitResult(allowed=True)
                )
                mock_rl_cls.return_value = mock_rl

                app = self._build_app(mock_bot, webhook_secret="real-secret-123")
                client = TestClient(app)

                resp = client.post(
                    "/api/v1/telegram/webhook",
                    json=_make_update("hello"),
                )
                assert resp.status_code == 403

    def test_wrong_secret_header_rejected(self, mock_bot):
        """Webhook with incorrect secret value is 403."""
        with patch("nikita.api.routes.telegram.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = "real-secret-123"
            mock_gs.return_value = mock_settings

            with patch("nikita.api.routes.telegram.DatabaseRateLimiter") as mock_rl_cls:
                mock_rl = MagicMock()
                mock_rl.check_by_telegram_id = AsyncMock(
                    return_value=RateLimitResult(allowed=True)
                )
                mock_rl_cls.return_value = mock_rl

                app = self._build_app(mock_bot, webhook_secret="real-secret-123")
                client = TestClient(app)

                resp = client.post(
                    "/api/v1/telegram/webhook",
                    json=_make_update("hello", update_id=2),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
                )
                assert resp.status_code == 403

    def test_correct_secret_header_accepted(self, mock_bot):
        """Webhook with correct secret value is accepted (200)."""
        with patch("nikita.api.routes.telegram.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = "real-secret-123"
            mock_gs.return_value = mock_settings

            with patch("nikita.api.routes.telegram.DatabaseRateLimiter") as mock_rl_cls:
                mock_rl = MagicMock()
                mock_rl.check_by_telegram_id = AsyncMock(
                    return_value=RateLimitResult(allowed=True)
                )
                mock_rl_cls.return_value = mock_rl

                app = self._build_app(mock_bot, webhook_secret="real-secret-123")
                client = TestClient(app)

                resp = client.post(
                    "/api/v1/telegram/webhook",
                    json=_make_update("hello", update_id=3),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "real-secret-123"},
                )
                assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Edge case message content tests
# ---------------------------------------------------------------------------


class TestEdgeCaseMessages:
    """Message content edge cases: empty, whitespace, long, unicode."""

    @pytest.fixture(autouse=True)
    def mock_settings_no_secret(self):
        with patch("nikita.api.routes.telegram.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = None
            mock_gs.return_value = mock_settings
            yield

    @pytest.fixture(autouse=True)
    def mock_rate_limiter(self):
        with patch("nikita.api.routes.telegram.DatabaseRateLimiter") as mock_rl_cls:
            mock_rl = MagicMock()
            mock_rl.check_by_telegram_id = AsyncMock(
                return_value=RateLimitResult(allowed=True)
            )
            mock_rl_cls.return_value = mock_rl
            yield

    @pytest.fixture(autouse=True)
    def clear_dedup_cache(self):
        import nikita.api.routes.telegram as tg_module
        tg_module._UPDATE_ID_CACHE.clear()
        yield
        tg_module._UPDATE_ID_CACHE.clear()

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock(spec=TelegramBot)
        bot.send_message = AsyncMock(return_value={"ok": True})
        return bot

    @pytest.fixture
    def app(self, mock_bot):
        from nikita.api.routes.telegram import (
            create_telegram_router,
            get_command_handler,
            get_message_handler,
            get_onboarding_handler,
            get_otp_handler,
            get_registration_handler,
        )
        from nikita.db.database import get_async_session
        from nikita.db.dependencies import (
            get_user_repo,
            get_pending_registration_repo,
            get_profile_repo,
            get_onboarding_state_repo,
        )

        app = FastAPI()
        app.state.telegram_bot = mock_bot

        mock_handler = AsyncMock()
        mock_handler.handle = AsyncMock()

        app.dependency_overrides[get_command_handler] = lambda: mock_handler
        app.dependency_overrides[get_message_handler] = lambda: mock_handler
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_handler
        app.dependency_overrides[get_otp_handler] = lambda: mock_handler
        app.dependency_overrides[get_registration_handler] = lambda: mock_handler
        app.dependency_overrides[get_user_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_pending_registration_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_profile_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_onboarding_state_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_async_session] = lambda: AsyncMock()

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_empty_string_message(self, client):
        """Empty string body does not crash the webhook."""
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_make_update("", update_id=10),
        )
        assert resp.status_code == 200

    def test_whitespace_only_message(self, client):
        """Whitespace-only message does not crash the webhook."""
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_make_update("   \t\n  ", update_id=11),
        )
        assert resp.status_code == 200

    def test_very_long_message(self, client):
        """4000+ character message is handled gracefully (no 500)."""
        long_text = "A" * 5000
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_make_update(long_text, update_id=12),
        )
        assert resp.status_code == 200

    def test_unicode_emoji_message(self, client):
        """Unicode, CJK, and emoji message is handled gracefully."""
        unicode_text = "Hello 🔥💕 你好世界 مرحبا 🇨🇭 Ñoño"
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_make_update(unicode_text, update_id=13),
        )
        assert resp.status_code == 200

    def test_null_text_message(self, client):
        """Message with no text field (e.g., photo-only) is handled."""
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_make_update(None, update_id=14),
        )
        assert resp.status_code == 200

    def test_no_message_in_update(self, client):
        """Update with no message field is handled gracefully."""
        resp = client.post(
            "/api/v1/telegram/webhook",
            json={"update_id": 15},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Rate limiter unit tests (in-memory, no DB)
# ---------------------------------------------------------------------------


class TestRateLimiterEdgeCases:
    """Rate limiter boundary and concurrency edge cases."""

    @pytest.fixture
    def cache(self):
        return InMemoryCache()

    @pytest.fixture
    def limiter(self, cache):
        return RateLimiter(cache)

    @pytest.mark.asyncio
    async def test_first_message_always_allowed(self, limiter):
        """Very first message from a user is always allowed."""
        from uuid import uuid4
        result = await limiter.check(uuid4())
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_minute_limit_blocks_at_21(self, limiter, cache):
        """21st message within a minute is blocked."""
        from uuid import uuid4
        user_id = uuid4()

        # Send 20 messages (the limit)
        for _ in range(20):
            result = await limiter.check(user_id)
            assert result.allowed is True

        # 21st should be blocked
        result = await limiter.check(user_id)
        assert result.allowed is False
        assert result.reason == "minute_limit_exceeded"

    @pytest.mark.asyncio
    async def test_rate_limit_result_has_retry_after(self, limiter, cache):
        """Blocked result includes retry_after_seconds."""
        from uuid import uuid4
        user_id = uuid4()

        for _ in range(21):
            result = await limiter.check(user_id)

        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0
