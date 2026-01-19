"""Scheduling tests for Proactive Touchpoint System (Spec 025, Phase B: T006-T011).

Tests:
- T006: TouchpointScheduler class
- T007: Time-based triggers
- T008: Event-based triggers
- T009: Gap-based triggers
- T010: Chapter-aware rates
- T011: Phase B coverage
"""

import random
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from nikita.touchpoints.models import (
    CHAPTER_CONFIGS,
    ScheduledTouchpoint,
    TouchpointConfig,
    TriggerContext,
    TriggerType,
    get_config_for_chapter,
)
from nikita.touchpoints.scheduler import (
    TouchpointScheduler,
    get_hours_since_interaction,
)


# =============================================================================
# T006: TouchpointScheduler Class Tests (AC-T006.1 - AC-T006.4)
# =============================================================================


class TestTouchpointSchedulerClass:
    """Test TouchpointScheduler class structure."""

    def test_scheduler_exists(self):
        """AC-T006.1: TouchpointScheduler class exists."""
        scheduler = TouchpointScheduler()
        assert scheduler is not None

    def test_scheduler_has_default_config(self):
        """Scheduler has default config."""
        scheduler = TouchpointScheduler()
        assert scheduler.default_config is not None
        assert isinstance(scheduler.default_config, TouchpointConfig)

    def test_scheduler_with_custom_config(self):
        """Scheduler accepts custom default config."""
        custom_config = TouchpointConfig(
            initiation_rate_min=0.40,
            initiation_rate_max=0.50,
        )
        scheduler = TouchpointScheduler(default_config=custom_config)
        assert scheduler.default_config.initiation_rate_min == 0.40

    def test_get_config_for_chapter(self):
        """Scheduler retrieves chapter-specific config."""
        scheduler = TouchpointScheduler()
        config = scheduler.get_config(2)
        assert config.initiation_rate_min == 0.20
        assert config.initiation_rate_max == 0.25


class TestScheduleMethod:
    """Test schedule() method (AC-T006.2)."""

    def test_schedule_creates_touchpoint(self):
        """AC-T006.2: schedule() creates touchpoint."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            chapter=2,
        )

        touchpoint = scheduler.schedule(
            user_id=user_id,
            trigger_context=trigger_context,
            message_content="Good morning!",
        )

        assert touchpoint.user_id == user_id
        assert touchpoint.trigger_type == TriggerType.TIME
        assert touchpoint.message_content == "Good morning!"
        assert touchpoint.delivered is False

    def test_schedule_with_delay(self):
        """Schedule with delivery delay."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()
        trigger_context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=30.0,
        )

        before = datetime.now(timezone.utc)
        touchpoint = scheduler.schedule(
            user_id=user_id,
            trigger_context=trigger_context,
            delivery_delay_minutes=30,
        )
        after = datetime.now(timezone.utc)

        # Delivery should be ~30 minutes from now
        expected_min = before + timedelta(minutes=29)
        expected_max = after + timedelta(minutes=31)
        assert expected_min <= touchpoint.delivery_at <= expected_max


class TestEvaluateUser:
    """Test evaluate_user() method (AC-T006.3)."""

    def test_evaluate_user_returns_list(self):
        """AC-T006.3: evaluate_user returns list of triggers."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Force time trigger to fire
        with patch.object(scheduler, "_should_trigger", return_value=True):
            with patch.object(scheduler, "_get_current_time_slot", return_value="morning"):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=1,
                    user_timezone="UTC",
                )

        assert isinstance(triggers, list)
        if triggers:
            assert all(isinstance(t, TriggerContext) for t in triggers)

    def test_evaluate_user_empty_when_no_triggers(self):
        """Returns empty list when no triggers apply."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Force no triggers
        with patch.object(scheduler, "_should_trigger", return_value=False):
            with patch.object(scheduler, "_get_current_time_slot", return_value=None):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=1,
                )

        assert triggers == []


# =============================================================================
# T007: Time-Based Triggers Tests (AC-T007.1 - AC-T007.5)
# =============================================================================


class TestTimeTriggers:
    """Test time-based trigger detection."""

    def test_morning_slot_detection(self):
        """AC-T007.1: Morning slot detection (8-10am)."""
        scheduler = TouchpointScheduler()
        config = TouchpointConfig()

        # 9am should be in morning slot
        assert scheduler._get_current_time_slot(9, config) == "morning"
        # 8am start
        assert scheduler._get_current_time_slot(8, config) == "morning"
        # 10am end (exclusive)
        assert scheduler._get_current_time_slot(10, config) is None

    def test_evening_slot_detection(self):
        """AC-T007.2: Evening slot detection (7-9pm)."""
        scheduler = TouchpointScheduler()
        config = TouchpointConfig()

        # 8pm should be in evening slot
        assert scheduler._get_current_time_slot(20, config) == "evening"
        # 7pm start
        assert scheduler._get_current_time_slot(19, config) == "evening"
        # 9pm end (exclusive)
        assert scheduler._get_current_time_slot(21, config) is None

    def test_outside_time_slots(self):
        """Returns None when outside time slots."""
        scheduler = TouchpointScheduler()
        config = TouchpointConfig()

        # Midday
        assert scheduler._get_current_time_slot(12, config) is None
        # Midnight
        assert scheduler._get_current_time_slot(0, config) is None
        # 3pm
        assert scheduler._get_current_time_slot(15, config) is None

    def test_probability_check(self):
        """AC-T007.3: Probability check per slot."""
        scheduler = TouchpointScheduler()
        config = TouchpointConfig(
            initiation_rate_min=0.20,
            initiation_rate_max=0.30,
        )

        # With seeded random, verify rate is within bounds
        rates = [scheduler._get_initiation_rate(config) for _ in range(100)]
        assert all(0.20 <= r <= 0.30 for r in rates)

    def test_timezone_handling(self):
        """AC-T007.4: Timezone handling from user profile."""
        scheduler = TouchpointScheduler()

        # UTC 9am
        utc_time = datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc)

        # Convert to US/Pacific (should be 1am)
        local_time = scheduler._get_user_local_time(utc_time, "US/Pacific")
        assert local_time.hour == 1

        # Convert to Europe/Paris (should be 10am)
        local_time = scheduler._get_user_local_time(utc_time, "Europe/Paris")
        assert local_time.hour == 10

    def test_invalid_timezone_fallback(self):
        """Invalid timezone falls back to UTC."""
        scheduler = TouchpointScheduler()
        utc_time = datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc)

        # Invalid timezone
        local_time = scheduler._get_user_local_time(utc_time, "Invalid/Timezone")
        assert local_time.hour == 9  # Falls back to UTC

    def test_time_trigger_evaluation(self):
        """Time trigger evaluation integrates all components."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Mock to ensure trigger fires
        with patch.object(scheduler, "_should_trigger", return_value=True):
            with patch.object(scheduler, "_get_current_time_slot", return_value="morning"):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=2,
                )

        assert len(triggers) >= 1
        time_trigger = next((t for t in triggers if t.trigger_type == TriggerType.TIME), None)
        assert time_trigger is not None
        assert time_trigger.time_slot == "morning"
        assert time_trigger.chapter == 2


# =============================================================================
# T008: Event-Based Triggers Tests (AC-T008.1 - AC-T008.4)
# =============================================================================


class TestEventTriggers:
    """Test event-based trigger detection."""

    def test_event_trigger_basic(self):
        """AC-T008.1: Event trigger creation."""
        scheduler = TouchpointScheduler()

        # Force trigger to fire
        with patch.object(scheduler, "_should_trigger", return_value=True):
            trigger = scheduler.evaluate_event_trigger(
                chapter=2,
                event_id="evt_123",
                event_type="work_drama",
                event_description="Boss was rude today",
            )

        assert trigger is not None
        assert trigger.trigger_type == TriggerType.EVENT
        assert trigger.event_id == "evt_123"
        assert trigger.event_type == "work_drama"

    def test_high_importance_events(self):
        """AC-T008.2: High-importance events more likely to trigger."""
        scheduler = TouchpointScheduler()

        # Track trigger rates for different importance levels
        high_triggers = 0
        low_triggers = 0
        iterations = 1000

        random.seed(42)  # Reproducible

        for _ in range(iterations):
            high = scheduler.evaluate_event_trigger(
                chapter=3,
                event_id="evt_high",
                event_type="major_event",
                event_description="Big news",
                importance=0.9,
                emotional_intensity=0.5,
            )
            if high:
                high_triggers += 1

        random.seed(42)  # Same seed

        for _ in range(iterations):
            low = scheduler.evaluate_event_trigger(
                chapter=3,
                event_id="evt_low",
                event_type="minor_event",
                event_description="Small update",
                importance=0.1,
                emotional_intensity=0.5,
            )
            if low:
                low_triggers += 1

        # High importance should trigger more often
        assert high_triggers > low_triggers

    def test_emotional_events(self):
        """AC-T008.3: Emotional events (upset, excited) trigger more often."""
        scheduler = TouchpointScheduler()

        emotional_triggers = 0
        calm_triggers = 0
        iterations = 1000

        random.seed(42)

        for _ in range(iterations):
            emotional = scheduler.evaluate_event_trigger(
                chapter=2,
                event_id="evt_emotional",
                event_type="emotional_event",
                event_description="Very upset",
                importance=0.5,
                emotional_intensity=0.9,
            )
            if emotional:
                emotional_triggers += 1

        random.seed(42)

        for _ in range(iterations):
            calm = scheduler.evaluate_event_trigger(
                chapter=2,
                event_id="evt_calm",
                event_type="calm_event",
                event_description="Normal day",
                importance=0.5,
                emotional_intensity=0.1,
            )
            if calm:
                calm_triggers += 1

        # Emotional events should trigger more often
        assert emotional_triggers > calm_triggers

    def test_event_includes_emotional_state(self):
        """Event trigger can include emotional state snapshot."""
        scheduler = TouchpointScheduler()
        emotional_state = {
            "valence": 0.3,
            "arousal": 0.8,
            "dominance": 0.4,
        }

        with patch.object(scheduler, "_should_trigger", return_value=True):
            trigger = scheduler.evaluate_event_trigger(
                chapter=3,
                event_id="evt_456",
                event_type="conflict",
                event_description="Argument with friend",
                emotional_state=emotional_state,
            )

        assert trigger is not None
        assert trigger.emotional_state == emotional_state


# =============================================================================
# T009: Gap-Based Triggers Tests (AC-T009.1 - AC-T009.4)
# =============================================================================


class TestGapTriggers:
    """Test gap-based trigger detection."""

    def test_gap_detection(self):
        """AC-T009.1: Detect gaps > 24 hours without contact."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # 30 hours ago
        last_interaction = datetime.now(timezone.utc) - timedelta(hours=30)

        # Force trigger to fire
        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler.evaluate_user(
                user_id=user_id,
                chapter=2,
                last_interaction_at=last_interaction,
            )

        gap_trigger = next((t for t in triggers if t.trigger_type == TriggerType.GAP), None)
        assert gap_trigger is not None
        assert gap_trigger.hours_since_contact >= 30

    def test_no_gap_trigger_within_24h(self):
        """No gap trigger if < 24 hours."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # 12 hours ago (within 24h)
        last_interaction = datetime.now(timezone.utc) - timedelta(hours=12)

        # Even if would trigger, gap check should prevent
        triggers = scheduler.evaluate_user(
            user_id=user_id,
            chapter=2,
            last_interaction_at=last_interaction,
        )

        gap_trigger = next((t for t in triggers if t.trigger_type == TriggerType.GAP), None)
        assert gap_trigger is None

    def test_gap_trigger_context_includes_hours(self):
        """Gap trigger includes hours_since_contact."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        last_interaction = datetime.now(timezone.utc) - timedelta(hours=48)

        with patch.object(scheduler, "_should_trigger", return_value=True):
            triggers = scheduler.evaluate_user(
                user_id=user_id,
                chapter=3,
                last_interaction_at=last_interaction,
            )

        gap_trigger = next((t for t in triggers if t.trigger_type == TriggerType.GAP), None)
        if gap_trigger:
            assert gap_trigger.hours_since_contact is not None
            assert gap_trigger.hours_since_contact >= 48

    def test_get_hours_since_interaction_utility(self):
        """Utility function calculates hours correctly."""
        now = datetime.now(timezone.utc)
        last = now - timedelta(hours=36)

        hours = get_hours_since_interaction(last, now)
        assert 35.9 <= hours <= 36.1

    def test_get_hours_since_interaction_none(self):
        """Returns infinity if no last interaction."""
        hours = get_hours_since_interaction(None)
        assert hours == float("inf")


# =============================================================================
# T010: Chapter-Aware Rates Tests (AC-T010.1 - AC-T010.4)
# =============================================================================


class TestChapterAwareRates:
    """Test chapter-specific initiation rates (FR-002)."""

    def test_rates_from_config(self):
        """AC-T010.1: Load rates from config."""
        # All chapters should have configs
        for chapter in range(1, 6):
            config = get_config_for_chapter(chapter)
            assert config is not None
            assert 0.0 <= config.initiation_rate_min <= 1.0
            assert 0.0 <= config.initiation_rate_max <= 1.0

    def test_chapter_1_rates(self):
        """AC-T010.2: Chapter 1: 15-20%."""
        config = get_config_for_chapter(1)
        assert config.initiation_rate_min == 0.15
        assert config.initiation_rate_max == 0.20

    def test_chapter_2_rates(self):
        """AC-T010.2: Chapter 2: 20-25%."""
        config = get_config_for_chapter(2)
        assert config.initiation_rate_min == 0.20
        assert config.initiation_rate_max == 0.25

    def test_chapter_3_plus_rates(self):
        """AC-T010.2: Chapter 3+: 25-30%."""
        for chapter in [3, 4, 5]:
            config = get_config_for_chapter(chapter)
            assert config.initiation_rate_min == 0.25
            assert config.initiation_rate_max == 0.30

    def test_rate_lookup_per_chapter(self):
        """AC-T010.3: Rate lookup per user's current chapter."""
        scheduler = TouchpointScheduler()

        config_1 = scheduler.get_config(1)
        config_3 = scheduler.get_config(3)

        assert config_1.initiation_rate_min < config_3.initiation_rate_min

    def test_rate_calculation_within_bounds(self):
        """AC-T010.4: Rate calculation stays within bounds."""
        scheduler = TouchpointScheduler()

        for chapter in range(1, 6):
            config = scheduler.get_config(chapter)
            rates = [scheduler._get_initiation_rate(config) for _ in range(100)]

            assert all(
                config.initiation_rate_min <= r <= config.initiation_rate_max
                for r in rates
            )


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplication:
    """Test deduplication logic to prevent double-triggering."""

    def test_no_trigger_if_recent_delivered(self):
        """No trigger if recently delivered touchpoint exists."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Recent delivered touchpoint
        recent = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
            ),
            delivery_at=datetime.now(timezone.utc) - timedelta(hours=2),
            delivered=True,
            delivered_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

        triggers = scheduler.evaluate_user(
            user_id=user_id,
            chapter=2,
            recent_touchpoints=[recent],
        )

        # Should be blocked by deduplication
        assert triggers == []

    def test_no_trigger_if_pending_exists(self):
        """No trigger if pending (undelivered, not skipped) touchpoint exists."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Pending touchpoint
        pending = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="evening",
            ),
            delivery_at=datetime.now(timezone.utc) + timedelta(hours=1),
            delivered=False,
            skipped=False,
        )

        triggers = scheduler.evaluate_user(
            user_id=user_id,
            chapter=2,
            recent_touchpoints=[pending],
        )

        # Should be blocked by pending touchpoint
        assert triggers == []

    def test_allows_trigger_after_min_gap(self):
        """Allows trigger if last touchpoint was long enough ago."""
        scheduler = TouchpointScheduler()
        user_id = uuid4()

        # Old delivered touchpoint (6 hours ago, min gap is 4)
        old = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
            ),
            delivery_at=datetime.now(timezone.utc) - timedelta(hours=6),
            delivered=True,
            delivered_at=datetime.now(timezone.utc) - timedelta(hours=6),
        )

        # Force trigger to fire
        with patch.object(scheduler, "_should_trigger", return_value=True):
            with patch.object(scheduler, "_get_current_time_slot", return_value="evening"):
                triggers = scheduler.evaluate_user(
                    user_id=user_id,
                    chapter=2,
                    recent_touchpoints=[old],
                )

        # Should allow because min_gap (4h) has passed
        assert len(triggers) >= 1


# =============================================================================
# T011: Phase B Coverage Tests (AC-T011.1, AC-T011.2)
# =============================================================================


class TestPhaseBCoverage:
    """Ensure Phase B has comprehensive test coverage."""

    def test_scheduler_module_importable(self):
        """AC-T011.1: Scheduler module importable."""
        from nikita.touchpoints.scheduler import (
            TouchpointScheduler,
            get_hours_since_interaction,
        )

        assert TouchpointScheduler is not None
        assert get_hours_since_interaction is not None

    def test_all_trigger_types_covered(self):
        """All trigger types have tests."""
        # This test documents that we've covered:
        # - TIME triggers (TestTimeTriggers)
        # - EVENT triggers (TestEventTriggers)
        # - GAP triggers (TestGapTriggers)
        assert TriggerType.TIME.value == "time"
        assert TriggerType.EVENT.value == "event"
        assert TriggerType.GAP.value == "gap"

    def test_chapter_configs_complete(self):
        """All chapter configs defined and tested."""
        for chapter in range(1, 6):
            assert chapter in CHAPTER_CONFIGS
            config = CHAPTER_CONFIGS[chapter]
            assert config.initiation_rate_min > 0
            assert config.initiation_rate_max > config.initiation_rate_min
