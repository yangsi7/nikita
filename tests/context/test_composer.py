"""Tests for HierarchicalPromptComposer (Spec 021, T013).

AC-T013.1: HierarchicalPromptComposer class orchestrates all layers
AC-T013.2: compose() method returns ComposedPrompt
AC-T013.3: Loads context package and injects into prompt
AC-T013.4: Graceful degradation when package unavailable
AC-T013.5: Logs layer breakdown for debugging
AC-T013.6: Unit tests for composer
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.context.composer import (
    HierarchicalPromptComposer,
    get_prompt_composer,
)
from nikita.context.package import (
    ActiveThread,
    ComposedPrompt,
    ContextPackage,
    EmotionalState,
)


class TestHierarchicalPromptComposer:
    """Tests for HierarchicalPromptComposer class."""

    def test_init_default(self):
        """AC-T013.1: Composer initializes properly."""
        composer = HierarchicalPromptComposer()
        assert composer is not None

    def test_compose_returns_composed_prompt(self):
        """AC-T013.2: compose() returns ComposedPrompt."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(),
            package=None,  # Test without package
        )

        assert isinstance(result, ComposedPrompt)
        assert isinstance(result.full_text, str)
        assert result.total_tokens > 0

    def test_compose_with_package(self):
        """AC-T013.3: Loads context package and injects into prompt."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        # Create test package
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            chapter_layer="Chapter overlay content",
            emotional_state_layer="Emotional state content",
            situation_hints={"current": "morning"},
            user_facts=["User works in finance", "User likes coffee"],
            relationship_events=["First date last week"],
            active_threads=[
                ActiveThread(
                    topic="Career discussion",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                )
            ],
            today_summary="Had a great chat about movies",
            week_summaries=["Week started well with deep conversations"],
            nikita_mood=EmotionalState(valence=0.7),
            nikita_energy=0.6,
            life_events_today=["Finished a security audit"],
        )

        result = composer.compose(
            user_id=user_id,
            chapter=2,
            emotional_state=EmotionalState(valence=0.7),
            package=package,
        )

        assert isinstance(result, ComposedPrompt)
        # Verify package content is in the prompt
        assert "works in finance" in result.full_text.lower() or "user facts" in result.full_text.lower()
        assert result.total_tokens > 0

    def test_compose_without_package_graceful_degradation(self):
        """AC-T013.4: Graceful degradation when package unavailable."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        # Should not raise exception
        result = composer.compose(
            user_id=user_id,
            chapter=3,
            emotional_state=None,  # Also test with None emotional state
            package=None,
        )

        assert isinstance(result, ComposedPrompt)
        assert len(result.full_text) > 100
        # Should still have Layer 1 (base personality)
        assert "nikita" in result.full_text.lower()

    def test_compose_includes_all_layers(self):
        """AC-T013.1: Composer includes all 6 layers when available."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(arousal=0.8),
            package=None,
            current_time=datetime.now(timezone.utc).replace(hour=9),  # Morning
            last_interaction=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Check layer breakdown is populated
        assert len(result.layer_breakdown) >= 4  # At least Layers 1-4

    def test_layer_breakdown_has_names_and_tokens(self):
        """AC-T013.5: Logs layer breakdown for debugging."""
        composer = HierarchicalPromptComposer()

        result = composer.compose(
            user_id=uuid4(),
            chapter=2,
            emotional_state=EmotionalState(),
            package=None,
        )

        # Each layer should have name and token count (int)
        for layer_name, token_count in result.layer_breakdown.items():
            assert isinstance(layer_name, str)
            assert isinstance(token_count, int)
            assert token_count >= 0

    def test_token_count_is_sum_of_layers(self):
        """AC-T013.5: Token count is sum of layer token counts."""
        composer = HierarchicalPromptComposer()

        result = composer.compose(
            user_id=uuid4(),
            chapter=1,
            emotional_state=EmotionalState(),
            package=None,
        )

        # Total tokens should be at least the sum of layer tokens (may have overhead)
        layer_sum = sum(tokens for tokens in result.layer_breakdown.values())
        # Allow some margin for formatting/separators
        assert result.total_tokens >= layer_sum * 0.9

    def test_compose_different_chapters(self):
        """AC-T013.1: Different chapters produce different prompts."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        prompts = []
        for chapter in range(1, 6):
            result = composer.compose(
                user_id=user_id,
                chapter=chapter,
                emotional_state=EmotionalState(),
                package=None,
            )
            prompts.append(result.full_text)

        # All prompts should be unique
        unique_prompts = set(prompts)
        assert len(unique_prompts) == 5

    def test_compose_different_emotional_states(self):
        """AC-T013.1: Different emotional states affect prompt."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        # Compose with high arousal
        high_arousal = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(arousal=0.9),
            package=None,
        )

        # Compose with low arousal
        low_arousal = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(arousal=0.1),
            package=None,
        )

        # Prompts should be different
        assert high_arousal.full_text != low_arousal.full_text

    def test_compose_validates_chapter(self):
        """AC-T013.1: Validates chapter input."""
        composer = HierarchicalPromptComposer()

        with pytest.raises(ValueError, match="chapter"):
            composer.compose(
                user_id=uuid4(),
                chapter=0,  # Invalid
                emotional_state=EmotionalState(),
                package=None,
            )

        with pytest.raises(ValueError, match="chapter"):
            composer.compose(
                user_id=uuid4(),
                chapter=6,  # Invalid
                emotional_state=EmotionalState(),
                package=None,
            )


class TestComposerModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_prompt_composer_singleton(self):
        """AC-T013.1: get_prompt_composer returns singleton."""
        composer1 = get_prompt_composer()
        composer2 = get_prompt_composer()

        assert composer1 is composer2

    def test_compose_convenience(self):
        """AC-T013.1: Convenience function works."""
        composer = get_prompt_composer()

        result = composer.compose(
            user_id=uuid4(),
            chapter=3,
            emotional_state=EmotionalState(),
            package=None,
        )

        assert isinstance(result, ComposedPrompt)
        assert len(result.full_text) > 100
