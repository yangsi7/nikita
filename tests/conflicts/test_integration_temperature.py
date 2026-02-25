"""Integration tests for Spec 057 temperature wiring.

T10: Generator temperature zone injection
T11: Detector temperature on trigger
T12: Escalation temperature integration
T13: Resolution temperature reduction + Gottman
T14: Breakup temperature thresholds
T15+T17: ConflictStage temperature consumption + time decay
T19: Full flow integration tests
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictDetails,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TemperatureZone,
    TriggerType,
)


# ============================================================================
# T10: Generator Temperature Zone Injection
# ============================================================================


class TestGeneratorTemperatureZoneInjection:
    """T10: ConflictGenerator uses temperature zone for injection probability."""

    @pytest.fixture
    def mock_store(self):
        store = MagicMock()
        store.get_active_conflict.return_value = None
        store.create_conflict.return_value = ActiveConflict(
            conflict_id="gen-001",
            user_id="user-1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
        )
        return store

    @pytest.fixture
    def generator(self, mock_store):
        from nikita.conflicts.generator import ConflictGenerator

        return ConflictGenerator(store=mock_store)

    @pytest.fixture
    def gen_context(self):
        from nikita.conflicts.generator import GenerationContext

        return GenerationContext(
            user_id="user-1",
            chapter=3,
            relationship_score=50,
        )

    @pytest.fixture
    def sample_triggers(self):
        return [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.DISMISSIVE,
                severity=0.4,
                context={"reason": "test"},
            ),
        ]

    def test_calm_zone_never_generates(self, generator, gen_context, sample_triggers):
        """CALM zone (temp < 25) should never generate conflicts."""
        calm_details = {"temperature": 10.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = generator.generate(sample_triggers, gen_context, conflict_details=calm_details)

        assert not result.generated
        assert "CALM" in result.reason

    def test_warm_zone_stochastic_injection(self, generator, gen_context, sample_triggers):
        """WARM zone should use stochastic injection (10-25% probability)."""
        warm_details = {"temperature": 35.0, "zone": "warm"}

        generated_count = 0
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            # Run 100 times to test probability
            for i in range(100):
                random.seed(i)
                result = generator.generate(sample_triggers, gen_context, conflict_details=warm_details)
                if result.generated:
                    generated_count += 1

        # WARM zone: 10-25% probability (expect ~10-30 out of 100)
        assert 3 <= generated_count <= 40

    def test_hot_zone_medium_probability(self, generator, gen_context, sample_triggers):
        """HOT zone should have medium injection probability (25-60%)."""
        hot_details = {"temperature": 60.0, "zone": "hot"}

        generated_count = 0
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            for i in range(100):
                random.seed(i)
                result = generator.generate(sample_triggers, gen_context, conflict_details=hot_details)
                if result.generated:
                    generated_count += 1

        assert 15 <= generated_count <= 75

    def test_critical_zone_high_probability(self, generator, gen_context, sample_triggers):
        """CRITICAL zone should have high injection probability (60-90%)."""
        critical_details = {"temperature": 85.0, "zone": "critical"}

        generated_count = 0
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            for i in range(100):
                random.seed(i)
                result = generator.generate(sample_triggers, gen_context, conflict_details=critical_details)
                if result.generated:
                    generated_count += 1

        assert generated_count >= 50  # Should be quite high

    def test_severity_capped_by_zone(self, generator, gen_context, mock_store):
        """Generated conflict severity should be capped by zone max."""
        warm_details = {"temperature": 30.0, "zone": "warm"}
        # High severity trigger
        high_triggers = [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.TRUST,
                severity=0.9,
                context={"reason": "test"},
            ),
        ]

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            # Try multiple seeds until one generates
            for i in range(1000):
                random.seed(i)
                result = generator.generate(high_triggers, gen_context, conflict_details=warm_details)
                if result.generated:
                    # Check the severity passed to create_conflict (not the mock return)
                    call_args = mock_store.create_conflict.call_args
                    actual_severity = call_args.kwargs.get("severity", call_args[1].get("severity") if len(call_args) > 1 else None)
                    if actual_severity is None:
                        # Positional args
                        actual_severity = call_args[1]["severity"]
                    # WARM zone max severity = 0.4
                    assert actual_severity <= 0.4, f"Severity {actual_severity} should be <= 0.4"
                    # Also check the reason mentions severity cap
                    assert "severity=" in result.reason
                    break

    def test_flag_off_uses_existing_logic(self, generator, gen_context, sample_triggers):
        """When flag is OFF, should fall through to existing cooldown logic."""
        warm_details = {"temperature": 35.0, "zone": "warm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = generator.generate(sample_triggers, gen_context, conflict_details=warm_details)

        # Should use existing logic (no temperature reference in reason)
        assert "Temperature" not in result.reason and "CALM" not in result.reason

    def test_no_triggers_skips_even_in_hot_zone(self, generator, gen_context):
        """No triggers should skip generation even in HOT zone."""
        hot_details = {"temperature": 60.0, "zone": "hot"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = generator.generate([], gen_context, conflict_details=hot_details)

        assert not result.generated
        assert "No triggers" in result.reason


# ============================================================================
# T11: Detector Temperature on Trigger
# ============================================================================


class TestDetectorTemperatureOnTrigger:
    """T11: TriggerDetector updates temperature on trigger detection."""

    @pytest.fixture
    def detector(self):
        from nikita.conflicts.detector import TriggerDetector

        return TriggerDetector(store=MagicMock(), llm_enabled=False)

    @pytest.fixture
    def detection_context(self):
        from nikita.conflicts.detector import DetectionContext

        return DetectionContext(
            user_id="user-1",
            message="k",  # Short dismissive message
            chapter=3,
            relationship_score=50,
        )

    @pytest.mark.asyncio
    async def test_trigger_detection_updates_temperature(self, detector, detection_context):
        """Detected triggers should increase temperature."""
        details = {"temperature": 10.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await detector.detect(detection_context, conflict_details=details)

        # Should have updated_conflict_details when triggers found
        if result.has_triggers:
            assert result.updated_conflict_details is not None
            assert result.updated_conflict_details["temperature"] > 10.0

    @pytest.mark.asyncio
    async def test_no_triggers_no_temperature_update(self, detector):
        """No triggers means no temperature update."""
        from nikita.conflicts.detector import DetectionContext

        context = DetectionContext(
            user_id="user-1",
            message="I really enjoyed our conversation about hiking yesterday",
            chapter=3,
            relationship_score=80,
        )
        details = {"temperature": 10.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await detector.detect(context, conflict_details=details)

        # If no triggers, updated_conflict_details should be None
        if not result.has_triggers:
            assert result.updated_conflict_details is None

    @pytest.mark.asyncio
    async def test_flag_off_no_temperature_update(self, detector, detection_context):
        """When flag is OFF, no temperature update."""
        details = {"temperature": 10.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = await detector.detect(detection_context, conflict_details=details)

        assert result.updated_conflict_details is None

    def test_each_trigger_type_has_temperature_delta(self):
        """Each trigger type should produce a non-zero temperature increase."""
        from nikita.conflicts.temperature import TemperatureEngine

        for trigger_type in TriggerType:
            delta = TemperatureEngine.calculate_delta_from_trigger(trigger_type)
            assert delta > 0, f"{trigger_type} should have positive delta"


# ============================================================================
# T12: Escalation Temperature Integration
# ============================================================================


class TestEscalationTemperatureIntegration:
    """T12: EscalationManager uses temperature zones for escalation."""

    @pytest.fixture
    def mock_store(self):
        store = MagicMock()
        store.escalate_conflict.return_value = None
        store.resolve_conflict.return_value = None
        store.update_conflict.return_value = None
        store.increment_resolution_attempts.return_value = None
        return store

    @pytest.fixture
    def manager(self, mock_store):
        from nikita.conflicts.escalation import EscalationManager

        return EscalationManager(store=mock_store)

    @pytest.fixture
    def subtle_conflict(self):
        return ActiveConflict(
            conflict_id="esc-001",
            user_id="user-1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=5),
        )

    def test_hot_zone_escalates_to_direct(self, manager, subtle_conflict):
        """HOT zone should escalate SUBTLE to DIRECT."""
        hot_details = {"temperature": 60.0, "zone": "hot"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_escalation(subtle_conflict, conflict_details=hot_details)

        assert result.escalated
        assert result.new_level == EscalationLevel.DIRECT

    def test_critical_zone_escalates_to_crisis(self, manager, subtle_conflict):
        """CRITICAL zone should escalate to CRISIS."""
        critical_details = {"temperature": 85.0, "zone": "critical"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_escalation(subtle_conflict, conflict_details=critical_details)

        assert result.escalated
        assert result.new_level == EscalationLevel.CRISIS

    def test_calm_zone_no_escalation(self, manager, subtle_conflict):
        """CALM zone should not escalate."""
        calm_details = {"temperature": 10.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_escalation(subtle_conflict, conflict_details=calm_details)

        assert not result.escalated

    def test_acknowledge_reduces_temperature(self, manager, subtle_conflict):
        """Acknowledging a conflict should reduce temperature."""
        warm_details = {
            "temperature": 40.0, "zone": "warm",
            "positive_count": 0, "negative_count": 0,
            "gottman_ratio": 0.0, "gottman_target": 20.0,
            "horsemen_detected": [], "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0, "session_negative": 0,
        }

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.acknowledge(subtle_conflict, conflict_details=warm_details)

        assert isinstance(result, dict)
        assert result["temperature"] < 40.0
        # SUBTLE level: reduction of 10
        assert result["temperature"] == pytest.approx(30.0, abs=0.1)


# ============================================================================
# T13: Resolution Temperature Reduction + Gottman
# ============================================================================


class TestResolutionTemperatureReduction:
    """T13: ResolutionManager updates temperature on resolution."""

    @pytest.fixture
    def mock_store(self):
        store = MagicMock()
        conflict = ActiveConflict(
            conflict_id="res-001",
            user_id="user-1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
        )
        store.get_conflict.return_value = conflict
        store.reduce_severity.return_value = None
        store.increment_resolution_attempts.return_value = None
        store.resolve_conflict.return_value = None
        return store

    @pytest.fixture
    def manager(self, mock_store):
        from nikita.conflicts.resolution import ResolutionManager

        return ResolutionManager(store=mock_store, llm_enabled=False)

    def test_excellent_resolution_reduces_temperature_25(self, manager):
        """EXCELLENT resolution should reduce temperature by 25."""
        from nikita.conflicts.resolution import ResolutionEvaluation, ResolutionQuality

        hot_details = {
            "temperature": 60.0, "zone": "hot",
            "positive_count": 3, "negative_count": 5,
            "gottman_ratio": 0.6, "gottman_target": 5.0,
            "horsemen_detected": [], "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0, "session_negative": 0,
        }
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.EXCELLENT,
            resolution_type=ResolutionType.FULL,
            severity_reduction=1.0,
        )

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            manager.resolve("res-001", evaluation, conflict_details=hot_details)

        updated = manager.get_last_updated_conflict_details()
        assert updated is not None
        assert updated["temperature"] == pytest.approx(35.0, abs=0.1)

    def test_harmful_resolution_increases_temperature(self, manager):
        """HARMFUL resolution should increase temperature by 5."""
        from nikita.conflicts.resolution import ResolutionEvaluation, ResolutionQuality

        details = {
            "temperature": 50.0, "zone": "hot",
            "positive_count": 2, "negative_count": 5,
            "gottman_ratio": 0.4, "gottman_target": 5.0,
            "horsemen_detected": [], "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0, "session_negative": 0,
        }
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.HARMFUL,
            resolution_type=ResolutionType.FAILED,
            severity_reduction=-0.2,
        )

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            manager.resolve("res-001", evaluation, conflict_details=details)

        updated = manager.get_last_updated_conflict_details()
        assert updated is not None
        assert updated["temperature"] > 50.0

    def test_good_resolution_records_repair_and_gottman(self, manager):
        """GOOD resolution should record repair and increment positive Gottman."""
        from nikita.conflicts.resolution import ResolutionEvaluation, ResolutionQuality

        details = {
            "temperature": 45.0, "zone": "warm",
            "positive_count": 3, "negative_count": 5,
            "gottman_ratio": 0.6, "gottman_target": 5.0,
            "horsemen_detected": [], "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0, "session_negative": 0,
        }
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.GOOD,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.6,
        )

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            manager.resolve("res-001", evaluation, conflict_details=details)

        updated = manager.get_last_updated_conflict_details()
        assert updated is not None
        # Temperature reduced by 15 (GOOD)
        assert updated["temperature"] < 45.0
        # Repair recorded
        assert len(updated["repair_attempts"]) == 1
        assert updated["repair_attempts"][0]["quality"] == "good"
        # Gottman positive incremented (GOOD is a positive repair)
        assert updated["positive_count"] == 4


# ============================================================================
# T14: Breakup Temperature Thresholds
# ============================================================================


class TestBreakupTemperatureThresholds:
    """T14: BreakupManager checks temperature-based breakup thresholds."""

    @pytest.fixture
    def mock_store(self):
        store = MagicMock()
        store.count_consecutive_unresolved_crises.return_value = 0
        return store

    @pytest.fixture
    def manager(self, mock_store):
        from nikita.conflicts.breakup import BreakupManager

        return BreakupManager(store=mock_store)

    def test_critical_zone_over_24h_warns(self, manager):
        """CRITICAL zone > 24h should trigger warning."""
        details = {"temperature": 80.0, "zone": "critical"}
        last_conflict = datetime.now(UTC) - timedelta(hours=30)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                "user-1", 50, conflict_details=details, last_conflict_at=last_conflict
            )

        assert result.should_warn
        assert "24h" in result.reason or "warning" in result.reason.lower()

    def test_temperature_90_over_48h_triggers_breakup(self, manager):
        """Temperature >90 for >48h should trigger breakup."""
        details = {"temperature": 95.0, "zone": "critical"}
        last_conflict = datetime.now(UTC) - timedelta(hours=50)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                "user-1", 50, conflict_details=details, last_conflict_at=last_conflict
            )

        assert result.should_breakup
        assert "48h" in result.reason or ">90" in result.reason

    def test_critical_zone_under_24h_no_temp_warning(self, manager):
        """CRITICAL zone < 24h should not trigger temperature-based warning."""
        details = {"temperature": 80.0, "zone": "critical"}
        last_conflict = datetime.now(UTC) - timedelta(hours=12)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                "user-1", 50, conflict_details=details, last_conflict_at=last_conflict
            )

        # Should fall through to score-based check
        assert not result.should_breakup

    def test_score_based_breakup_still_works_with_flag_on(self, manager):
        """Score-based breakup should still work even with flag ON."""
        calm_details = {"temperature": 5.0, "zone": "calm"}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold("user-1", 5, conflict_details=calm_details)

        assert result.should_breakup
        assert "below breakup threshold" in result.reason

    def test_flag_off_uses_score_only(self, manager):
        """When flag is OFF, only score-based breakup triggers."""
        critical_details = {"temperature": 95.0, "zone": "critical"}
        last_conflict = datetime.now(UTC) - timedelta(hours=50)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = manager.check_threshold(
                "user-1", 50, conflict_details=critical_details, last_conflict_at=last_conflict
            )

        # Should NOT trigger breakup because score is 50 (healthy)
        assert not result.should_breakup


# ============================================================================
# T15 + T17: ConflictStage Temperature Consumption + Time Decay
# ============================================================================


class TestConflictStageTemperature:
    """T15: ConflictStage reads temperature and maps to active_conflict.
    T17: ConflictStage applies passive time decay.
    """

    @pytest.fixture
    def stage(self):
        from nikita.pipeline.stages.conflict import ConflictStage

        return ConflictStage()

    @pytest.fixture
    def base_ctx(self):
        from dataclasses import dataclass, field
        from decimal import Decimal
        from uuid import uuid4

        @dataclass
        class MockCtx:
            user_id: str = str(uuid4())
            chapter: int = 3
            relationship_score: Decimal = Decimal("50")
            emotional_state: dict = field(default_factory=dict)
            active_conflict: bool = False
            conflict_type: str | None = None
            conflict_temperature: float = 0.0
            conflict_details: dict | None = None
            game_over_triggered: bool = False

        return MockCtx()

    @pytest.mark.asyncio
    async def test_hot_zone_sets_active_conflict(self, stage, base_ctx):
        """HOT zone should set active_conflict=True."""
        base_ctx.conflict_details = {"temperature": 60.0, "zone": "hot", "last_temp_update": None}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await stage._run_temperature_mode(base_ctx)

        assert base_ctx.active_conflict is True
        assert result["zone"] == "hot"

    @pytest.mark.asyncio
    async def test_calm_zone_sets_no_conflict(self, stage, base_ctx):
        """CALM zone should set active_conflict=False."""
        base_ctx.conflict_details = {"temperature": 10.0, "zone": "calm", "last_temp_update": None}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("nikita.conflicts.breakup.BreakupManager.check_threshold",
                       return_value=MagicMock(should_breakup=False)):
                result = await stage._run_temperature_mode(base_ctx)

        assert base_ctx.active_conflict is False
        assert result["zone"] == "calm"

    @pytest.mark.asyncio
    async def test_time_decay_reduces_temperature(self, stage, base_ctx):
        """Temperature should decay over time (0.5/hr)."""
        two_hours_ago = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        base_ctx.conflict_details = {
            "temperature": 40.0, "zone": "warm",
            "last_temp_update": two_hours_ago,
            "positive_count": 0, "negative_count": 0,
            "gottman_ratio": 0.0, "gottman_target": 20.0,
            "horsemen_detected": [], "repair_attempts": [],
            "session_positive": 0, "session_negative": 0,
        }

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("nikita.conflicts.breakup.BreakupManager.check_threshold",
                       return_value=MagicMock(should_breakup=False)):
                result = await stage._run_temperature_mode(base_ctx)

        # 2 hours * 0.5/hr = 1.0 decay -> 40 - 1 = 39
        assert result["temperature"] < 40.0
        assert result["temperature"] >= 38.0  # Allow small timing variance

    @pytest.mark.asyncio
    async def test_empty_conflict_details_defaults_to_zero(self, stage, base_ctx):
        """Empty/None conflict_details should default to temperature 0."""
        base_ctx.conflict_details = None

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("nikita.conflicts.breakup.BreakupManager.check_threshold",
                       return_value=MagicMock(should_breakup=False)):
                result = await stage._run_temperature_mode(base_ctx)

        assert result["temperature"] == 0.0
        assert result["zone"] == "calm"
        assert base_ctx.active_conflict is False

    @pytest.mark.asyncio
    async def test_temperature_stored_in_ctx(self, stage, base_ctx):
        """Temperature value should be stored in ctx.conflict_temperature."""
        base_ctx.conflict_details = {"temperature": 55.0, "zone": "hot", "last_temp_update": None}

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("nikita.conflicts.breakup.BreakupManager.check_threshold",
                       return_value=MagicMock(should_breakup=False)):
                await stage._run_temperature_mode(base_ctx)

        assert base_ctx.conflict_temperature == 55.0


# ============================================================================
# T19: Full Flow Integration Tests
# ============================================================================


class TestFullFlowIntegration:
    """Full flow integration: scoring → temperature → conflict → resolution."""

    def test_scoring_to_temperature_to_conflict_flow(self):
        """Negative scoring should increase temperature, enabling conflict injection."""
        from nikita.conflicts.models import ConflictDetails
        from nikita.conflicts.temperature import TemperatureEngine
        from nikita.engine.scoring.models import get_horsemen_from_behaviors

        # Start with empty details
        details = ConflictDetails()

        # Simulate 5 negative interactions
        for _ in range(5):
            score_delta = -5.0
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)

        # Temperature should have risen significantly
        assert details.temperature > 25.0  # Past CALM
        zone = TemperatureEngine.get_zone(details.temperature)
        assert zone != TemperatureZone.CALM

    def test_repair_flow_reduces_temperature(self):
        """Resolution should reduce temperature and update Gottman."""
        from nikita.conflicts.gottman import GottmanTracker
        from nikita.conflicts.models import ConflictDetails
        from nikita.conflicts.temperature import TemperatureEngine

        # Start in HOT zone
        details = ConflictDetails(temperature=60.0, zone="hot", negative_count=5)

        # EXCELLENT repair: -25 temperature
        details = TemperatureEngine.update_conflict_details(details, -25.0)
        assert details.temperature == 35.0

        # Gottman positive from repair
        details = GottmanTracker.update_conflict_details(details, is_positive=True, is_in_conflict=False)
        assert details.positive_count == 1

    def test_sustained_critical_leads_to_breakup(self):
        """Sustained CRITICAL zone should eventually trigger breakup warning."""
        from nikita.conflicts.breakup import BreakupManager

        store = MagicMock()
        store.count_consecutive_unresolved_crises.return_value = 0
        manager = BreakupManager(store=store)

        details = {"temperature": 95.0, "zone": "critical"}
        last_conflict = datetime.now(UTC) - timedelta(hours=50)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                "user-1", 50, conflict_details=details, last_conflict_at=last_conflict
            )

        assert result.should_breakup

    def test_flag_off_zero_behavior_change(self):
        """With flag OFF, full flow should produce zero temperature changes."""
        from nikita.conflicts.generator import ConflictGenerator, GenerationContext
        from nikita.conflicts.models import ConflictDetails

        store = MagicMock()
        store.get_active_conflict.return_value = None
        store.create_conflict.return_value = ActiveConflict(
            conflict_id="flag-off-001",
            user_id="user-1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.4,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
        )
        generator = ConflictGenerator(store=store)

        context = GenerationContext(user_id="user-1", chapter=3, relationship_score=50)
        triggers = [
            ConflictTrigger(
                trigger_id="t1", trigger_type=TriggerType.DISMISSIVE,
                severity=0.4, context={"reason": "test"},
            ),
        ]

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = generator.generate(triggers, context, conflict_details={"temperature": 60.0})

        # Should use existing logic, not temperature-based
        assert "Temperature" not in result.reason and "CALM" not in result.reason
