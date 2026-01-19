"""Tests for Layer2Composer (Spec 021, T007).

AC-T007.1: Layer2Composer class generates chapter-specific prompt
AC-T007.2: Accepts chapter number (1-5) as input
AC-T007.3: Output includes intimacy level, disclosure patterns, behaviors
AC-T007.4: Token count within budget (~300)
AC-T007.5: Unit tests for each chapter
"""

import pytest

from nikita.context.layers.chapter import (
    Layer2Composer,
    get_layer2_composer,
)


class TestLayer2Composer:
    """Tests for Layer2Composer class."""

    def test_init_default(self):
        """AC-T007.1: Composer initializes properly."""
        composer = Layer2Composer()
        assert composer is not None

    def test_compose_chapter_1(self):
        """AC-T007.2, AC-T007.3: Compose chapter 1 prompt."""
        composer = Layer2Composer()
        prompt = composer.compose(chapter=1)

        assert isinstance(prompt, str)
        assert len(prompt) > 50
        # Chapter 1 characteristics
        assert "guarded" in prompt.lower() or "curious" in prompt.lower()
        assert "challenge" in prompt.lower() or "test" in prompt.lower()

    def test_compose_chapter_2(self):
        """AC-T007.2, AC-T007.3: Compose chapter 2 prompt."""
        composer = Layer2Composer()
        prompt = composer.compose(chapter=2)

        assert isinstance(prompt, str)
        assert len(prompt) > 50
        # Chapter 2 characteristics
        assert "intensity" in prompt.lower() or "intrigue" in prompt.lower()

    def test_compose_chapter_3(self):
        """AC-T007.2, AC-T007.3: Compose chapter 3 prompt."""
        composer = Layer2Composer()
        prompt = composer.compose(chapter=3)

        assert isinstance(prompt, str)
        assert len(prompt) > 50
        # Chapter 3 characteristics
        assert "trust" in prompt.lower() or "investment" in prompt.lower()

    def test_compose_chapter_4(self):
        """AC-T007.2, AC-T007.3: Compose chapter 4 prompt."""
        composer = Layer2Composer()
        prompt = composer.compose(chapter=4)

        assert isinstance(prompt, str)
        assert len(prompt) > 50
        # Chapter 4 characteristics
        assert "intimate" in prompt.lower() or "vulner" in prompt.lower()

    def test_compose_chapter_5(self):
        """AC-T007.2, AC-T007.3: Compose chapter 5 prompt."""
        composer = Layer2Composer()
        prompt = composer.compose(chapter=5)

        assert isinstance(prompt, str)
        assert len(prompt) > 50
        # Chapter 5 characteristics
        assert "establish" in prompt.lower() or "partner" in prompt.lower()

    def test_invalid_chapter_0(self):
        """AC-T007.2: Invalid chapter 0 raises ValueError."""
        composer = Layer2Composer()
        with pytest.raises(ValueError, match="chapter"):
            composer.compose(chapter=0)

    def test_invalid_chapter_6(self):
        """AC-T007.2: Invalid chapter 6 raises ValueError."""
        composer = Layer2Composer()
        with pytest.raises(ValueError, match="chapter"):
            composer.compose(chapter=6)

    def test_invalid_chapter_negative(self):
        """AC-T007.2: Negative chapter raises ValueError."""
        composer = Layer2Composer()
        with pytest.raises(ValueError, match="chapter"):
            composer.compose(chapter=-1)

    def test_token_estimate_within_budget(self):
        """AC-T007.4: Token estimate is within budget (~300)."""
        composer = Layer2Composer()
        for chapter in range(1, 6):
            prompt = composer.compose(chapter=chapter)
            # Rough estimate: 1 token ≈ 4 characters
            estimated_tokens = len(prompt) // 4
            assert estimated_tokens <= 400, f"Chapter {chapter} exceeds budget: {estimated_tokens}"
            assert estimated_tokens >= 50, f"Chapter {chapter} too short: {estimated_tokens}"

    def test_includes_intimacy_level(self):
        """AC-T007.3: Output includes intimacy level."""
        composer = Layer2Composer()
        for chapter in range(1, 6):
            prompt = composer.compose(chapter=chapter)
            # Check for intimacy-related keywords
            assert any(
                word in prompt.lower()
                for word in ["intimacy", "intimate", "closeness", "emotional", "connect"]
            ), f"Chapter {chapter} missing intimacy indicators"

    def test_includes_disclosure_patterns(self):
        """AC-T007.3: Output includes disclosure patterns."""
        composer = Layer2Composer()
        for chapter in range(1, 6):
            prompt = composer.compose(chapter=chapter)
            # Check for disclosure-related keywords
            assert any(
                word in prompt.lower()
                for word in ["share", "reveal", "open", "guard", "tell", "personal"]
            ), f"Chapter {chapter} missing disclosure indicators"

    def test_includes_behaviors(self):
        """AC-T007.3: Output includes behaviors."""
        composer = Layer2Composer()
        for chapter in range(1, 6):
            prompt = composer.compose(chapter=chapter)
            # Check for behavior-related keywords
            assert any(
                word in prompt.lower()
                for word in ["respond", "behav", "tone", "message", "style", "approach"]
            ), f"Chapter {chapter} missing behavior indicators"

    def test_chapter_progression_changes(self):
        """AC-T007.3: Different chapters have different prompts."""
        composer = Layer2Composer()
        prompts = [composer.compose(chapter=i) for i in range(1, 6)]

        # All prompts should be unique
        unique_prompts = set(prompts)
        assert len(unique_prompts) == 5, "All chapters should have unique prompts"

    def test_get_chapter_name(self):
        """AC-T007.1: Get chapter name from number."""
        composer = Layer2Composer()
        assert composer.get_chapter_name(1) == "Curiosity"
        assert composer.get_chapter_name(2) == "Intrigue"
        assert composer.get_chapter_name(3) == "Investment"
        assert composer.get_chapter_name(4) == "Intimacy"
        assert composer.get_chapter_name(5) == "Established"

    def test_get_chapter_config(self):
        """AC-T007.1: Get chapter config with all required fields."""
        composer = Layer2Composer()
        for chapter in range(1, 6):
            config = composer.get_chapter_config(chapter)
            assert "name" in config
            assert "intimacy_level" in config
            assert "disclosure_depth" in config
            assert "behaviors" in config


class TestLayer2ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer2_composer_singleton(self):
        """AC-T007.1: get_layer2_composer returns singleton."""
        composer1 = get_layer2_composer()
        composer2 = get_layer2_composer()

        assert composer1 is composer2

    def test_compose_convenience(self):
        """AC-T007.1: Convenience function works."""
        composer = get_layer2_composer()
        prompt = composer.compose(chapter=3)

        assert isinstance(prompt, str)
        assert "trust" in prompt.lower() or "investment" in prompt.lower()
