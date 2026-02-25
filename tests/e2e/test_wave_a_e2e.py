"""E2E Integration Tests for Wave A — Conflict Temperature Wiring.

Tests the full message → scoring → temperature → conflict → breakup pipeline.
Uses in-process mocking (no real DB or Cloud Run needed).

Test Groups:
- Temperature Accumulation (T1-T4)
- Gottman Ratio (T5-T7)
- Pipeline Integration (T8-T10)
- Breakup Threshold (T11-T12)
"""

import asyncio
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import ConflictDetails, GottmanCounters, TemperatureZone
from nikita.conflicts.temperature import TemperatureEngine
from nikita.engine.scoring.calculator import ScoreResult
from nikita.engine.scoring.models import MetricDeltas, ResponseAnalysis


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_details() -> ConflictDetails:
    """Fresh conflict details (temperature=0, all counters at 0)."""
    return ConflictDetails()


@pytest.fixture
def warm_details() -> ConflictDetails:
    """Conflict details at WARM zone (temperature=30)."""
    return ConflictDetails(
        temperature=30.0,
        zone="warm",
        positive_count=3,
        negative_count=5,
        gottman_ratio=0.6,
        gottman_target=5.0,
        last_temp_update=datetime.now(UTC).isoformat(),
    )


@pytest.fixture
def critical_details() -> ConflictDetails:
    """Conflict details at CRITICAL zone (temperature=85)."""
    return ConflictDetails(
        temperature=85.0,
        zone="critical",
        positive_count=2,
        negative_count=20,
        gottman_ratio=0.1,
        gottman_target=5.0,
        last_temp_update=datetime.now(UTC).isoformat(),
    )


@pytest.fixture
def mock_scoring_service():
    """Create a ScoringService that returns predictable results."""
    from nikita.engine.scoring.service import ScoringService

    service = ScoringService()
    return service


def make_negative_analysis() -> ResponseAnalysis:
    """Create a negative interaction analysis."""
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("-3"),
            passion=Decimal("-2"),
            trust=Decimal("-4"),
            secureness=Decimal("-1"),
        ),
        explanation="User was dismissive and hostile",
        behaviors_identified=["dismissive", "horseman:criticism"],
    )


def make_positive_analysis() -> ResponseAnalysis:
    """Create a positive interaction analysis."""
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("3"),
            passion=Decimal("2"),
            trust=Decimal("2"),
            secureness=Decimal("1"),
        ),
        explanation="User was kind and attentive",
        behaviors_identified=["supportive", "empathetic"],
    )


# ============================================================================
# Test Group 1: Temperature Accumulation (T1-T4)
# ============================================================================


class TestTemperatureAccumulation:
    """T1-T4: Verify temperature increases, decreases, decays, and stays at zero."""

    @pytest.mark.asyncio
    async def test_t1_negative_messages_increase_temperature(self):
        """T1: Three negative messages should accumulate temperature."""
        details = ConflictDetails()
        assert details.temperature == 0.0

        # Simulate 3 negative scoring rounds
        for i in range(3):
            score_delta = -5.0  # Negative score change
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            assert temp_delta > 0, f"Negative score should increase temp, got {temp_delta}"
            details = TemperatureEngine.update_conflict_details(details, temp_delta)

        # After 3 negative interactions, temperature should be well above 0
        assert details.temperature > 15.0, (
            f"After 3 negative interactions, temp should be >15, got {details.temperature}"
        )
        assert details.zone != "calm" or details.temperature >= 20.0

    @pytest.mark.asyncio
    async def test_t2_positive_message_decreases_temperature(self):
        """T2: Positive interaction after negatives should decrease temperature."""
        # Start at WARM (30)
        details = ConflictDetails(
            temperature=30.0,
            zone="warm",
            last_temp_update=datetime.now(UTC).isoformat(),
        )

        # Apply positive score delta
        score_delta = 5.0  # Positive score change
        temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
        assert temp_delta < 0, f"Positive score should decrease temp, got {temp_delta}"

        details = TemperatureEngine.update_conflict_details(details, temp_delta)
        assert details.temperature < 30.0, (
            f"After positive interaction, temp should decrease from 30, got {details.temperature}"
        )

    @pytest.mark.asyncio
    async def test_t3_passive_time_decay(self):
        """T3: Temperature should decay passively over time."""
        current_temp = 50.0
        hours_elapsed = 4.0

        new_temp = TemperatureEngine.apply_time_decay(
            current=current_temp,
            hours_elapsed=hours_elapsed,
        )

        # Default decay rate is 0.5/hr, so 4h = -2.0
        expected = current_temp - (hours_elapsed * TemperatureEngine.TIME_DECAY_RATE)
        assert abs(new_temp - expected) < 0.01, (
            f"Expected {expected}, got {new_temp}"
        )
        assert new_temp < current_temp

    @pytest.mark.asyncio
    async def test_t4_calm_stays_calm_with_neutral_message(self):
        """T4: Temperature at 0 should stay at 0 with zero-delta message."""
        details = ConflictDetails(temperature=0.0, zone="calm")

        # Zero score delta = no temperature change
        score_delta = 0.0
        temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
        assert temp_delta == 0.0

        details = TemperatureEngine.update_conflict_details(details, temp_delta)
        assert details.temperature == 0.0
        assert details.zone == "calm"


# ============================================================================
# Test Group 2: Gottman Ratio (T5-T7)
# ============================================================================


class TestGottmanRatio:
    """T5-T7: Verify Gottman positive/negative tracking and ratio calculation."""

    @pytest.mark.asyncio
    async def test_t5_five_positive_one_negative_ratio(self):
        """T5: 5 positive + 1 negative should yield ratio ~5:1."""
        counters = GottmanCounters()

        # Record 5 positive interactions
        for _ in range(5):
            counters = GottmanTracker.record_interaction(counters, is_positive=True)

        # Record 1 negative
        counters = GottmanTracker.record_interaction(counters, is_positive=False)

        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 5.0, f"Expected ratio 5.0, got {ratio}"
        assert counters.positive_count == 5
        assert counters.negative_count == 1

    @pytest.mark.asyncio
    async def test_t6_only_negatives_zero_ratio(self):
        """T6: Only negative interactions should yield ratio 0.0."""
        counters = GottmanCounters()

        for _ in range(5):
            counters = GottmanTracker.record_interaction(counters, is_positive=False)

        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 0.0, f"Expected ratio 0.0, got {ratio}"
        assert counters.positive_count == 0
        assert counters.negative_count == 5

        # Temperature should increase for below-target ratio
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta > 0, f"Below-target ratio should increase temp, got {delta}"

    @pytest.mark.asyncio
    async def test_t7_mixed_interactions_persist_counters(self):
        """T7: Mixed sequence should accumulate across ConflictDetails roundtrip."""
        details = ConflictDetails()

        # Sequence: +, +, -, +, -, +, +
        interactions = [True, True, False, True, False, True, True]
        for is_positive in interactions:
            is_in_conflict = details.zone in ("hot", "critical")
            details = GottmanTracker.update_conflict_details(
                details, is_positive=is_positive, is_in_conflict=is_in_conflict
            )

        assert details.positive_count == 5
        assert details.negative_count == 2
        assert abs(details.gottman_ratio - 2.5) < 0.01

        # Roundtrip through JSONB
        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert restored.positive_count == 5
        assert restored.negative_count == 2
        assert abs(restored.gottman_ratio - 2.5) < 0.01


# ============================================================================
# Test Group 3: Pipeline Integration (T8-T10)
# ============================================================================


class TestPipelineIntegration:
    """T8-T10: Verify ConflictStage reads temperature, handles flag toggle."""

    @pytest.mark.asyncio
    async def test_t8_conflict_stage_reads_persisted_temperature(self):
        """T8: ConflictStage in temperature mode reads ctx.conflict_details."""
        from nikita.pipeline.stages.conflict import ConflictStage

        stage = ConflictStage()
        # Simulate pipeline context with conflict_details already loaded
        ctx = MagicMock()
        ctx.user_id = uuid4()
        ctx.relationship_score = Decimal("50")
        ctx.chapter = 2
        # Pre-loaded conflict details with HOT temperature
        ctx.conflict_details = ConflictDetails(
            temperature=60.0,
            zone="hot",
            last_temp_update=datetime.now(UTC).isoformat(),
        ).to_jsonb()

        with patch.object(stage, "_session", None):  # No DB session in test
            result = await stage._run(ctx)

        assert result["active"] is True
        assert result["zone"] == "hot"
        assert result["temperature"] >= 58.0  # Slight decay possible

    @pytest.mark.asyncio
    async def test_t9_no_conflict_details_uses_default(self):
        """T9: No conflict_details → ConflictStage defaults to calm/zero temperature."""
        from nikita.pipeline.stages.conflict import ConflictStage

        stage = ConflictStage()
        ctx = MagicMock()
        ctx.user_id = uuid4()
        ctx.relationship_score = Decimal("50")
        ctx.chapter = 2
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5}
        ctx.conflict_details = None  # No details → defaults

        result = await stage._run(ctx)

        # Default temperature is 0 → CALM zone → no active conflict
        assert result.get("active") is False or result.get("temperature", 0) == 0

    @pytest.mark.asyncio
    async def test_t10_scoring_always_returns_conflict_details(self):
        """T10: Scoring service always returns conflict_details (temperature always processed)."""
        from nikita.conflicts.models import ConflictDetails
        from nikita.engine.scoring.service import ScoringService

        details = ConflictDetails(temperature=45.0, zone="warm")
        service = ScoringService()

        result = service._update_temperature_and_gottman(
            analysis=make_positive_analysis(),
            result=MagicMock(delta=Decimal("3")),
            conflict_details=details.to_jsonb(),
        )

        # Temperature always processed — result is never None
        assert result is not None
        assert "temperature" in result


# ============================================================================
# Test Group 4: Breakup Threshold (T11-T12)
# ============================================================================


class TestBreakupThreshold:
    """T11-T12: Verify breakup triggers at CRITICAL zone boundary."""

    @pytest.mark.asyncio
    async def test_t11_critical_zone_triggers_breakup_check(self):
        """T11: Temperature >90 for extended period should trigger breakup consideration."""
        from nikita.conflicts.breakup import BreakupManager

        manager = BreakupManager()
        details = ConflictDetails(
            temperature=92.0,
            zone="critical",
            negative_count=25,
            positive_count=1,
            gottman_ratio=0.04,
        ).to_jsonb()

        # Breakup manager checks relationship_score + conflict_details
        result = manager.check_threshold(
            user_id=str(uuid4()),
            relationship_score=8,  # Very low score
            conflict_details=details,
        )

        # With score=8 (<10 breakup threshold) and CRITICAL temperature,
        # breakup should trigger
        assert result.should_breakup is True

    @pytest.mark.asyncio
    async def test_t12_below_critical_no_breakup(self):
        """T12: Temperature at 89.9 with moderate score should NOT trigger breakup."""
        from nikita.conflicts.breakup import BreakupManager

        manager = BreakupManager()
        details = ConflictDetails(
            temperature=89.9,
            zone="critical",  # Still in CRITICAL zone but score is ok
            negative_count=10,
            positive_count=5,
        ).to_jsonb()

        # Score is above breakup threshold
        result = manager.check_threshold(
            user_id=str(uuid4()),
            relationship_score=35,  # Above breakup threshold (10)
            conflict_details=details,
        )

        assert result.should_breakup is False


# ============================================================================
# Test Group 5: Scoring Service Integration (end-to-end wiring)
# ============================================================================


class TestScoringServiceIntegration:
    """Verify ScoringService correctly updates conflict_details through full flow."""

    @pytest.mark.asyncio
    async def test_scoring_service_updates_temperature_on_negative(self):
        """Negative interaction through ScoringService should increase temperature."""
        from nikita.config.enums import EngagementState
        from nikita.engine.scoring.models import ConversationContext
        from nikita.engine.scoring.service import ScoringService

        service = ScoringService()

        # Mock the analyzer to return negative analysis
        service.analyzer.analyze = AsyncMock(return_value=make_negative_analysis())

        context = ConversationContext(
            chapter=2,
            relationship_score=Decimal("45"),
            recent_messages=[("user", "whatever"), ("nikita", "fine.")],
            engagement_state="in_zone",
        )

        initial_details = ConflictDetails().to_jsonb()

        result = await service.score_interaction(
            user_id=uuid4(),
            user_message="I don't care about you",
            nikita_response="Fine.",
            context=context,
            current_metrics={
                "intimacy": Decimal("50"),
                "passion": Decimal("50"),
                "trust": Decimal("50"),
                "secureness": Decimal("50"),
            },
            engagement_state=EngagementState.IN_ZONE,
            conflict_details=initial_details,
        )

        # Result should have updated conflict_details
        assert result.conflict_details is not None
        assert result.conflict_details["temperature"] > 0.0
        assert result.conflict_details["negative_count"] > 0

    @pytest.mark.asyncio
    async def test_scoring_service_preserves_details_across_calls(self):
        """Conflict details should accumulate across multiple scoring calls."""
        from nikita.config.enums import EngagementState
        from nikita.engine.scoring.models import ConversationContext
        from nikita.engine.scoring.service import ScoringService

        service = ScoringService()
        service.analyzer.analyze = AsyncMock(return_value=make_negative_analysis())

        context = ConversationContext(
            chapter=2,
            relationship_score=Decimal("45"),
            recent_messages=[("user", "msg"), ("nikita", "resp")],
            engagement_state="in_zone",
        )

        current_details = ConflictDetails().to_jsonb()
        user_id = uuid4()

        # Run 5 negative interactions, passing conflict_details each time
        for i in range(5):
            result = await service.score_interaction(
                user_id=user_id,
                user_message=f"Negative message {i}",
                nikita_response="...",
                context=context,
                current_metrics={
                    "intimacy": Decimal("50"),
                    "passion": Decimal("50"),
                    "trust": Decimal("50"),
                    "secureness": Decimal("50"),
                },
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=current_details,
            )
            # Pass the updated details to the next call (simulating DB round-trip)
            current_details = result.conflict_details

        # After 5 negative interactions, temperature should be significantly elevated
        assert current_details["temperature"] > 30.0, (
            f"After 5 negatives, temp should be >30, got {current_details['temperature']}"
        )
        assert current_details["negative_count"] == 5
        # Zone should have escalated from calm
        assert current_details["zone"] != "calm"


# ============================================================================
# Test Group 6: Persistence Round-Trip (mock DB)
# ============================================================================


class TestPersistenceRoundTrip:
    """Verify conflict_details JSONB serialization/deserialization fidelity."""

    def test_conflict_details_roundtrip_fidelity(self):
        """ConflictDetails survives to_jsonb() → from_jsonb() cycle."""
        original = ConflictDetails(
            temperature=42.7,
            zone="warm",
            positive_count=10,
            negative_count=3,
            gottman_ratio=3.33,
            gottman_target=5.0,
            horsemen_detected=["criticism", "contempt"],
            repair_attempts=[{"at": "2026-02-18T10:00:00Z", "quality": "good", "temp_delta": -5.0}],
            last_temp_update="2026-02-18T10:00:00Z",
            session_positive=2,
            session_negative=1,
        )

        jsonb = original.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)

        assert abs(restored.temperature - original.temperature) < 0.01
        assert restored.zone == original.zone
        assert restored.positive_count == original.positive_count
        assert restored.negative_count == original.negative_count
        assert abs(restored.gottman_ratio - original.gottman_ratio) < 0.01
        assert restored.horsemen_detected == original.horsemen_detected
        assert len(restored.repair_attempts) == 1
        assert restored.session_positive == original.session_positive

    def test_from_jsonb_handles_none(self):
        """from_jsonb(None) should return empty defaults."""
        details = ConflictDetails.from_jsonb(None)
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0

    def test_from_jsonb_handles_empty_dict(self):
        """from_jsonb({}) should return empty defaults."""
        details = ConflictDetails.from_jsonb({})
        assert details.temperature == 0.0

    def test_from_jsonb_ignores_unknown_keys(self):
        """from_jsonb with extra keys should not crash."""
        data = {"temperature": 50.0, "zone": "hot", "unknown_field": "ignore_me"}
        details = ConflictDetails.from_jsonb(data)
        assert details.temperature == 50.0
        assert details.zone == "hot"
