"""Tests for /telegram/webhook routing — Spec 216-A telegram-canonical-routing.

Bare `/start` and `/start welcome` from unbound telegram_id MUST enter
`SignupHandler.handle_welcome` (NOT `_handle_start` E1 path). Bound users
bypass FSM and route to `CommandHandler` (existing behavior preserved).

Mapped AC: A1.1, A1.2, A1.3 (regression guard: A1.4 covered by T-A-1
golden test for route entry).

Tests use the FastAPI app fixture pattern from `tests/api/routes/test_telegram.py`
(`mock_user_repo.get_by_telegram_id` controls bound vs unbound). The
production routing dispatch wraps `_run_signup_with_fresh_session` in
`background_tasks.add_task(...)`, so we patch the symbol on the module
to capture the call without exercising DB / Supabase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.message_handler import MessageHandler


@pytest.fixture(autouse=True)
def mock_settings_no_webhook_secret():
    """Disable TELEGRAM_WEBHOOK_SECRET signature check for tests."""
    with patch("nikita.api.routes.telegram.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.telegram_webhook_secret = None
        mock_get_settings.return_value = mock_settings
        yield mock_settings


@pytest.fixture(autouse=True)
def mock_database_rate_limiter():
    """GH #134: prevent real DB hit when webhook builds DatabaseRateLimiter."""
    from nikita.platforms.telegram.rate_limiter import (
        DatabaseRateLimiter,
        RateLimitResult,
    )

    mock_rl = MagicMock(spec=DatabaseRateLimiter)
    mock_rl.check_by_telegram_id = AsyncMock(
        return_value=RateLimitResult(
            allowed=True,
            reason=None,
            minute_remaining=19,
            day_remaining=499,
            retry_after_seconds=None,
            warning_threshold_reached=False,
        )
    )
    with patch(
        "nikita.api.routes.telegram.DatabaseRateLimiter",
        return_value=mock_rl,
    ):
        yield mock_rl


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock(spec=TelegramBot)
    bot.send_message = AsyncMock(return_value={"ok": True})
    return bot


@pytest.fixture
def mock_command_handler() -> AsyncMock:
    handler = AsyncMock(spec=CommandHandler)
    handler.handle = AsyncMock()
    handler._handle_start = AsyncMock()
    return handler


@pytest.fixture
def mock_message_handler() -> AsyncMock:
    handler = AsyncMock(spec=MessageHandler)
    handler.handle = AsyncMock()
    return handler


@pytest.fixture
def mock_otp_handler() -> AsyncMock:
    from nikita.platforms.telegram.otp_handler import OTPVerificationHandler

    handler = MagicMock(spec=OTPVerificationHandler)
    handler.handle = AsyncMock(return_value=True)
    return handler


@pytest.fixture
def mock_registration_handler() -> AsyncMock:
    handler = AsyncMock()
    handler.handle = AsyncMock()
    return handler


@pytest.fixture
def mock_user_repo_unbound() -> AsyncMock:
    """Unbound: telegram_id has no row in `users`."""
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=None)
    repo.get_by_telegram_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_user_repo_bound() -> AsyncMock:
    """Bound: telegram_id resolves to a `users.id`."""
    repo = AsyncMock()
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    repo.get = AsyncMock(return_value=user)
    repo.get_by_telegram_id = AsyncMock(return_value=user)
    return repo


@pytest.fixture
def mock_pending_repo() -> AsyncMock:
    """No pending signup session by default."""
    repo = AsyncMock()
    repo.get_by_telegram_id = AsyncMock(return_value=None)
    repo.get = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_profile_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_onboarding_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=None)
    repo.get_or_create = AsyncMock(return_value=None)
    return repo


def _build_app(
    *,
    mock_bot,
    mock_command_handler,
    mock_message_handler,
    mock_otp_handler,
    mock_user_repo,
    mock_pending_repo,
    mock_profile_repo,
    mock_onboarding_repo,
    mock_registration_handler,
) -> FastAPI:
    """Build a FastAPI app with telegram router + DI overrides."""
    from nikita.api.routes.telegram import (
        create_telegram_router,
        get_command_handler,
        get_message_handler,
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

    app.dependency_overrides[get_command_handler] = lambda: mock_command_handler
    app.dependency_overrides[get_message_handler] = lambda: mock_message_handler
    app.dependency_overrides[get_otp_handler] = lambda: mock_otp_handler
    app.dependency_overrides[get_registration_handler] = lambda: mock_registration_handler
    app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
    app.dependency_overrides[get_pending_registration_repo] = lambda: mock_pending_repo
    app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
    app.dependency_overrides[get_onboarding_state_repo] = lambda: mock_onboarding_repo
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()

    router = create_telegram_router(bot=mock_bot)
    app.include_router(router, prefix="/api/v1/telegram")
    return app


def _build_update(text: str, *, telegram_id: int = 123456789, update_id: int = 90001) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Test", "is_bot": False},
            "chat": {"id": telegram_id, "type": "private"},
            "text": text,
            "date": 1234567890,
        },
    }


# ---------------------------------------------------------------------------
# A1.1 — Bare `/start` for unbound telegram_id enters SignupHandler.handle_welcome
# ---------------------------------------------------------------------------


class TestBareStartUnboundRouting:
    """Spec 216-A AC A1.1: bare `/start` (no payload) for unbound users
    MUST enter SignupHandler.handle_welcome (NOT `_handle_start` E1 path).
    """

    def test_bare_start_unbound_enters_signup_handler(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_unbound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """A1.1 GOLDEN: bare `/start` from unbound telegram_id routes
        directly into the consolidated signup FSM via
        `_run_signup_with_fresh_session(flow="welcome")`. CommandHandler
        is NOT invoked for unbound users. (RED on master: master's
        predicate at telegram.py:639-644 requires `payload == "welcome"`,
        so a bare `/start` falls through to CommandHandler.)
        """
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ) as mock_run_signup:
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_unbound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)

            update = _build_update("/start")
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200

            # AC A1.1: SignupHandler.handle_welcome path must be invoked.
            assert mock_run_signup.await_count == 1, (
                "bare /start unbound MUST route to SignupHandler via "
                "_run_signup_with_fresh_session (Spec 216-A A1.1). "
                f"Got await_count={mock_run_signup.await_count}."
            )
            call_kwargs = mock_run_signup.await_args.kwargs
            call_args = mock_run_signup.await_args.args
            # Positional args: (bot_instance, flow); kwargs: telegram_id, chat_id.
            assert "welcome" in call_args, (
                f"flow positional arg must be 'welcome', got args={call_args}"
            )
            assert call_kwargs.get("telegram_id") == 123456789
            assert call_kwargs.get("chat_id") == 123456789

            # AC A1.1 (negative): CommandHandler.handle MUST NOT be invoked
            # for the unbound `/start` path — the request is fully handled
            # by the SignupHandler dispatch.
            mock_command_handler.handle.assert_not_awaited()


# ---------------------------------------------------------------------------
# A1.2 — `/start welcome` payload-literal still routes to SignupHandler
# ---------------------------------------------------------------------------


class TestWelcomePayloadUnboundRouting:
    """Spec 216-A AC A1.2: `/start welcome` deep-link payload also enters
    SignupHandler.handle_welcome (existing path preserved).
    """

    def test_welcome_payload_unbound_enters_signup_handler(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_unbound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """A1.2: bare `/start` AND `/start welcome` converge to same handler."""
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ) as mock_run_signup:
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_unbound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)

            update = _build_update("/start welcome", update_id=90002)
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200
            assert mock_run_signup.await_count == 1, (
                "/start welcome unbound MUST also route to SignupHandler "
                "(Spec 216-A A1.2)."
            )
            call_args = mock_run_signup.await_args.args
            call_kwargs = mock_run_signup.await_args.kwargs
            assert "welcome" in call_args
            assert call_kwargs.get("telegram_id") == 123456789
            assert call_kwargs.get("chat_id") == 123456789
            mock_command_handler.handle.assert_not_awaited()


# ---------------------------------------------------------------------------
# A1.3 — Bound users bypass FSM, route to CommandHandler
# ---------------------------------------------------------------------------


class TestBoundUserStartRouting:
    """Spec 216-A AC A1.3: bound telegram_id (resolves to users.id) MUST
    bypass the FSM and route to the standard CommandHandler.handle path.
    """

    def test_bare_start_bound_uses_command_handler(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_bound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """A1.3: bound user → CommandHandler, NOT SignupHandler."""
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ) as mock_run_signup:
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_bound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)

            update = _build_update("/start", update_id=90003)
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200
            # Bound user: SignupHandler MUST NOT be invoked.
            mock_run_signup.assert_not_awaited()
            # CommandHandler.handle is dispatched via background_tasks; the
            # TestClient awaits background tasks before returning, so the
            # await must register here.
            mock_command_handler.handle.assert_awaited_once()


# ---------------------------------------------------------------------------
# Regression guard — A1.1 negative branch on commands._handle_start
# ---------------------------------------------------------------------------


class TestHandleStartE1NotInvokedForUnbound:
    """Regression guard: the legacy `_handle_start` E1 path
    (`_send_bare_portal_auth_link`) MUST NOT be invoked for unbound
    `/start`. Since the unbound branch returns from receive_webhook
    before scheduling CommandHandler.handle, `CommandHandler.handle` is
    not awaited at all.
    """

    def test_handle_start_e1_path_not_called_for_unbound_start(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_unbound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """Regression: `_handle_start` (and therefore E1
        `_send_bare_portal_auth_link`) is unreachable from `/start` for
        unbound users post-Spec-216-A.
        """
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ):
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_unbound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)
            update = _build_update("/start", update_id=90004)
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200
            # CommandHandler.handle (which would invoke _handle_start, then
            # _send_bare_portal_auth_link via the E1 branch) MUST NOT be
            # called for unbound /start.
            mock_command_handler.handle.assert_not_awaited()
            # The E1-path internal method is also never invoked.
            mock_command_handler._handle_start.assert_not_awaited()


# ---------------------------------------------------------------------------
# Edge case — whitespace-only payload defaults to "welcome"
# ---------------------------------------------------------------------------


class TestWhitespacePayloadRouting:
    """Edge case (test-engineer review): `/start   ` (trailing whitespace
    only) defaults `entry_point` to "welcome" and routes to SignupHandler.
    Documents the predicate `entry_point = payload or "welcome"` after
    `parts[1].strip()` in `telegram.py:642`.
    """

    def test_bare_start_with_whitespace_payload_routes_to_signup(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_unbound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """`/start    ` (trailing whitespace) for unbound user → "welcome"
        flow, same as bare `/start`. Both forms must converge to the FSM
        without leaking through to CommandHandler.
        """
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ) as mock_run_signup:
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_unbound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)

            update = _build_update("/start    ", update_id=90005)
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200
            assert mock_run_signup.await_count == 1
            call_args = mock_run_signup.await_args.args
            # whitespace-only payload → empty after strip → "welcome" default
            assert "welcome" in call_args, (
                "Whitespace-only payload must default entry_point to "
                "'welcome', preventing _send_bare_portal_auth_link reach."
            )
            mock_command_handler.handle.assert_not_awaited()


# ---------------------------------------------------------------------------
# Regression guard — entry_point payload propagation (test-engineer review)
# ---------------------------------------------------------------------------


class TestEntryPointPayloadPropagation:
    """Regression guard: a non-empty non-welcome payload (e.g., a future
    referral code `/start ref:abc`) MUST propagate to
    `_run_signup_with_fresh_session` as the `flow` argument, NOT silently
    coerce to "welcome".

    Catches the latent bug from initial T-A-2 commit where `entry_point`
    was computed at telegram.py:654 but ignored at :664 (hardcoded
    "welcome"). After the fix, downstream code can branch on the payload
    without a second routing layer.
    """

    def test_referral_payload_unbound_propagates_to_signup_flow(
        self,
        mock_bot,
        mock_command_handler,
        mock_message_handler,
        mock_otp_handler,
        mock_user_repo_unbound,
        mock_pending_repo,
        mock_profile_repo,
        mock_onboarding_repo,
        mock_registration_handler,
    ):
        """`/start ref:abc` unbound → flow="ref:abc", NOT "welcome"."""
        with patch(
            "nikita.api.routes.telegram._run_signup_with_fresh_session",
            new_callable=AsyncMock,
        ) as mock_run_signup:
            app = _build_app(
                mock_bot=mock_bot,
                mock_command_handler=mock_command_handler,
                mock_message_handler=mock_message_handler,
                mock_otp_handler=mock_otp_handler,
                mock_user_repo=mock_user_repo_unbound,
                mock_pending_repo=mock_pending_repo,
                mock_profile_repo=mock_profile_repo,
                mock_onboarding_repo=mock_onboarding_repo,
                mock_registration_handler=mock_registration_handler,
            )
            client = TestClient(app)

            update = _build_update("/start ref:abc", update_id=90006)
            response = client.post("/api/v1/telegram/webhook", json=update)

            assert response.status_code == 200
            assert mock_run_signup.await_count == 1
            call_args = mock_run_signup.await_args.args
            assert "ref:abc" in call_args, (
                "Non-welcome payload MUST propagate to _run_signup_with_"
                "fresh_session as flow. Catches the regression where "
                "entry_point was computed but ignored (hardcoded 'welcome')."
            )
            assert "welcome" not in call_args, (
                "Hardcoded 'welcome' would shadow the actual referral "
                "payload — regression guard."
            )
            mock_command_handler.handle.assert_not_awaited()
