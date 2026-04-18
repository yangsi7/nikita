"""Tests for /tasks/generate-daily-arcs endpoint (Spec 215 PR 215-D, US-1).

Spec ACs covered:
- AC-FR2-001: plan persisted with both forms (arc_json + narrative_text)
- AC-FR2-002: idempotent — second run same date upserts in-place (one row)
- AC-FR8-001: game_over users skipped (G1 + FR-008/OD4 also skips 'won')
- FR-014: cost circuit breaker — 503 + Retry-After when daily ceiling reached
- FR-015: error envelope shape — no str(e) leak

Storage contract (contracts.md Contract 1, FROZEN 2026-04-18):
    arc_json={"steps": [step.model_dump() for step in arc.steps]}
    narrative_text=arc.narrative
    model_used=arc.model_used

Field-name divergence is intentional: Pydantic `DailyArc.narrative` maps to
repo kwarg `narrative_text` (DB column also `narrative_text`).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.api.routes.tasks import router
from nikita.db.models.job_execution import JobName
from nikita.heartbeat.planner import ArcStep, DailyArc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create test FastAPI app with tasks router."""
    app = FastAPI()
    app.include_router(router, prefix="/tasks")
    return app


@pytest.fixture
async def client(app):
    """Create async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _mock_settings(**overrides):
    """Mock settings — heartbeat enabled, $50/day default ceiling."""
    defaults = dict(
        task_auth_secret=None,
        telegram_webhook_secret=None,
        heartbeat_engine_enabled=True,
        heartbeat_cost_circuit_breaker_usd_per_day=50.0,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _mock_session_maker(mock_session):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_maker = MagicMock()
    mock_maker.return_value = mock_ctx
    return mock_maker


def _make_user(**overrides):
    """Mock User suitable for the daily-arc handler — active by default."""
    defaults = dict(
        id=uuid4(),
        chapter=2,
        game_status="active",
        telegram_id=12345,
        last_interaction_at=datetime.now(UTC) - timedelta(hours=2),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_mock_arc():
    """Build a deterministic DailyArc fixture for assertion-friendly tests."""
    return DailyArc(
        steps=[
            ArcStep(at="08:00", state="morning routine", action=None),
            ArcStep(at="12:00", state="lunch", action=None),
            ArcStep(at="20:00", state="evening winddown", action=None),
        ],
        narrative="Test narrative for prompt injection.",
        model_used="claude-haiku-4-5-20251001",
    )


# ---------------------------------------------------------------------------
# JobName enum entry — Contract 2
# ---------------------------------------------------------------------------


class TestJobNameEnum:
    """Spec 215 contracts.md Contract 2: GENERATE_DAILY_ARCS enum entry exists."""

    def test_generate_daily_arcs_enum_entry_exists(self):
        """JobName.GENERATE_DAILY_ARCS.value == 'generate_daily_arcs' per contracts.md."""
        assert JobName.GENERATE_DAILY_ARCS.value == "generate_daily_arcs"


# ---------------------------------------------------------------------------
# /tasks/generate-daily-arcs — endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateDailyArcsEndpoint:
    """Spec 215 PR 215-D: /tasks/generate-daily-arcs handler."""

    async def test_auth_required_when_secret_configured(self, client):
        """No Bearer token + secret configured → 401/403."""
        with patch(
            "nikita.api.routes.tasks.get_settings",
            return_value=_mock_settings(task_auth_secret="real_secret"),
        ):
            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code in (401, 403)

    async def test_idempotency_skips_when_recent_execution(self, client):
        """Daily idempotency: 1440-min window per contracts.md Contract 3."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=True)
        mock_job_repo.start_execution = AsyncMock()

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo):

            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "recent_execution"
        mock_job_repo.start_execution.assert_not_called()

        # 1440-min daily window per contracts.md Contract 3
        first_call = mock_job_repo.has_recent_execution.call_args
        assert first_call.kwargs.get("window_minutes") == 1440 or (
            len(first_call.args) >= 2 and first_call.args[1] == 1440
        )
        # Job name = GENERATE_DAILY_ARCS
        assert first_call.args[0] == JobName.GENERATE_DAILY_ARCS.value

    async def test_storage_contract_field_mappings(self, client):
        """Contract 1 storage shape (FROZEN): arc_json={"steps": [...]}, narrative_text, model_used."""
        users = [_make_user()]
        arc = _build_mock_arc()

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_plan_repo = AsyncMock()
        mock_plan_repo.upsert_plan = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch(
                 "nikita.db.repositories.heartbeat_repository.NikitaDailyPlanRepository",
                 return_value=mock_plan_repo,
             ), \
             patch("nikita.heartbeat.planner.generate_daily_arc", AsyncMock(return_value=arc)):

            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code == 200, response.text

        # Verify the upsert was called with EXACTLY the contract field shapes
        mock_plan_repo.upsert_plan.assert_awaited_once()
        kwargs = mock_plan_repo.upsert_plan.call_args.kwargs

        assert kwargs["user_id"] == users[0].id
        assert isinstance(kwargs["plan_date"], date)

        # Storage contract: arc_json wraps steps under {"steps": [...]}
        assert "steps" in kwargs["arc_json"]
        assert isinstance(kwargs["arc_json"]["steps"], list)
        assert len(kwargs["arc_json"]["steps"]) == 3
        # Each step is a serialized ArcStep dict (model_dump)
        first_step = kwargs["arc_json"]["steps"][0]
        assert first_step["at"] == "08:00"
        assert first_step["state"] == "morning routine"

        # narrative_text repo kwarg = arc.narrative Pydantic field (intentional divergence)
        assert kwargs["narrative_text"] == arc.narrative

        # model_used pass-through
        assert kwargs["model_used"] == arc.model_used

    async def test_skips_game_over_and_won_users(self, client):
        """FR-008 + OD4: game_over and won users MUST NOT receive plans.

        Active-user filter centralized in UserRepository.get_active_users_for_heartbeat;
        the handler trusts the repo and never filters in-route.
        """
        # Repo returns ONLY active users (filter happened in repo)
        active_user = _make_user(game_status="active")
        users = [active_user]
        arc = _build_mock_arc()

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_plan_repo = AsyncMock()
        mock_plan_repo.upsert_plan = AsyncMock(return_value=SimpleNamespace(id=uuid4()))

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch(
                 "nikita.db.repositories.heartbeat_repository.NikitaDailyPlanRepository",
                 return_value=mock_plan_repo,
             ), \
             patch("nikita.heartbeat.planner.generate_daily_arc", AsyncMock(return_value=arc)):

            response = await client.post("/tasks/generate-daily-arcs")

        # Active-user filter was used (FR-008/G1 enforced via the repo)
        mock_user_repo.get_active_users_for_heartbeat.assert_awaited_once()
        # Only the one active user got a plan
        assert mock_plan_repo.upsert_plan.await_count == 1

    async def test_cost_circuit_breaker_returns_503_with_retry_after(self, client):
        """FR-014(a): daily-aggregate ceiling reached → 503 + Retry-After (next midnight UTC)."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock()
        # Ceiling reached: simulate cost ledger reporting >= 50.0 USD spent today
        mock_job_repo.get_today_cost_usd = AsyncMock(return_value=99.99)

        with patch(
            "nikita.api.routes.tasks.get_settings",
            return_value=_mock_settings(heartbeat_cost_circuit_breaker_usd_per_day=50.0),
        ), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo):

            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code == 503
        # Retry-After is present and non-empty
        assert "retry-after" in {k.lower() for k in response.headers.keys()}
        # Body should NOT include raw cost ledger numbers (just a graceful-degradation note)
        # Just confirm it's a structured envelope
        # We allow either text seconds or HTTP-date format
        retry_after = response.headers.get("retry-after") or response.headers.get(
            "Retry-After"
        )
        assert retry_after is not None and len(retry_after) > 0

    async def test_feature_flag_off_short_circuits(self, client):
        """FR-020 rollback: heartbeat_engine_enabled=False → no plans generated."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=[])

        mock_plan_repo = AsyncMock()
        mock_plan_repo.upsert_plan = AsyncMock()

        with patch(
            "nikita.api.routes.tasks.get_settings",
            return_value=_mock_settings(heartbeat_engine_enabled=False),
        ), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch(
                 "nikita.db.repositories.heartbeat_repository.NikitaDailyPlanRepository",
                 return_value=mock_plan_repo,
             ):

            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        mock_plan_repo.upsert_plan.assert_not_called()
        mock_user_repo.get_active_users_for_heartbeat.assert_not_called()

    async def test_per_user_error_isolation(self, client):
        """1-of-3 planner errors → others succeed; status remains ok."""
        users = [_make_user() for _ in range(3)]
        arc = _build_mock_arc()

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()
        mock_job_repo.fail_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_plan_repo = AsyncMock()
        mock_plan_repo.upsert_plan = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )

        call_count = 0

        async def _planner_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("LLM transient failure")
            return arc

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch(
                 "nikita.db.repositories.heartbeat_repository.NikitaDailyPlanRepository",
                 return_value=mock_plan_repo,
             ), \
             patch(
                 "nikita.heartbeat.planner.generate_daily_arc",
                 AsyncMock(side_effect=_planner_side_effect),
             ):

            response = await client.post("/tasks/generate-daily-arcs")

        assert response.status_code == 200
        data = response.json()
        assert data["generated"] == 2
        assert data["errors"] == 1
        # Job completed (graceful degradation), not failed
        mock_job_repo.complete_execution.assert_awaited_once()
        mock_job_repo.fail_execution.assert_not_called()

    async def test_error_envelope_redacts_exception_string(self, client):
        """FR-015: catastrophic failure must NOT leak str(exception) into response."""
        secret_token = "PII_SECRET_DAILY_ARCS_xyzzy"

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.fail_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(
            side_effect=RuntimeError(f"db unavailable: {secret_token}")
        )

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):

            response = await client.post("/tasks/generate-daily-arcs")

        data = response.json()
        assert data["status"] == "error"
        assert secret_token not in response.text, (
            "FR-015 violation: raw exception string leaked into response payload"
        )
        mock_job_repo.fail_execution.assert_awaited_once()
