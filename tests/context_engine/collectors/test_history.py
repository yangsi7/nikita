"""Tests for HistoryCollector (Spec 039 Phase 1)."""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.context_engine.collectors.history import (
    HistoryCollector,
    HistoryData,
)
from nikita.context_engine.collectors.base import CollectorContext


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def collector_context(mock_session):
    """Create collector context."""
    return CollectorContext(
        session=mock_session,
        user_id=uuid.uuid4(),
    )


@pytest.fixture
def mock_thread():
    """Create mock ConversationThread."""
    thread = MagicMock()
    thread.content = "What's your favorite movie?"
    thread.status = "open"
    thread.created_at = datetime.now(UTC) - timedelta(hours=2)
    return thread


@pytest.fixture
def mock_thought():
    """Create mock NikitaThought."""
    thought = MagicMock()
    thought.content = "I wonder if he's thinking about me..."
    return thought


@pytest.fixture
def mock_summary():
    """Create mock DailySummary."""
    summary = MagicMock()
    summary.summary_text = "Great conversation about travel plans"
    summary.nikita_summary_text = None
    summary.key_moments = [{"description": "Discussed Paris trip"}]
    summary.date = date.today()
    return summary


class TestHistoryData:
    """Tests for HistoryData model."""

    def test_default_values(self):
        """Test default empty values."""
        data = HistoryData()
        assert data.open_threads == []
        assert data.thread_count_by_type == {}
        assert data.recent_thoughts == []
        assert data.today_summary is None
        assert data.today_key_moments == []
        assert data.week_summaries == []
        assert data.last_conversation_summary is None

    def test_with_data(self):
        """Test with actual data."""
        from nikita.context_engine.models import ThreadInfo

        data = HistoryData(
            open_threads=[
                ThreadInfo(
                    topic="What's your favorite movie?",
                    status="open",
                    priority=4,
                    age_hours=2.0,
                )
            ],
            thread_count_by_type={"question": 1, "follow_up": 2},
            recent_thoughts=["I wonder about him..."],
            today_summary="Had a fun chat today",
            today_key_moments=["Laughed about the coffee incident"],
            week_summaries=["Monday: Talked about work"],
        )
        assert len(data.open_threads) == 1
        assert data.thread_count_by_type["question"] == 1
        assert len(data.recent_thoughts) == 1


class TestHistoryCollector:
    """Tests for HistoryCollector."""

    def test_collector_name(self):
        """Test collector name is 'history'."""
        collector = HistoryCollector()
        assert collector.name == "history"

    def test_collector_timeout(self):
        """Test timeout is 5s."""
        collector = HistoryCollector()
        assert collector.timeout_seconds == 5.0

    def test_max_retries(self):
        """Test max retries is 2."""
        collector = HistoryCollector()
        assert collector.max_retries == 2

    @pytest.mark.asyncio
    async def test_collect_empty_history(self, collector_context):
        """Test collecting from empty history."""
        collector = HistoryCollector()

        mock_thread_repo = AsyncMock()
        mock_thread_repo.get_threads_for_prompt.return_value = {}

        mock_thought_repo = AsyncMock()
        mock_thought_repo.get_active_thoughts.return_value = []

        mock_summary_repo = AsyncMock()
        mock_summary_repo.get_by_date.return_value = None
        mock_summary_repo.get_range.return_value = []
        mock_summary_repo.get_recent.return_value = []

        with (
            patch(
                "nikita.context_engine.collectors.history.ConversationThreadRepository",
                return_value=mock_thread_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.NikitaThoughtRepository",
                return_value=mock_thought_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.DailySummaryRepository",
                return_value=mock_summary_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert isinstance(result, HistoryData)
        assert result.open_threads == []
        assert result.recent_thoughts == []
        assert result.today_summary is None

    @pytest.mark.asyncio
    async def test_collect_with_threads(self, collector_context, mock_thread):
        """Test collecting threads with priority calculation."""
        collector = HistoryCollector()

        mock_thread_repo = AsyncMock()
        mock_thread_repo.get_threads_for_prompt.return_value = {
            "question": [mock_thread],
            "follow_up": [],
        }

        mock_thought_repo = AsyncMock()
        mock_thought_repo.get_active_thoughts.return_value = []

        mock_summary_repo = AsyncMock()
        mock_summary_repo.get_by_date.return_value = None
        mock_summary_repo.get_range.return_value = []
        mock_summary_repo.get_recent.return_value = []

        with (
            patch(
                "nikita.context_engine.collectors.history.ConversationThreadRepository",
                return_value=mock_thread_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.NikitaThoughtRepository",
                return_value=mock_thought_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.DailySummaryRepository",
                return_value=mock_summary_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert len(result.open_threads) == 1
        assert result.open_threads[0].topic == "What's your favorite movie?"
        assert result.thread_count_by_type["question"] == 1

    @pytest.mark.asyncio
    async def test_collect_with_thoughts(self, collector_context, mock_thought):
        """Test collecting Nikita's thoughts."""
        collector = HistoryCollector()

        mock_thread_repo = AsyncMock()
        mock_thread_repo.get_threads_for_prompt.return_value = {}

        mock_thought_repo = AsyncMock()
        mock_thought_repo.get_active_thoughts.return_value = [mock_thought]

        mock_summary_repo = AsyncMock()
        mock_summary_repo.get_by_date.return_value = None
        mock_summary_repo.get_range.return_value = []
        mock_summary_repo.get_recent.return_value = []

        with (
            patch(
                "nikita.context_engine.collectors.history.ConversationThreadRepository",
                return_value=mock_thread_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.NikitaThoughtRepository",
                return_value=mock_thought_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.DailySummaryRepository",
                return_value=mock_summary_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert len(result.recent_thoughts) == 1
        assert "wonder if he's thinking" in result.recent_thoughts[0]

    @pytest.mark.asyncio
    async def test_collect_with_today_summary(self, collector_context, mock_summary):
        """Test collecting today's summary and key moments."""
        collector = HistoryCollector()

        mock_thread_repo = AsyncMock()
        mock_thread_repo.get_threads_for_prompt.return_value = {}

        mock_thought_repo = AsyncMock()
        mock_thought_repo.get_active_thoughts.return_value = []

        mock_summary_repo = AsyncMock()
        mock_summary_repo.get_by_date.return_value = mock_summary
        mock_summary_repo.get_range.return_value = []
        mock_summary_repo.get_recent.return_value = [mock_summary]

        with (
            patch(
                "nikita.context_engine.collectors.history.ConversationThreadRepository",
                return_value=mock_thread_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.NikitaThoughtRepository",
                return_value=mock_thought_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.DailySummaryRepository",
                return_value=mock_summary_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert result.today_summary == "Great conversation about travel plans"
        assert len(result.today_key_moments) == 1
        assert "Paris trip" in result.today_key_moments[0]

    @pytest.mark.asyncio
    async def test_collect_with_week_summaries(self, collector_context):
        """Test collecting past week summaries."""
        collector = HistoryCollector()

        mock_thread_repo = AsyncMock()
        mock_thread_repo.get_threads_for_prompt.return_value = {}

        mock_thought_repo = AsyncMock()
        mock_thought_repo.get_active_thoughts.return_value = []

        # Create mock summaries for different days
        monday_summary = MagicMock()
        monday_summary.summary_text = "Work stress discussion"
        monday_summary.nikita_summary_text = None
        monday_summary.date = date.today() - timedelta(days=2)

        tuesday_summary = MagicMock()
        tuesday_summary.summary_text = None
        tuesday_summary.nikita_summary_text = "Had a lovely chat about music"
        tuesday_summary.date = date.today() - timedelta(days=1)

        mock_summary_repo = AsyncMock()
        mock_summary_repo.get_by_date.return_value = None
        mock_summary_repo.get_range.return_value = [monday_summary, tuesday_summary]
        mock_summary_repo.get_recent.return_value = [tuesday_summary]

        with (
            patch(
                "nikita.context_engine.collectors.history.ConversationThreadRepository",
                return_value=mock_thread_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.NikitaThoughtRepository",
                return_value=mock_thought_repo,
            ),
            patch(
                "nikita.context_engine.collectors.history.DailySummaryRepository",
                return_value=mock_summary_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert len(result.week_summaries) == 2

    def test_calculate_priority_question_recent(self):
        """Test priority calculation for recent question (highest)."""
        collector = HistoryCollector()
        # Recent question (<1 hour) gets base 4 + 2 = 5 (capped)
        priority = collector._calculate_priority("question", 0.5)
        assert priority == 5

    def test_calculate_priority_question_day_old(self):
        """Test priority for day-old question."""
        collector = HistoryCollector()
        # 12-hour old question gets base 4 + 1 = 5
        priority = collector._calculate_priority("question", 12)
        assert priority == 5

    def test_calculate_priority_question_old(self):
        """Test priority for old question (>72h)."""
        collector = HistoryCollector()
        # 100-hour old question gets base 4 - 1 = 3
        priority = collector._calculate_priority("question", 100)
        assert priority == 3

    def test_calculate_priority_topic(self):
        """Test priority for topic thread (lowest base)."""
        collector = HistoryCollector()
        # Topic has base priority 1
        priority = collector._calculate_priority("topic", 24)
        assert priority == 1

    def test_calculate_priority_unknown_type(self):
        """Test priority for unknown thread type defaults to 1."""
        collector = HistoryCollector()
        priority = collector._calculate_priority("unknown", 10)
        assert priority == 2  # base 1 + 1 for <24h

    def test_get_fallback(self):
        """Test fallback returns empty HistoryData."""
        collector = HistoryCollector()
        fallback = collector.get_fallback()

        assert isinstance(fallback, HistoryData)
        assert fallback.open_threads == []
        assert fallback.recent_thoughts == []
        assert fallback.today_summary is None
        assert fallback.week_summaries == []
