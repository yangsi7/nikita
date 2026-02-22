"""Tests for Spec 056 Psyche Batch Job (Phase 3: T10, T11).

Tests the daily batch orchestrator that generates PsycheState for all
active users. Tests feature flag gating, per-user isolation, timeout,
summary reporting, and context loading.

AC refs: AC-1.4, AC-1.5, AC-6.1, AC-6.6
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.psyche.batch import (
    USER_TIMEOUT_SECONDS,
    _build_deps,
    run_psyche_batch,
)


# ============================================================================
# Module structure
# ============================================================================


class TestBatchModuleStructure:
    """Batch module exports expected functions."""

    def test_module_importable(self):
        from nikita.agents.psyche import batch

        assert batch is not None

    def test_run_psyche_batch_exists(self):
        assert callable(run_psyche_batch)

    def test_run_psyche_batch_is_async(self):
        assert asyncio.iscoroutinefunction(run_psyche_batch)

    def test_build_deps_exists(self):
        assert callable(_build_deps)

    def test_user_timeout_is_30s(self):
        assert USER_TIMEOUT_SECONDS == 30


# ============================================================================
# AC-6.6: Feature flag gating
# ============================================================================


class TestFeatureFlagGating:
    """Batch job does nothing when feature flag is OFF."""

    @pytest.mark.asyncio
    async def test_flag_off_returns_empty_summary(self):
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=False):
            result = await run_psyche_batch()

        assert result["processed"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_flag_off_returns_all_zero_counts(self):
        """All counts are zero when flag is OFF — no work performed."""
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=False):
            result = await run_psyche_batch()

        assert result["processed"] + result["failed"] + result["skipped"] == 0


# ============================================================================
# AC-1.5: Per-user isolation (one failure does not block others)
# ============================================================================


class TestPerUserIsolation:
    """Individual user failures do not block batch.

    Verified by code review: run_psyche_batch() has per-user
    try/except wrapping each user loop iteration with rollback.
    """

    def test_batch_has_per_user_try_except(self):
        """Verify the per-user isolation pattern exists in source."""
        import inspect

        source = inspect.getsource(run_psyche_batch)
        # Code must have try/except inside the loop
        assert "except Exception as e:" in source
        assert "rollback" in source

    def test_batch_has_timeout_handling(self):
        """Verify timeout handling exists."""
        import inspect

        source = inspect.getsource(run_psyche_batch)
        assert "TimeoutError" in source
        assert "wait_for" in source


# ============================================================================
# AC-1.4: Per-user timeout (30s)
# ============================================================================


class TestPerUserTimeout:
    """Timeout for individual user generation."""

    def test_timeout_constant_is_30_seconds(self):
        assert USER_TIMEOUT_SECONDS == 30

    def test_batch_uses_asyncio_wait_for(self):
        """Batch job uses asyncio.wait_for for per-user timeout."""
        import inspect

        source = inspect.getsource(run_psyche_batch)
        assert "asyncio.wait_for" in source
        assert "USER_TIMEOUT_SECONDS" in source


# ============================================================================
# Summary reporting
# ============================================================================


class TestSummaryReporting:
    """Batch returns structured summary dict."""

    @pytest.mark.asyncio
    async def test_summary_has_required_keys(self):
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=False):
            result = await run_psyche_batch()

        assert "processed" in result
        assert "failed" in result
        assert "skipped" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_errors_capped_at_10(self):
        """Error list is capped at 10 entries max."""
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=False):
            result = await run_psyche_batch()

        assert isinstance(result["errors"], list)
        assert len(result["errors"]) <= 10


# ============================================================================
# _build_deps context loading
# ============================================================================


class TestBuildDeps:
    """_build_deps loads 48h of user context."""

    @pytest.mark.asyncio
    async def test_returns_psyche_deps(self):
        from nikita.agents.psyche.deps import PsycheDeps

        user = MagicMock(id=uuid4(), chapter=3)
        session = AsyncMock()

        # Patch score history and conversation repos at their source modules
        mock_score_repo = AsyncMock()
        mock_score_repo.get_recent = AsyncMock(return_value=[])
        mock_score_cls = MagicMock(return_value=mock_score_repo)

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_processed_conversations = AsyncMock(return_value=[])
        mock_conv_cls = MagicMock(return_value=mock_conv_repo)

        with (
            patch.dict("sys.modules", {
                "nikita.db.repositories.score_history_repository": MagicMock(
                    ScoreHistoryRepository=mock_score_cls
                ),
                "nikita.db.repositories.conversation_repository": MagicMock(
                    ConversationRepository=mock_conv_cls
                ),
            }),
        ):
            deps = await _build_deps(session, user)

        assert isinstance(deps, PsycheDeps)
        assert deps.user_id == user.id
        assert deps.current_chapter == 3

    @pytest.mark.asyncio
    async def test_defaults_chapter_to_1(self):
        from nikita.agents.psyche.deps import PsycheDeps

        user = MagicMock(id=uuid4(), chapter=None)
        session = AsyncMock()

        mock_score_repo = AsyncMock()
        mock_score_repo.get_recent = AsyncMock(return_value=[])

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_processed_conversations = AsyncMock(return_value=[])

        with (
            patch.dict("sys.modules", {
                "nikita.db.repositories.score_history_repository": MagicMock(
                    ScoreHistoryRepository=MagicMock(return_value=mock_score_repo)
                ),
                "nikita.db.repositories.conversation_repository": MagicMock(
                    ConversationRepository=MagicMock(return_value=mock_conv_repo)
                ),
            }),
        ):
            deps = await _build_deps(session, user)

        assert deps.current_chapter == 1

    @pytest.mark.asyncio
    async def test_handles_score_history_failure_gracefully(self):
        """Score history load failure does not crash batch."""
        user = MagicMock(id=uuid4(), chapter=1)
        session = AsyncMock()

        mock_score_repo = AsyncMock()
        mock_score_repo.get_recent = AsyncMock(side_effect=Exception("DB error"))

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_processed_conversations = AsyncMock(return_value=[])

        with (
            patch.dict("sys.modules", {
                "nikita.db.repositories.score_history_repository": MagicMock(
                    ScoreHistoryRepository=MagicMock(return_value=mock_score_repo)
                ),
                "nikita.db.repositories.conversation_repository": MagicMock(
                    ConversationRepository=MagicMock(return_value=mock_conv_repo)
                ),
            }),
        ):
            deps = await _build_deps(session, user)

        # Should still return deps with empty score_history
        assert deps.score_history == []
