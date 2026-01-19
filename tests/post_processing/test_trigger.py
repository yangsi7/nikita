"""Tests for Pipeline Trigger (Spec 021, T024).

AC-T024.1: ConversationRepository.save() triggers pipeline via BackgroundTasks
AC-T024.2: Pipeline runs async (non-blocking)
AC-T024.3: Logging for pipeline trigger
AC-T024.4: Feature flag `enable_post_processing_pipeline`
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.post_processing.trigger import (
    add_pipeline_trigger_to_background_tasks,
    is_pipeline_enabled,
    trigger_pipeline,
    trigger_pipeline_background,
)


class TestIsPipelineEnabled:
    """Tests for is_pipeline_enabled function."""

    def test_returns_true_by_default(self):
        """AC-T024.4: Pipeline is enabled by default."""
        with patch("nikita.post_processing.trigger.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                enable_post_processing_pipeline=True
            )
            assert is_pipeline_enabled()

    def test_returns_false_when_disabled(self):
        """AC-T024.4: Feature flag can disable pipeline."""
        with patch("nikita.post_processing.trigger.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                enable_post_processing_pipeline=False
            )
            assert not is_pipeline_enabled()


class TestTriggerPipeline:
    """Tests for trigger_pipeline function."""

    @pytest.mark.asyncio
    async def test_trigger_when_enabled(self):
        """AC-T024.2: Pipeline runs when enabled."""
        user_id = uuid4()
        conversation_id = uuid4()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.completed_steps = [MagicMock(), MagicMock()]
        mock_result.failed_steps = []

        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=True), \
             patch("nikita.post_processing.trigger.get_post_processing_pipeline", return_value=mock_pipeline):

            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            assert result == mock_result
            mock_pipeline.process.assert_called_once_with(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=None,
            )

    @pytest.mark.asyncio
    async def test_trigger_when_disabled(self):
        """Pipeline doesn't run when disabled."""
        user_id = uuid4()
        conversation_id = uuid4()

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=False):
            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_trigger_with_transcript(self):
        """Pipeline receives transcript when provided."""
        user_id = uuid4()
        conversation_id = uuid4()
        transcript = [{"role": "user", "content": "Hello"}]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.completed_steps = []
        mock_result.failed_steps = []

        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=True), \
             patch("nikita.post_processing.trigger.get_post_processing_pipeline", return_value=mock_pipeline):

            await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=transcript,
            )

            mock_pipeline.process.assert_called_once_with(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=transcript,
            )

    @pytest.mark.asyncio
    async def test_trigger_handles_exception(self):
        """AC-T024.3: Logs and handles exceptions."""
        user_id = uuid4()
        conversation_id = uuid4()

        mock_pipeline = AsyncMock()
        mock_pipeline.process.side_effect = Exception("Pipeline failed")

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=True), \
             patch("nikita.post_processing.trigger.get_post_processing_pipeline", return_value=mock_pipeline):

            result = await trigger_pipeline(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            # Should return None on exception
            assert result is None


class TestTriggerPipelineBackground:
    """Tests for trigger_pipeline_background function."""

    @pytest.mark.asyncio
    async def test_background_catches_exceptions(self):
        """Background wrapper catches all exceptions."""
        user_id = uuid4()
        conversation_id = uuid4()

        with patch("nikita.post_processing.trigger.trigger_pipeline") as mock_trigger:
            mock_trigger.side_effect = Exception("Something failed")

            # Should not raise
            await trigger_pipeline_background(
                user_id=user_id,
                conversation_id=conversation_id,
            )


class TestAddPipelineTriggerToBackgroundTasks:
    """Tests for add_pipeline_trigger_to_background_tasks function."""

    def test_adds_task_when_enabled(self):
        """AC-T024.1: Adds task to BackgroundTasks when enabled."""
        user_id = uuid4()
        conversation_id = uuid4()
        background_tasks = MagicMock()

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=True):
            add_pipeline_trigger_to_background_tasks(
                background_tasks=background_tasks,
                user_id=user_id,
                conversation_id=conversation_id,
            )

            background_tasks.add_task.assert_called_once()

    def test_does_not_add_when_disabled(self):
        """Doesn't add task when pipeline disabled."""
        user_id = uuid4()
        conversation_id = uuid4()
        background_tasks = MagicMock()

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=False):
            add_pipeline_trigger_to_background_tasks(
                background_tasks=background_tasks,
                user_id=user_id,
                conversation_id=conversation_id,
            )

            background_tasks.add_task.assert_not_called()

    def test_passes_transcript(self):
        """Transcript is passed to background task."""
        user_id = uuid4()
        conversation_id = uuid4()
        transcript = [{"role": "user", "content": "Test"}]
        background_tasks = MagicMock()

        with patch("nikita.post_processing.trigger.is_pipeline_enabled", return_value=True):
            add_pipeline_trigger_to_background_tasks(
                background_tasks=background_tasks,
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=transcript,
            )

            # Verify transcript was passed
            call_args = background_tasks.add_task.call_args
            assert call_args.kwargs.get("transcript") == transcript
