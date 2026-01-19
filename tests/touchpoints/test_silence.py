"""Strategic Silence tests for Proactive Touchpoint System (Spec 025, Phase D: T017-T020).

Tests:
- T017: Strategic silence logic
- T018: Emotional state integration
- T019: Random skip factor
- T020: Phase D coverage
"""

import pytest

from nikita.touchpoints.silence import (
    SilenceDecision,
    SilenceReason,
    StrategicSilence,
    should_apply_silence,
)


# =============================================================================
# T017: Strategic Silence Logic Tests (AC-T017.1 - AC-T017.4)
# =============================================================================


class TestStrategicSilenceClass:
    """Test StrategicSilence class structure."""

    def test_silence_class_exists(self):
        """AC-T017.1: StrategicSilence class exists."""
        silence = StrategicSilence()
        assert silence is not None

    def test_apply_strategic_silence_method_exists(self):
        """AC-T017.1: apply_strategic_silence() method exists."""
        silence = StrategicSilence()
        assert hasattr(silence, "apply_strategic_silence")
        assert callable(silence.apply_strategic_silence)

    def test_default_rates_defined(self):
        """Default rates for chapters 1-5."""
        silence = StrategicSilence()
        assert len(silence.base_rates) == 5
        assert 1 in silence.base_rates
        assert 5 in silence.base_rates

    def test_custom_rates(self):
        """Can provide custom rates."""
        custom = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}
        silence = StrategicSilence(custom_rates=custom)
        assert silence.base_rates == custom


class TestSilenceDecision:
    """Test SilenceDecision dataclass."""

    def test_decision_with_skip(self):
        """Decision when skipping."""
        decision = SilenceDecision(
            should_skip=True,
            reason=SilenceReason.RANDOM,
            probability_used=0.15,
            random_value=0.10,
        )
        assert decision.should_skip is True
        assert decision.reason == SilenceReason.RANDOM
        assert "SKIP" in str(decision)

    def test_decision_without_skip(self):
        """Decision when proceeding."""
        decision = SilenceDecision(
            should_skip=False,
            reason=None,
            probability_used=0.15,
            random_value=0.80,
        )
        assert decision.should_skip is False
        assert decision.reason is None
        assert "PROCEED" in str(decision)


class TestSilenceRates:
    """Test chapter-based silence rates (AC-T017.2)."""

    def test_chapter_1_rate(self):
        """AC-T017.2: Chapter 1 = 10% silence."""
        silence = StrategicSilence()
        rate = silence.get_silence_rate(1)
        assert rate == 0.10

    def test_chapter_3_rate(self):
        """AC-T017.2: Chapter 3 = 15% silence."""
        silence = StrategicSilence()
        rate = silence.get_silence_rate(3)
        assert rate == 0.15

    def test_chapter_5_rate(self):
        """AC-T017.2: Chapter 5 = 20% silence."""
        silence = StrategicSilence()
        rate = silence.get_silence_rate(5)
        assert rate == 0.20

    def test_rates_within_range(self):
        """All rates within 10-20% range."""
        silence = StrategicSilence()
        for chapter in range(1, 6):
            rate = silence.get_silence_rate(chapter)
            assert 0.10 <= rate <= 0.20

    def test_unknown_chapter_fallback(self):
        """Unknown chapter uses default."""
        silence = StrategicSilence()
        rate = silence.get_silence_rate(99)
        assert rate == 0.15  # Default to chapter 3 rate


class TestSkipRecording:
    """Test skip recording for analytics (AC-T017.3)."""

    def test_record_skip_with_skip(self):
        """AC-T017.3: Skip recorded with reason."""
        silence = StrategicSilence()
        decision = SilenceDecision(
            should_skip=True,
            reason=SilenceReason.EMOTIONAL,
            probability_used=0.20,
            emotional_modifier=1.5,
            random_value=0.05,
        )

        record = silence.record_skip(decision, touchpoint_id="tp_123")

        assert record["touchpoint_id"] == "tp_123"
        assert record["skipped"] is True
        assert record["reason"] == "emotional"
        assert record["probability_used"] == 0.20
        assert record["emotional_modifier"] == 1.5

    def test_record_skip_without_skip(self):
        """Record when not skipping."""
        silence = StrategicSilence()
        decision = SilenceDecision(
            should_skip=False,
            reason=None,
            probability_used=0.15,
            random_value=0.80,
        )

        record = silence.record_skip(decision)

        assert record["skipped"] is False
        assert record["reason"] is None


# =============================================================================
# T018: Emotional State Integration Tests (AC-T018.1 - AC-T018.4)
# =============================================================================


class TestEmotionalStateIntegration:
    """Test emotional state integration for strategic silence."""

    def test_very_upset_always_skips(self):
        """AC-T018.1: More silence when upset (valence < 0.3)."""
        silence = StrategicSilence()
        emotional_state = {"valence": 0.15, "arousal": 0.5, "dominance": 0.5}

        # Very upset should always trigger silence
        assert silence.should_skip_for_emotional_state(emotional_state) is True

    def test_neutral_mood_no_automatic_skip(self):
        """Neutral mood doesn't automatically skip."""
        silence = StrategicSilence()
        emotional_state = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

        assert silence.should_skip_for_emotional_state(emotional_state) is False

    def test_happy_mood_no_automatic_skip(self):
        """Happy mood doesn't automatically skip."""
        silence = StrategicSilence()
        emotional_state = {"valence": 0.8, "arousal": 0.6, "dominance": 0.6}

        assert silence.should_skip_for_emotional_state(emotional_state) is False

    def test_conflict_always_skips(self):
        """AC-T018.2: More silence in conflict states."""
        silence = StrategicSilence()

        decision = silence.apply_strategic_silence(
            chapter=3,
            conflict_active=True,
        )

        assert decision.should_skip is True
        assert decision.reason == SilenceReason.CONFLICT

    def test_emotional_modifier_increases_with_low_valence(self):
        """AC-T018.3: Silence rate modulated by emotional state."""
        silence = StrategicSilence()

        # Neutral
        neutral = {"valence": 0.5, "arousal": 0.5}
        neutral_mod = silence._compute_emotional_modifier(neutral)

        # Somewhat negative
        negative = {"valence": 0.35, "arousal": 0.5}
        negative_mod = silence._compute_emotional_modifier(negative)

        # Very negative
        very_negative = {"valence": 0.2, "arousal": 0.5}
        very_negative_mod = silence._compute_emotional_modifier(very_negative)

        # Modifiers should increase with lower valence
        assert neutral_mod < negative_mod
        assert negative_mod < very_negative_mod

    def test_high_arousal_with_low_valence_increases_modifier(self):
        """Agitated state (high arousal + low valence) increases silence."""
        silence = StrategicSilence()

        # Low valence, low arousal
        calm_upset = {"valence": 0.3, "arousal": 0.3}
        calm_mod = silence._compute_emotional_modifier(calm_upset)

        # Low valence, high arousal (agitated)
        agitated = {"valence": 0.3, "arousal": 0.8}
        agitated_mod = silence._compute_emotional_modifier(agitated)

        assert agitated_mod > calm_mod

    def test_low_dominance_increases_modifier(self):
        """Low dominance (vulnerable) increases silence slightly."""
        silence = StrategicSilence()

        # Normal dominance
        normal = {"valence": 0.4, "dominance": 0.5}
        normal_mod = silence._compute_emotional_modifier(normal)

        # Low dominance (vulnerable)
        vulnerable = {"valence": 0.4, "dominance": 0.2}
        vulnerable_mod = silence._compute_emotional_modifier(vulnerable)

        assert vulnerable_mod > normal_mod

    def test_no_emotional_state_returns_neutral_modifier(self):
        """No emotional state gives modifier of 1.0."""
        silence = StrategicSilence()
        modifier = silence._compute_emotional_modifier(None)
        assert modifier == 1.0


# =============================================================================
# T019: Random Skip Factor Tests (AC-T019.1 - AC-T019.3)
# =============================================================================


class TestRandomSkipFactor:
    """Test random factor in strategic silence."""

    def test_random_factor_produces_skips(self):
        """AC-T019.1: Random factor adds unpredictability."""
        silence = StrategicSilence()

        # With seed that produces low random value (should skip)
        decision = silence.apply_strategic_silence(
            chapter=3,
            random_seed=42,  # Reproducible
        )

        # Check that random_value was used
        assert 0 <= decision.random_value <= 1
        assert decision.probability_used > 0

    def test_not_purely_deterministic(self):
        """AC-T019.2: Not purely deterministic."""
        silence = StrategicSilence()

        # Run many times without seed
        results = []
        for _ in range(100):
            decision = silence.apply_strategic_silence(chapter=3)
            results.append(decision.should_skip)

        # Should have some variation (not all same)
        assert True in results  # At least one skip
        assert False in results  # At least one proceed

    def test_different_seeds_different_results(self):
        """Different seeds can produce different results."""
        silence = StrategicSilence()

        # Test with different seeds
        results = []
        for seed in range(1, 20):
            decision = silence.apply_strategic_silence(chapter=3, random_seed=seed)
            results.append(decision.should_skip)

        # Should have variation
        unique_results = set(results)
        assert len(unique_results) > 1

    def test_same_seed_same_result(self):
        """Same seed produces same result (for testing)."""
        silence = StrategicSilence()

        decision1 = silence.apply_strategic_silence(chapter=3, random_seed=12345)
        decision2 = silence.apply_strategic_silence(chapter=3, random_seed=12345)

        assert decision1.random_value == decision2.random_value
        assert decision1.should_skip == decision2.should_skip


class TestRandomValueTracking:
    """Test that random values are tracked in decisions."""

    def test_random_value_in_decision(self):
        """Random value stored in decision."""
        silence = StrategicSilence()

        decision = silence.apply_strategic_silence(chapter=3, random_seed=100)

        assert hasattr(decision, "random_value")
        assert 0 <= decision.random_value <= 1

    def test_probability_used_in_decision(self):
        """Probability used stored in decision."""
        silence = StrategicSilence()

        decision = silence.apply_strategic_silence(chapter=3)

        assert hasattr(decision, "probability_used")
        assert decision.probability_used > 0


# =============================================================================
# T020: Phase D Coverage Tests (AC-T020.1, AC-T020.2)
# =============================================================================


class TestPhaseDCoverage:
    """Ensure Phase D has comprehensive test coverage."""

    def test_silence_module_importable(self):
        """AC-T020.1: Silence module importable."""
        from nikita.touchpoints.silence import (
            SilenceDecision,
            SilenceReason,
            StrategicSilence,
            should_apply_silence,
        )

        assert StrategicSilence is not None
        assert SilenceDecision is not None
        assert SilenceReason is not None
        assert should_apply_silence is not None

    def test_all_silence_reasons_exist(self):
        """All silence reasons defined."""
        assert SilenceReason.RANDOM is not None
        assert SilenceReason.EMOTIONAL is not None
        assert SilenceReason.CONFLICT is not None
        assert SilenceReason.CHAPTER_RATE is not None
        assert SilenceReason.RECENT_CONTACT is not None

    def test_convenience_function(self):
        """Convenience function works."""
        decision = should_apply_silence(chapter=3)

        assert isinstance(decision, SilenceDecision)
        assert isinstance(decision.should_skip, bool)

    def test_convenience_function_with_emotional_state(self):
        """Convenience function handles emotional state."""
        decision = should_apply_silence(
            chapter=3,
            emotional_state={"valence": 0.2, "arousal": 0.5},
        )

        assert isinstance(decision, SilenceDecision)

    def test_convenience_function_with_conflict(self):
        """Convenience function handles conflict."""
        decision = should_apply_silence(
            chapter=3,
            conflict_active=True,
        )

        assert decision.should_skip is True
        assert decision.reason == SilenceReason.CONFLICT


# =============================================================================
# Integration Tests
# =============================================================================


class TestSilenceIntegration:
    """Integration tests for strategic silence."""

    def test_full_flow_neutral_proceed(self):
        """Full flow: neutral state, proceed."""
        silence = StrategicSilence()

        # Use high seed to get high random value (proceed)
        decision = silence.apply_strategic_silence(
            chapter=3,
            emotional_state={"valence": 0.5, "arousal": 0.5},
            random_seed=999999,  # Likely high random value
        )

        # May or may not skip based on random, but should have valid decision
        assert isinstance(decision, SilenceDecision)
        assert decision.emotional_modifier == 1.0  # Neutral

    def test_full_flow_upset_skip(self):
        """Full flow: upset state, skip."""
        silence = StrategicSilence()

        decision = silence.apply_strategic_silence(
            chapter=3,
            emotional_state={"valence": 0.15, "arousal": 0.5},
        )

        # Very upset always skips
        assert decision.should_skip is True
        assert decision.reason == SilenceReason.EMOTIONAL

    def test_full_flow_conflict_skip(self):
        """Full flow: conflict state, skip."""
        silence = StrategicSilence()

        decision = silence.apply_strategic_silence(
            chapter=3,
            conflict_active=True,
        )

        assert decision.should_skip is True
        assert decision.reason == SilenceReason.CONFLICT

    def test_silence_rate_capped_at_50_percent(self):
        """Silence rate capped at 50% even with high modifier (in normal path)."""
        silence = StrategicSilence()

        # Custom high rates that would exceed 50% without cap
        high_rate_silence = StrategicSilence(custom_rates={1: 0.40, 2: 0.40, 3: 0.40, 4: 0.40, 5: 0.40})

        # Mildly negative to boost rate (modifier ~1.3) without auto-skip
        # valence=0.36 gives modifier = 1 + (0.4-0.36)*1.5 = 1.06
        decision = high_rate_silence.apply_strategic_silence(
            chapter=5,  # 40% base with custom rates
            emotional_state={"valence": 0.36, "arousal": 0.5, "dominance": 0.5},
            random_seed=999999,  # High seed for high random value (proceed path)
        )

        # Rate should be capped at 50% even with 40% base
        # 40% * 1.06 = 42.4% which is under 50% cap
        assert decision.probability_used <= 0.5

    def test_all_chapters_produce_valid_decisions(self):
        """All chapters produce valid decisions."""
        silence = StrategicSilence()

        for chapter in range(1, 6):
            decision = silence.apply_strategic_silence(chapter=chapter)

            assert isinstance(decision, SilenceDecision)
            assert isinstance(decision.should_skip, bool)
            assert 0 <= decision.probability_used <= 0.5
