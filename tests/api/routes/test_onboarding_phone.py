"""Tests for phone field in POST /api/v1/onboarding/profile (Spec 212 PR B).

Tests:
- T011: Route-level phone validation and persistence

Patching source module per testing.md rule:
  nikita.db.repositories.user_repository.UserRepository

Non-empty fixtures per testing.md rule (every repo-mock test has
a sibling with non-empty data). No zero-assertion test bodies.

Failing until T015/T016/T017 (implementation) are committed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")

# Use an explicit test-only Swiss phone constant
TEST_PHONE = "+41791234567"

_VALID_BODY = {
    "location_city": "Zurich",
    "social_scene": "techno",
    "drug_tolerance": 3,
    "phone": TEST_PHONE,
}

_BODY_NO_PHONE = {
    "location_city": "Zurich",
    "social_scene": "techno",
    "drug_tolerance": 3,
}


def _make_app_and_client(mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo):
    """Build a test FastAPI app with overridden dependencies."""
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.api.routes.onboarding import (
        get_profile_repo,
        get_user_repo,
        get_vice_repo,
        router,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
    app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
    app.dependency_overrides[get_vice_repo] = lambda: mock_vice_repo

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_user():
    """Non-empty user fixture (onboarding not yet completed)."""
    user = MagicMock()
    user.id = USER_ID
    user.phone = None
    user.onboarding_status = "pending"
    user.telegram_id = 123456789
    return user


@pytest.fixture
def mock_user_repo(mock_user):
    """Mock UserRepository with non-empty user return."""
    repo = AsyncMock()
    repo.get.return_value = mock_user
    repo.update_onboarding_status.return_value = None
    repo.activate_game.return_value = None
    repo.update_phone.return_value = None
    repo.set_pending_handoff.return_value = None
    return repo


@pytest.fixture
def mock_profile_repo():
    """Mock ProfileRepository — no existing profile."""
    repo = AsyncMock()
    repo.get_by_user_id.return_value = None
    repo.create_profile.return_value = MagicMock()
    return repo


@pytest.fixture
def mock_vice_repo():
    """Mock VicePreferenceRepository."""
    repo = AsyncMock()
    return repo


class TestSavePortalProfilePhone:
    """Phone field acceptance tests for POST /api/v1/onboarding/profile."""

    def test_valid_phone_returns_200_and_calls_update_phone(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """Valid phone -> 200 OK and update_phone called with normalized value."""
        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        with patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            response = client.post("/api/v1/onboarding/profile", json=_VALID_BODY)

        assert response.status_code == 200
        mock_user_repo.update_phone.assert_awaited_once_with(USER_ID, TEST_PHONE)

    def test_invalid_phone_returns_422(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """Invalid phone 'abc' -> 422 Unprocessable Entity (Pydantic validation)."""
        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        body = {**_BODY_NO_PHONE, "phone": "abc"}
        response = client.post("/api/v1/onboarding/profile", json=body)

        assert response.status_code == 422
        # update_phone must NOT have been called
        mock_user_repo.update_phone.assert_not_awaited()

    def test_no_phone_field_returns_200_and_does_not_call_update_phone(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """Missing phone field -> 200 OK, update_phone NOT called."""
        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        with patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            response = client.post("/api/v1/onboarding/profile", json=_BODY_NO_PHONE)

        assert response.status_code == 200
        mock_user_repo.update_phone.assert_not_awaited()

    def test_integrity_error_returns_409(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """IntegrityError from update_phone -> 409 with generic detail (no PII)."""
        mock_user_repo.update_phone.side_effect = IntegrityError(
            "duplicate key value", {}, Exception()
        )

        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        response = client.post("/api/v1/onboarding/profile", json=_VALID_BODY)

        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "Phone already registered"

    def test_409_response_body_does_not_leak_pii(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """409 response body must NOT contain UUID or raw phone digits."""
        mock_user_repo.update_phone.side_effect = IntegrityError(
            "duplicate key value", {}, Exception()
        )

        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        response = client.post("/api/v1/onboarding/profile", json=_VALID_BODY)

        assert response.status_code == 409
        body_text = response.text
        # Must not contain the raw phone number
        assert TEST_PHONE not in body_text
        # Must not contain the UUID
        assert str(USER_ID) not in body_text

    def test_phone_correction_on_completed_onboarding_calls_update_phone(
        self, mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
    ):
        """Phone-correction: completed onboarding + new phone -> update_phone still called.

        update_phone is BEFORE the idempotency guard at :712, so even when
        onboarding_status == 'completed', a new phone can be written.
        """
        mock_user.onboarding_status = "completed"
        mock_user.phone = None  # Has no phone yet

        client = _make_app_and_client(
            mock_user, mock_user_repo, mock_profile_repo, mock_vice_repo
        )

        response = client.post("/api/v1/onboarding/profile", json=_VALID_BODY)

        # Idempotency guard returns early, but update_phone should have been called first
        assert response.status_code == 200
        mock_user_repo.update_phone.assert_awaited_once_with(USER_ID, TEST_PHONE)
