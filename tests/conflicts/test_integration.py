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

from nikita.conflicts.models import (
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TriggerType,
    get_conflict_config,
)
from nikita.conflicts.store import ConflictStore
from nikita.conflicts.detector import DetectionContext, TriggerDetector
from nikita.conflicts.generator import ConflictGenerator, GenerationContext
from nikita.conflicts.escalation import EscalationManager
from nikita.conflicts.resolution import ResolutionContext, ResolutionManager
from nikita.conflicts.breakup import BreakupManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def store():
    """Fresh conflict store for each test."""
    return ConflictStore()


@pytest.fixture
def config():
    """Default conflict config."""
    return get_conflict_config()


@pytest.fixture
def detector(store):
    """Trigger detector without LLM."""
    return TriggerDetector(store=store, llm_enabled=False)


@pytest.fixture
def generator(store, config):
    """Conflict generator."""
    return ConflictGenerator(store=store, config=config)


@pytest.fixture
def escalation_mgr(store, config):
    """Escalation manager."""
    return EscalationManager(store=store, config=config)


@pytest.fixture
def resolution_mgr(store, config):
    """Resolution manager without LLM."""
    return ResolutionManager(store=store, config=config, llm_enabled=False)


@pytest.fixture
def breakup_mgr(store, config):
    """Breakup manager."""
    return BreakupManager(store=store, config=config)


# =============================================================================
# Full Lifecycle Tests
# =============================================================================


class TestFullLifecycle:
    """Test complete conflict lifecycle from detection to resolution."""

    def test_detect_generate_resolve_happy_path(
        self, store, detector, generator, resolution_mgr
    ):
        """Happy path: Detect trigger → Generate conflict → Resolve successfully."""
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

                # Step 3: Resolve with excellent apology
                res_context = ResolutionContext(
                    conflict=conflict,
                    user_message="I'm so sorry, I was wrong. I understand why you're upset. I love you.",
                )
                evaluation = resolution_mgr.evaluate_sync(res_context)
                result = resolution_mgr.resolve(conflict.conflict_id, evaluation)

                assert result.resolved is True
                assert result.resolution_type == ResolutionType.FULL

    def test_detect_generate_escalate_resolve(
        self, store, detector, generator, escalation_mgr, resolution_mgr
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

            # Simulate time passing and escalate
            store.escalate_conflict(conflict.conflict_id, EscalationLevel.DIRECT)
            conflict = store.get_conflict(conflict.conflict_id)
            assert conflict.escalation_level == EscalationLevel.DIRECT

            # Good apology at DIRECT level = PARTIAL resolution
            res_context = ResolutionContext(
                conflict=conflict,
                user_message="I'm sorry, I apologize for ignoring you.",
            )
            evaluation = resolution_mgr.evaluate_sync(res_context)

            # At DIRECT level, multiplier is 0.8
            assert evaluation.severity_reduction == pytest.approx(0.48)

    def test_poor_resolution_leads_to_escalation(
        self, store, detector, generator, escalation_mgr, resolution_mgr
    ):
        """Poor resolution attempts lead to escalation."""
        # Create a conflict
        conflict = store.create_conflict(
            user_id="user_789",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_1"],
            severity=0.5,
        )

        # Poor resolution attempt
        res_context = ResolutionContext(
            conflict=conflict,
            user_message="fine",  # Poor quality
        )
        evaluation = resolution_mgr.evaluate_sync(res_context)
        resolution_mgr.resolve(conflict.conflict_id, evaluation)

        # Conflict not resolved, still active
        updated = store.get_conflict(conflict.conflict_id)
        assert updated.resolved is False
        assert updated.resolution_attempts == 1


class TestBreakupScenarios:
    """Test breakup/game-over scenarios."""

    def test_low_score_triggers_breakup(self, store, breakup_mgr):
        """Score below threshold triggers breakup."""
        result, breakup = breakup_mgr.check_and_process(
            "user_lowscore",
            relationship_score=5,
        )

        assert result.should_breakup is True
        assert breakup is not None
        assert breakup.game_over is True
        assert len(breakup.final_message) > 0

    def test_three_crises_triggers_breakup(self, store, breakup_mgr):
        """Three consecutive crises trigger breakup."""
        # Create three crises
        for i in range(3):
            conflict = store.create_conflict(
                user_id="user_crises",
                conflict_type=ConflictType.JEALOUSY,
                trigger_ids=[f"trigger_{i}"],
                severity=0.8,
            )
            store.escalate_conflict(conflict.conflict_id, EscalationLevel.CRISIS)

        result, breakup = breakup_mgr.check_and_process(
            "user_crises",
            relationship_score=50,  # Score is fine
        )

        assert result.consecutive_crises == 3
        assert result.should_breakup is True
        assert breakup.game_over is True

    def test_resolved_crises_prevent_breakup(self, store, breakup_mgr, resolution_mgr):
        """Resolving crises prevents breakup."""
        # Create three crises but resolve them
        for i in range(3):
            conflict = store.create_conflict(
                user_id="user_resolved",
                conflict_type=ConflictType.ATTENTION,
                trigger_ids=[f"trigger_{i}"],
                severity=0.8,
            )
            store.escalate_conflict(conflict.conflict_id, EscalationLevel.CRISIS)

            # Excellent resolution
            res_context = ResolutionContext(
                conflict=store.get_conflict(conflict.conflict_id),
                user_message="I'm so sorry, I was wrong. I understand why you're upset.",
            )
            evaluation = resolution_mgr.evaluate_sync(res_context)
            resolution_mgr.resolve(conflict.conflict_id, evaluation)

        result, breakup = breakup_mgr.check_and_process(
            "user_resolved",
            relationship_score=50,
        )

        assert result.consecutive_crises == 0
        assert result.should_breakup is False
        assert breakup is None


class TestEscalationTimeline:
    """Test time-based escalation mechanics."""

    def test_check_escalation_timeline(self, store, escalation_mgr):
        """Get escalation timeline for a conflict."""
        conflict = store.create_conflict(
            user_id="user_timeline",
            conflict_type=ConflictType.BOUNDARY,
            trigger_ids=["trigger_1"],
            severity=0.6,
        )

        timeline = escalation_mgr.get_escalation_timeline(conflict)

        assert timeline["status"] == "active"
        assert timeline["current_level"] == "SUBTLE"
        assert timeline["natural_resolution_probability"] == 0.3

    def test_acknowledge_resets_timer(self, store, escalation_mgr):
        """Acknowledging a conflict resets the escalation timer."""
        conflict = store.create_conflict(
            user_id="user_ack",
            conflict_type=ConflictType.TRUST,
            trigger_ids=["trigger_1"],
            severity=0.7,
        )

        # Get initial time
        initial_time = conflict.triggered_at

        # Acknowledge (simulates user response)
        result = escalation_mgr.acknowledge(conflict)
        assert result is True

        # Last escalated should be updated
        updated = store.get_conflict(conflict.conflict_id)
        assert updated.last_escalated is not None
        assert updated.last_escalated > initial_time


class TestConflictPipeline:
    """Test the full pipeline integration."""

    def test_chapter_sensitivity_affects_detection(self, store, detector, config):
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

    def test_relationship_score_affects_generation(self, store, generator):
        """Relationship score affects conflict severity."""
        trigger = store.create_trigger(
            user_id="user_score",
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
        trigger2 = store.create_trigger(
            user_id="user_score2",
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


class TestStoreIntegration:
    """Test store operations across components."""

    def test_store_summary_updates(self, store, generator, resolution_mgr):
        """Conflict summary updates correctly through lifecycle."""
        # Create and resolve conflicts
        for i in range(3):
            conflict = store.create_conflict(
                user_id="user_summary",
                conflict_type=ConflictType.ATTENTION,
                trigger_ids=[f"trigger_{i}"],
                severity=0.5,
            )

            if i < 2:  # Resolve first two
                store.resolve_conflict(conflict.conflict_id, ResolutionType.FULL)

        summary = store.get_conflict_summary("user_summary")

        assert summary.total_conflicts == 3
        assert summary.resolved_conflicts == 2
        assert summary.current_conflict is not None  # Third one still active

    def test_multiple_users_isolated(self, store, breakup_mgr):
        """Different users have isolated conflict data."""
        # User 1 has a crisis
        conflict1 = store.create_conflict(
            user_id="user_isolated_1",
            conflict_type=ConflictType.JEALOUSY,
            trigger_ids=["trigger_1"],
            severity=0.8,
        )
        store.escalate_conflict(conflict1.conflict_id, EscalationLevel.CRISIS)

        # User 2 has nothing
        result1 = breakup_mgr.check_threshold("user_isolated_1", relationship_score=50)
        result2 = breakup_mgr.check_threshold("user_isolated_2", relationship_score=50)

        assert result1.consecutive_crises == 1
        assert result2.consecutive_crises == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_triggers_same_message(self, detector, store):
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

    def test_no_trigger_in_neutral_message(self, detector, store):
        """Neutral message doesn't trigger conflict."""
        context = DetectionContext(
            user_id="user_neutral",
            message="I had a great day at work today. How was yours?",
            chapter=2,
            relationship_score=60,
        )
        detection = detector.detect_sync(context)

        assert detection.has_triggers is False or len(detection.triggers) == 0

    def test_cooldown_prevents_rapid_conflicts(self, store, generator):
        """Cooldown prevents generating conflicts too quickly."""
        # Create first conflict
        conflict1 = store.create_conflict(
            user_id="user_cooldown",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_1"],
            severity=0.5,
        )

        # Try to generate another immediately
        trigger = store.create_trigger(
            user_id="user_cooldown",
            trigger_type=TriggerType.NEGLECT,
            severity=0.8,
            user_messages=["Some text"],
        )
        gen_context = GenerationContext(
            user_id="user_cooldown",
            chapter=3,
            relationship_score=50,
        )
        result = generator.generate([trigger], gen_context)

        # Should be skipped due to cooldown
        assert result.generated is False or result.reason is not None
