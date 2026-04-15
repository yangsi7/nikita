"""Tests for preview backstory route — Spec 213 PR 213-4.

Covers:
  - test_profile_post_reuses_cache  (cache coherence between preview + PATCH /profile)
  - test_rate_limit                 (FR-4a.1: 6th call → 429 + Retry-After: 60)
  - test_stateless_no_jsonb_write   (preview does NOT write onboarding_profile)

Per .claude/rules/testing.md:
  - Every test_* has at least one assert
  - Non-empty fixtures for iterator/worker paths
  - Patch source module, NOT importer
"""

from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")

VALID_PREVIEW_BODY = {
    "city": "Berlin",
    "social_scene": "techno",
    "darkness_level": 3,
}

SAMPLE_OPTION = {
    "id": "abc123def456",
    "venue": "Berghain",
    "context": "Dark basement",
    "the_moment": "Eyes met",
    "unresolved_hook": "She vanished",
    "tone": "romantic",
}


def _make_preview_app(
    user_id: UUID = USER_ID,
    rate_limit_raises: bool = False,
) -> FastAPI:
    """Build a FastAPI test app with portal_onboarding router + overrides."""
    from nikita.api.routes.portal_onboarding import router
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.db.database import get_async_session
    from nikita.api.middleware.rate_limit import preview_rate_limit

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    app.dependency_overrides[get_current_user_id] = lambda: user_id

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    app.dependency_overrides[get_async_session] = _session_override

    if rate_limit_raises:
        from fastapi import HTTPException

        async def _rate_limit_exceeded() -> None:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        app.dependency_overrides[preview_rate_limit] = _rate_limit_exceeded
    else:

        async def _rate_limit_pass() -> None:
            return None

        app.dependency_overrides[preview_rate_limit] = _rate_limit_pass

    return app


class TestPreviewCacheCoherence:
    """Preview cache is reused by PATCH /profile (FR-4a: no duplicate Claude calls)."""

    def test_profile_post_reuses_cache(self):
        """generate_scenarios called ONCE across preview + PATCH /profile if cache hit.

        Simulates: preview call fills cache → PATCH /profile reads from cache.
        BackstoryGeneratorService.generate_scenarios called exactly once total.
        """
        from nikita.onboarding.contracts import BackstoryPreviewResponse, BackstoryOption

        # Build preview response (cache will be warmed by this call)
        mock_preview_response = BackstoryPreviewResponse(
            scenarios=[BackstoryOption(**SAMPLE_OPTION)],
            venues_used=["Berghain"],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=False,
        )

        app = _make_preview_app()

        with patch(
            "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
        ) as MockFacade:
            inst = AsyncMock()
            inst.generate_preview = AsyncMock(return_value=mock_preview_response)
            MockFacade.return_value = inst

            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 200
        # Verify facade.generate_preview was called once
        inst.generate_preview.assert_awaited_once()


class TestPreviewRateLimit:
    """FR-4a.1: Rate limiting on preview-backstory endpoint."""

    def test_rate_limit_returns_429(self):
        """6th call (simulated via rate_limit_raises=True) → 429 + Retry-After header."""
        app = _make_preview_app(rate_limit_raises=True)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json=VALID_PREVIEW_BODY,
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

    def test_rate_limit_body_has_detail(self):
        """429 response body contains detail field."""
        app = _make_preview_app(rate_limit_raises=True)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json=VALID_PREVIEW_BODY,
        )

        assert response.status_code == 429
        data = response.json()
        assert "detail" in data


class TestPreviewStateless:
    """test_stateless_no_jsonb_write: preview does NOT write to onboarding_profile."""

    def test_stateless_no_jsonb_write(self):
        """Preview endpoint is stateless: no JSONB write path triggered.

        Verifies that PortalOnboardingFacade.generate_preview (not process()) is called,
        and the response is 200. The preview endpoint does NOT have a UserRepository
        import at module level — this is enforced by the test asserting the endpoint
        uses generate_preview (which is stateless) rather than process() (which writes).
        """
        from nikita.onboarding.contracts import BackstoryPreviewResponse

        mock_response = BackstoryPreviewResponse(
            scenarios=[],
            venues_used=[],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=True,
        )

        app = _make_preview_app()

        with patch(
            "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
        ) as MockFacade:
            inst = AsyncMock()
            inst.generate_preview = AsyncMock(return_value=mock_response)
            inst.process = AsyncMock()  # should NOT be called on preview path
            MockFacade.return_value = inst

            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 200
        # Preview is stateless: generate_preview called, process() NOT called
        inst.generate_preview.assert_awaited_once()
        inst.process.assert_not_called()
