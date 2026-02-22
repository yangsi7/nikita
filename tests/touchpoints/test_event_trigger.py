"""Tests for Wave F — Touchpoint Event Wiring (Spec 071).

Tests the integration of LifeEvent objects from LifeSimStage into the
TouchpointStage → TouchpointEngine → TouchpointScheduler pipeline.

Coverage:
- Unit: _evaluate_event_trigger() with high/low importance events
- Unit: dedup — same event skipped if already triggered recently
- Unit: chapter-specific rates applied
- Integration: life_events passed through TouchpointStage → engine → scheduler
- Integration: high-importance event creates EVENT touchpoint
- Integration: empty life_events → no event triggers
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    EmotionalImpact,
    EventDomain,
    EventType,
    LifeEvent,
    TimeOfDay,
)
from nikita.touchpoints.models import (
    ScheduledTouchpoint,
    TriggerContext,
    TriggerType,
)
from nikita.touchpoints.scheduler import TouchpointScheduler


# =============================================================================
# Helpers
# =============================================================================


def make_life_event(
    user_id=None,
    importance: float = 0.8,
    event_type: EventType = EventType.WIN,
    domain: EventDomain = EventDomain.WORK,
    description: str = "Got promoted today at work, huge news!",
    arousal_delta: float = 0.2,
    valence_delta: float = 0.2,
) -> LifeEvent:
    """Build a LifeEvent for testing."""
    return LifeEvent(
        user_id=user_id or uuid4(),
        event_date=date.today(),
        time_of_day=TimeOfDay.AFTERNOON,
        domain=domain,
        event_type=event_type,
        description=description,
        importance=importance,
        emotional_impact=EmotionalImpact(
            arousal_delta=arousal_delta,
            valence_delta=valence_delta,
        ),
    )


# =============================================================================
# Unit: _evaluate_event_trigger() — importance filter
# =============================================================================


class TestEvaluateEventTriggerImportanceFilter:
    """Test importance >= 0.7 filter in _evaluate_event_trigger()."""

    def test_high_importance_event_creates_trigger(self):
        """Event with importance >= 0.7 should produce a trigger context."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.8)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        assert len(triggers) == 1
        assert triggers[0].trigger_type == TriggerType.EVENT
        assert triggers[0].event_type is not None
        assert triggers[0].event_description is not None

    def test_importance_exactly_at_threshold_creates_trigger(self):
        """Event with importance == 0.7 (boundary) should pass the filter."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.7)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=1,
            )

        assert len(triggers) == 1

    def test_low_importance_event_filtered_out(self):
        """Event with importance < 0.7 should be discarded."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.5)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        assert triggers == []

    def test_zero_importance_filtered_out(self):
        """Event with importance 0.0 must be filtered."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.0)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=3,
            )

        assert triggers == []

    def test_empty_event_list_returns_empty(self):
        """No events → no triggers."""
        scheduler = TouchpointScheduler()
        triggers = scheduler._evaluate_event_trigger(
            user_id=uuid4(),
            life_events=[],
            chapter=1,
        )
        assert triggers == []

    def test_none_event_list_returns_empty(self):
        """None events list → no triggers."""
        scheduler = TouchpointScheduler()
        triggers = scheduler._evaluate_event_trigger(
            user_id=uuid4(),
            life_events=None,
            chapter=1,
        )
        assert triggers == []


# =============================================================================
# Unit: _evaluate_event_trigger() — emotional impact filter
# =============================================================================


class TestEvaluateEventTriggerEmotionalImpact:
    """Events with no significant emotional impact should be filtered even if importance >= 0.7."""

    def test_event_with_emotional_impact_triggers(self):
        """High-importance event with significant emotional impact creates trigger."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [
            make_life_event(
                user_id=user_id,
                importance=0.8,
                arousal_delta=0.2,
                valence_delta=0.15,
            )
        ]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        assert len(triggers) == 1

    def test_event_with_zero_emotional_impact_filtered(self):
        """High-importance event with NO emotional impact is filtered out."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [
            make_life_event(
                user_id=user_id,
                importance=0.8,
                arousal_delta=0.0,
                valence_delta=0.0,
            )
        ]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        # Zero emotional impact means no meaningful emotional content to share
        assert triggers == []

    def test_negative_emotional_impact_still_triggers(self):
        """Negative emotional impact (distress) should still produce a trigger."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [
            make_life_event(
                user_id=user_id,
                importance=0.8,
                event_type=EventType.SETBACK,
                domain=EventDomain.WORK,
                description="Lost a major client today, very stressful and upsetting",
                arousal_delta=0.2,
                valence_delta=-0.2,
            )
        ]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        assert len(triggers) == 1


# =============================================================================
# Unit: _evaluate_event_trigger() — TriggerContext fields
# =============================================================================


class TestEvaluateEventTriggerContext:
    """Verify TriggerContext fields are populated correctly from LifeEvent."""

    def test_trigger_context_has_correct_event_fields(self):
        """event_id, event_type, event_description populated from LifeEvent."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        event = make_life_event(
            user_id=user_id,
            importance=0.9,
            event_type=EventType.FRIEND_HANGOUT,
            domain=EventDomain.SOCIAL,
            description="Had an amazing time with Sarah at the rooftop bar",
            arousal_delta=0.15,
            valence_delta=0.2,
        )

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=[event],
                chapter=3,
            )

        assert len(triggers) == 1
        ctx = triggers[0]
        assert ctx.trigger_type == TriggerType.EVENT
        assert ctx.event_id == str(event.event_id)
        assert ctx.event_type == event.event_type.value
        assert ctx.event_description == event.description
        assert ctx.chapter == 3

    def test_multiple_high_importance_events_all_evaluated(self):
        """Multiple events >= 0.7 importance are each evaluated for triggering."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [
            make_life_event(user_id=user_id, importance=0.8, arousal_delta=0.2, valence_delta=0.1),
            make_life_event(
                user_id=user_id,
                importance=0.9,
                event_type=EventType.FRIEND_DRAMA,
                domain=EventDomain.SOCIAL,
                description="Had a serious falling-out with my best friend today",
                arousal_delta=0.2,
                valence_delta=-0.15,
            ),
        ]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        # Both high-importance events should be evaluated and both produce triggers
        assert len(triggers) == 2

    def test_mixed_importance_only_high_trigger(self):
        """Mix of high and low importance: only high ones trigger."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [
            make_life_event(user_id=user_id, importance=0.8, arousal_delta=0.2, valence_delta=0.1),  # high
            make_life_event(user_id=user_id, importance=0.4, arousal_delta=0.1, valence_delta=0.1),  # low
            make_life_event(
                user_id=user_id,
                importance=0.3,
                event_type=EventType.ERRAND,
                domain=EventDomain.PERSONAL,
                description="Went to the grocery store and post office today",
                arousal_delta=0.05,
                valence_delta=0.0,
            ),  # low
        ]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
            )

        # Only the 1 high-importance event should produce a trigger
        assert len(triggers) == 1


# =============================================================================
# Unit: _evaluate_event_trigger() — deduplication
# =============================================================================


class TestEvaluateEventTriggerDedup:
    """Event touchpoint skipped if recent touchpoint exists for same event."""

    def test_same_event_id_skipped_if_recent_exists(self):
        """If recent_touchpoints contains an EVENT trigger for same event_id, skip."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        event = make_life_event(user_id=user_id, importance=0.9, arousal_delta=0.2, valence_delta=0.2)
        event_id_str = str(event.event_id)

        # Simulate a recent touchpoint for the same event
        recent_ctx = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id=event_id_str,
            event_type=event.event_type.value,
            event_description=event.description,
            chapter=2,
        )
        recent_tp = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.EVENT,
            trigger_context=recent_ctx,
            delivery_at=datetime.now(timezone.utc) - timedelta(hours=12),
            delivered=True,
            delivered_at=datetime.now(timezone.utc) - timedelta(hours=12),
        )

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=[event],
                chapter=2,
                recent_event_touchpoints=[recent_tp],
            )

        # Should be deduplicated
        assert triggers == []

    def test_different_event_id_not_deduplicated(self):
        """Different event_id in recent touchpoints does NOT block new trigger."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        event = make_life_event(user_id=user_id, importance=0.9, arousal_delta=0.2, valence_delta=0.2)

        # Recent touchpoint for a DIFFERENT event
        different_event_ctx = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="different-event-uuid-here",
            event_type="some_type",
            event_description="Some other event",
            chapter=2,
        )
        recent_tp = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.EVENT,
            trigger_context=different_event_ctx,
            delivery_at=datetime.now(timezone.utc) - timedelta(hours=12),
            delivered=True,
            delivered_at=datetime.now(timezone.utc) - timedelta(hours=12),
        )

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=[event],
                chapter=2,
                recent_event_touchpoints=[recent_tp],
            )

        assert len(triggers) == 1

    def test_no_recent_touchpoints_not_deduplicated(self):
        """No recent touchpoints provided → dedup not applied."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.8, arousal_delta=0.2, valence_delta=0.1)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=events,
                chapter=2,
                recent_event_touchpoints=None,
            )

        assert len(triggers) == 1


# =============================================================================
# Unit: _evaluate_event_trigger() — chapter-specific rates
# =============================================================================


class TestEvaluateEventTriggerChapterRates:
    """Chapter-specific initiation rates are applied to event triggers."""

    def test_chapter_rates_applied_to_event_triggers(self):
        """Higher chapters have higher initiation rates, affecting event triggers."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        iterations = 500

        ch1_triggers = 0
        ch3_triggers = 0

        random.seed(42)
        for _ in range(iterations):
            event = make_life_event(user_id=user_id, importance=0.8, arousal_delta=0.2, valence_delta=0.1)
            results = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=[event],
                chapter=1,
            )
            ch1_triggers += len(results)

        random.seed(42)
        for _ in range(iterations):
            event = make_life_event(user_id=user_id, importance=0.8, arousal_delta=0.2, valence_delta=0.1)
            results = scheduler._evaluate_event_trigger(
                user_id=user_id,
                life_events=[event],
                chapter=3,
            )
            ch3_triggers += len(results)

        # Chapter 3 should trigger more often than chapter 1 due to higher rates
        assert ch3_triggers > ch1_triggers


# =============================================================================
# Unit: evaluate_user() — life_events parameter
# =============================================================================


class TestEvaluateUserWithLifeEvents:
    """evaluate_user() calls _evaluate_event_trigger() when life_events present."""

    def test_evaluate_user_with_life_events_calls_event_trigger(self):
        """evaluate_user() evaluates event triggers when life_events provided."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        events = [make_life_event(user_id=user_id, importance=0.9, arousal_delta=0.2, valence_delta=0.2)]

        with patch.object(scheduler, "_should_trigger", return_value=True):
            with patch.object(scheduler, "_get_current_time_slot", return_value=None):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=2,
                    life_events=events,
                )

        event_triggers = [t for t in triggers if t.trigger_type == TriggerType.EVENT]
        assert len(event_triggers) >= 1

    def test_evaluate_user_without_life_events_no_event_trigger(self):
        """evaluate_user() without life_events produces no EVENT triggers."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        with patch.object(scheduler, "_should_trigger", return_value=False):
            with patch.object(scheduler, "_get_current_time_slot", return_value=None):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=2,
                    # No life_events
                )

        event_triggers = [t for t in triggers if t.trigger_type == TriggerType.EVENT]
        assert len(event_triggers) == 0

    def test_evaluate_user_empty_life_events_no_event_trigger(self):
        """evaluate_user() with empty life_events produces no EVENT triggers."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        with patch.object(scheduler, "_should_trigger", return_value=True):
            with patch.object(scheduler, "_get_current_time_slot", return_value=None):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=2,
                    life_events=[],
                )

        event_triggers = [t for t in triggers if t.trigger_type == TriggerType.EVENT]
        assert len(event_triggers) == 0


# =============================================================================
# Integration: TouchpointStage passes ctx.life_events → engine → scheduler
# =============================================================================


class TestTouchpointStageLifeEventsIntegration:
    """TouchpointStage wires ctx.life_events into TouchpointEngine.

    Note: TouchpointEngine is imported lazily inside _run(), so we patch it
    at its canonical module path nikita.touchpoints.engine.TouchpointEngine.
    """

    @pytest.mark.asyncio
    async def test_touchpoint_stage_passes_life_events_to_engine(self):
        """TouchpointStage passes ctx.life_events to engine.evaluate_and_schedule_for_user."""
        from nikita.pipeline.models import PipelineContext
        from nikita.pipeline.stages.touchpoint import TouchpointStage

        user_id = uuid4()
        life_events = [
            make_life_event(user_id=user_id, importance=0.9, arousal_delta=0.2, valence_delta=0.2)
        ]

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform="telegram",
        )
        ctx.life_events = life_events

        mock_session = MagicMock()
        stage = TouchpointStage(session=mock_session)

        captured_life_events = {}

        async def fake_evaluate(user_id, current_time=None, life_events=None):
            captured_life_events["value"] = life_events
            return None

        # TouchpointEngine is imported lazily inside _run(), patch at source module
        with patch("nikita.touchpoints.engine.TouchpointEngine") as MockEngine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.evaluate_and_schedule_for_user = AsyncMock(
                side_effect=fake_evaluate
            )
            MockEngine.return_value = mock_engine_instance

            await stage._run(ctx)

        assert "value" in captured_life_events
        assert captured_life_events["value"] == life_events

    @pytest.mark.asyncio
    async def test_touchpoint_stage_empty_life_events_still_works(self):
        """TouchpointStage with empty life_events does not raise errors."""
        from nikita.pipeline.models import PipelineContext
        from nikita.pipeline.stages.touchpoint import TouchpointStage

        user_id = uuid4()
        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform="telegram",
        )
        ctx.life_events = []

        mock_session = MagicMock()
        stage = TouchpointStage(session=mock_session)

        # TouchpointEngine is imported lazily inside _run(), patch at source module
        with patch("nikita.touchpoints.engine.TouchpointEngine") as MockEngine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.evaluate_and_schedule_for_user = AsyncMock(return_value=None)
            MockEngine.return_value = mock_engine_instance

            result = await stage._run(ctx)

        assert result is not None
        assert ctx.touchpoint_scheduled is False


# =============================================================================
# Integration: High-importance event creates EVENT touchpoint in full flow
# =============================================================================


class TestHighImportanceEventEndToEnd:
    """High-importance life events produce EVENT touchpoints in the full flow.

    Notes on patching:
    - MessageGenerator is created in TouchpointEngine.__init__(); patch before init.
    - UserRepository is imported lazily inside evaluate_and_schedule_for_user();
      patch at its source module path.
    - TouchpointStore is created in TouchpointEngine.__init__(); replace after init.
    """

    @pytest.mark.asyncio
    async def test_high_importance_event_creates_event_touchpoint_via_engine(self):
        """Full flow: high-importance LifeEvent → TouchpointEngine → EVENT touchpoint."""
        from nikita.touchpoints.engine import TouchpointEngine

        user_id = uuid4()
        life_events = [
            make_life_event(user_id=user_id, importance=0.9, arousal_delta=0.2, valence_delta=0.2)
        ]

        mock_session = MagicMock()

        # Mock user data
        mock_user = MagicMock()
        mock_user.chapter = 2
        mock_user.timezone = "UTC"
        mock_user.last_interaction_at = datetime.now(timezone.utc) - timedelta(hours=5)

        created_touchpoints = []

        async def fake_create(**kwargs):
            tp = MagicMock()
            tp.id = uuid4()
            tp.trigger_type = kwargs.get("trigger_type")
            created_touchpoints.append(tp)
            return tp

        # Patch MessageGenerator to prevent Anthropic client init at engine construction time
        with patch("nikita.touchpoints.engine.MessageGenerator"):
            # Patch TouchpointStore to prevent real DB calls at engine construction time
            with patch("nikita.touchpoints.engine.TouchpointStore"):
                engine = TouchpointEngine(session=mock_session)

        # Replace store and generator with controlled mocks after construction
        engine.store = MagicMock()
        engine.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine.store.create = AsyncMock(side_effect=fake_create)

        # UserRepository is imported lazily; patch at its source module
        with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo

            with patch.object(engine.scheduler, "_should_trigger", return_value=True):
                with patch.object(engine.scheduler, "_get_current_time_slot", return_value=None):
                    result = await engine.evaluate_and_schedule_for_user(
                        user_id=user_id,
                        life_events=life_events,
                    )

        # A touchpoint should have been created via EVENT trigger
        assert result is not None
        assert len(created_touchpoints) == 1
        assert created_touchpoints[0].trigger_type == TriggerType.EVENT

    @pytest.mark.asyncio
    async def test_empty_life_events_no_event_touchpoint_via_engine(self):
        """Empty life_events → no EVENT touchpoint created."""
        from nikita.touchpoints.engine import TouchpointEngine

        user_id = uuid4()

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.chapter = 2
        mock_user.timezone = "UTC"
        mock_user.last_interaction_at = datetime.now(timezone.utc) - timedelta(hours=5)

        # Patch MessageGenerator and TouchpointStore to prevent real init side-effects
        with patch("nikita.touchpoints.engine.MessageGenerator"):
            with patch("nikita.touchpoints.engine.TouchpointStore"):
                engine = TouchpointEngine(session=mock_session)

        engine.store = MagicMock()
        engine.store.get_recent_touchpoints = AsyncMock(return_value=[])
        engine.store.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        # UserRepository is imported lazily; patch at its source module
        with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo

            # Force no time or gap triggers, empty events → no triggers at all
            with patch.object(engine.scheduler, "_should_trigger", return_value=False):
                result = await engine.evaluate_and_schedule_for_user(
                    user_id=user_id,
                    life_events=[],
                )

        assert result is None
