"""Tests for POST /api/v1/onboarding/preview-backstory endpoint — Spec 213 PR 213-3.

TDD phase: endpoint tests using FastAPI dependency_overrides for auth + rate limit.

Per .claude/rules/testing.md:
  - Every test_* must have at least one assert
  - Patch source module, NOT importer
  - Non-empty fixture required for iterator/worker paths
"""

from unittest.mock import AsyncMock, MagicMock, patch
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


def _make_app(user_id: UUID = USER_ID, rate_limit_raises: bool = False) -> FastAPI:
    """Build a FastAPI test app with portal_onboarding router.

    Uses dependency_overrides for:
      - get_current_user_id: returns user_id directly
      - get_async_session: returns AsyncMock session
      - preview_rate_limit (aliased _preview_rate_limit): no-op or 429
    """
    from nikita.api.routes.portal_onboarding import router
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.db.database import get_async_session
    from nikita.api.middleware.rate_limit import preview_rate_limit

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    # Auth override
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    # Session override — provide a real AsyncMock
    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    app.dependency_overrides[get_async_session] = _session_override

    # Rate limit override — no typed params to avoid FastAPI Pydantic introspection
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


class TestPreviewBackstoryEndpointHappyPath:
    """POST /preview-backstory happy path tests."""

    def test_returns_200_with_valid_body(self):
        """Valid request body → 200 with BackstoryPreviewResponse shape."""
        from nikita.onboarding.contracts import BackstoryPreviewResponse, BackstoryOption

        mock_response = BackstoryPreviewResponse(
            scenarios=[BackstoryOption(**SAMPLE_OPTION)],
            venues_used=["Berghain"],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=False,
        )

        app = _make_app()
        with patch(
            "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
        ) as MockFacade:
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "cache_key" in data
        assert "degraded" in data
        assert "venues_used" in data

    def test_response_contains_backstory_options(self):
        """Response scenarios list contains valid BackstoryOption shapes."""
        from nikita.onboarding.contracts import BackstoryPreviewResponse, BackstoryOption

        mock_response = BackstoryPreviewResponse(
            scenarios=[BackstoryOption(**SAMPLE_OPTION)],
            venues_used=["Berghain"],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=False,
        )

        app = _make_app()
        with patch(
            "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
        ) as MockFacade:
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 200
        scenarios = response.json()["scenarios"]
        assert len(scenarios) == 1
        assert scenarios[0]["venue"] == "Berghain"
        assert scenarios[0]["tone"] in ("romantic", "intellectual", "chaotic")

    def test_degraded_path_returns_200_with_empty_scenarios(self):
        """Degraded response: 200, scenarios=[], degraded=True."""
        from nikita.onboarding.contracts import BackstoryPreviewResponse

        mock_response = BackstoryPreviewResponse(
            scenarios=[],
            venues_used=[],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=True,
        )

        app = _make_app()
        with patch(
            "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
        ) as MockFacade:
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            client = TestClient(app)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["scenarios"] == []


class TestPreviewBackstoryEndpointValidation:
    """Input validation tests for POST /preview-backstory."""

    def test_missing_city_returns_422(self):
        """city is required — omitting it returns 422."""
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"social_scene": "techno", "darkness_level": 3},
        )
        assert response.status_code == 422

    def test_invalid_social_scene_returns_422(self):
        """social_scene must be a valid Literal."""
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"city": "Berlin", "social_scene": "opera", "darkness_level": 3},
        )
        assert response.status_code == 422

    def test_darkness_level_out_of_range_returns_422(self):
        """darkness_level must be 1-5."""
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"city": "Berlin", "social_scene": "techno", "darkness_level": 10},
        )
        assert response.status_code == 422


class TestPreviewBackstoryRateLimit:
    """Rate limiting tests for POST /preview-backstory (FR-4a.1)."""

    def test_rate_limit_exceeded_returns_429(self):
        """Rate limit exceeded → 429 with Retry-After header."""
        app = _make_app(rate_limit_raises=True)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json=VALID_PREVIEW_BODY,
        )
        assert response.status_code == 429
        # Retry-After header should be present
        assert "retry-after" in response.headers

    def test_rate_limit_response_has_detail(self):
        """429 response body contains detail field."""
        app = _make_app(rate_limit_raises=True)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json=VALID_PREVIEW_BODY,
        )
        assert "detail" in response.json()
