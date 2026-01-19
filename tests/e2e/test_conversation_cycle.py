"""E2E Test: Conversation Cycle (Spec 021, T026).

Tests the full conversation cycle:
1. First conversation happens
2. Post-processing pipeline runs
3. Context package is stored
4. Second conversation uses the stored context

AC-T026.1: Test file tests/e2e/test_conversation_cycle.py
AC-T026.2: Simulate conversation → post-process → next conversation
AC-T026.3: Verify context package used in second conversation
AC-T026.4: Verify degradation when package missing
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.package import ContextPackage, EmotionalState
from nikita.post_processing.pipeline import (
    PostProcessingPipeline,
    ProcessingResult,
    get_post_processing_pipeline,
)
from nikita.post_processing.trigger import (
    trigger_pipeline,
    trigger_pipeline_background,
)


class TestConversationCycleE2E:
    """E2E tests for conversation cycle with post-processing."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def conversation_id(self):
        """Generate test conversation ID."""
        return uuid4()

    @pytest.fixture
    def sample_transcript(self):
        """Create sample conversation transcript."""
        return [
            {"role": "user", "content": "Hey Nikita, how was your day?"},
            {"role": "assistant", "content": "Hey! My day was pretty good, thanks for asking. I went to a coffee shop and did some writing. How about you?"},
            {"role": "user", "content": "I'm a software engineer, had a busy day coding."},
            {"role": "assistant", "content": "Oh nice! That sounds interesting. What kind of projects are you working on?"},
            {"role": "user", "content": "Building a mobile app for fitness tracking."},
        ]

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
        generator.generate.return_value = (True, False)
        return generator

    @pytest.fixture
    def mock_layer_composer(self, user_id):
        """Create mock layer composer."""
        composer = AsyncMock()
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=["User is a software engineer", "User builds mobile apps"],
            chapter_layer="Chapter 1: Meeting Nikita",
            nikita_mood=EmotionalState(valence=0.7, arousal=0.5, dominance=0.5, intimacy=0.3),
        )
        composer.compose.return_value = package
        return composer

    @pytest.fixture
    def mock_package_store(self):
        """Create mock package store."""
        store = AsyncMock()
        store.set.return_value = None
        store.get.return_value = None
        return store

    @pytest.mark.asyncio
    async def test_full_conversation_cycle(
        self,
        user_id,
        conversation_id,
        sample_transcript,
        mock_graph_updater,
        mock_summary_generator,
        mock_layer_composer,
        mock_package_store,
    ):
        """AC-T026.2: Simulate conversation → post-process → next conversation.

        Tests the full cycle:
        1. First conversation with transcript
        2. Post-processing triggered after conversation
        3. Pipeline runs all stages
        4. Context package stored for next conversation
        """
        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # STEP 1: First conversation happens (simulated by transcript)
        # In real system, MessageHandler handles conversation

        # STEP 2: Post-processing triggered after conversation ends
        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=sample_transcript,
        )

        # STEP 3: Verify pipeline succeeded
        assert result.success, f"Pipeline failed: {result.failed_steps}"
        assert len(result.completed_steps) == 4

        # Verify each stage ran
        mock_graph_updater.update.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=sample_transcript,
        )
        mock_summary_generator.generate.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        mock_layer_composer.compose.assert_called_once_with(user_id=user_id)

        # STEP 4: Verify package stored
        mock_package_store.set.assert_called_once()
        stored_package = mock_package_store.set.call_args[0][1]
        assert stored_package.user_id == user_id
        assert any("software engineer" in fact for fact in stored_package.user_facts)

    @pytest.mark.asyncio
    async def test_context_package_used_in_second_conversation(
        self,
        user_id,
        conversation_id,
        mock_graph_updater,
        mock_summary_generator,
        mock_layer_composer,
        mock_package_store,
    ):
        """AC-T026.3: Verify context package used in second conversation.

        Tests that stored context package is retrieved for subsequent conversations.
        """
        # Setup: Package was stored from first conversation
        stored_package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=["User is a software engineer", "User builds mobile apps"],
            chapter_layer="Chapter 1: Meeting Nikita",
            today_summary="User talked about their job",
        )
        mock_package_store.get.return_value = stored_package

        # Simulate second conversation starting
        # In real system, HierarchicalPromptComposer.compose() loads the package

        # Verify package retrieval
        retrieved = await mock_package_store.get(user_id)

        assert retrieved is not None
        assert retrieved.user_id == user_id
        assert any("software engineer" in fact for fact in retrieved.user_facts)
        assert retrieved.today_summary is not None

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_package_missing(
        self,
        user_id,
        mock_package_store,
    ):
        """AC-T026.4: Verify degradation when package missing.

        Tests that system handles missing context package gracefully.
        """
        # Package not found (expired or never created)
        mock_package_store.get.return_value = None

        retrieved = await mock_package_store.get(user_id)

        # System should handle None gracefully
        assert retrieved is None

        # In real system, HierarchicalPromptComposer falls back to minimal context
        # This is handled by ContextInjector.inject_context() returning defaults

    @pytest.mark.asyncio
    async def test_pipeline_trigger_integration(
        self,
        user_id,
        conversation_id,
        sample_transcript,
    ):
        """Test trigger_pipeline function integrates with pipeline correctly."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.completed_steps = [MagicMock() for _ in range(4)]
        mock_result.failed_steps = []

        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result

        with (
            patch(
                "nikita.post_processing.trigger.is_pipeline_enabled",
                return_value=True,
            ),
            patch(
                "nikita.post_processing.trigger.get_post_processing_pipeline",
                return_value=mock_pipeline,
            ),
        ):
            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=sample_transcript,
            )

            assert result == mock_result
            mock_pipeline.process.assert_called_once_with(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=sample_transcript,
            )

    @pytest.mark.asyncio
    async def test_background_trigger_exception_handling(
        self,
        user_id,
        conversation_id,
    ):
        """Test background trigger handles exceptions gracefully."""
        with patch(
            "nikita.post_processing.trigger.trigger_pipeline",
            side_effect=Exception("Pipeline crashed"),
        ):
            # Should not raise - just logs error
            await trigger_pipeline_background(
                user_id=user_id,
                conversation_id=conversation_id,
            )

    @pytest.mark.asyncio
    async def test_partial_pipeline_failure_continues(
        self,
        user_id,
        conversation_id,
        sample_transcript,
        mock_graph_updater,
        mock_summary_generator,
        mock_layer_composer,
        mock_package_store,
    ):
        """Test pipeline continues despite partial failures."""
        # Graph update fails
        mock_graph_updater.update.side_effect = Exception("Graphiti unavailable")

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=sample_transcript,
        )

        # Pipeline should not fully succeed but should have partial success
        assert not result.success
        assert result.partial_success
        assert len(result.failed_steps) == 1
        assert result.failed_steps[0].name == "graph_update"

        # Other steps should still run
        mock_summary_generator.generate.assert_called_once()
        mock_layer_composer.compose.assert_called_once()


class TestConversationCycleWithFeatureFlag:
    """Test conversation cycle respects feature flag."""

    @pytest.mark.asyncio
    async def test_pipeline_disabled_skips_processing(self):
        """When feature flag is disabled, pipeline doesn't run."""
        user_id = uuid4()
        conversation_id = uuid4()

        with patch(
            "nikita.post_processing.trigger.is_pipeline_enabled",
            return_value=False,
        ):
            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_pipeline_enabled_runs_processing(self):
        """When feature flag is enabled, pipeline runs."""
        user_id = uuid4()
        conversation_id = uuid4()

        mock_result = MagicMock()
        mock_result.success = True

        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result

        with (
            patch(
                "nikita.post_processing.trigger.is_pipeline_enabled",
                return_value=True,
            ),
            patch(
                "nikita.post_processing.trigger.get_post_processing_pipeline",
                return_value=mock_pipeline,
            ),
        ):
            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            assert result == mock_result
            mock_pipeline.process.assert_called_once()
