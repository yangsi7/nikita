"""Tests for POST /api/v1/onboarding/preview-backstory endpoint — Spec 213 PR 213-3.

TDD RED phase: tests written BEFORE implementation.
Uses FastAPI TestClient (sync) with mocked facade and rate limiter.

Per .claude/rules/testing.md:
  - Every async def test_* must have at least one assert
  - Patch source module, NOT importer
  - Non-empty fixture required for iterator/worker paths
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
AUTH_HEADER = {"Authorization": "Bearer test-token"}

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


def make_app_with_mocked_auth(user_id: UUID = USER_ID) -> FastAPI:
    """Build a minimal FastAPI app with portal_onboarding router + mocked auth."""
    from nikita.api.routes.portal_onboarding import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    # Override get_current_user_id dep
    from nikita.api.dependencies.auth import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: user_id
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

        with (
            patch(
                "nikita.api.routes.portal_onboarding.PortalOnboardingFacade"
            ) as MockFacade,
            patch(
                "nikita.api.routes.portal_onboarding.get_async_session"
            ) as MockSession,
            patch(
                "nikita.api.routes.portal_onboarding._preview_rate_limit"
            ) as MockRL,
        ):
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            MockRL.return_value = None  # rate limit passes
            MockSession.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            app = make_app_with_mocked_auth()
            client = TestClient(app)

            # Override session dep too
            from nikita.db.database import get_async_session
            from sqlalchemy.ext.asyncio import AsyncSession

            mock_sess = AsyncMock(spec=AsyncSession)
            app.dependency_overrides[get_async_session] = lambda: mock_sess

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

        with (
            patch("nikita.api.routes.portal_onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.portal_onboarding._preview_rate_limit") as MockRL,
        ):
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            MockRL.return_value = None

            app = make_app_with_mocked_auth()
            from nikita.db.database import get_async_session
            from sqlalchemy.ext.asyncio import AsyncSession

            app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)
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
        """Degraded response still 200, scenarios=[], degraded=True."""
        from nikita.onboarding.contracts import BackstoryPreviewResponse

        mock_response = BackstoryPreviewResponse(
            scenarios=[],
            venues_used=[],
            cache_key="berlin|techno|3|unknown|unknown|unknown|unknown",
            degraded=True,
        )

        with (
            patch("nikita.api.routes.portal_onboarding.PortalOnboardingFacade") as MockFacade,
            patch("nikita.api.routes.portal_onboarding._preview_rate_limit") as MockRL,
        ):
            MockFacade.return_value.generate_preview = AsyncMock(return_value=mock_response)
            MockRL.return_value = None

            app = make_app_with_mocked_auth()
            from nikita.db.database import get_async_session
            from sqlalchemy.ext.asyncio import AsyncSession

            app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)
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
        app = make_app_with_mocked_auth()
        from nikita.db.database import get_async_session
        from sqlalchemy.ext.asyncio import AsyncSession

        app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)
        client = TestClient(app)

        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"social_scene": "techno", "darkness_level": 3},
        )
        assert response.status_code == 422

    def test_invalid_social_scene_returns_422(self):
        """social_scene must be a valid Literal."""
        app = make_app_with_mocked_auth()
        from nikita.db.database import get_async_session
        from sqlalchemy.ext.asyncio import AsyncSession

        app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)
        client = TestClient(app)

        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"city": "Berlin", "social_scene": "opera", "darkness_level": 3},
        )
        assert response.status_code == 422

    def test_darkness_level_out_of_range_returns_422(self):
        """darkness_level must be 1-5."""
        app = make_app_with_mocked_auth()
        from nikita.db.database import get_async_session
        from sqlalchemy.ext.asyncio import AsyncSession

        app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)
        client = TestClient(app)

        response = client.post(
            "/api/v1/onboarding/preview-backstory",
            json={"city": "Berlin", "social_scene": "techno", "darkness_level": 10},
        )
        assert response.status_code == 422


class TestPreviewBackstoryRateLimit:
    """Rate limiting tests for POST /preview-backstory (FR-4a.1)."""

    def test_rate_limit_exceeded_returns_429(self):
        """6th call in 1 minute → 429 with Retry-After header."""
        from fastapi import HTTPException

        app = make_app_with_mocked_auth()
        from nikita.db.database import get_async_session
        from sqlalchemy.ext.asyncio import AsyncSession

        app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)

        with patch("nikita.api.routes.portal_onboarding._preview_rate_limit") as MockRL:
            MockRL.side_effect = HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert response.status_code == 429
        assert response.headers.get("retry-after") == "60"

    def test_rate_limit_response_has_detail(self):
        """429 response body contains detail field."""
        from fastapi import HTTPException

        app = make_app_with_mocked_auth()
        from nikita.db.database import get_async_session
        from sqlalchemy.ext.asyncio import AsyncSession

        app.dependency_overrides[get_async_session] = lambda: AsyncMock(spec=AsyncSession)

        with patch("nikita.api.routes.portal_onboarding._preview_rate_limit") as MockRL:
            MockRL.side_effect = HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/onboarding/preview-backstory",
                json=VALID_PREVIEW_BODY,
            )

        assert "detail" in response.json()
