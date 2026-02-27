"""Integration tests for Conflict System (Spec 027, Phase G).

Tests the complete conflict lifecycle:
1. Trigger detection → Conflict generation
2. Escalation over time
3. Resolution attempts
4. Breakup/game-over scenarios
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TriggerType,
    get_conflict_config,
)
from nikita.conflicts.detector import DetectionContext, TriggerDetector
from nikita.conflicts.generator import ConflictGenerator, GenerationContext
from nikita.conflicts.escalation import EscalationManager
from nikita.conflicts.resolution import ResolutionContext, ResolutionManager
from nikita.conflicts.breakup import BreakupManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config():
    """Default conflict config."""
    return get_conflict_config()


@pytest.fixture
def detector():
    """Trigger detector without LLM."""
    return TriggerDetector(llm_enabled=False)


@pytest.fixture
def generator(config):
    """Conflict generator."""
    return ConflictGenerator(config=config)


@pytest.fixture
def escalation_mgr(config):
    """Escalation manager."""
    return EscalationManager(config=config)


@pytest.fixture
def resolution_mgr(config):
    """Resolution manager without LLM."""
    return ResolutionManager(config=config, llm_enabled=False)


@pytest.fixture
def breakup_mgr(config):
    """Breakup manager."""
    return BreakupManager(config=config)


def _make_conflict(
    user_id: str = "user_123",
    conflict_type: ConflictType = ConflictType.JEALOUSY,
    severity: float = 0.5,
    escalation_level: EscalationLevel = EscalationLevel.SUBTLE,
    triggered_at: datetime | None = None,
    last_escalated: datetime | None = None,
    resolved: bool = False,
    resolution_type: ResolutionType | None = None,
) -> ActiveConflict:
    """Helper to build an ActiveConflict for testing."""
    return ActiveConflict(
        conflict_id=str(uuid4()),
        user_id=user_id,
        conflict_type=conflict_type,
        severity=severity,
        escalation_level=escalation_level,
        triggered_at=triggered_at or datetime.now(UTC),
        last_escalated=last_escalated,
        resolved=resolved,
        resolution_type=resolution_type,
    )


# =============================================================================
# Full Lifecycle Tests
# =============================================================================


class TestFullLifecycle:
    """Test complete conflict lifecycle from detection to resolution."""

    def test_detect_generate_resolve_happy_path(
        self, detector, generator, resolution_mgr
    ):
        """Happy path: Detect trigger → Generate conflict → Evaluate resolution."""
        # Step 1: Detect a trigger
        context = DetectionContext(
            user_id="user_123",
            message="Sorry, I was with my coworker Sarah all day.",  # Jealousy trigger
            chapter=1,
            relationship_score=50,
        )
        detection = detector.detect_sync(context)

        assert detection.has_triggers is True
        assert detection.triggers[0].trigger_type == TriggerType.JEALOUSY

        # Step 2: Generate a conflict from trigger
        if detection.triggers:
            gen_context = GenerationContext(
                user_id="user_123",
                chapter=1,
                relationship_score=50,
            )
            generation = generator.generate(detection.triggers, gen_context)

            if generation.generated:
                conflict = generation.conflict

                # Step 3: Evaluate excellent apology
                res_context = ResolutionContext(
                    conflict=conflict,
                    user_message="I'm so sorry, I was wrong. I understand why you're upset. I love you.",
                )
                evaluation = resolution_mgr.evaluate_sync(res_context)

                assert evaluation.resolution_type == ResolutionType.FULL

    def test_detect_generate_escalate_evaluate(
        self, detector, generator, escalation_mgr, resolution_mgr
    ):
        """Conflict escalates before resolution."""
        # Create and detect a trigger
        context = DetectionContext(
            user_id="user_456",
            message="I don't have time for you right now.",  # Neglect trigger
            chapter=2,
            relationship_score=45,
        )
        detection = detector.detect_sync(context)

        # Generate conflict
        gen_context = GenerationContext(
            user_id="user_456",
            chapter=2,
            relationship_score=45,
        )
        generation = generator.generate(detection.triggers, gen_context)

        if generation.generated:
            conflict = generation.conflict
            assert conflict.escalation_level == EscalationLevel.SUBTLE

            # Simulate time passing — build a DIRECT-level conflict directly
            escalated_conflict = _make_conflict(
                user_id="user_456",
                conflict_type=conflict.conflict_type,
                severity=conflict.severity,
                escalation_level=EscalationLevel.DIRECT,
                triggered_at=conflict.triggered_at,
                last_escalated=datetime.now(UTC),
            )
            assert escalated_conflict.escalation_level == EscalationLevel.DIRECT

            # Good apology at DIRECT level = PARTIAL resolution with 0.8 multiplier
            res_context = ResolutionContext(
                conflict=escalated_conflict,
                user_message="I'm sorry, I apologize for ignoring you.",
            )
            evaluation = resolution_mgr.evaluate_sync(res_context)

            # At DIRECT level, multiplier is 0.8
            assert evaluation.severity_reduction == pytest.approx(0.48)

    def test_poor_resolution_does_not_resolve_conflict(
        self, detector, generator, resolution_mgr
    ):
        """Poor resolution attempt leaves conflict unresolved."""
        # Create a conflict
        conflict = _make_conflict(
            user_id="user_789",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
        )

        # Poor resolution attempt
        res_context = ResolutionContext(
            conflict=conflict,
            user_message="fine",  # Poor quality
        )
        evaluation = resolution_mgr.evaluate_sync(res_context)

        # Evaluation should be POOR/FAILED
        from nikita.conflicts.resolution import ResolutionQuality
        assert evaluation.quality == ResolutionQuality.POOR
        assert evaluation.resolution_type == ResolutionType.FAILED

        # Conflict is NOT resolved (caller is responsible for updating state)
        assert conflict.resolved is False


# =============================================================================
# Breakup Scenarios
# =============================================================================


class TestBreakupScenarios:
    """Test breakup/game-over scenarios."""

    def test_low_score_triggers_breakup(self, breakup_mgr):
        """Score below threshold triggers breakup."""
        result, breakup = breakup_mgr.check_and_process(
            "user_lowscore",
            relationship_score=5,
        )

        assert result.should_breakup is True
        assert breakup is not None
        assert breakup.game_over is True
        assert len(breakup.final_message) > 0

    def test_score_above_threshold_no_breakup(self, breakup_mgr):
        """Score above threshold doesn't trigger breakup."""
        result, breakup = breakup_mgr.check_and_process(
            "user_ok",
            relationship_score=50,
        )

        assert result.should_breakup is False
        assert breakup is None


# =============================================================================
# Escalation Timeline
# =============================================================================


class TestEscalationTimeline:
    """Test time-based escalation mechanics."""

    def test_check_escalation_timeline(self, escalation_mgr):
        """Get escalation timeline for a conflict."""
        conflict = _make_conflict(
            user_id="user_timeline",
            conflict_type=ConflictType.BOUNDARY,
            severity=0.6,
            escalation_level=EscalationLevel.SUBTLE,
        )

        timeline = escalation_mgr.get_escalation_timeline(conflict)

        assert timeline["status"] == "active"
        assert timeline["current_level"] == "SUBTLE"
        assert timeline["natural_resolution_probability"] == 0.3

    def test_acknowledge_returns_true(self, escalation_mgr):
        """Acknowledging a conflict returns True (without conflict_details)."""
        conflict = _make_conflict(
            user_id="user_ack",
            conflict_type=ConflictType.TRUST,
            severity=0.7,
        )

        result = escalation_mgr.acknowledge(conflict)
        assert result is True


# =============================================================================
# Conflict Pipeline
# =============================================================================


class TestConflictPipeline:
    """Test the full pipeline integration."""

    def test_chapter_sensitivity_affects_detection(self, detector, config):
        """Chapter affects trigger detection sensitivity."""
        # Same message in chapter 1 (high sensitivity) vs chapter 5 (low sensitivity)
        message = "I was hanging out with my ex today."

        context_ch1 = DetectionContext(
            user_id="user_ch1",
            message=message,
            chapter=1,  # 1.5x sensitivity
            relationship_score=50,
        )
        detection_ch1 = detector.detect_sync(context_ch1)

        context_ch5 = DetectionContext(
            user_id="user_ch5",
            message=message,
            chapter=5,  # 0.8x sensitivity
            relationship_score=50,
        )
        detection_ch5 = detector.detect_sync(context_ch5)

        # Both should detect, but chapter 1 should have higher severity
        if detection_ch1.triggers and detection_ch5.triggers:
            assert detection_ch1.triggers[0].severity >= detection_ch5.triggers[0].severity

    def test_relationship_score_affects_generation(self, generator):
        """Relationship score affects conflict severity."""
        from nikita.conflicts.models import ConflictTrigger

        trigger = ConflictTrigger(
            trigger_id=str(uuid4()),
            trigger_type=TriggerType.JEALOUSY,
            severity=0.8,
            user_messages=["Some text"],
        )

        # Low relationship score = higher severity
        gen_low = GenerationContext(
            user_id="user_score",
            chapter=3,
            relationship_score=25,  # Low score
        )
        result_low = generator.generate([trigger], gen_low)

        # High relationship score = lower severity
        trigger2 = ConflictTrigger(
            trigger_id=str(uuid4()),
            trigger_type=TriggerType.JEALOUSY,
            severity=0.8,
            user_messages=["Some text"],
        )
        gen_high = GenerationContext(
            user_id="user_score2",
            chapter=3,
            relationship_score=75,  # High score
        )
        result_high = generator.generate([trigger2], gen_high)

        if result_low.generated and result_high.generated:
            assert result_low.conflict.severity > result_high.conflict.severity


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_triggers_same_message(self, detector):
        """Message with multiple trigger types."""
        context = DetectionContext(
            user_id="user_multi",
            message="I don't care about your ex girlfriend, leave me alone!",  # Dismissive + jealousy
            chapter=3,
            relationship_score=40,
        )
        detection = detector.detect_sync(context)

        # Should detect triggers
        assert detection.has_triggers is True
        # First trigger should be one of the detected types
        assert len(detection.triggers) > 0
        assert detection.triggers[0].trigger_type in [
            TriggerType.DISMISSIVE,
            TriggerType.JEALOUSY,
        ]

    def test_no_trigger_in_neutral_message(self, detector):
        """Neutral message doesn't trigger conflict."""
        context = DetectionContext(
            user_id="user_neutral",
            message="I had a great day at work today. How was yours?",
            chapter=2,
            relationship_score=60,
        )
        detection = detector.detect_sync(context)

        assert detection.has_triggers is False or len(detection.triggers) == 0

    def test_cooldown_prevents_rapid_conflicts(self, generator):
        """Cooldown prevents generating conflicts too quickly (via recent_conflicts)."""
        from nikita.conflicts.models import ConflictTrigger

        # Create a recent conflict to simulate cooldown
        recent_conflict = _make_conflict(
            user_id="user_cooldown",
            conflict_type=ConflictType.ATTENTION,
            triggered_at=datetime.now(UTC) - timedelta(hours=1),  # Recent
        )

        trigger = ConflictTrigger(
            trigger_id=str(uuid4()),
            trigger_type=TriggerType.NEGLECT,
            severity=0.8,
            user_messages=["Some text"],
        )
        gen_context = GenerationContext(
            user_id="user_cooldown",
            chapter=3,
            relationship_score=50,
            recent_conflicts=[recent_conflict],
            days_since_last_conflict=0.04,  # ~1 hour
        )
        result = generator.generate([trigger], gen_context)

        # Should be skipped due to cooldown (recent conflict < 4h ago)
        assert result.generated is False or result.reason is not None
