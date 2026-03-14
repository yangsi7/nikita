"""Tests for Spec 116 — Extraction Checkpoint (MP-004).

Verifies that PersistenceStage runs before MemoryUpdateStage so that
extracted thoughts/threads are durably written even when memory_update fails.

AC-001: persistence at index 1 (immediately after extraction)
AC-002: memory_update at index 2 (after persistence)
AC-004: all 11 stages remain present
"""

import pytest
from uuid import uuid4

from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import BaseStage, StageResult


# ── Fake stages for integration test ─────────────────────────────────────────


class FakeOkStage(BaseStage):
    name = "fake_ok"
    is_critical = False
    timeout_seconds = 5.0

    async def _run(self, ctx):
        return {"status": "ok"}


# ── Stage Order Tests ─────────────────────────────────────────────────────────


class TestExtractionCheckpointStageOrder:
    """AC-001/002/004: persistence precedes memory_update in STAGE_DEFINITIONS."""

    def test_persistence_before_memory_update(self):
        """AC-001/002: persistence index < memory_update index."""
        names = [name for name, _, _ in PipelineOrchestrator.STAGE_DEFINITIONS]
        persistence_idx = names.index("persistence")
        memory_update_idx = names.index("memory_update")
        assert persistence_idx < memory_update_idx, (
            f"persistence (idx {persistence_idx}) must precede "
            f"memory_update (idx {memory_update_idx})"
        )

    def test_persistence_at_index_1(self):
        """AC-001: persistence is immediately after extraction."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[1][0] == "persistence"

    def test_memory_update_at_index_2(self):
        """AC-002: memory_update follows persistence."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[2][0] == "memory_update"

    def test_extraction_still_at_index_0(self):
        """extraction must remain first (CRITICAL)."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[0][0] == "extraction"

    def test_all_original_stages_present(self):
        """AC-004: all 10 original stages remain after reorder (count may be 10 or 11 depending on merge order)."""
        names = {name for name, _, _ in PipelineOrchestrator.STAGE_DEFINITIONS}
        required = {
            "extraction", "memory_update", "persistence", "life_sim",
            "emotional", "game_state", "conflict", "touchpoint", "summary", "prompt_builder",
        }
        missing = required - names
        assert not missing, f"Stages lost by reorder: {missing}"

    def test_persistence_is_non_critical(self):
        """Persistence must stay non-critical so memory_update runs even if persistence fails."""
        entry = next(e for e in PipelineOrchestrator.STAGE_DEFINITIONS if e[0] == "persistence")
        assert entry[2] is False, "persistence must be non-critical"

    def test_memory_update_is_critical(self):
        """memory_update must remain critical."""
        entry = next(e for e in PipelineOrchestrator.STAGE_DEFINITIONS if e[0] == "memory_update")
        assert entry[2] is True, "memory_update must be critical"


# ── Integration: persistence survives memory_update failure ───────────────────


class TestPersistenceSurvivesMemoryUpdateFailure:
    """Spec 116 core scenario: persistence runs before memory_update fails."""

    @pytest.mark.asyncio
    async def test_persistence_failure_does_not_block_memory_update(self, mock_session):
        """Non-critical persistence failure must NOT prevent memory_update from running."""
        memory_update_called = []

        class FakePersistenceFail(BaseStage):
            name = "persistence"
            is_critical = False
            timeout_seconds = 5.0

            async def _run(self, ctx):
                raise Exception("DB write failure")

        class FakeMemoryOk(BaseStage):
            name = "memory_update"
            is_critical = True
            timeout_seconds = 5.0

            async def _run(self, ctx):
                memory_update_called.append(True)
                return {"stored": 1}

        stages = [
            ("extraction",    FakeOkStage(session=mock_session),       True),
            ("persistence",   FakePersistenceFail(session=mock_session), False),
            ("memory_update", FakeMemoryOk(session=mock_session),       True),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        assert result.success is True, "pipeline must succeed when only non-critical persistence fails"
        assert len(memory_update_called) == 1, "memory_update must run despite persistence failure"
        assert "persistence" in result.context.stage_errors

    @pytest.mark.asyncio
    async def test_persistence_runs_before_critical_failure(self, mock_session):
        """When memory_update (critical) fails, persistence has already executed."""
        persistence_called = []

        class FakePersistence(BaseStage):
            name = "persistence"
            is_critical = False
            timeout_seconds = 5.0

            async def _run(self, ctx):
                persistence_called.append(True)
                return {"thoughts_persisted": 1, "threads_persisted": 0}

        class FakeMemoryFail(BaseStage):
            name = "memory_update"
            is_critical = True
            timeout_seconds = 5.0

            async def _run(self, ctx):
                raise Exception("OpenAI outage")

        stages = [
            ("extraction",    FakeOkStage(session=mock_session),    True),
            ("persistence",   FakePersistence(session=mock_session), False),
            ("memory_update", FakeMemoryFail(session=mock_session),  True),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "memory_update"
        assert len(persistence_called) == 1, (
            "persistence must have run before memory_update failed"
        )
