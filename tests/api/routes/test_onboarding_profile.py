"""Tests for POST /api/v1/onboarding/profile endpoint (Spec 081, GH #183).

Tests verify the portal profile save endpoint that replaces
Telegram-based profile collection.

AC Coverage: AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5 (Spec 081)
GH #183: Game activation (game_status, relationship_score, vices, handoff)
"""

import pytest
from decimal import Decimal
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
        repo.activate_game.return_value = None
        repo.get.return_value = MagicMock(telegram_id=None, phone=None, onboarding_profile=None)
        return repo

    @pytest.fixture
    def mock_vice_repo(self):
        repo = AsyncMock()
        repo.discover.return_value = MagicMock()
        return repo

    @pytest.fixture
    def client(self, mock_profile_repo, mock_user_repo, mock_vice_repo):
        """Create TestClient with dependency overrides for the profile endpoint."""
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.api.routes.onboarding import (
            get_profile_repo,
            get_user_repo,
            get_vice_repo,
            router,
        )

        app = FastAPI()
        app.include_router(router, prefix="/onboarding")

        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
        app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
        app.dependency_overrides[get_vice_repo] = lambda: mock_vice_repo

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
        mock_user_repo.activate_game.assert_awaited_once()
        # Bug 2 fix (PR #273): JSONB persistence — save_portal_profile MUST write
        # all profile fields to users.onboarding_profile so handoff can read full profile,
        # not just darkness_level. Per .claude/rules/testing.md: no zero-assertion shells.
        mock_user_repo.update_onboarding_profile.assert_awaited_once()
        call_args = mock_user_repo.update_onboarding_profile.call_args
        profile_payload = call_args.kwargs.get("profile") or (call_args.args[1] if len(call_args.args) > 1 else None)
        assert profile_payload is not None, "update_onboarding_profile must receive a profile payload"
        assert profile_payload.get("location_city") == "Zurich"
        assert profile_payload.get("social_scene") == "techno"
        assert profile_payload.get("darkness_level") == 3

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


class TestOnboardingGameActivation:
    """GH #183: Game activation after portal profile save.

    Verifies that save_portal_profile activates game state,
    seeds vices, and triggers handoff.
    """

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
        repo.activate_game.return_value = None
        return repo

    @pytest.fixture
    def mock_vice_repo(self):
        repo = AsyncMock()
        repo.discover.return_value = MagicMock()
        return repo

    @pytest.fixture
    def client(self, mock_profile_repo, mock_user_repo, mock_vice_repo):
        """Create TestClient with dependency overrides."""
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.api.routes.onboarding import (
            get_profile_repo,
            get_user_repo,
            get_vice_repo,
            router,
        )

        app = FastAPI()
        app.include_router(router, prefix="/onboarding")

        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
        app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
        app.dependency_overrides[get_vice_repo] = lambda: mock_vice_repo

        return TestClient(app)

    def test_game_activated_after_profile_save(
        self, client, mock_user_repo
    ):
        """GH #183: game_status set to 'active' after portal profile save."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        assert response.status_code == 200

        mock_user_repo.activate_game.assert_awaited_once_with(USER_ID)

    def test_vices_seeded_after_profile_save(
        self, client, mock_vice_repo
    ):
        """GH #183: Vice preferences seeded from drug_tolerance."""
        response = client.post("/onboarding/profile", json={
            "location_city": "Berlin",
            "social_scene": "art",
            "drug_tolerance": 4,
        })
        assert response.status_code == 200

        # drug_tolerance=4 maps to TIER_HIGH which has 5 categories
        assert mock_vice_repo.discover.await_count > 0

    @patch("nikita.api.routes.onboarding.HandoffManager")
    @patch("nikita.api.routes.onboarding.get_session_maker")
    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_handoff_triggered_in_background(
        self, mock_user_repo_cls, mock_get_session_maker, mock_handoff_cls, client, mock_user_repo
    ):
        """GH #183: HandoffManager.execute_handoff called as background task.

        FR-14 (PR 213-4): _trigger_portal_handoff now opens its own session via
        get_session_maker() instead of accepting user_repo. We must mock
        get_session_maker + UserRepository so the background task can look up
        the user without a live database connection.
        """
        mock_handoff = AsyncMock()
        mock_handoff.execute_handoff.return_value = MagicMock(success=True, error=None)
        mock_handoff_cls.return_value = mock_handoff

        # Build a mock session context for the background task's fresh session
        mock_fresh_session = AsyncMock()
        mock_fresh_session.commit = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_fresh_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock()
        mock_maker.return_value = mock_ctx
        mock_get_session_maker.return_value = mock_maker

        # Mock UserRepository returned from the fresh session
        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        mock_user.phone = None
        mock_user.onboarding_profile = None
        mock_repo_inst = AsyncMock()
        mock_repo_inst.get.return_value = mock_user
        mock_repo_inst.set_pending_handoff = AsyncMock()
        mock_repo_inst.update_onboarding_profile_key = AsyncMock()
        mock_user_repo_cls.return_value = mock_repo_inst

        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        assert response.status_code == 200

        # Background task runs synchronously in TestClient
        mock_handoff.execute_handoff.assert_awaited_once()
        call_kwargs = mock_handoff.execute_handoff.call_args
        assert call_kwargs[1]["user_id"] == USER_ID
        assert call_kwargs[1]["telegram_id"] == 12345

    def test_idempotent_profile_skips_activation(
        self, client, mock_profile_repo, mock_user_repo
    ):
        """GH #183: Existing profile returns early without re-activating game."""
        mock_profile_repo.get_by_user_id.return_value = MagicMock()  # Profile exists

        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        assert response.status_code == 200
        assert response.json()["message"] == "Profile already exists"

        # Game activation should NOT happen
        mock_user_repo.activate_game.assert_not_awaited()

    def test_idempotent_completed_status_skips_profile_check(
        self, client, mock_profile_repo, mock_user_repo
    ):
        """REL-004: Completed onboarding_status returns early without hitting profile repo."""
        mock_user_repo.get.return_value = MagicMock(onboarding_status="completed")

        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        assert response.status_code == 200
        assert response.json()["message"] == "Profile already exists"

        # Should NOT check profile or activate game
        mock_profile_repo.get_by_user_id.assert_not_awaited()
        mock_user_repo.activate_game.assert_not_awaited()

    def test_vice_seeding_failure_does_not_break_endpoint(
        self, client, mock_vice_repo, mock_user_repo
    ):
        """GH #183: Vice seeding failure is logged but does not fail the request."""
        mock_vice_repo.discover.side_effect = Exception("DB error")

        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        # Should still succeed despite vice seeding failure
        assert response.status_code == 200
        mock_user_repo.activate_game.assert_awaited_once()

    @patch("nikita.api.routes.onboarding.HandoffManager")
    def test_handoff_failure_does_not_break_endpoint(
        self, mock_handoff_cls, client, mock_user_repo
    ):
        """GH #183: Handoff failure in background does not affect response."""
        mock_handoff = AsyncMock()
        mock_handoff.execute_handoff.side_effect = Exception("Telegram down")
        mock_handoff_cls.return_value = mock_handoff

        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        mock_user.phone = None
        mock_user.onboarding_profile = None
        mock_user_repo.get.return_value = mock_user

        response = client.post("/onboarding/profile", json={
            "location_city": "Zurich",
            "social_scene": "techno",
            "drug_tolerance": 3,
        })
        # Response should succeed even if handoff fails
        assert response.status_code == 200


class TestPortalProfileCityValidation:
    """PR-2 / GH #198: stricter city validation in PortalProfileRequest."""

    @pytest.mark.parametrize(
        "city",
        ["", "   ", "hey", "HEY", "test", "12345", "x" * 101, "a"],
    )
    def test_invalid_city_raises_validation_error(self, city: str) -> None:
        """Each flagged value must be rejected by Pydantic."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        with pytest.raises(ValidationError):
            PortalProfileRequest(
                location_city=city,
                social_scene="techno",
                drug_tolerance=3,
            )

    def test_invalid_city_returns_422_via_api(self) -> None:
        """POST with a blocklisted city returns HTTP 422."""
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.api.routes.onboarding import (
            get_profile_repo,
            get_user_repo,
            get_vice_repo,
            router,
        )

        app = FastAPI()
        app.include_router(router, prefix="/onboarding")
        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
        app.dependency_overrides[get_profile_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_user_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_vice_repo] = lambda: AsyncMock()
        client = TestClient(app)

        response = client.post(
            "/onboarding/profile",
            json={
                "location_city": "hey",
                "social_scene": "techno",
                "drug_tolerance": 3,
            },
        )
        assert response.status_code == 422

    def test_valid_city_accepted(self) -> None:
        """Legitimate city names still pass validation."""
        from nikita.api.routes.onboarding import PortalProfileRequest

        req = PortalProfileRequest(
            location_city="São Paulo",
            social_scene="techno",
            drug_tolerance=3,
        )
        assert req.location_city == "São Paulo"


class TestPortalProfilePendingHandoff:
    """PR-2 / GH #198-linked: pending_handoff flag persistence."""

    @pytest.fixture
    def mock_profile_repo(self):
        repo = AsyncMock()
        repo.get_by_user_id.return_value = None
        repo.create_profile.return_value = MagicMock(id=USER_ID)
        return repo

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        repo.update_onboarding_status.return_value = None
        repo.activate_game.return_value = None
        repo.set_pending_handoff.return_value = None
        # Default: user is in pre-onboarding state and has NO telegram_id
        repo.get.return_value = MagicMock(
            telegram_id=None,
            phone=None,
            onboarding_profile=None,
            onboarding_status="pending",
        )
        return repo

    @pytest.fixture
    def mock_vice_repo(self):
        repo = AsyncMock()
        repo.discover.return_value = MagicMock()
        return repo

    @pytest.fixture
    def client(self, mock_profile_repo, mock_user_repo, mock_vice_repo):
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.api.routes.onboarding import (
            get_profile_repo,
            get_user_repo,
            get_vice_repo,
            router,
        )

        app = FastAPI()
        app.include_router(router, prefix="/onboarding")
        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
        app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
        app.dependency_overrides[get_vice_repo] = lambda: mock_vice_repo
        return TestClient(app)

    @staticmethod
    def _build_session_maker(mock_repo_inst: AsyncMock) -> MagicMock:
        """Return a mock session_maker that yields a session backed by mock_repo_inst.

        FR-14 (PR 213-4): _trigger_portal_handoff no longer accepts user_repo.
        It calls get_session_maker() internally.  We mock the full session-maker
        stack so background tasks can use the supplied mock_repo_inst without a
        live database.
        """
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock()
        mock_maker.return_value = mock_ctx
        return mock_maker

    @patch("nikita.api.routes.onboarding.get_session_maker")
    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_sets_pending_handoff_when_telegram_id_missing(
        self, mock_user_repo_cls, mock_get_session_maker, client, mock_user_repo
    ) -> None:
        """When user.telegram_id is None, the deferred-handoff flag is set True.

        FR-14: background task opens its own session — we patch get_session_maker
        and UserRepository so the task sees a user with no telegram_id.
        """
        # Build repo for the background task's fresh session (user with no telegram_id)
        task_repo = AsyncMock()
        task_repo.get.return_value = MagicMock(
            telegram_id=None, phone=None, onboarding_profile=None,
        )
        task_repo.set_pending_handoff = AsyncMock(return_value=None)
        task_repo.update_onboarding_profile_key = AsyncMock()
        mock_user_repo_cls.return_value = task_repo

        mock_get_session_maker.return_value = self._build_session_maker(task_repo)

        response = client.post(
            "/onboarding/profile",
            json={
                "location_city": "Zurich",
                "social_scene": "techno",
                "drug_tolerance": 3,
            },
        )
        assert response.status_code == 200
        task_repo.set_pending_handoff.assert_awaited_with(USER_ID, True)

    @patch("nikita.api.routes.onboarding.HandoffManager")
    @patch("nikita.api.routes.onboarding.get_session_maker")
    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_does_not_set_pending_handoff_when_telegram_id_present(
        self, mock_user_repo_cls, mock_get_session_maker, mock_handoff_cls,
        client, mock_user_repo
    ) -> None:
        """When telegram_id exists, handoff fires immediately — no flag.

        FR-14: background task uses its own session; we mock both the session
        maker and UserRepository so the task sees a user with telegram_id.
        """
        task_repo = AsyncMock()
        task_repo.get.return_value = MagicMock(
            telegram_id=12345, phone=None, onboarding_profile=None,
        )
        task_repo.set_pending_handoff = AsyncMock()
        task_repo.update_onboarding_profile_key = AsyncMock()
        mock_user_repo_cls.return_value = task_repo

        mock_get_session_maker.return_value = self._build_session_maker(task_repo)

        mock_handoff = AsyncMock()
        mock_handoff.execute_handoff.return_value = MagicMock(success=True, error=None)
        mock_handoff_cls.return_value = mock_handoff

        response = client.post(
            "/onboarding/profile",
            json={
                "location_city": "Zurich",
                "social_scene": "techno",
                "drug_tolerance": 3,
            },
        )
        assert response.status_code == 200
        task_repo.set_pending_handoff.assert_not_awaited()
        mock_handoff.execute_handoff.assert_awaited_once()

    @patch("nikita.api.routes.onboarding.get_session_maker")
    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_profile_save_survives_pending_handoff_flag_failure(
        self, mock_user_repo_cls, mock_get_session_maker, client, mock_user_repo
    ) -> None:
        """If set_pending_handoff raises, the profile save must still return 200.

        The inner try/except in ``_trigger_portal_handoff`` is the safety
        net for a transient DB blip during the deferred-handoff bookkeeping.
        Even if the flag never gets persisted, the profile must save and the
        user must not see an HTTP error — they can always retry linking.

        FR-14: background task opens its own session; we provide a task_repo whose
        set_pending_handoff raises so we can verify the 200 still returns.
        """
        # telegram_id=None so we hit the deferred-handoff branch
        task_repo = AsyncMock()
        task_repo.get.return_value = MagicMock(
            telegram_id=None, phone=None, onboarding_profile=None,
        )
        task_repo.set_pending_handoff = AsyncMock(side_effect=RuntimeError("db blip"))
        task_repo.update_onboarding_profile_key = AsyncMock()
        mock_user_repo_cls.return_value = task_repo

        mock_get_session_maker.return_value = self._build_session_maker(task_repo)

        response = client.post(
            "/onboarding/profile",
            json={
                "location_city": "Zurich",
                "social_scene": "techno",
                "drug_tolerance": 3,
            },
        )
        # Response is 200 even though the background task's flag-set failed
        assert response.status_code == 200
        task_repo.set_pending_handoff.assert_awaited_with(USER_ID, True)
