"""T-B3-5 (Spec 216-B3): /converse 410-Gone shim with feature flag.

Default behavior (flag off): POST /converse routes to the existing handler.
Flag-on behavior: POST /converse returns 410 with RFC 8594 Sunset +
Deprecation headers + Link: rel="successor-version" → /answer.

The flag exists so this PR can land without breaking the FE on master
(use-onboarding-api.ts:233 still calls /converse). After 216-C migrates the FE
to /answer and ships, ops flips ``CONVERSE_SUNSET_ENABLED=true`` at deploy
time and stale tabs see graceful migration messaging instead of garbled state.

Hard rules verified:
  - Sunset header is the env-configured fixed instant, NOT computed per-request
  - Deprecation: true (RFC 8594 §3)
  - Link: relative URL with rel="successor-version" so HTTP libraries can
    auto-follow
  - Default flag-off MUST NOT 410 — protects the migration window
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _make_app() -> FastAPI:
    """Build a FastAPI app with portal_onboarding router + bypassed deps.

    /converse on the legacy path requires an array of overrides; we install
    rate-limit + auth bypasses and let the body short-circuit on the 410
    sunset gate (no agent invocation needed).
    """
    from nikita.api.dependencies.auth import (
        AuthenticatedUser,
        get_authenticated_user,
        get_current_user_id,
    )
    from nikita.api.middleware.rate_limit import converse_rate_limit
    from nikita.api.routes.portal_onboarding import router
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    async def _auth_override() -> AuthenticatedUser:
        return AuthenticatedUser(id=USER_ID, email="test@example.com")

    async def _session_override():
        from unittest.mock import AsyncMock
        from sqlalchemy.ext.asyncio import AsyncSession as _S

        return AsyncMock(spec=_S)

    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[converse_rate_limit] = lambda: None
    return app


def _make_settings(*, sunset: bool):
    from nikita.config.settings import Settings

    return Settings(
        converse_sunset_enabled=sunset,
        converse_sunset_date="Wed, 01 Jul 2026 00:00:00 GMT",
    )


class TestConverseSunsetShim:
    """B1.16 — /converse responds 410 only when CONVERSE_SUNSET_ENABLED=true."""

    def test_default_flag_off_does_not_return_410(self) -> None:
        """Flag default False → /converse MUST NOT return 410. The legacy
        path proceeds as before, so the FE on master keeps working until
        216-C ships."""
        app = _make_app()
        from nikita.config.settings import get_settings

        get_settings.cache_clear()
        with patch(
            "nikita.api.routes.portal_onboarding.get_settings",
            return_value=_make_settings(sunset=False),
        ):
            # raise_server_exceptions=False so legacy-path mock-session
            # edges surface as 500 instead of bubbling — the falsifier
            # we care about is "NOT 410", not the deeper handler shape
            # which is exercised by the dedicated /converse test suites.
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/onboarding/converse",
                json={
                    "conversation_history": [],
                    "user_input": "hi",
                    "turn_id": str(uuid4()),
                },
            )
        assert response.status_code != 410, (
            f"Default flag-off MUST NOT 410. Got {response.status_code}: "
            f"{response.text}"
        )

    def test_flag_on_returns_410_with_sunset_headers(self) -> None:
        """Flag True → /converse returns 410 with RFC 8594 headers.

        Body carries migration_url. Headers:
          - Sunset: configured fixed instant
          - Deprecation: true
          - Link: </api/v1/onboarding/answer>; rel="successor-version"
        """
        app = _make_app()
        from nikita.config.settings import get_settings

        get_settings.cache_clear()
        with patch(
            "nikita.api.routes.portal_onboarding.get_settings",
            return_value=_make_settings(sunset=True),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/converse",
                json={
                    "conversation_history": [],
                    "user_input": "hi",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 410, response.text
        body = response.json()
        assert "deprecated" in body["detail"].lower()
        assert "/answer" in body["migration_url"]

        sunset = response.headers.get("sunset", "")
        assert "2026" in sunset, (
            f"Sunset header must carry the configured RFC 8594 fixed instant, "
            f"got {sunset!r}."
        )
        assert response.headers.get("deprecation", "").lower() == "true"

        link = response.headers.get("link", "")
        assert 'rel="successor-version"' in link
        assert "/api/v1/onboarding/answer" in link
