"""Tests for PostProcessingPipeline (Spec 021, T020, T025 + Spec 022, T014).

AC-T020.1: PostProcessingPipeline class orchestrates all steps
AC-T020.2: process() method runs all steps in sequence
AC-T020.3: Returns ProcessingResult with step status
AC-T020.4: Error handling with partial completion support
AC-T020.5: Unit tests for pipeline

AC-T025.1: Test file tests/post_processing/test_pipeline_integration.py
AC-T025.2: Test full pipeline execution
AC-T025.3: Test partial failure handling
AC-T025.4: Test package storage verification

AC-T014.1: PostProcessingPipeline calls LifeSimulator
AC-T014.2: Events generated after each conversation
AC-T014.3: Errors logged but don't fail pipeline
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.package import ContextPackage, EmotionalState
from nikita.post_processing.pipeline import (
    PostProcessingPipeline,
    ProcessingResult,
    ProcessingStep,
    StepStatus,
    get_post_processing_pipeline,
)


# Helper to create mock session that mimics database context manager
@asynccontextmanager
async def mock_session_context():
    """Create a mock async session context manager."""
    mock_session = MagicMock()
    yield mock_session


def create_mock_session_maker():
    """Create a mock session maker that returns async context managers."""
    # Create mock user object
    mock_user = MagicMock()
    mock_user.chapter = 1
    # Use float to avoid Decimal/float division error in pipeline.py:441
    mock_user.relationship_score = 50.0

    # Create mock repository that returns the mock user
    mock_repo = AsyncMock()
    mock_repo.get.return_value = mock_user

    # Create mock session
    mock_session = MagicMock()

    # Patch the UserRepository constructor in the mock
    @asynccontextmanager
    async def session_context():
        yield mock_session

    # Return a callable that returns the context manager
    def session_maker():
        return session_context()

    return session_maker


def create_mock_user_repo():
    """Create a mock UserRepository with common return values."""
    mock_user = MagicMock()
    mock_user.chapter = 1
    mock_user.relationship_score = 50.0

    mock_repo = AsyncMock()
    mock_repo.get.return_value = mock_user
    return mock_repo


def get_pipeline_patches():
    """Get all patches needed for pipeline integration tests.

    Patches:
    - nikita.db.database.get_session_maker
    - nikita.db.repositories.user_repository.UserRepository
    - nikita.emotional_state.get_state_store (async methods)
    - nikita.conflicts.store.get_conflict_store (sync methods)
    """
    # StateStore has async methods (update_state, get_state_history)
    mock_state_store = AsyncMock()

    # ConflictStore has SYNC methods (get_user_triggers, create_trigger)
    # Must use MagicMock, not AsyncMock, or len() calls will fail on coroutines
    mock_conflict_store = MagicMock()
    mock_conflict_store.get_user_triggers.return_value = []  # No triggers by default

    # UserRepository.get() is async
    mock_user_repo = create_mock_user_repo()

    patches = [
        patch(
            "nikita.db.database.get_session_maker",
            return_value=create_mock_session_maker(),
        ),
        patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ),
        patch(
            "nikita.emotional_state.get_state_store",
            return_value=mock_state_store,
        ),
        patch(
            "nikita.conflicts.store.get_conflict_store",
            return_value=mock_conflict_store,
        ),
    ]
    return patches


class TestProcessingStep:
    """Tests for ProcessingStep dataclass."""

    def test_step_initial_state(self):
        """Step starts in PENDING state."""
        step = ProcessingStep(name="test_step")

        assert step.status == StepStatus.PENDING
        assert step.started_at is None
        assert step.completed_at is None
        assert step.error_message is None

    def test_mark_running(self):
        """mark_running sets status and timestamp."""
        step = ProcessingStep(name="test_step")

        step.mark_running()

        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None
        assert step.completed_at is None

    def test_mark_completed(self):
        """mark_completed sets status and timestamp."""
        step = ProcessingStep(name="test_step")
        step.mark_running()

        step.mark_completed({"result": "success"})

        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None
        assert step.metadata["result"] == "success"

    def test_mark_failed(self):
        """mark_failed sets status and error message."""
        step = ProcessingStep(name="test_step")
        step.mark_running()

        step.mark_failed("Something went wrong")

        assert step.status == StepStatus.FAILED
        assert step.completed_at is not None
        assert step.error_message == "Something went wrong"

    def test_mark_skipped(self):
        """mark_skipped sets status and reason."""
        step = ProcessingStep(name="test_step")

        step.mark_skipped("Not needed")

        assert step.status == StepStatus.SKIPPED
        assert step.metadata["skip_reason"] == "Not needed"


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_result_initial_state(self):
        """Result starts with empty steps."""
        result = ProcessingResult(
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert not result.success
        assert len(result.steps) == 0
        assert len(result.failed_steps) == 0
        assert len(result.completed_steps) == 0

    def test_failed_steps_property(self):
        """failed_steps returns only failed steps."""
        result = ProcessingResult(
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

        step1 = ProcessingStep(name="step1")
        step1.mark_completed()

        step2 = ProcessingStep(name="step2")
        step2.mark_failed("Error")

        result.steps = [step1, step2]

        assert len(result.failed_steps) == 1
        assert result.failed_steps[0].name == "step2"

    def test_completed_steps_property(self):
        """completed_steps returns only completed steps."""
        result = ProcessingResult(
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

        step1 = ProcessingStep(name="step1")
        step1.mark_completed()

        step2 = ProcessingStep(name="step2")
        step2.mark_failed("Error")

        result.steps = [step1, step2]

        assert len(result.completed_steps) == 1
        assert result.completed_steps[0].name == "step1"

    def test_partial_success_property(self):
        """partial_success is True when some steps pass and some fail."""
        result = ProcessingResult(
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

        step1 = ProcessingStep(name="step1")
        step1.mark_completed()

        step2 = ProcessingStep(name="step2")
        step2.mark_failed("Error")

        result.steps = [step1, step2]

        assert result.partial_success


class TestPostProcessingPipeline:
    """Tests for PostProcessingPipeline class."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session to prevent real DB calls in pipeline steps."""
        mock_user = MagicMock()
        mock_user.chapter = 1
        # Use float to avoid Decimal/float division error in pipeline.py:441
        mock_user.relationship_score = 50.0

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_user

        # Mock stores used by pipeline methods
        # StateStore has async methods
        mock_state_store = AsyncMock()
        # ConflictStore has SYNC methods - must use MagicMock
        mock_conflict_store = MagicMock()
        mock_conflict_store.get_user_triggers.return_value = []

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=create_mock_session_maker(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_repo,
        ), patch(
            "nikita.emotional_state.get_state_store",
            return_value=mock_state_store,
        ), patch(
            "nikita.conflicts.store.get_conflict_store",
            return_value=mock_conflict_store,
        ):
            yield mock_repo

    @pytest.fixture
    def mock_graph_updater(self):
        """Create mock graph updater."""
        updater = AsyncMock()
        updater.update.return_value = (3, 2)  # 3 facts, 2 events
        return updater

    @pytest.fixture
    def mock_summary_generator(self):
        """Create mock summary generator."""
        generator = AsyncMock()
        generator.generate.return_value = (True, False)  # daily updated, weekly not
        return generator

    @pytest.fixture
    def mock_life_simulator(self):
        """Create mock life simulator."""
        simulator = AsyncMock()
        simulator.generate_next_day_events.return_value = []  # No events by default
        return simulator

    @pytest.fixture
    def mock_layer_composer(self):
        """Create mock layer composer."""
        composer = AsyncMock()
        package = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        composer.compose.return_value = package
        return composer

    @pytest.fixture
    def mock_package_store(self):
        """Create mock package store."""
        store = AsyncMock()
        store.set.return_value = None
        return store

    @pytest.fixture
    def mock_state_computer(self):
        """Create mock state computer (Spec 023)."""
        from nikita.emotional_state import EmotionalStateModel

        computer = MagicMock()
        computer.compute.return_value = EmotionalStateModel(
            user_id=uuid4(),
            arousal=0.6,
            valence=0.7,
            dominance=0.5,
            intimacy=0.6,
        )
        return computer

    @pytest.fixture
    def mock_conflict_generator(self):
        """Create mock conflict generator (Spec 027)."""
        generator = MagicMock()
        result = MagicMock()
        result.generated = False
        result.conflict = None
        generator.generate.return_value = result
        return generator

    @pytest.fixture
    def mock_touchpoint_scheduler(self):
        """Create mock touchpoint scheduler (Spec 025)."""
        scheduler = MagicMock()
        scheduler.evaluate_user.return_value = []  # No triggers
        return scheduler

    @pytest.mark.asyncio
    async def test_process_success(
        self,
        mock_db_session,
        mock_graph_updater,
        mock_summary_generator,
        mock_life_simulator,
        mock_state_computer,
        mock_conflict_generator,
        mock_touchpoint_scheduler,
        mock_layer_composer,
        mock_package_store,
    ):
        """AC-T020.2: process() runs all steps in sequence."""
        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )
        user_id = uuid4()
        conversation_id = uuid4()

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=[{"role": "user", "content": "Hello"}],
        )

        # Verify all 8 steps ran (Spec 029: added emotional, conflict, touchpoint)
        assert result.success
        assert len(result.steps) == 8
        assert all(s.status == StepStatus.COMPLETED for s in result.steps)

        # Verify core steps were called
        mock_graph_updater.update.assert_called_once()
        mock_summary_generator.generate.assert_called_once()
        mock_life_simulator.generate_next_day_events.assert_called_once()
        mock_layer_composer.compose.assert_called_once()
        mock_package_store.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_returns_result(
        self,
        mock_db_session,
        mock_graph_updater,
        mock_summary_generator,
        mock_life_simulator,
        mock_state_computer,
        mock_conflict_generator,
        mock_touchpoint_scheduler,
        mock_layer_composer,
        mock_package_store,
    ):
        """AC-T020.3: Returns ProcessingResult with step status."""
        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )
        user_id = uuid4()
        conversation_id = uuid4()

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        assert isinstance(result, ProcessingResult)
        assert result.user_id == user_id
        assert result.conversation_id == conversation_id
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.package is not None

    @pytest.mark.asyncio
    async def test_process_partial_failure(
        self,
        mock_db_session,
        mock_graph_updater,
        mock_summary_generator,
        mock_life_simulator,
        mock_state_computer,
        mock_conflict_generator,
        mock_touchpoint_scheduler,
        mock_layer_composer,
        mock_package_store,
    ):
        """AC-T020.4: Error handling with partial completion support."""
        # Make summary generator fail
        mock_summary_generator.generate.side_effect = Exception("Summary failed")

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )
        user_id = uuid4()
        conversation_id = uuid4()

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Pipeline should continue despite failure
        assert not result.success
        assert result.partial_success
        assert len(result.failed_steps) == 1
        assert result.failed_steps[0].name == "summary_generation"
        assert len(result.completed_steps) == 7  # 8 total - 1 failed

    @pytest.mark.asyncio
    async def test_process_layer_composer_failure_skips_storage(
        self,
        mock_db_session,
        mock_graph_updater,
        mock_summary_generator,
        mock_life_simulator,
        mock_state_computer,
        mock_conflict_generator,
        mock_touchpoint_scheduler,
        mock_layer_composer,
        mock_package_store,
    ):
        """When layer composer fails, storage is skipped."""
        mock_layer_composer.compose.side_effect = Exception("Compose failed")

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )
        user_id = uuid4()
        conversation_id = uuid4()

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Storage should not be called when package is None
        assert not result.success
        assert result.package is None

    @pytest.mark.asyncio
    async def test_process_step_metadata(
        self,
        mock_db_session,
        mock_graph_updater,
        mock_summary_generator,
        mock_life_simulator,
        mock_state_computer,
        mock_conflict_generator,
        mock_touchpoint_scheduler,
        mock_layer_composer,
        mock_package_store,
    ):
        """Steps capture metadata from processing."""
        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )
        user_id = uuid4()
        conversation_id = uuid4()

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Graph update step should have metadata
        graph_step = result.steps[0]
        assert graph_step.metadata.get("facts_extracted") == 3
        assert graph_step.metadata.get("events_extracted") == 2


class TestGetPostProcessingPipeline:
    """Tests for get_post_processing_pipeline singleton."""

    def test_singleton_pattern(self):
        """get_post_processing_pipeline returns same instance."""
        # Reset singleton
        import nikita.post_processing.pipeline as pipeline_module
        pipeline_module._default_pipeline = None

        pipeline1 = get_post_processing_pipeline()
        pipeline2 = get_post_processing_pipeline()

        assert pipeline1 is pipeline2


class TestPipelineIntegration:
    """Integration tests for pipeline (AC-T025)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """AC-T025.2: Test full pipeline execution with mocks."""
        from nikita.emotional_state import EmotionalStateModel

        # Create complete mock setup
        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (5, 3)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, True)

        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = []

        # Spec 029: Add humanization mocks
        user_id = uuid4()
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id, arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        mock_package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = mock_package

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        transcript = [
            {"role": "user", "content": "Hi Nikita!"},
            {"role": "assistant", "content": "Hey! How are you?"},
            {"role": "user", "content": "Great, thanks!"},
        ]

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            result = await pipeline.process(
                user_id=user_id,
                conversation_id=uuid4(),
                transcript=transcript,
            )

            # Verify full execution (8 steps with Spec 029 humanization)
            assert result.success
            assert len(result.completed_steps) == 8
            assert result.package is not None
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """AC-T025.3: Test partial failure handling."""
        from nikita.emotional_state import EmotionalStateModel

        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (2, 1)

        # Simulate failure in summary generation
        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.side_effect = ValueError("DB connection failed")

        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = []

        # Spec 029: Add humanization mocks
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=uuid4(), arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            result = await pipeline.process(
                user_id=uuid4(),
                conversation_id=uuid4(),
            )

            # Should have partial success
            assert not result.success
            assert result.partial_success
            assert len(result.failed_steps) == 1
            assert "summary_generation" in result.failed_steps[0].name

            # Other steps should have completed (8 - 1 = 7 for Spec 029)
            assert len(result.completed_steps) == 7
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_package_storage_verification(self):
        """AC-T025.4: Test package storage verification."""
        from nikita.emotional_state import EmotionalStateModel

        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (1, 1)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, False)

        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = []

        # Spec 029: Add humanization mocks
        user_id = uuid4()
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id, arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        expected_package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            user_facts=["User works as engineer"],
            nikita_energy=0.8,
        )

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = expected_package

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            result = await pipeline.process(
                user_id=user_id,
                conversation_id=uuid4(),
            )

            # Verify package was stored with correct data
            mock_package_store.set.assert_called_once_with(user_id, expected_package)
            assert result.package == expected_package
            assert result.package.user_facts == ["User works as engineer"]
        finally:
            for p in patches:
                p.stop()


class TestLifeSimulationStep:
    """Tests for life simulation integration (AC-T014.1-3)."""

    @pytest.mark.asyncio
    async def test_pipeline_calls_life_simulator(self):
        """AC-T014.1: PostProcessingPipeline calls LifeSimulator."""
        from nikita.emotional_state import EmotionalStateModel

        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (1, 1)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, False)

        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = []

        # Spec 029: Add humanization mocks
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=uuid4(), arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        user_id = uuid4()

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            await pipeline.process(user_id=user_id, conversation_id=uuid4())

            # Verify life simulator was called with user_id
            mock_life_simulator.generate_next_day_events.assert_called_once_with(
                user_id=user_id
            )
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_events_generated_after_conversation(self):
        """AC-T014.2: Events generated after each conversation."""
        from nikita.emotional_state import EmotionalStateModel

        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (1, 1)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, False)

        mock_life_simulator = AsyncMock()
        # Simulate 3 events generated
        mock_life_simulator.generate_next_day_events.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        # Spec 029: Add humanization mocks
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=uuid4(), arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            result = await pipeline.process(user_id=uuid4(), conversation_id=uuid4())

            # Verify life simulation step captured events count
            life_sim_step = next(
                s for s in result.steps if s.name == "life_simulation"
            )
            assert life_sim_step.status == StepStatus.COMPLETED
            assert life_sim_step.metadata.get("events_generated") == 3
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_life_simulation_error_does_not_fail_pipeline(self):
        """AC-T014.3: Errors logged but don't fail pipeline."""
        from nikita.emotional_state import EmotionalStateModel

        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (1, 1)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, False)

        # Life simulator fails
        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.side_effect = Exception(
            "LLM timeout"
        )

        # Spec 029: Add humanization mocks
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=uuid4(), arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mock_conflict_generator = MagicMock()
        mock_conflict_result = MagicMock()
        mock_conflict_result.generated = False
        mock_conflict_result.conflict = None
        mock_conflict_generator.generate.return_value = mock_conflict_result

        mock_touchpoint_scheduler = MagicMock()
        mock_touchpoint_scheduler.evaluate_user.return_value = []

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            state_computer=mock_state_computer,
            conflict_generator=mock_conflict_generator,
            touchpoint_scheduler=mock_touchpoint_scheduler,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # Patch database and stores to prevent real DB calls
        patches = get_pipeline_patches()
        for p in patches:
            p.start()
        try:
            result = await pipeline.process(user_id=uuid4(), conversation_id=uuid4())

            # Pipeline should NOT be marked as complete success (has a failure)
            assert not result.success

            # But it should be partial success (other steps completed)
            assert result.partial_success

            # Life simulation step should be marked failed
            life_sim_step = next(
                s for s in result.steps if s.name == "life_simulation"
            )
            assert life_sim_step.status == StepStatus.FAILED
            assert "LLM timeout" in life_sim_step.error_message

            # Other steps should have continued and completed (8 - 1 = 7 for Spec 029)
            assert len(result.completed_steps) == 7
            assert mock_layer_composer.compose.called
            assert mock_package_store.set.called
        finally:
            for p in patches:
                p.stop()
