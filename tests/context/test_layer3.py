"""Tests for Layer3Composer (Spec 021, T008).

AC-T008.1: Layer3Composer class generates emotional state prompt
AC-T008.2: Accepts EmotionalState as input
AC-T008.3: STUB implementation returns neutral state (0.5 all dimensions)
AC-T008.4: Interface ready for Spec 023 integration
AC-T008.5: Token count within budget (~150)
AC-T008.6: Unit tests for composer
"""

import pytest

from nikita.context.layers.emotional_state import (
    Layer3Composer,
    get_layer3_composer,
)
from nikita.context.package import EmotionalState


class TestLayer3Composer:
    """Tests for Layer3Composer class."""

    def test_init_default(self):
        """AC-T008.1: Composer initializes properly."""
        composer = Layer3Composer()
        assert composer is not None

    def test_compose_neutral_state(self):
        """AC-T008.2, AC-T008.3: Compose with neutral emotional state."""
        composer = Layer3Composer()
        state = EmotionalState()  # Default is 0.5 all dimensions

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
        # Should indicate neutral/balanced state
        assert any(
            word in prompt.lower()
            for word in ["neutral", "balanced", "calm", "stable", "moderate"]
        )

    def test_compose_high_arousal(self):
        """AC-T008.2: Compose with high arousal state."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.9, valence=0.5, dominance=0.5, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["energy", "excited", "animated", "high"]
        )

    def test_compose_low_arousal(self):
        """AC-T008.2: Compose with low arousal state."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.1, valence=0.5, dominance=0.5, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["low", "quiet", "subdued", "calm", "relaxed"]
        )

    def test_compose_positive_valence(self):
        """AC-T008.2: Compose with positive valence."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.9, dominance=0.5, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["positive", "happy", "good", "warm", "pleasant"]
        )

    def test_compose_negative_valence(self):
        """AC-T008.2: Compose with negative valence."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.1, dominance=0.5, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["negative", "down", "low", "off", "upset"]
        )

    def test_compose_high_dominance(self):
        """AC-T008.2: Compose with high dominance."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.5, dominance=0.9, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["confident", "control", "assert", "strong"]
        )

    def test_compose_low_dominance(self):
        """AC-T008.2: Compose with low dominance."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.5, dominance=0.1, intimacy=0.5)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["uncertain", "receptive", "open", "vulner"]
        )

    def test_compose_high_intimacy(self):
        """AC-T008.2: Compose with high intimacy."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.9)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["connect", "close", "intimate", "warm", "open"]
        )

    def test_compose_low_intimacy(self):
        """AC-T008.2: Compose with low intimacy."""
        composer = Layer3Composer()
        state = EmotionalState(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.1)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["distant", "guard", "reserved", "boundar"]
        )

    def test_token_estimate_within_budget(self):
        """AC-T008.5: Token estimate is within budget (~150)."""
        composer = Layer3Composer()
        state = EmotionalState()

        prompt = composer.compose(state)
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = len(prompt) // 4

        assert estimated_tokens <= 200, f"Exceeds budget: {estimated_tokens}"
        assert estimated_tokens >= 30, f"Too short: {estimated_tokens}"

    def test_default_neutral_state(self):
        """AC-T008.3: Default state is neutral (0.5 all dimensions)."""
        composer = Layer3Composer()
        default_state = composer.get_default_state()

        assert default_state.arousal == 0.5
        assert default_state.valence == 0.5
        assert default_state.dominance == 0.5
        assert default_state.intimacy == 0.5

    def test_compose_with_none_returns_neutral(self):
        """AC-T008.3: Composing with None returns neutral state prompt."""
        composer = Layer3Composer()

        prompt = composer.compose(None)

        assert isinstance(prompt, str)
        assert any(
            word in prompt.lower()
            for word in ["neutral", "balanced", "calm", "stable", "moderate"]
        )

    def test_interface_for_spec023(self):
        """AC-T008.4: Interface ready for Spec 023 integration."""
        composer = Layer3Composer()

        # Should have methods for external integration
        assert hasattr(composer, "compose")
        assert hasattr(composer, "get_default_state")
        assert hasattr(composer, "describe_state")

        # describe_state should return a dict with dimension descriptions
        state = EmotionalState(arousal=0.8, valence=0.7, dominance=0.6, intimacy=0.5)
        description = composer.describe_state(state)

        assert "arousal" in description
        assert "valence" in description
        assert "dominance" in description
        assert "intimacy" in description


class TestLayer3ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer3_composer_singleton(self):
        """AC-T008.1: get_layer3_composer returns singleton."""
        composer1 = get_layer3_composer()
        composer2 = get_layer3_composer()

        assert composer1 is composer2

    def test_compose_convenience(self):
        """AC-T008.1: Convenience function works."""
        composer = get_layer3_composer()
        state = EmotionalState(arousal=0.7, valence=0.6)

        prompt = composer.compose(state)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
