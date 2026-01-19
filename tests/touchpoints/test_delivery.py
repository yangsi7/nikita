"""Delivery tests for Proactive Touchpoint System (Spec 025, Phase E: T021-T025).

Tests:
- T021: TouchpointEngine.deliver()
- T022: pg_cron job configuration (SQL scripts)
- T023: Telegram delivery integration
- T024: Deduplication logic
- T025: Phase E coverage
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.touchpoints.engine import DeliveryResult, TouchpointEngine, deliver_due_touchpoints
from nikita.touchpoints.models import (
    ScheduledTouchpoint,
    TouchpointConfig,
    TriggerContext,
    TriggerType,
)
from nikita.touchpoints.silence import SilenceReason


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create mock AsyncSession."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_store():
    """Create mock TouchpointStore."""
    return MagicMock()


@pytest.fixture
def mock_scheduler():
    """Create mock TouchpointScheduler."""
    return MagicMock()


@pytest.fixture
def mock_generator():
    """Create mock MessageGenerator."""
    return MagicMock()


@pytest.fixture
def mock_silence():
    """Create mock StrategicSilence."""
    return MagicMock()


@pytest.fixture
def sample_touchpoint():
    """Create a sample touchpoint for testing."""
    return ScheduledTouchpoint(
        touchpoint_id=uuid4(),
        user_id=uuid4(),
        trigger_type=TriggerType.TIME,
        trigger_context=TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            chapter=2,
        ),
        message_content="hey there :)",
        delivery_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )


@pytest.fixture
def engine_with_mocks(mock_session, mock_store, mock_scheduler, mock_generator, mock_silence):
    """Create engine with all dependencies mocked."""
    with patch("nikita.touchpoints.engine.TouchpointStore") as store_class, \
         patch("nikita.touchpoints.engine.TouchpointScheduler") as sched_class, \
         patch("nikita.touchpoints.engine.MessageGenerator") as gen_class, \
         patch("nikita.touchpoints.engine.StrategicSilence") as silence_class:

        store_class.return_value = mock_store
        sched_class.return_value = mock_scheduler
        gen_class.return_value = mock_generator
        silence_class.return_value = mock_silence

        engine = TouchpointEngine(mock_session)
        engine.store = mock_store
        engine.scheduler = mock_scheduler
        engine.generator = mock_generator
        engine.silence = mock_silence

        yield engine


# =============================================================================
# T021: TouchpointEngine Tests (AC-T021.1 - AC-T021.4)
# =============================================================================


class TestTouchpointEngineClass:
    """Test TouchpointEngine class structure."""

    def test_engine_exists(self, mock_session):
        """AC-T021.1: TouchpointEngine class exists."""
        with patch("nikita.touchpoints.engine.TouchpointStore"), \
             patch("nikita.touchpoints.engine.MessageGenerator"), \
             patch("nikita.touchpoints.engine.TouchpointScheduler"), \
             patch("nikita.touchpoints.engine.StrategicSilence"):
            engine = TouchpointEngine(mock_session)
            assert engine is not None

    def test_engine_has_session(self, engine_with_mocks, mock_session):
        """Engine stores session."""
        assert engine_with_mocks.session is mock_session

    def test_engine_has_config(self, engine_with_mocks):
        """Engine has config."""
        assert engine_with_mocks.config is not None
        assert isinstance(engine_with_mocks.config, TouchpointConfig)

    def test_engine_has_min_gap(self, engine_with_mocks):
        """Engine has min_gap_minutes."""
        assert engine_with_mocks.min_gap_minutes > 0


class TestDeliverDueTouchpoints:
    """Test deliver_due_touchpoints() method (AC-T021.2)."""

    @pytest.mark.asyncio
    async def test_deliver_processes_queue(self, engine_with_mocks, sample_touchpoint):
        """AC-T021.2: deliver_due_touchpoints() processes queue."""
        engine_with_mocks.store.get_due_touchpoints = AsyncMock(
            return_value=[sample_touchpoint]
        )
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=False)
        )
        engine_with_mocks.store.mark_delivered = AsyncMock()

        with patch.object(engine_with_mocks, "_send_telegram_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            results = await engine_with_mocks.deliver_due_touchpoints()

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_deliver_empty_queue(self, engine_with_mocks):
        """Empty queue returns empty results."""
        engine_with_mocks.store.get_due_touchpoints = AsyncMock(return_value=[])

        results = await engine_with_mocks.deliver_due_touchpoints()

        assert results == []

    @pytest.mark.asyncio
    async def test_deliver_handles_error_gracefully(self, engine_with_mocks, sample_touchpoint):
        """AC-T021.3: Handles errors gracefully."""
        engine_with_mocks.store.get_due_touchpoints = AsyncMock(
            return_value=[sample_touchpoint]
        )
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(
            side_effect=Exception("Database error")
        )

        results = await engine_with_mocks.deliver_due_touchpoints()

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error is not None


class TestDeliverySingleTouchpoint:
    """Test single touchpoint delivery."""

    @pytest.mark.asyncio
    async def test_successful_delivery(self, engine_with_mocks, sample_touchpoint):
        """Successful delivery marks as delivered."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=False)
        )
        engine_with_mocks.store.mark_delivered = AsyncMock()

        with patch.object(engine_with_mocks, "_send_telegram_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is True
        engine_with_mocks.store.mark_delivered.assert_called_once()

    @pytest.mark.asyncio
    async def test_skipped_for_silence(self, engine_with_mocks, sample_touchpoint):
        """Touchpoint skipped for strategic silence."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=True, reason=SilenceReason.EMOTIONAL)
        )
        engine_with_mocks.store.mark_skipped = AsyncMock()

        result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is False
        assert result.skipped_reason == "emotional"
        engine_with_mocks.store.mark_skipped.assert_called_once()

    @pytest.mark.asyncio
    async def test_telegram_failure_marks_failed(self, engine_with_mocks, sample_touchpoint):
        """Telegram failure marks touchpoint for retry."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=False)
        )
        engine_with_mocks.store.mark_failed = AsyncMock()

        with patch.object(engine_with_mocks, "_send_telegram_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is False
        assert result.error == "telegram_send_failed"
        engine_with_mocks.store.mark_failed.assert_called_once()


# =============================================================================
# T023: Telegram Delivery Integration Tests (AC-T023.1 - AC-T023.4)
# =============================================================================


class TestTelegramDelivery:
    """Test Telegram delivery integration."""

    @pytest.mark.asyncio
    async def test_send_uses_existing_bot(self, engine_with_mocks, sample_touchpoint):
        """AC-T023.1: Use existing TelegramBot.send_message()."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=False)
        )
        engine_with_mocks.store.mark_delivered = AsyncMock()

        with patch("nikita.touchpoints.engine.TouchpointEngine._get_chat_id") as mock_chat, \
             patch("nikita.platforms.telegram.bot.get_bot") as mock_get_bot:
            mock_chat.return_value = 12345
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_get_bot.return_value = mock_bot

            result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is True
        mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_chat_id_fails(self, engine_with_mocks, sample_touchpoint):
        """AC-T023.2: Fails if no chat_id found."""
        with patch.object(engine_with_mocks, "_get_chat_id", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = None
            result = await engine_with_mocks._send_telegram_message(sample_touchpoint)

        assert result is False

    @pytest.mark.asyncio
    async def test_telegram_exception_returns_false(self, engine_with_mocks, sample_touchpoint):
        """AC-T023.3: Handle send failures."""
        with patch.object(engine_with_mocks, "_get_chat_id", new_callable=AsyncMock) as mock_chat, \
             patch("nikita.platforms.telegram.bot.get_bot") as mock_get_bot:
            mock_chat.return_value = 12345
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
            mock_get_bot.return_value = mock_bot

            result = await engine_with_mocks._send_telegram_message(sample_touchpoint)

        assert result is False


# =============================================================================
# T024: Deduplication Logic Tests (AC-T024.1 - AC-T024.4)
# =============================================================================


class TestDeduplication:
    """Test deduplication logic."""

    @pytest.mark.asyncio
    async def test_skip_if_recent_touchpoint(self, engine_with_mocks, sample_touchpoint):
        """AC-T024.1: Check recent touchpoints before scheduling."""
        # Simulate recent touchpoint exists
        recent_touchpoint = ScheduledTouchpoint(
            user_id=sample_touchpoint.user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
                chapter=2,
            ),
            delivery_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            delivered=True,
        )

        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(
            return_value=[recent_touchpoint]
        )
        engine_with_mocks.store.mark_skipped = AsyncMock()

        result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is False
        assert result.skipped_reason == "dedup"

    @pytest.mark.asyncio
    async def test_proceed_if_no_recent(self, engine_with_mocks, sample_touchpoint):
        """Proceed if no recent touchpoints."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine_with_mocks.silence.apply_strategic_silence = MagicMock(
            return_value=MagicMock(should_skip=False)
        )
        engine_with_mocks.store.mark_delivered = AsyncMock()

        with patch.object(engine_with_mocks, "_send_telegram_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_min_gap_respected(self, engine_with_mocks, sample_touchpoint):
        """AC-T024.2: Minimum gap between touchpoints."""
        # Set custom min gap
        engine_with_mocks.min_gap_minutes = 60

        # Recent touchpoint within gap
        recent = ScheduledTouchpoint(
            user_id=sample_touchpoint.user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
            ),
            delivery_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            delivered=True,
        )

        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(
            return_value=[recent]
        )
        engine_with_mocks.store.mark_skipped = AsyncMock()

        result = await engine_with_mocks._deliver_single(sample_touchpoint)

        assert result.success is False
        assert result.skipped_reason == "dedup"

    @pytest.mark.asyncio
    async def test_excludes_self_from_dedup(self, engine_with_mocks, sample_touchpoint):
        """AC-T024.3: Exclude current touchpoint from dedup check."""
        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])

        await engine_with_mocks._should_skip_for_dedup(sample_touchpoint)

        # Verify exclude_id was passed
        call_args = engine_with_mocks.store.get_recent_touchpoints.call_args
        assert call_args.kwargs.get("exclude_id") == sample_touchpoint.id


# =============================================================================
# T025: Phase E Coverage Tests (AC-T025.1 - AC-T025.3)
# =============================================================================


class TestPhasECoverage:
    """Ensure Phase E has comprehensive test coverage."""

    def test_engine_module_importable(self):
        """AC-T025.1: Engine module importable."""
        from nikita.touchpoints.engine import (
            DeliveryResult,
            TouchpointEngine,
            deliver_due_touchpoints,
        )

        assert TouchpointEngine is not None
        assert DeliveryResult is not None
        assert deliver_due_touchpoints is not None

    def test_engine_in_package_exports(self):
        """Engine exported from package."""
        from nikita.touchpoints import (
            DeliveryResult,
            TouchpointEngine,
            deliver_due_touchpoints,
        )

        assert TouchpointEngine is not None
        assert DeliveryResult is not None
        assert deliver_due_touchpoints is not None

    def test_delivery_result_repr(self):
        """DeliveryResult has useful repr."""
        success = DeliveryResult(
            touchpoint_id=uuid4(),
            success=True,
            delivered_at=datetime.now(timezone.utc),
        )
        assert "success=True" in repr(success)

        failed = DeliveryResult(
            touchpoint_id=uuid4(),
            success=False,
            error="some_error",
        )
        assert "error=some_error" in repr(failed)

        skipped = DeliveryResult(
            touchpoint_id=uuid4(),
            success=False,
            skipped_reason="silence",
        )
        assert "skipped=silence" in repr(skipped)

    @pytest.mark.asyncio
    async def test_convenience_function(self, mock_session):
        """Convenience function works."""
        with patch("nikita.touchpoints.engine.TouchpointStore") as mock_store_class, \
             patch("nikita.touchpoints.engine.MessageGenerator"), \
             patch("nikita.touchpoints.engine.StrategicSilence"):

            mock_store = MagicMock()
            mock_store.get_due_touchpoints = AsyncMock(return_value=[])
            mock_store_class.return_value = mock_store

            results = await deliver_due_touchpoints(mock_session)

        assert results == []


# =============================================================================
# Engine Scheduling Tests
# =============================================================================


class TestEngineScheduling:
    """Test engine scheduling capabilities."""

    @pytest.mark.asyncio
    async def test_evaluate_and_schedule(self, engine_with_mocks):
        """Engine can evaluate and schedule for user."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.chapter = 2
        mock_user.last_interaction_at = datetime.now(timezone.utc) - timedelta(hours=6)
        mock_user.telegram_chat_id = 12345

        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])

        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            # Mock scheduler to return a trigger context
            trigger_context = TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
                chapter=2,
            )
            engine_with_mocks.scheduler.evaluate_user = MagicMock(return_value=trigger_context)
            engine_with_mocks.store.create = AsyncMock(return_value=MagicMock())

            result = await engine_with_mocks.evaluate_and_schedule_for_user(mock_user.id)

        engine_with_mocks.store.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_if_recent_contact(self, engine_with_mocks):
        """Skip scheduling if recent touchpoint exists."""
        user_id = uuid4()

        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(
            return_value=[MagicMock()]  # Recent touchpoint exists
        )

        result = await engine_with_mocks.evaluate_and_schedule_for_user(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_if_not_eligible(self, engine_with_mocks):
        """Skip scheduling if user not eligible."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.chapter = 1
        mock_user.last_interaction_at = datetime.now(timezone.utc) - timedelta(hours=1)

        engine_with_mocks.store.get_recent_touchpoints = AsyncMock(return_value=[])

        with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            # Scheduler says not eligible
            engine_with_mocks.scheduler.evaluate_user = MagicMock(return_value=None)

            result = await engine_with_mocks.evaluate_and_schedule_for_user(mock_user.id)

        assert result is None


class TestDeliveryTimeComputation:
    """Test delivery time computation."""

    def test_time_trigger_immediate(self, engine_with_mocks):
        """TIME triggers deliver immediately."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
        )
        current_time = datetime.now(timezone.utc)

        delivery_time = engine_with_mocks._compute_delivery_time(trigger_context, current_time)

        assert delivery_time == current_time

    def test_event_trigger_delayed(self, engine_with_mocks):
        """EVENT triggers have small delay."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_1",
            event_type="test",
            event_description="test",
        )
        current_time = datetime.now(timezone.utc)

        delivery_time = engine_with_mocks._compute_delivery_time(trigger_context, current_time)

        assert delivery_time > current_time
        assert (delivery_time - current_time).total_seconds() <= 300  # Max 5 min

    def test_gap_trigger_soon(self, engine_with_mocks):
        """GAP triggers deliver soon."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=30.0,
        )
        current_time = datetime.now(timezone.utc)

        delivery_time = engine_with_mocks._compute_delivery_time(trigger_context, current_time)

        assert delivery_time > current_time
        assert (delivery_time - current_time).total_seconds() <= 120  # Max 2 min
