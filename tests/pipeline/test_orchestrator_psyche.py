"""Tests for psyche state loading in PipelineOrchestrator (Spec 209 PR 209-1).

AC-FR001-001: Pipeline includes psyche state in prompt when record exists
AC-FR001-002: No error/placeholder when psyche record is None
AC-FR001-003: No DB call when psyche_agent_enabled = False
AC-FR001-004: Exception handled gracefully (orchestrator side)
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import StageResult

# Patch target: module-level import in orchestrator
PSYCHE_REPO_PATH = "nikita.pipeline.orchestrator.PsycheStateRepository"


class FakeStage:
    """Minimal stage that always succeeds."""

    def __init__(self, name: str = "fake"):
        self.name = name

    async def execute(self, context):
        return StageResult.ok(data={}, duration_ms=1.0)


def _make_orchestrator(session=None) -> PipelineOrchestrator:
    """Create orchestrator with a single fake stage (just need process() to run)."""
    session = session or MagicMock()
    stages = [("fake", FakeStage("fake"), False)]
    return PipelineOrchestrator(session=session, stages=stages)


def _make_user(**overrides):
    """Create a mock User ORM object with defaults."""
    defaults = dict(
        id=uuid4(),
        chapter=2,
        game_status="active",
        relationship_score=50.0,
        user_metrics=None,
        engagement_state=None,
        vice_preferences=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
class TestPsycheStateLoading:
    """Spec 209 FR-001: Psyche-aware voice calls via pipeline injection."""

    async def test_psyche_record_exists_populates_ctx(self):
        """AC-FR001-001: Pipeline includes psyche state when record exists."""
        psyche_state = {
            "emotional_tone": "melancholic",
            "behavioral_guidance": "be gentle",
            "topics_to_encourage": ["music"],
            "topics_to_avoid": ["work"],
        }
        mock_record = SimpleNamespace(state=psyche_state)

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_current = AsyncMock(return_value=mock_record)

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.observability_enabled = False

        user = _make_user()
        orch = _make_orchestrator()

        with patch(
            PSYCHE_REPO_PATH,
            return_value=mock_repo_instance,
        ) as mock_repo_cls, patch(
            "nikita.pipeline.orchestrator.get_settings",
            return_value=mock_settings,
        ):
            result = await orch.process(
                uuid4(), user.id, "voice", user=user
            )

        assert result.context.psyche_state == psyche_state
        mock_repo_cls.assert_called_once()
        mock_repo_instance.get_current.assert_awaited_once_with(user.id)

    async def test_psyche_record_none_stays_none(self):
        """AC-FR001-002: No error when psyche record is None."""
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_current = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.observability_enabled = False

        user = _make_user()
        orch = _make_orchestrator()

        with patch(
            PSYCHE_REPO_PATH,
            return_value=mock_repo_instance,
        ), patch(
            "nikita.pipeline.orchestrator.get_settings",
            return_value=mock_settings,
        ):
            result = await orch.process(
                uuid4(), user.id, "voice", user=user
            )

        assert result.context.psyche_state is None

    async def test_psyche_disabled_no_db_call(self):
        """AC-FR001-003: No DB call when psyche_agent_enabled = False."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = False
        mock_settings.observability_enabled = False

        user = _make_user()
        orch = _make_orchestrator()

        with patch(
            PSYCHE_REPO_PATH,
        ) as mock_repo_cls, patch(
            "nikita.pipeline.orchestrator.get_settings",
            return_value=mock_settings,
        ):
            result = await orch.process(
                uuid4(), user.id, "voice", user=user
            )

        mock_repo_cls.assert_not_called()
        assert result.context.psyche_state is None

    async def test_psyche_exception_graceful_fallback(self, caplog):
        """AC-FR001-004 (partial): Exception caught, logged, psyche stays None."""
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_current = AsyncMock(
            side_effect=Exception("DB connection lost")
        )

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.observability_enabled = False

        user = _make_user()
        orch = _make_orchestrator()

        with patch(
            PSYCHE_REPO_PATH,
            return_value=mock_repo_instance,
        ), patch(
            "nikita.pipeline.orchestrator.get_settings",
            return_value=mock_settings,
        ), caplog.at_level(logging.WARNING, logger="nikita.pipeline.orchestrator"):
            result = await orch.process(
                uuid4(), user.id, "voice", user=user
            )

        assert result.context.psyche_state is None
        assert "pipeline_psyche_error" in caplog.text
        assert "DB connection lost" in caplog.text

    async def test_no_user_skips_psyche_loading(self):
        """When user=None, psyche loading is skipped entirely."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.observability_enabled = False

        orch = _make_orchestrator()

        with patch(
            PSYCHE_REPO_PATH,
        ) as mock_repo_cls, patch(
            "nikita.pipeline.orchestrator.get_settings",
            return_value=mock_settings,
        ):
            result = await orch.process(uuid4(), uuid4(), "voice")

        mock_repo_cls.assert_not_called()
        assert result.context.psyche_state is None
