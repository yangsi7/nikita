"""Tests for /tasks/refresh-voice-prompts endpoint (Spec 209 PR 209-5).

AC-FR005-001: Stale prompts (>6h) regenerated via pipeline
AC-FR005-002: Fresh prompts (<6h) not regenerated
AC-FR005-003: Idempotent — no duplicate work on double-run
AC-FR005-004: Auth required — rejects without Bearer token
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.api.routes.tasks import router
from nikita.db.models.job_execution import JobName


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
    """Create mock settings allowing task auth bypass."""
    defaults = dict(
        task_auth_secret=None,
        telegram_webhook_secret=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _mock_session_maker(mock_session):
    """Create a mock session maker that returns async context managers.

    get_session_maker() -> session_maker (callable)
    session_maker() -> async context manager yielding mock_session
    """
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_maker = MagicMock()
    mock_maker.return_value = mock_ctx
    return mock_maker


def _make_user(**overrides):
    """Create mock User for refresh tests."""
    defaults = dict(
        id=uuid4(),
        chapter=2,
        game_status="active",
        cached_voice_prompt_at=datetime.now(UTC) - timedelta(hours=8),
        metrics=MagicMock(),
        vice_preferences=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
class TestVoicePromptRefresh:
    """Spec 209 FR-005: Background voice prompt refresh."""

    async def test_stale_users_refreshed(self, client):
        """AC-FR005-001: Stale prompts (>6h) regenerated."""
        stale_users = [_make_user() for _ in range(3)]

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
        mock_user_repo.count_users_with_stale_voice_prompts = AsyncMock(return_value=3)
        mock_user_repo.get_users_with_stale_voice_prompts = AsyncMock(
            return_value=stale_users
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process = AsyncMock()

        mock_settings = _mock_settings()

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.pipeline.orchestrator.PipelineOrchestrator", return_value=mock_orchestrator):

            response = await client.post("/tasks/refresh-voice-prompts")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["refreshed"] == 3
        assert data["errors"] == 0
        assert data["deferred"] == 0
        # Verify pipeline was actually invoked for each user
        assert mock_orchestrator.process.await_count == 3
        for call_args in mock_orchestrator.process.call_args_list:
            assert call_args.kwargs.get("platform") == "voice"

    async def test_idempotent_recent_execution(self, client):
        """AC-FR005-003: Idempotent — skips if recent execution."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=True)
        mock_job_repo.start_execution = AsyncMock()

        mock_settings = _mock_settings()

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo):

            response = await client.post("/tasks/refresh-voice-prompts")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "recent_execution"
        mock_job_repo.start_execution.assert_not_called()

    async def test_auth_required(self, client):
        """AC-FR005-004: Auth required — rejects without Bearer token."""
        mock_settings = _mock_settings(task_auth_secret="real_secret")

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            response = await client.post("/tasks/refresh-voice-prompts")

        assert response.status_code in (401, 403)

    async def test_per_user_error_isolation(self, client):
        """Pipeline failure for 1 of 3 users -> refreshed=2, errors=1."""
        users = [_make_user() for _ in range(3)]

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
        mock_user_repo.count_users_with_stale_voice_prompts = AsyncMock(return_value=3)
        mock_user_repo.get_users_with_stale_voice_prompts = AsyncMock(
            return_value=users
        )

        # Pipeline succeeds for first 2 users, fails for 3rd
        call_count = 0

        async def _process_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("Pipeline failed for user 3")

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process = AsyncMock(side_effect=_process_side_effect)

        mock_settings = _mock_settings()

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.pipeline.orchestrator.PipelineOrchestrator", return_value=mock_orchestrator):

            response = await client.post("/tasks/refresh-voice-prompts")

        data = response.json()
        assert data["refreshed"] == 2
        assert data["errors"] == 1
        # Job still completes even with partial errors
        mock_job_repo.complete_execution.assert_awaited_once()


    async def test_deferred_count_when_over_cap(self, client):
        """deferred = total_stale - 50 when more than 50 stale users exist."""
        stale_users = [_make_user() for _ in range(50)]

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
        mock_user_repo.count_users_with_stale_voice_prompts = AsyncMock(return_value=75)
        mock_user_repo.get_users_with_stale_voice_prompts = AsyncMock(
            return_value=stale_users
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process = AsyncMock()
        mock_settings = _mock_settings()

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.pipeline.orchestrator.PipelineOrchestrator", return_value=mock_orchestrator):

            response = await client.post("/tasks/refresh-voice-prompts")

        data = response.json()
        assert data["deferred"] == 25
        assert data["refreshed"] == 50

    async def test_no_stale_users(self, client):
        """Empty batch — nothing to refresh."""
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
        mock_user_repo.count_users_with_stale_voice_prompts = AsyncMock(return_value=0)
        mock_user_repo.get_users_with_stale_voice_prompts = AsyncMock(return_value=[])

        mock_settings = _mock_settings()

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):

            response = await client.post("/tasks/refresh-voice-prompts")

        data = response.json()
        assert data["refreshed"] == 0
        assert data["deferred"] == 0
        assert data["errors"] == 0


@pytest.mark.asyncio
class TestJobNameEnum:
    """Spec 209 T001: JobName enum pre-condition."""

    def test_refresh_voice_prompts_value(self):
        """AC-T001-1: JobName.REFRESH_VOICE_PROMPTS.value == 'refresh_voice_prompts'."""
        assert JobName.REFRESH_VOICE_PROMPTS.value == "refresh_voice_prompts"

    def test_existing_enums_unchanged(self):
        """AC-T001-2: Existing enum values not broken."""
        assert JobName.DECAY.value == "decay"
        assert JobName.PSYCHE_BATCH.value == "psyche_batch"


@pytest.mark.asyncio
class TestStaleUserRepository:
    """Tests for UserRepository.get_users_with_stale_voice_prompts()."""

    async def test_method_exists(self):
        """get_users_with_stale_voice_prompts method exists on UserRepository."""
        from nikita.db.repositories.user_repository import UserRepository

        assert hasattr(UserRepository, "get_users_with_stale_voice_prompts")

    async def test_returns_list(self):
        """Method returns a list (may be empty)."""
        from nikita.db.repositories.user_repository import UserRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_unique = MagicMock()
        mock_unique.scalars.return_value = mock_scalars
        mock_result.unique.return_value = mock_unique
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.get_users_with_stale_voice_prompts()

        assert result == []
        mock_session.execute.assert_awaited_once()
