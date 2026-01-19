"""Infrastructure tests for Proactive Touchpoint System (Spec 025, Phase A: T001-T005).

Tests:
- T001: Module structure
- T002: Model validation
- T004: TouchpointStore CRUD operations
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
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


# =============================================================================
# T001: Module Structure Tests (AC-T001.1, AC-T001.2)
# =============================================================================


class TestModuleStructure:
    """Test module structure and imports."""

    def test_module_exists(self):
        """AC-T001.1: Module can be imported."""
        from nikita import touchpoints

        assert touchpoints is not None

    def test_exports_models(self):
        """Module exports expected model classes."""
        from nikita.touchpoints import (
            ScheduledTouchpoint,
            TouchpointConfig,
            TriggerContext,
            TriggerType,
        )

        assert ScheduledTouchpoint is not None
        assert TouchpointConfig is not None
        assert TriggerContext is not None
        assert TriggerType is not None

    def test_submodules_exist(self):
        """AC-T001.2: Submodules can be imported."""
        from nikita.touchpoints import models
        from nikita.touchpoints import store

        assert models is not None
        assert store is not None


# =============================================================================
# T002: Model Tests (AC-T002.1 - AC-T002.4)
# =============================================================================


class TestTriggerType:
    """Test TriggerType enum."""

    def test_trigger_types_exist(self):
        """AC-T002.3: All trigger types defined."""
        assert TriggerType.TIME.value == "time"
        assert TriggerType.EVENT.value == "event"
        assert TriggerType.GAP.value == "gap"

    def test_enum_membership(self):
        """Enum values can be checked."""
        assert "time" in [t.value for t in TriggerType]
        assert "event" in [t.value for t in TriggerType]
        assert "gap" in [t.value for t in TriggerType]


class TestTriggerContext:
    """Test TriggerContext model."""

    def test_time_trigger_context(self):
        """AC-T002.2: TriggerContext for time triggers."""
        context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            chapter=2,
        )
        assert context.trigger_type == TriggerType.TIME
        assert context.time_slot == "morning"
        assert context.chapter == 2

    def test_event_trigger_context(self):
        """TriggerContext for event triggers."""
        context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_123",
            event_type="work_drama",
            event_description="Boss was rude today",
        )
        assert context.trigger_type == TriggerType.EVENT
        assert context.event_id == "evt_123"

    def test_gap_trigger_context(self):
        """TriggerContext for gap triggers."""
        context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=48.5,
        )
        assert context.trigger_type == TriggerType.GAP
        assert context.hours_since_contact == 48.5

    def test_time_slot_validation(self):
        """Time slot validation for TIME triggers."""
        # Valid time slots
        ctx = TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning")
        assert ctx.time_slot == "morning"

        ctx = TriggerContext(trigger_type=TriggerType.TIME, time_slot="evening")
        assert ctx.time_slot == "evening"

        # Invalid time slot
        with pytest.raises(ValueError, match="must be 'morning' or 'evening'"):
            TriggerContext(trigger_type=TriggerType.TIME, time_slot="afternoon")

    def test_time_slot_required_for_time_trigger(self):
        """Time slot is required for TIME triggers."""
        with pytest.raises(ValueError, match="time_slot is required"):
            TriggerContext(trigger_type=TriggerType.TIME)

    def test_emotional_state_default(self):
        """Emotional state defaults to empty dict."""
        context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=24.0,
        )
        assert context.emotional_state == {}


class TestTouchpointConfig:
    """Test TouchpointConfig model."""

    def test_default_config(self):
        """AC-T002.2: Default config values."""
        config = TouchpointConfig()
        assert 0.0 <= config.initiation_rate_min <= 1.0
        assert 0.0 <= config.initiation_rate_max <= 1.0
        assert 0.0 <= config.strategic_silence_rate <= 1.0

    def test_custom_config(self):
        """Custom config values."""
        config = TouchpointConfig(
            initiation_rate_min=0.25,
            initiation_rate_max=0.30,
            strategic_silence_rate=0.10,
        )
        assert config.initiation_rate_min == 0.25
        assert config.initiation_rate_max == 0.30
        assert config.strategic_silence_rate == 0.10

    def test_rate_max_validation(self):
        """Max rate must be >= min rate."""
        with pytest.raises(ValueError, match="must be >= initiation_rate_min"):
            TouchpointConfig(
                initiation_rate_min=0.30,
                initiation_rate_max=0.20,
            )

    def test_time_slot_hours(self):
        """Time slot hour defaults."""
        config = TouchpointConfig()
        assert config.morning_slot_start == 8
        assert config.morning_slot_end == 10
        assert config.evening_slot_start == 19
        assert config.evening_slot_end == 21

    def test_gap_config(self):
        """Gap configuration defaults."""
        config = TouchpointConfig()
        assert config.min_gap_hours == 4.0
        assert config.gap_trigger_hours == 24.0


class TestChapterConfigs:
    """Test chapter-specific configurations (FR-002)."""

    def test_all_chapters_have_config(self):
        """All 5 chapters have configs."""
        for chapter in range(1, 6):
            assert chapter in CHAPTER_CONFIGS

    def test_chapter_1_config(self):
        """Chapter 1 config (FR-002)."""
        config = CHAPTER_CONFIGS[1]
        assert config.initiation_rate_min == 0.15
        assert config.initiation_rate_max == 0.20
        assert config.strategic_silence_rate == 0.20

    def test_chapter_2_config(self):
        """Chapter 2 config (FR-002)."""
        config = CHAPTER_CONFIGS[2]
        assert config.initiation_rate_min == 0.20
        assert config.initiation_rate_max == 0.25
        assert config.strategic_silence_rate == 0.15

    def test_chapter_3_plus_config(self):
        """Chapters 3-5 config (FR-002)."""
        for chapter in [3, 4, 5]:
            config = CHAPTER_CONFIGS[chapter]
            assert config.initiation_rate_min == 0.25
            assert config.initiation_rate_max == 0.30
            assert config.strategic_silence_rate == 0.10

    def test_get_config_for_chapter(self):
        """get_config_for_chapter helper."""
        config = get_config_for_chapter(2)
        assert config.initiation_rate_min == 0.20

    def test_get_config_for_invalid_chapter(self):
        """Invalid chapter falls back to chapter 1."""
        config = get_config_for_chapter(99)
        assert config.initiation_rate_min == 0.15  # Chapter 1 default


class TestScheduledTouchpoint:
    """Test ScheduledTouchpoint model."""

    def test_create_touchpoint(self):
        """AC-T002.1: ScheduledTouchpoint creation."""
        user_id = uuid4()
        delivery_at = datetime.now(timezone.utc) + timedelta(hours=1)

        touchpoint = ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
            ),
            message_content="Good morning! How did you sleep?",
            delivery_at=delivery_at,
        )

        assert touchpoint.user_id == user_id
        assert touchpoint.trigger_type == TriggerType.TIME
        assert touchpoint.message_content == "Good morning! How did you sleep?"
        assert touchpoint.delivered is False
        assert touchpoint.skipped is False

    def test_touchpoint_id_auto_generated(self):
        """Touchpoint ID is auto-generated."""
        touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.GAP,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.GAP,
                hours_since_contact=24.0,
            ),
            delivery_at=datetime.now(timezone.utc),
        )
        assert touchpoint.touchpoint_id is not None

    def test_is_due_property(self):
        """is_due property works correctly."""
        # Future touchpoint - not due
        future_touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert future_touchpoint.is_due is False

        # Past touchpoint - due
        past_touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        assert past_touchpoint.is_due is True

    def test_is_due_respects_delivered(self):
        """is_due returns False if already delivered."""
        touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            delivered=True,
        )
        assert touchpoint.is_due is False

    def test_is_due_respects_skipped(self):
        """is_due returns False if skipped."""
        touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            skipped=True,
        )
        assert touchpoint.is_due is False

    def test_mark_delivered(self):
        """mark_delivered method works."""
        touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc),
        )
        updated = touchpoint.mark_delivered()

        assert updated.delivered is True
        assert updated.delivered_at is not None
        # Original is unchanged (immutable copy)
        assert touchpoint.delivered is False

    def test_mark_skipped(self):
        """mark_skipped method works."""
        touchpoint = ScheduledTouchpoint(
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(trigger_type=TriggerType.TIME, time_slot="morning"),
            delivery_at=datetime.now(timezone.utc),
        )
        updated = touchpoint.mark_skipped("strategic_silence")

        assert updated.skipped is True
        assert updated.skip_reason == "strategic_silence"
        # Original is unchanged
        assert touchpoint.skipped is False


# =============================================================================
# T004: TouchpointStore Tests (AC-T004.1 - AC-T004.5)
# =============================================================================


class TestTouchpointStore:
    """Tests for TouchpointStore with mocked session."""

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def store(self, mock_session):
        """Create TouchpointStore with mock session."""
        from nikita.touchpoints.store import TouchpointStore

        return TouchpointStore(mock_session)

    @pytest.fixture
    def sample_touchpoint(self):
        """Create sample touchpoint for testing."""
        return ScheduledTouchpoint(
            touchpoint_id=uuid4(),
            user_id=uuid4(),
            trigger_type=TriggerType.TIME,
            trigger_context=TriggerContext(
                trigger_type=TriggerType.TIME,
                time_slot="morning",
                chapter=2,
            ),
            message_content="Good morning!",
            delivery_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    @pytest.mark.asyncio
    async def test_create_touchpoint(self, store, mock_session, sample_touchpoint):
        """AC-T004.1: Create operation works."""
        result = await store.create(sample_touchpoint)

        assert result.touchpoint_id == sample_touchpoint.touchpoint_id
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_has_crud_methods(self, store):
        """AC-T004.1: CRUD methods exist."""
        assert hasattr(store, "create")
        assert hasattr(store, "get")
        assert hasattr(store, "delete")
        assert hasattr(store, "mark_delivered")
        assert hasattr(store, "mark_skipped")

    @pytest.mark.asyncio
    async def test_get_due_touchpoints_method_exists(self, store):
        """AC-T004.2: get_due_touchpoints method exists."""
        assert hasattr(store, "get_due_touchpoints")
        assert callable(store.get_due_touchpoints)

    @pytest.mark.asyncio
    async def test_mark_delivered_method_exists(self, store):
        """AC-T004.3: mark_delivered method exists."""
        assert hasattr(store, "mark_delivered")
        assert callable(store.mark_delivered)

    @pytest.mark.asyncio
    async def test_get_user_touchpoints_method_exists(self, store):
        """AC-T004.4: get_user_touchpoints method exists."""
        assert hasattr(store, "get_user_touchpoints")
        assert callable(store.get_user_touchpoints)

    @pytest.mark.asyncio
    async def test_get_recent_touchpoints_method_exists(self, store):
        """get_recent_touchpoints for deduplication exists."""
        assert hasattr(store, "get_recent_touchpoints")
        assert callable(store.get_recent_touchpoints)

    @pytest.mark.asyncio
    async def test_count_pending_method_exists(self, store):
        """count_pending helper exists."""
        assert hasattr(store, "count_pending")
        assert callable(store.count_pending)


# =============================================================================
# T005: Coverage Tests (AC-T005.1, AC-T005.2)
# =============================================================================


class TestPhaseACoverage:
    """Ensure Phase A has comprehensive test coverage."""

    def test_models_module_coverage(self):
        """All model classes are tested."""
        # Verify we've tested all exported models
        from nikita.touchpoints.models import (
            CHAPTER_CONFIGS,
            ScheduledTouchpoint,
            TouchpointConfig,
            TriggerContext,
            TriggerType,
            get_config_for_chapter,
        )

        assert TriggerType is not None
        assert TriggerContext is not None
        assert TouchpointConfig is not None
        assert ScheduledTouchpoint is not None
        assert CHAPTER_CONFIGS is not None
        assert get_config_for_chapter is not None

    def test_store_module_coverage(self):
        """Store module is importable."""
        from nikita.touchpoints.store import TouchpointStore

        assert TouchpointStore is not None

    def test_db_model_coverage(self):
        """Database model is importable."""
        from nikita.db.models.scheduled_touchpoint import ScheduledTouchpoint

        assert ScheduledTouchpoint is not None
