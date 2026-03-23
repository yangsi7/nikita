"""Tests for POST /api/v1/onboarding/profile endpoint (Spec 081).

Tests verify the portal profile save endpoint that replaces
Telegram-based profile collection.

AC Coverage: AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5 (Spec 081)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


# We'll import the router after patching deps
USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class TestOnboardingProfileEndpoint:
    """Tests for POST /onboarding/profile."""

    @pytest.mark.asyncio
    async def test_profile_request_model_accepts_valid_input(self):
        """AC-4.1: PortalProfileRequest accepts valid data and preserves field values."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        request = PortalProfileRequest(
            location_city="Zurich",
            social_scene="techno",
            drug_tolerance=3,
        )
        assert request.location_city == "Zurich"
        assert request.social_scene == "techno"
        assert request.drug_tolerance == 3

    @pytest.mark.asyncio
    async def test_profile_request_validates_drug_tolerance_range(self):
        """AC-4.2: drug_tolerance must be 1-5."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        with pytest.raises(ValidationError):
            PortalProfileRequest(
                location_city="Zurich",
                social_scene="techno",
                drug_tolerance=6,  # Invalid — max is 5
            )

    @pytest.mark.asyncio
    async def test_profile_request_validates_social_scene_enum(self):
        """AC-4.3: social_scene must be one of the 5 valid values."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        with pytest.raises(ValidationError):
            PortalProfileRequest(
                location_city="Zurich",
                social_scene="invalid_scene",
                drug_tolerance=3,
            )

    @pytest.mark.asyncio
    async def test_profile_request_requires_location_city(self):
        """AC-4.4: location_city is required (min 2 chars)."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        with pytest.raises(ValidationError):
            PortalProfileRequest(
                location_city="",  # Empty — invalid
                social_scene="techno",
                drug_tolerance=3,
            )

    @pytest.mark.asyncio
    async def test_portal_profile_request_model_exists(self):
        """AC-4.1: PortalProfileRequest Pydantic model exists with expected fields."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        req = PortalProfileRequest(
            location_city="Berlin",
            social_scene="art",
            drug_tolerance=4,
            life_stage="creative",
            interest="photography",
        )
        assert req.location_city == "Berlin"
        assert req.life_stage == "creative"
        assert req.interest == "photography"

    @pytest.mark.asyncio
    async def test_save_portal_profile_function_exists(self):
        """AC-4.1: save_portal_profile endpoint function exists."""
        from nikita.api.routes.onboarding import save_portal_profile

        assert callable(save_portal_profile)


class TestOnboardingProfileIntegration:
    """TestClient integration tests for POST /onboarding/profile."""

    @pytest.fixture
    def mock_profile_repo(self):
        repo = AsyncMock()
        repo.get_by_user_id.return_value = None  # No existing profile
        repo.create_profile.return_value = MagicMock(id=USER_ID)
        return repo

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        repo.update_onboarding_status.return_value = None
        return repo

    @pytest.fixture
    def client(self, mock_profile_repo, mock_user_repo):
        """Create TestClient with dependency overrides for the profile endpoint."""
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.api.routes.onboarding import (
            get_profile_repo,
            get_user_repo,
            router,
        )

        app = FastAPI()
        app.include_router(router, prefix="/onboarding")

        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
        app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        return TestClient(app)

    def test_profile_endpoint_returns_200_on_valid_post(
        self, client, mock_profile_repo, mock_user_repo
    ):
        """Full endpoint test: valid profile data returns 200 + correct body."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data

        # Verify mocks were called
        mock_profile_repo.create_profile.assert_awaited_once()
        mock_user_repo.update_onboarding_status.assert_awaited_once()

    def test_profile_endpoint_returns_422_on_missing_fields(self, client):
        """Missing required fields return 422 validation error."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            # missing social_scene and drug_tolerance
        })
        assert response.status_code == 422

    def test_profile_endpoint_returns_422_on_invalid_drug_tolerance(self, client):
        """drug_tolerance=6 (out of 1-5 range) returns 422."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 6,
        })
        assert response.status_code == 422

    def test_profile_endpoint_returns_422_on_invalid_social_scene(self, client):
        """Invalid social_scene value returns 422."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "invalid",
            "drug_tolerance": 3,
        })
        assert response.status_code == 422
