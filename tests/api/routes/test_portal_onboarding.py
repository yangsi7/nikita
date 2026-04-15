"""Tests for portal onboarding routes — Spec 213 PR 213-4.

Covers:
  - GET /pipeline-ready/{user_id}  (D1, US-2, FR-5, FR-2a)
  - PATCH /profile                 (D2, US-6, FR-9)

TDD: RED phase written before implementation.

Per .claude/rules/testing.md:
  - Every test_* has at least one assert
  - Non-empty fixtures for iterator/worker paths
  - Patch source module, NOT importer
  - No zero-assertion shells
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.onboarding.tuning import (
    PIPELINE_GATE_MAX_WAIT_S,
    PIPELINE_GATE_POLL_INTERVAL_S,
)


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
OTHER_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


# ---------------------------------------------------------------------------
# Test app factory helpers
# ---------------------------------------------------------------------------


def _make_app(current_user_id: UUID = USER_ID, mock_user: object = None) -> tuple[FastAPI, object]:
    """Build a FastAPI test app with portal_onboarding router.

    Returns (app, mock_session) so callers can introspect session calls.

    Rate-limit deps (Spec 214 PR 214-D) default-bypassed so handler-logic tests
    can focus on endpoint behaviour; the 429-specific tests below install their
    own overrides.  Mirrors _make_chosen_app pattern.
    """
    from nikita.api.routes.portal_onboarding import router
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.api.middleware.rate_limit import pipeline_ready_rate_limit
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    app.dependency_overrides[get_current_user_id] = lambda: current_user_id

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[pipeline_ready_rate_limit] = lambda: None

    return app, mock_session


def _make_user(
    onboarding_profile: dict | None = None,
    user_id: UUID = USER_ID,
) -> MagicMock:
    """Build a mock User ORM object."""
    user = MagicMock()
    user.id = user_id
    user.onboarding_profile = onboarding_profile if onboarding_profile is not None else {}
    return user


# ---------------------------------------------------------------------------
# GET /pipeline-ready/{user_id}
# ---------------------------------------------------------------------------


class TestPipelineReadyStates:
    """AC-2.x: /pipeline-ready returns correct state from JSONB."""

    @pytest.mark.parametrize(
        "pipeline_state",
        ["pending", "ready", "degraded", "failed"],
    )
    def test_pipeline_ready_states(self, pipeline_state: str):
        """AC-2.1: all four PipelineReadyState values returned correctly."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": pipeline_state})

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == pipeline_state

    def test_pipeline_ready_includes_new_fields(self):
        """AC-2.5: FR-2a fields (venue_research_status, backstory_available) present."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={
            "pipeline_state": "ready",
            "venue_research_status": "complete",
            "backstory_available": True,
        })

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["venue_research_status"] == "complete"
        assert data["backstory_available"] is True
        assert data["state"] == "ready"

    def test_pipeline_ready_defaults(self):
        """Empty JSONB → defaults: state=pending, venue_research_status=pending, backstory_available=False."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={})

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "pending"
        assert data["venue_research_status"] == "pending"
        assert data["backstory_available"] is False

    def test_pipeline_ready_null_jsonb_uses_defaults(self):
        """None onboarding_profile → same defaults as empty dict."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile=None)

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "pending"
        assert data["venue_research_status"] == "pending"
        assert data["backstory_available"] is False

    def test_pipeline_ready_has_checked_at_timestamp(self):
        """Response includes checked_at ISO-8601 timestamp."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert "checked_at" in data
        # Verify it parses as a datetime
        dt = datetime.fromisoformat(data["checked_at"])
        assert isinstance(dt, datetime)


class TestPipelineReadyAccessControl:
    """AC-2.4: cross-user 403; AC-2.6: unknown user 404."""

    def test_cross_user_403_with_correct_body(self):
        """AC-2.4: accessing another user's pipeline-ready → 403 with expected detail."""
        # current_user_id is USER_ID, but requesting OTHER_USER_ID
        app, _ = _make_app(current_user_id=USER_ID)

        client = TestClient(app)
        response = client.get(f"/api/v1/onboarding/pipeline-ready/{OTHER_USER_ID}")

        assert response.status_code == 403
        data = response.json()
        assert data == {"detail": "Not authorized"}

    def test_pipeline_ready_unknown_user_404(self):
        """user_repo.get returns None → 404 Not found."""
        app, _ = _make_app()

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 404
        data = response.json()
        assert data == {"detail": "User not found"}


class TestPipelineReadyMessageField:
    """AC-2.x: message field present on degraded/failed, absent on others."""

    @pytest.mark.parametrize("state", ["degraded", "failed"])
    def test_message_present_on_degraded_failed(self, state: str):
        """degraded/failed states include a message string."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": state})

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] is not None
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    @pytest.mark.parametrize("state", ["pending", "ready"])
    def test_message_absent_on_pending_ready(self, state: str):
        """pending/ready states: message is None."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": state})

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] is None


# ---------------------------------------------------------------------------
# PATCH /profile
# ---------------------------------------------------------------------------


VALID_PATCH_BODY = {
    "location_city": "Berlin",
    "social_scene": "techno",
    "drug_tolerance": 3,
}


def _make_patch_app(
    current_user_id: UUID = USER_ID,
    pipeline_state: str | None = None,
) -> tuple[FastAPI, MagicMock]:
    """Build app for PATCH /profile tests. Returns (app, mock_user_repo)."""
    from nikita.api.routes.portal_onboarding import router
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    app.dependency_overrides[get_current_user_id] = lambda: current_user_id

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    app.dependency_overrides[get_async_session] = _session_override

    return app, mock_session


class TestPatchProfileMerge:
    """AC-6.x: PATCH /profile JSONB merge semantics."""

    def test_patch_preserves_wizard_step(self):
        """AC-6.1: update_onboarding_profile_key called per-field; other keys preserved."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={
            "pipeline_state": "ready",
            "wizard_step": 5,
        })

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json={"wizard_step": 7},
            )

        assert response.status_code == 200
        # update_onboarding_profile_key called with "wizard_step"
        repo_inst.update_onboarding_profile_key.assert_awaited()
        calls = [c[0] for c in repo_inst.update_onboarding_profile_key.await_args_list]
        keys_written = [c[1] for c in calls]  # second positional arg is the key
        assert "wizard_step" in keys_written

    def test_patch_merges_jsonb(self):
        """AC-6.2: update_onboarding_profile_key called for each field in body."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        # 3 fields in VALID_PATCH_BODY → 3 update calls
        assert repo_inst.update_onboarding_profile_key.await_count == len(VALID_PATCH_BODY)

    def test_patch_returns_null_for_unset_fields(self):
        """AC-6.3: response chosen_option is always None from this spec."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["chosen_option"] is None
        assert data["backstory_options"] == []


class TestPatchProfileHandoffTrigger:
    """FR-14: PATCH /profile triggers handoff on missing/failed pipeline_state."""

    def test_patch_no_retrigger_when_pipeline_ready(self):
        """pipeline_state='ready' → _trigger_portal_handoff NOT scheduled."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch(
                "nikita.api.routes.onboarding._trigger_portal_handoff"
            ) as mock_trigger,
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        # Background task not added because pipeline is ready
        mock_trigger.assert_not_called()

    def test_patch_retriggers_when_pipeline_failed(self):
        """pipeline_state='failed' → _trigger_portal_handoff is scheduled via background_tasks."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "failed"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch(
                "nikita.api.routes.onboarding._trigger_portal_handoff"
            ) as mock_trigger,
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        # Background task was added — mock_trigger is the function itself;
        # with TestClient (sync), BackgroundTasks.add_task runs immediately.
        # FR-14 contract: kwargs MUST be only user_id + drug_tolerance (no session/repo).
        mock_trigger.assert_called_once_with(
            user_id=USER_ID, drug_tolerance=VALID_PATCH_BODY["drug_tolerance"]
        )

    def test_patch_retriggers_when_pipeline_missing(self):
        """pipeline_state absent from JSONB → treated as missing → handoff scheduled."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={})  # no pipeline_state key

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch(
                "nikita.api.routes.onboarding._trigger_portal_handoff"
            ) as mock_trigger,
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        mock_trigger.assert_called_once_with(
            user_id=USER_ID, drug_tolerance=VALID_PATCH_BODY["drug_tolerance"]
        )

    def test_patch_no_retrigger_when_pipeline_degraded(self):
        """pipeline_state='degraded' → handoff NOT re-scheduled (spec FR-9)."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "degraded"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch(
                "nikita.api.routes.onboarding._trigger_portal_handoff"
            ) as mock_trigger,
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        mock_trigger.assert_not_called()

    def test_patch_no_retrigger_when_pipeline_pending(self):
        """pipeline_state='pending' → handoff NOT re-scheduled (concurrent bootstrap already in-flight)."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "pending"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch(
                "nikita.api.routes.onboarding._trigger_portal_handoff"
            ) as mock_trigger,
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        mock_trigger.assert_not_called()


class TestPatchProfileResponse:
    """PATCH /profile response shape (OnboardingV2ProfileResponse)."""

    def test_patch_response_includes_poll_endpoint(self):
        """Response contains poll_endpoint pointing to pipeline-ready."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert "poll_endpoint" in data
        assert str(USER_ID) in data["poll_endpoint"]

    def test_patch_response_includes_poll_intervals(self):
        """Response includes poll_interval_seconds and poll_max_wait_seconds."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert "poll_interval_seconds" in data
        assert "poll_max_wait_seconds" in data
        assert data["poll_interval_seconds"] == PIPELINE_GATE_POLL_INTERVAL_S
        assert data["poll_max_wait_seconds"] == PIPELINE_GATE_MAX_WAIT_S

    def test_patch_response_pipeline_state_from_jsonb(self):
        """pipeline_state in response reflects actual stored value."""
        app, _ = _make_patch_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "pending"})

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.api.routes.onboarding._trigger_portal_handoff"),
        ):
            repo_inst = MockRepo.return_value
            repo_inst.update_onboarding_profile_key = AsyncMock()
            repo_inst.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.patch(
                "/api/v1/onboarding/profile",
                json=VALID_PATCH_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_state"] == "pending"


# ---------------------------------------------------------------------------
# Spec 214 PR 214-D: PUT /profile/chosen-option  (T011)
# ---------------------------------------------------------------------------


CACHE_KEY = "berlin|techno|3|tech|unknown|twenties|tech"
OPTION_ID_A = "aabbccdd1122"


def _make_chosen_option_dict() -> dict:
    """Minimal BackstoryOption dict suitable for chosen_option assertions."""
    return {
        "id": OPTION_ID_A,
        "venue": "Tresor",
        "context": "Dark basement, peak hour.",
        "the_moment": "She handed back my lighter.",
        "unresolved_hook": "She knew my name before I told her.",
        "tone": "chaotic",
    }


def _make_chosen_app(
    current_user_id: UUID = USER_ID,
    bypass_rate_limit: bool = True,
) -> tuple[FastAPI, object]:
    """Build test app with portal_onboarding router and optional rate-limit bypass.

    Rate limit is bypassed by default (returns None) so tests can focus on
    endpoint logic.  Set bypass_rate_limit=False to test 429 behaviour.
    """
    from nikita.api.routes.portal_onboarding import router
    from nikita.api.dependencies.auth import get_current_user_id
    from nikita.db.database import get_async_session
    from nikita.api.middleware.rate_limit import choice_rate_limit

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    app.dependency_overrides[get_current_user_id] = lambda: current_user_id

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    app.dependency_overrides[get_async_session] = _session_override

    if bypass_rate_limit:
        app.dependency_overrides[choice_rate_limit] = lambda: None

    return app, mock_session


VALID_CHOICE_BODY = {
    "chosen_option_id": OPTION_ID_A,
    "cache_key": CACHE_KEY,
}


class TestPutChosenOptionAccessControl:
    """AC-10.1 / AC-10.3: access control and cache_key mismatch."""

    def test_put_chosen_option_cross_user_returns_403(self):
        """Facade raises 403 on cache_key mismatch (cross-user or stale profile)."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        app, _ = _make_chosen_app()

        with patch.object(
            PortalOnboardingFacade,
            "set_chosen_option",
            side_effect=__import__("fastapi").HTTPException(
                status_code=403, detail="Clearance mismatch. Start over."
            ),
        ):
            client = TestClient(app)
            response = client.put(
                "/api/v1/onboarding/profile/chosen-option",
                json=VALID_CHOICE_BODY,
            )

        assert response.status_code == 403
        data = response.json()
        assert isinstance(data.get("detail"), str)
        # Must NOT leak PII
        detail = data["detail"].lower()
        assert "name" not in detail
        assert "age" not in detail
        assert "occupation" not in detail
        assert "phone" not in detail

    def test_put_chosen_option_stale_cache_key_returns_404(self):
        """Facade raises 404 when cache row not found for valid cache_key."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        app, _ = _make_chosen_app()

        with patch.object(
            PortalOnboardingFacade,
            "set_chosen_option",
            side_effect=__import__("fastapi").HTTPException(
                status_code=404, detail="Backstory not found."
            ),
        ):
            client = TestClient(app)
            response = client.put(
                "/api/v1/onboarding/profile/chosen-option",
                json=VALID_CHOICE_BODY,
            )

        assert response.status_code == 404


class TestPutChosenOptionValidation:
    """AC-10.2: unknown chosen_option_id → 409."""

    def test_put_chosen_option_unknown_option_id_returns_409(self):
        """chosen_option_id not in cache scenarios → 409 Conflict."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        app, _ = _make_chosen_app()

        with patch.object(
            PortalOnboardingFacade,
            "set_chosen_option",
            side_effect=__import__("fastapi").HTTPException(
                status_code=409,
                detail="That scenario doesn't exist. Pick one she actually generated for you.",
            ),
        ):
            client = TestClient(app)
            response = client.put(
                "/api/v1/onboarding/profile/chosen-option",
                json=VALID_CHOICE_BODY,
            )

        assert response.status_code == 409
        data = response.json()
        assert isinstance(data.get("detail"), str)


class TestPutChosenOptionHappyPath:
    """AC-10.5: success returns OnboardingV2ProfileResponse with chosen_option."""

    def test_put_chosen_option_happy_path_writes_snapshot(self):
        """Happy path: 200 with chosen_option populated in response."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.contracts import BackstoryOption

        app, _ = _make_chosen_app()
        option = BackstoryOption(**_make_chosen_option_dict())
        mock_user = _make_user(onboarding_profile={"pipeline_state": "ready"})

        with (
            patch.object(
                PortalOnboardingFacade,
                "set_chosen_option",
                return_value=option,
            ),
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.put(
                "/api/v1/onboarding/profile/chosen-option",
                json=VALID_CHOICE_BODY,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["chosen_option"] is not None
        assert data["chosen_option"]["id"] == OPTION_ID_A
        assert data["chosen_option"]["venue"] == "Tresor"
        assert data["chosen_option"]["tone"] == "chaotic"
        assert data["backstory_options"] == []


class TestPutChosenOptionNoPiiInErrorBodies:
    """AC-10.6: no PII in any error response body."""

    def test_put_chosen_option_response_has_no_pii_substrings(self):
        """Error bodies (403/404/409) must not contain name/age/occupation/phone/city."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        pii_payloads = [
            ("name", "Alice"),
            ("age", "25"),
            ("occupation", "banker"),
            ("phone", "+49123456789"),
            ("city", "Berlin"),
        ]
        app, _ = _make_chosen_app()

        for pii_field, pii_value in pii_payloads:
            with patch.object(
                PortalOnboardingFacade,
                "set_chosen_option",
                side_effect=__import__("fastapi").HTTPException(
                    status_code=403, detail="Clearance mismatch. Start over."
                ),
            ):
                client = TestClient(app)
                response = client.put(
                    "/api/v1/onboarding/profile/chosen-option",
                    json=VALID_CHOICE_BODY,
                )

            response_text = response.text.lower()
            assert pii_value.lower() not in response_text, (
                f"PII field '{pii_field}' value '{pii_value}' leaked into response: {response.text}"
            )


class TestPutChosenOptionRateLimit:
    """AC-10.7 / AC-10.9: 429 includes Retry-After: 60 header."""

    def test_put_chosen_option_rate_limit_429_includes_retry_after(self):
        """Rate limit exceeded → 429 with Retry-After: 60 header."""
        from nikita.api.routes.portal_onboarding import router
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import choice_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/onboarding")
        app.dependency_overrides[get_current_user_id] = lambda: USER_ID

        mock_session = AsyncMock(spec=AsyncSession)

        async def _session_override():
            return mock_session

        app.dependency_overrides[get_async_session] = _session_override

        # Override rate limit to raise 429 with Retry-After header
        async def _rate_limit_429():
            raise __import__("fastapi").HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        app.dependency_overrides[choice_rate_limit] = _rate_limit_429

        client = TestClient(app)
        response = client.put(
            "/api/v1/onboarding/profile/chosen-option",
            json=VALID_CHOICE_BODY,
        )

        assert response.status_code == 429
        assert response.headers.get("retry-after") == "60"


# ---------------------------------------------------------------------------
# Spec 214 PR 214-D: wizard_step passthrough + pipeline-ready rate limit (T011)
# ---------------------------------------------------------------------------


class TestPipelineReadyWizardStep:
    """AC-10.7: GET /pipeline-ready includes wizard_step from JSONB."""

    def test_pipeline_ready_wizard_step_passthrough(self):
        """wizard_step present in onboarding_profile → included in response."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={
            "pipeline_state": "ready",
            "wizard_step": 7,
        })

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["wizard_step"] == 7

    def test_pipeline_ready_wizard_step_none_when_absent(self):
        """wizard_step absent from JSONB → None in response (not missing)."""
        app, _ = _make_app()
        mock_user = _make_user(onboarding_profile={"pipeline_state": "pending"})
        # No wizard_step key in profile

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=mock_user)
            client = TestClient(app)
            response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 200
        data = response.json()
        # Field must be present in response (optional, default None)
        assert "wizard_step" in data
        assert data["wizard_step"] is None


class TestPipelineReadyRateLimit:
    """AC-5.6: GET /pipeline-ready rate-limited (429 with Retry-After: 60)."""

    def test_pipeline_ready_rate_limit_429_retry_after_60(self):
        """Rate limit dependency raises 429 with Retry-After: 60 on pipeline-ready."""
        from nikita.api.routes.portal_onboarding import router
        from nikita.api.dependencies.auth import get_current_user_id
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import pipeline_ready_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/onboarding")
        app.dependency_overrides[get_current_user_id] = lambda: USER_ID

        mock_session = AsyncMock(spec=AsyncSession)

        async def _session_override():
            return mock_session

        app.dependency_overrides[get_async_session] = _session_override

        # Override pipeline_ready_rate_limit to raise 429
        async def _rate_limit_429():
            raise __import__("fastapi").HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        app.dependency_overrides[pipeline_ready_rate_limit] = _rate_limit_429

        client = TestClient(app)
        response = client.get(f"/api/v1/onboarding/pipeline-ready/{USER_ID}")

        assert response.status_code == 429
        assert response.headers.get("retry-after") == "60"
