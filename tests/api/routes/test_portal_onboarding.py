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
    """
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
