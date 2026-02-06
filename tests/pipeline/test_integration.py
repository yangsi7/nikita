"""Integration tests for the unified pipeline (T2.11)."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import BaseStage, StageResult


class MockStage(BaseStage):
    """Mock stage for integration testing."""

    def __init__(
        self,
        name: str,
        is_critical: bool = False,
        fail: bool = False,
        error_msg: str = "",
    ):
        self.name = name
        self.is_critical = is_critical
        self._fail = fail
        self._error_msg = error_msg
        super().__init__()

    async def _run(self, ctx):
        if self._fail:
            raise Exception(self._error_msg or f"{self.name} failed")
        return {"stage": self.name, "ok": True}


@pytest.mark.asyncio
class TestPipelineIntegration:

    async def test_full_pipeline_all_stages_succeed(self):
        """Full pipeline with 9 mocked stages all succeeding."""
        stage_names = [
            "extraction",
            "memory_update",
            "life_sim",
            "emotional",
            "game_state",
            "conflict",
            "touchpoint",
            "summary",
            "prompt_builder",
        ]
        stages = [
            (
                name,
                MockStage(
                    name,
                    is_critical=(name in ("extraction", "memory_update")),
                ),
                name in ("extraction", "memory_update"),
            )
            for name in stage_names
        ]

        orch = PipelineOrchestrator(session=MagicMock(), stages=stages)
        result = await orch.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert result.stages_completed == 9
        assert len(result.context.stage_errors) == 0

    async def test_critical_failure_halts_pipeline(self):
        """Critical stage failure stops remaining stages."""
        stages = [
            (
                "extraction",
                MockStage(
                    "extraction",
                    is_critical=True,
                    fail=True,
                    error_msg="LLM down",
                ),
                True,
            ),
            (
                "memory_update",
                MockStage("memory_update", is_critical=True),
                True,
            ),
            ("life_sim", MockStage("life_sim"), False),
        ]
        orch = PipelineOrchestrator(session=MagicMock(), stages=stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is False
        assert result.error_stage == "extraction"

    async def test_non_critical_failure_continues(self):
        """Non-critical stage failure records error, continues."""
        stages = [
            (
                "extraction",
                MockStage("extraction", is_critical=True),
                True,
            ),
            (
                "life_sim",
                MockStage(
                    "life_sim", fail=True, error_msg="sim crashed"
                ),
                False,
            ),
            ("emotional", MockStage("emotional"), False),
        ]
        orch = PipelineOrchestrator(session=MagicMock(), stages=stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert "life_sim" in result.context.stage_errors

    async def test_voice_platform_context(self):
        """Voice platform is passed through to context."""
        stages = [("s1", MockStage("s1"), False)]
        orch = PipelineOrchestrator(session=MagicMock(), stages=stages)
        result = await orch.process(uuid4(), uuid4(), "voice")
        assert result.context.platform == "voice"

    async def test_text_platform_default(self):
        """Text is the default platform."""
        stages = [("s1", MockStage("s1"), False)]
        orch = PipelineOrchestrator(session=MagicMock(), stages=stages)
        result = await orch.process(uuid4(), uuid4())
        assert result.context.platform == "text"

    async def test_empty_stages_succeeds(self):
        """Pipeline with no stages succeeds immediately."""
        orch = PipelineOrchestrator(session=MagicMock(), stages=[])
        result = await orch.process(uuid4(), uuid4())
        assert result.success is True
        assert result.stages_completed == 0
