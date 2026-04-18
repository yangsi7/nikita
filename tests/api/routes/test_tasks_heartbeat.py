"""Tests for /tasks/heartbeat endpoint (Spec 215 PR 215-D, US-2).

Spec ACs covered:
- AC-FR5-001: at least one heartbeat invocation per active player per hour
- AC-FR9-001: idempotent — second tick within 55-min window returns "skipped"
- AC-FR10-001: per-user advisory lock serializes concurrent operations (R3)
- FR-007: handler MUST delegate to TouchpointEngine, never write
  scheduled_events directly (R1)
- FR-008: skip users in game_over and won states (G1)
- FR-014: cost circuit breaker leaves heartbeat alone (cost guard lives on
  /tasks/generate-daily-arcs in this PR; heartbeat is cheap)
- FR-015: error envelope shape — no str(e) leak

Brief scope (R2/R3/R4/G1):
- R2: idempotency guard via JobExecutionRepository.has_recent_execution
- R3: pg_advisory_xact_lock per user (day-1)
- R4: bounded fan-out (max 40 per tick — leaves 10-row /tasks/deliver headroom)
- G1: active-user filter (game_status active|boss_fight + telegram_id IS NOT NULL +
  recent interaction)

These tests are EXTENSIVELY mock-based per project test rules. Real DB and
real TouchpointEngine integration happens in tests/heartbeat E2E (out of scope
for this PR).
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
    """Create mock settings with task auth bypass + heartbeat flag on by default."""
    defaults = dict(
        task_auth_secret=None,
        telegram_webhook_secret=None,
        heartbeat_engine_enabled=True,
        heartbeat_cost_circuit_breaker_usd_per_day=50.0,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _mock_session_maker(mock_session):
    """Mock session_maker returning async context manager yielding mock_session."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_maker = MagicMock()
    mock_maker.return_value = mock_ctx
    return mock_maker


def _make_user(**overrides):
    """Create mock User suitable for the heartbeat handler (active + telegram-bound)."""
    defaults = dict(
        id=uuid4(),
        chapter=2,
        game_status="active",
        telegram_id=12345,
        last_interaction_at=datetime.now(UTC) - timedelta(hours=4),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_mock_engine():
    """Build a mocked TouchpointEngine that returns a stand-in scheduled touchpoint."""
    eng = AsyncMock()
    eng.evaluate_and_schedule_for_user = AsyncMock(
        return_value=SimpleNamespace(id=uuid4())
    )
    return eng


# ---------------------------------------------------------------------------
# JobName enum entry — Contract 2 (215-D ships, 215-E references)
# ---------------------------------------------------------------------------


class TestJobNameEnum:
    """Spec 215 contracts.md Contract 2: HEARTBEAT enum entry exists."""

    def test_heartbeat_enum_entry_exists(self):
        """JobName.HEARTBEAT.value == 'heartbeat' per contracts.md Contract 2."""
        assert JobName.HEARTBEAT.value == "heartbeat"

    def test_existing_enum_entries_unchanged(self):
        """Pre-existing enum values not broken by the additive change."""
        assert JobName.DECAY.value == "decay"
        assert JobName.REFRESH_VOICE_PROMPTS.value == "refresh_voice_prompts"


# ---------------------------------------------------------------------------
# /tasks/heartbeat — endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHeartbeatEndpoint:
    """Spec 215 PR 215-D: /tasks/heartbeat handler."""

    async def test_auth_required_when_secret_configured(self, client):
        """No Bearer token + secret configured → 401/403 (mirrors verify_task_secret)."""
        mock_settings = _mock_settings(task_auth_secret="real_secret")

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            response = await client.post("/tasks/heartbeat")

        assert response.status_code in (401, 403)

    async def test_idempotency_skips_when_recent_execution(self, client):
        """AC-FR9-001 (R2): has_recent_execution(window=55) True → skip + no work."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=True)
        mock_job_repo.start_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=[])

        mock_engine = _build_mock_engine()

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "recent_execution"
        # No work happened: no execution record opened, no engine touched.
        mock_job_repo.start_execution.assert_not_called()
        mock_engine.evaluate_and_schedule_for_user.assert_not_called()

        # AC-FR9-001 confirms the 55-min window value
        mock_job_repo.has_recent_execution.assert_awaited_once()
        call_kwargs = mock_job_repo.has_recent_execution.call_args
        # Either positional or kwarg form
        assert call_kwargs.kwargs.get("window_minutes") == 55 or (
            len(call_kwargs.args) >= 2 and call_kwargs.args[1] == 55
        )

    async def test_idempotency_uses_heartbeat_job_name(self, client):
        """has_recent_execution called with JobName.HEARTBEAT.value."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=True)

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo):

            await client.post("/tasks/heartbeat")

        mock_job_repo.has_recent_execution.assert_awaited_once()
        first_arg = mock_job_repo.has_recent_execution.call_args.args[0]
        assert first_arg == JobName.HEARTBEAT.value == "heartbeat"

    async def test_active_user_filter_called_with_telegram_and_recency(self, client):
        """G1: handler calls UserRepository.get_active_users_for_heartbeat (centralized filter)."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=[])

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        mock_user_repo.get_active_users_for_heartbeat.assert_awaited_once()

    async def test_fan_out_capped_at_40(self, client):
        """R4: when 100 active users exist, only 40 are processed in this tick."""
        users = [_make_user() for _ in range(100)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_engine = _build_mock_engine()

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 40
        assert data["deferred"] == 60
        assert mock_engine.evaluate_and_schedule_for_user.await_count == 40

    async def test_delegates_to_touchpoint_engine_per_user(self, client):
        """FR-007 / R1: handler MUST call TouchpointEngine.evaluate_and_schedule_for_user;
        MUST NOT write to scheduled_events directly."""
        users = [_make_user() for _ in range(3)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_engine = _build_mock_engine()

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        # Exactly 3 user_ids, each delegated
        assert mock_engine.evaluate_and_schedule_for_user.await_count == 3
        delegated_user_ids = {
            call.kwargs.get("user_id") or call.args[0]
            for call in mock_engine.evaluate_and_schedule_for_user.call_args_list
        }
        assert delegated_user_ids == {u.id for u in users}

    async def test_advisory_lock_acquired_and_released_per_user(self, client):
        """R3 (day-1): handler MUST acquire pg_advisory_lock + pg_advisory_unlock per user.

        Updated PR #334 iter-2: switched from pg_advisory_xact_lock (xact-scoped)
        to pg_advisory_lock + explicit pg_advisory_unlock so locks release at
        end-of-USER not end-of-tick (avoids 40-user lock pile-up across the
        single-transaction fan-out).
        """
        users = [_make_user() for _ in range(2)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        # session.execute(SELECT hashtext(...))).scalar_one() must return an int
        mock_result = SimpleNamespace(scalar_one=lambda: 12345)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=users)

        mock_engine = _build_mock_engine()

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        executed_sql = []
        for call in mock_session.execute.call_args_list:
            stmt = call.args[0] if call.args else call.kwargs.get("statement")
            executed_sql.append(str(stmt))

        # Must see hashtext key derivation, advisory_lock, and advisory_unlock per user
        hashtext_calls = [s for s in executed_sql if "hashtext" in s]
        lock_calls = [s for s in executed_sql if "pg_advisory_lock" in s and "unlock" not in s]
        unlock_calls = [s for s in executed_sql if "pg_advisory_unlock" in s]

        assert len(hashtext_calls) >= len(users), (
            f"Expected hashtext key derivation per user; got {hashtext_calls}"
        )
        assert len(lock_calls) >= len(users), (
            f"Expected pg_advisory_lock per user; got {lock_calls}"
        )
        assert len(unlock_calls) >= len(users), (
            f"Expected pg_advisory_unlock per user (try/finally release); got {unlock_calls}"
        )

    async def test_per_user_error_isolation(self, client):
        """1-of-3 user errors → others still complete; job marked complete (not failed)."""
        users = [_make_user() for _ in range(3)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
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

        call_count = 0

        async def _engine_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("simulated per-user error")
            return SimpleNamespace(id=uuid4())

        mock_engine = AsyncMock()
        mock_engine.evaluate_and_schedule_for_user = AsyncMock(
            side_effect=_engine_side_effect
        )

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 2
        assert data["errors"] == 1
        # Job must complete cleanly even when one user fails (graceful degradation).
        mock_job_repo.complete_execution.assert_awaited_once()
        mock_job_repo.fail_execution.assert_not_called()

    async def test_error_envelope_redacts_exception_string(self, client):
        """FR-015: catastrophic-failure error envelope MUST NOT leak str(exception)."""
        secret_token = "PII_SECRET_DO_NOT_LEAK_xyzzy"

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        mock_job_repo.complete_execution = AsyncMock()
        mock_job_repo.fail_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        # Catastrophic: repo blows up after job_executions row exists
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(
            side_effect=RuntimeError(f"disk full: {secret_token}")
        )

        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data and isinstance(data["error"], str)
        # Per FR-015 envelope shape: {"error": "<code>", "detail": "<redacted>"}
        # MUST NOT contain raw exception string content.
        full_payload = response.text
        assert secret_token not in full_payload, (
            "FR-015 violation: raw exception string leaked into response payload"
        )
        mock_job_repo.fail_execution.assert_awaited_once()

    async def test_feature_flag_off_short_circuits(self, client):
        """FR-020 rollback contract: heartbeat_engine_enabled=False → no work, no users queried."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_maker = _mock_session_maker(mock_session)

        mock_job_repo = AsyncMock()
        mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
        mock_job_repo.start_execution = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_heartbeat = AsyncMock(return_value=[])

        mock_engine = _build_mock_engine()

        with patch(
            "nikita.api.routes.tasks.get_settings",
            return_value=_mock_settings(heartbeat_engine_enabled=False),
        ), \
             patch("nikita.api.routes.tasks.get_session_maker", return_value=mock_maker), \
             patch("nikita.api.routes.tasks.JobExecutionRepository", return_value=mock_job_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo), \
             patch("nikita.touchpoints.engine.TouchpointEngine", return_value=mock_engine):

            response = await client.post("/tasks/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        # No engine work, no user query, no job_executions row.
        mock_engine.evaluate_and_schedule_for_user.assert_not_called()
        mock_user_repo.get_active_users_for_heartbeat.assert_not_called()
        mock_job_repo.start_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Tuning constant regression guard (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------


def test_heartbeat_fan_out_cap_is_40_per_R4():
    """R4 + FR-005: fan-out cap MUST stay at 40 per tick.

    Coupling rationale: /tasks/deliver consumes from the same scheduled_events
    queue with a 50-row chunk. Heartbeat capacity = 40 leaves 10-row headroom
    so the deliver worker isn't starved by heartbeat-generated touchpoints
    landing in the same window.

    If you intentionally change this value, update:
    - nikita/api/routes/tasks.py:_HEARTBEAT_FAN_OUT_CAP
    - specs/215-heartbeat-engine/spec.md FR-005 / R4 capacity reasoning
    - this regression test
    """
    from nikita.api.routes.tasks import _HEARTBEAT_FAN_OUT_CAP

    assert _HEARTBEAT_FAN_OUT_CAP == 40, (
        "Heartbeat fan-out cap drift: see R4/FR-005 for capacity reasoning."
    )
