"""Tests for NarrativeArcsStage.

Verifies Stage 2.6 (narrative arcs) functionality:
- Starting new arcs
- Incrementing arc conversation counts
- Advancing arc stages
- Completing arcs
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.narrative_arcs import (
    NarrativeArcsInput,
    NarrativeArcsResult,
    NarrativeArcsStage,
)


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_logger():
    """Create mock structlog logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def pipeline_context():
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 2
    return user


@pytest.fixture
def mock_conversation():
    """Create mock conversation."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = uuid4()
    return conv


class TestNarrativeArcsStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'narrative_arcs'."""
        stage = NarrativeArcsStage(mock_session, mock_logger)
        assert stage.name == "narrative_arcs"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        stage = NarrativeArcsStage(mock_session, mock_logger)
        assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 20 seconds."""
        stage = NarrativeArcsStage(mock_session, mock_logger)
        assert stage.timeout_seconds == 20.0

    def test_max_retries(self, mock_session, mock_logger):
        """Verify max retries is 2."""
        stage = NarrativeArcsStage(mock_session, mock_logger)
        assert stage.max_retries == 2


class TestNarrativeArcCreation:
    """Test arc creation logic."""

    @pytest.mark.asyncio
    async def test_creates_new_arc_when_under_limit(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_user,
        mock_conversation,
    ):
        """Verify new arc created when under 2 active arcs."""
        with patch("nikita.db.repositories.narrative_arc_repository.NarrativeArcRepository") as mock_repo_cls, \
             patch("nikita.life_simulation.arcs.get_arc_system") as mock_get_system:
            # Mock repo
            mock_repo = AsyncMock()
            mock_repo.get_active_arcs = AsyncMock(return_value=[])  # No active arcs
            mock_repo.create_arc = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            # Mock arc system
            mock_template = MagicMock()
            mock_template.name = "lost_childhood_friend"
            mock_template.category = MagicMock(value="reunion")
            mock_template.involved_characters = ["Alex"]
            mock_template.duration_conversations = (3, 7)

            mock_system = MagicMock()
            mock_system.should_start_new_arc.return_value = True
            mock_system.select_arc_template.return_value = mock_template
            mock_get_system.return_value = mock_system

            stage = NarrativeArcsStage(mock_session, mock_logger)
            # Force the arc to start by mocking random
            with patch.object(stage, "_should_start_arc", return_value=True):
                input_data = NarrativeArcsInput(
                    user=mock_user,
                    conversation=mock_conversation,
                    vulnerability_level=3,
                    days_since_last_arc=5,
                )

                result = await stage._run(pipeline_context, input_data)

            assert result.created == "lost_childhood_friend"
            assert result.arcs_updated >= 1
            mock_repo.create_arc.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_create_when_at_limit(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_user,
        mock_conversation,
    ):
        """Verify no new arc when already at 2 active."""
        with patch("nikita.db.repositories.narrative_arc_repository.NarrativeArcRepository") as mock_repo_cls, \
             patch("nikita.life_simulation.arcs.get_arc_system") as mock_get_system, \
             patch("nikita.life_simulation.arcs.ArcCategory") as mock_arc_category:
            # Mock ArcCategory enum
            mock_arc_category.side_effect = lambda x: x  # Pass through

            # Mock 2 active arcs - use MagicMock for category to avoid enum conversion
            mock_arc1 = MagicMock()
            mock_arc1.id = uuid4()
            mock_arc1.category = MagicMock()  # Not a string, so no conversion
            mock_arc1.template_name = "arc1"
            mock_arc1.conversations_in_arc = 1
            mock_arc1.max_conversations = 5
            mock_arc1.current_stage = "setup"

            mock_arc2 = MagicMock()
            mock_arc2.id = uuid4()
            mock_arc2.category = MagicMock()
            mock_arc2.template_name = "arc2"
            mock_arc2.conversations_in_arc = 1
            mock_arc2.max_conversations = 5
            mock_arc2.current_stage = "setup"

            mock_repo = AsyncMock()
            mock_repo.get_active_arcs = AsyncMock(return_value=[mock_arc1, mock_arc2])
            mock_repo.increment_conversation_count = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            mock_system = MagicMock()
            mock_get_system.return_value = mock_system

            stage = NarrativeArcsStage(mock_session, mock_logger)

            input_data = NarrativeArcsInput(
                user=mock_user,
                conversation=mock_conversation,
                vulnerability_level=3,
                days_since_last_arc=5,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.created is None
            # Should have incremented counts for existing arcs
            assert mock_repo.increment_conversation_count.call_count == 2


class TestArcProgression:
    """Test arc advancement and completion."""

    @pytest.mark.asyncio
    async def test_advances_arc_at_midpoint(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_user,
        mock_conversation,
    ):
        """Verify arc advances when at midpoint."""
        with patch("nikita.db.repositories.narrative_arc_repository.NarrativeArcRepository") as mock_repo_cls, \
             patch("nikita.life_simulation.arcs.get_arc_system") as mock_get_system, \
             patch("nikita.life_simulation.arcs.ArcCategory") as mock_arc_category:
            # Mock ArcCategory enum
            mock_arc_category.side_effect = lambda x: x

            # Mock arc at midpoint - use MagicMock for category
            mock_arc = MagicMock()
            mock_arc.id = uuid4()
            mock_arc.category = MagicMock()  # Not a string
            mock_arc.template_name = "test_arc"
            mock_arc.conversations_in_arc = 5  # At midpoint of 10
            mock_arc.max_conversations = 10
            mock_arc.current_stage = "rising"

            mock_repo = AsyncMock()
            mock_repo.get_active_arcs = AsyncMock(return_value=[mock_arc])
            mock_repo.increment_conversation_count = AsyncMock()
            mock_repo.advance_arc = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            mock_system = MagicMock()
            mock_system.should_start_new_arc.return_value = False
            mock_get_system.return_value = mock_system

            stage = NarrativeArcsStage(mock_session, mock_logger)

            input_data = NarrativeArcsInput(
                user=mock_user,
                conversation=mock_conversation,
                vulnerability_level=3,
                days_since_last_arc=5,
            )

            result = await stage._run(pipeline_context, input_data)

            assert "test_arc" in result.advanced
            mock_repo.advance_arc.assert_called_once_with(mock_arc.id)

    @pytest.mark.asyncio
    async def test_completes_arc_at_max(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_user,
        mock_conversation,
    ):
        """Verify arc completes when max conversations reached."""
        with patch("nikita.db.repositories.narrative_arc_repository.NarrativeArcRepository") as mock_repo_cls, \
             patch("nikita.life_simulation.arcs.get_arc_system") as mock_get_system, \
             patch("nikita.life_simulation.arcs.ArcCategory") as mock_arc_category:
            # Mock ArcCategory enum
            mock_arc_category.side_effect = lambda x: x

            # Mock arc at max - use MagicMock for category
            mock_arc = MagicMock()
            mock_arc.id = uuid4()
            mock_arc.category = MagicMock()  # Not a string
            mock_arc.template_name = "finished_arc"
            mock_arc.conversations_in_arc = 10  # At max
            mock_arc.max_conversations = 10
            mock_arc.current_stage = "climax"

            mock_repo = AsyncMock()
            mock_repo.get_active_arcs = AsyncMock(return_value=[mock_arc])
            mock_repo.increment_conversation_count = AsyncMock()
            mock_repo.resolve_arc = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            mock_system = MagicMock()
            mock_system.should_start_new_arc.return_value = False
            mock_get_system.return_value = mock_system

            stage = NarrativeArcsStage(mock_session, mock_logger)

            input_data = NarrativeArcsInput(
                user=mock_user,
                conversation=mock_conversation,
                vulnerability_level=3,
                days_since_last_arc=5,
            )

            result = await stage._run(pipeline_context, input_data)

            assert "finished_arc" in result.completed
            mock_repo.resolve_arc.assert_called_once_with(
                arc_id=mock_arc.id,
                resolution="completed",
            )


class TestShouldStartArc:
    """Test the _should_start_arc helper."""

    def test_does_not_start_if_category_active(self, mock_session, mock_logger):
        """Verify does not start if category already active."""
        stage = NarrativeArcsStage(mock_session, mock_logger)

        category = "drama"
        active_categories = ["drama", "reunion"]

        result = stage._should_start_arc(category, active_categories, chance=1.0)
        assert result is False

    def test_starts_with_random_chance(self, mock_session, mock_logger):
        """Verify starts based on random chance."""
        stage = NarrativeArcsStage(mock_session, mock_logger)

        category = "drama"
        active_categories = ["reunion"]

        with patch("random.random", return_value=0.1):  # Below 0.3 threshold
            result = stage._should_start_arc(category, active_categories, chance=0.3)
        assert result is True

        with patch("random.random", return_value=0.5):  # Above 0.3 threshold
            result = stage._should_start_arc(category, active_categories, chance=0.3)
        assert result is False


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_returns_error_result_on_failure(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_user,
        mock_conversation,
    ):
        """Verify returns error result on failure."""
        with patch("nikita.db.repositories.narrative_arc_repository.NarrativeArcRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_active_arcs = AsyncMock(
                side_effect=RuntimeError("Database error")
            )
            mock_repo_cls.return_value = mock_repo

            stage = NarrativeArcsStage(mock_session, mock_logger)

            input_data = NarrativeArcsInput(
                user=mock_user,
                conversation=mock_conversation,
                vulnerability_level=3,
                days_since_last_arc=5,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.arcs_updated == 0
            assert "Database error" in result.error
            mock_logger.warning.assert_called()
