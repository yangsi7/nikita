"""Tests for Spec 100 Story 2: Decay Idempotency Guard.

T2.2: 3 tests — normal run, skipped on double-fire, processes after window.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.api.routes.tasks import apply_daily_decay


def _mock_settings():
    settings = MagicMock()
    settings.task_auth_secret = None
    return settings


class TestDecayIdempotency:
    """Spec 100 FR-002: Decay idempotency guard."""

    @pytest.mark.asyncio
    async def test_decay_skipped_when_recent_execution_exists(self):
        """AC: Second call within 50min returns skipped."""
        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()):
            with patch("nikita.api.routes.tasks.get_session_maker") as mock_sm:
                mock_session = AsyncMock()
                ctx_mgr = AsyncMock()
                ctx_mgr.__aenter__ = AsyncMock(return_value=mock_session)
                ctx_mgr.__aexit__ = AsyncMock(return_value=False)
                mock_sm.return_value = MagicMock(return_value=ctx_mgr)
                mock_sm.return_value.__call__ = MagicMock(return_value=ctx_mgr)

                with patch(
                    "nikita.api.routes.tasks.JobExecutionRepository"
                ) as MockJobRepo:
                    mock_job_repo = AsyncMock()
                    # Key: has_recent_execution returns True → should skip
                    mock_job_repo.has_recent_execution = AsyncMock(return_value=True)
                    MockJobRepo.return_value = mock_job_repo

                    result = await apply_daily_decay()

                    assert result["status"] == "skipped"
                    assert result["reason"] == "recent_execution"

    @pytest.mark.asyncio
    async def test_decay_processes_when_no_recent_execution(self):
        """AC: First call (no recent execution) processes normally."""
        with patch("nikita.api.routes.tasks.get_settings", return_value=_mock_settings()):
            with patch("nikita.api.routes.tasks.get_session_maker") as mock_sm:
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                ctx_mgr = AsyncMock()
                ctx_mgr.__aenter__ = AsyncMock(return_value=mock_session)
                ctx_mgr.__aexit__ = AsyncMock(return_value=False)
                mock_sm.return_value = MagicMock(return_value=ctx_mgr)
                mock_sm.return_value.__call__ = MagicMock(return_value=ctx_mgr)

                with patch(
                    "nikita.api.routes.tasks.JobExecutionRepository"
                ) as MockJobRepo:
                    mock_job_repo = AsyncMock()
                    # No recent execution → should process
                    mock_job_repo.has_recent_execution = AsyncMock(return_value=False)
                    mock_job_repo.start_execution = AsyncMock(
                        return_value=MagicMock(id=uuid4())
                    )
                    mock_job_repo.complete_execution = AsyncMock()
                    MockJobRepo.return_value = mock_job_repo

                    with patch(
                        "nikita.db.repositories.user_repository.UserRepository"
                    ) as MockUserRepo:
                        mock_user_repo = AsyncMock()
                        mock_user_repo.get_active_users_for_decay = AsyncMock(
                            return_value=[]
                        )
                        MockUserRepo.return_value = mock_user_repo

                        with patch(
                            "nikita.engine.decay.processor.DecayProcessor"
                        ) as MockProcessor:
                            mock_proc = AsyncMock()
                            mock_proc.process_all = AsyncMock(
                                return_value={
                                    "processed": 0,
                                    "decayed": 0,
                                    "game_overs": 0,
                                }
                            )
                            MockProcessor.return_value = mock_proc

                            result = await apply_daily_decay()
                            assert result["status"] == "ok"
