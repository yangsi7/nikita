"""Tests for PsychologyStage.

Verifies Stage 2.5 (psychology analysis) functionality:
- Analyzing conversation dynamics
- Generating psychological insights
- Creating psychological thoughts
- Handling errors gracefully
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.psychology import PsychologyInput, PsychologyResult, PsychologyStage


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
def mock_conversation():
    """Create mock conversation."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = uuid4()
    conv.started_at = datetime.now(UTC)
    conv.messages = [
        {"role": "user", "content": "Hey, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thanks for asking!"},
    ]
    return conv


@pytest.fixture
def mock_extraction():
    """Create mock extraction result."""
    extraction = MagicMock()
    extraction.summary = "A pleasant conversation"
    return extraction


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock()
    user.chapter = 2
    user.relationship_score = 65.0
    return user


class TestPsychologyStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'psychology'."""
        with patch("nikita.db.repositories.user_repository.UserRepository"), \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository"):
            stage = PsychologyStage(mock_session, mock_logger)
            assert stage.name == "psychology"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        with patch("nikita.db.repositories.user_repository.UserRepository"), \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository"):
            stage = PsychologyStage(mock_session, mock_logger)
            assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 30 seconds."""
        with patch("nikita.db.repositories.user_repository.UserRepository"), \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository"):
            stage = PsychologyStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 30.0

    def test_max_retries(self, mock_session, mock_logger):
        """Verify max retries is 2."""
        with patch("nikita.db.repositories.user_repository.UserRepository"), \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository"):
            stage = PsychologyStage(mock_session, mock_logger)
            assert stage.max_retries == 2


class TestPsychologyAnalysis:
    """Test psychology analysis functionality."""

    @pytest.mark.asyncio
    async def test_successful_analysis(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
        mock_user,
    ):
        """Verify successful psychology analysis."""
        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_user_repo_cls, \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository") as mock_thought_repo_cls, \
             patch("nikita.context.relationship_analyzer.get_relationship_analyzer") as mock_get_analyzer:
            # Setup mocks
            mock_user_repo = AsyncMock()
            mock_user_repo.get = AsyncMock(return_value=mock_user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_thought_repo = AsyncMock()
            mock_thought_repo_cls.return_value = mock_thought_repo

            # Mock analyzer
            mock_dynamics = MagicMock()
            mock_dynamics.detected_triggers = []

            mock_health = MagicMock()
            mock_health.health_rating = "healthy"

            mock_insight = MagicMock()
            mock_insight.nikita_emotional_state = "secure"
            mock_insight.emotional_temperature = 0.5

            mock_analyzer = MagicMock()
            mock_analyzer.analyze_conversation.return_value = mock_dynamics
            mock_analyzer.calculate_relationship_health.return_value = mock_health
            mock_analyzer.generate_psychological_insight.return_value = mock_insight
            mock_get_analyzer.return_value = mock_analyzer

            stage = PsychologyStage(mock_session, mock_logger)

            input_data = PsychologyInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert isinstance(result, PsychologyResult)
            assert result.insight == mock_insight
            assert result.health == mock_health
            mock_analyzer.analyze_conversation.assert_called_once()
            mock_analyzer.calculate_relationship_health.assert_called_once()
            mock_analyzer.generate_psychological_insight.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_thoughts_when_triggers_detected(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
        mock_user,
    ):
        """Verify psychological thoughts created when triggers detected."""
        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_user_repo_cls, \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository") as mock_thought_repo_cls, \
             patch("nikita.context.relationship_analyzer.get_relationship_analyzer") as mock_get_analyzer, \
             patch("nikita.db.models.context.THOUGHT_TYPES", {"worry", "reflection", "anticipation", "desire"}):
            # Setup mocks
            mock_user_repo = AsyncMock()
            mock_user_repo.get = AsyncMock(return_value=mock_user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_thought_repo = AsyncMock()
            mock_thought_repo.bulk_create_thoughts = AsyncMock()
            mock_thought_repo_cls.return_value = mock_thought_repo

            # Mock analyzer with triggers
            mock_dynamics = MagicMock()
            mock_dynamics.detected_triggers = ["abandonment", "criticism"]

            mock_health = MagicMock()
            mock_health.health_rating = "at_risk"

            mock_insight = MagicMock()
            mock_insight.nikita_emotional_state = "anxious"
            mock_insight.emotional_temperature = 0.1
            mock_insight.healing_opportunity = None
            mock_insight.healing_context = None

            mock_analyzer = MagicMock()
            mock_analyzer.analyze_conversation.return_value = mock_dynamics
            mock_analyzer.calculate_relationship_health.return_value = mock_health
            mock_analyzer.generate_psychological_insight.return_value = mock_insight
            mock_get_analyzer.return_value = mock_analyzer

            stage = PsychologyStage(mock_session, mock_logger)

            input_data = PsychologyInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            await stage._run(pipeline_context, input_data)

            # Should have created thoughts
            mock_thought_repo.bulk_create_thoughts.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_returns_defaults_on_error(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify returns default insight/health on error."""
        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_user_repo_cls, \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository") as mock_thought_repo_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get = AsyncMock(side_effect=RuntimeError("Database error"))
            mock_user_repo_cls.return_value = mock_user_repo

            mock_thought_repo_cls.return_value = AsyncMock()

            stage = PsychologyStage(mock_session, mock_logger)

            input_data = PsychologyInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            # Should not raise - returns defaults
            result = await stage._run(pipeline_context, input_data)

            assert isinstance(result, PsychologyResult)
            assert result.insight.nikita_emotional_state == "neutral"
            assert result.insight.emotional_temperature == 0.0
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_handles_user_not_found(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify handles missing user gracefully."""
        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_user_repo_cls, \
             patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository") as mock_thought_repo_cls, \
             patch("nikita.context.relationship_analyzer.get_relationship_analyzer") as mock_get_analyzer:
            # User returns None
            mock_user_repo = AsyncMock()
            mock_user_repo.get = AsyncMock(return_value=None)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_thought_repo_cls.return_value = AsyncMock()

            # Mock analyzer
            mock_dynamics = MagicMock()
            mock_dynamics.detected_triggers = []

            mock_health = MagicMock()
            mock_health.health_rating = "healthy"

            mock_insight = MagicMock()
            mock_insight.nikita_emotional_state = "neutral"
            mock_insight.emotional_temperature = 0.0

            mock_analyzer = MagicMock()
            mock_analyzer.analyze_conversation.return_value = mock_dynamics
            mock_analyzer.calculate_relationship_health.return_value = mock_health
            mock_analyzer.generate_psychological_insight.return_value = mock_insight
            mock_get_analyzer.return_value = mock_analyzer

            stage = PsychologyStage(mock_session, mock_logger)

            input_data = PsychologyInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            # Should use default chapter=1, relationship_score=50.0
            result = await stage._run(pipeline_context, input_data)

            assert isinstance(result, PsychologyResult)
            # Analyzer should have been called with defaults
            mock_analyzer.analyze_conversation.assert_called_once()
            call_kwargs = mock_analyzer.analyze_conversation.call_args.kwargs
            assert call_kwargs["user_chapter"] == 1
            assert call_kwargs["relationship_score"] == 50.0
