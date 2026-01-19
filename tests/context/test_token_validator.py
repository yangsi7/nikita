"""Tests for TokenValidator (Spec 021, T016).

AC-T016.1: TokenValidator class counts tokens via tiktoken
AC-T016.2: Validates total prompt < 4000 tokens
AC-T016.3: Truncates layers that exceed budget with warning
AC-T016.4: Unit tests for validator
"""

import pytest

from nikita.context.validation import (
    TokenValidator,
    ValidationResult,
    get_token_validator,
)


class TestTokenValidator:
    """Tests for TokenValidator class."""

    def test_init_default(self):
        """AC-T016.1: Validator initializes properly."""
        validator = TokenValidator()
        assert validator is not None

    def test_init_with_custom_budget(self):
        """AC-T016.2: Validator accepts custom token budget."""
        validator = TokenValidator(max_tokens=3000)
        assert validator.max_tokens == 3000

    def test_count_tokens_simple(self):
        """AC-T016.1: Counts tokens for simple text."""
        validator = TokenValidator()

        # Simple sentence should be ~5-10 tokens
        count = validator.count_tokens("Hello, how are you today?")

        assert isinstance(count, int)
        assert count > 0
        assert count < 20  # Should be reasonable for a short sentence

    def test_count_tokens_empty(self):
        """AC-T016.1: Handles empty string."""
        validator = TokenValidator()

        count = validator.count_tokens("")

        assert count == 0

    def test_count_tokens_long_text(self):
        """AC-T016.1: Counts tokens for longer text."""
        validator = TokenValidator()

        # Generate ~1000 characters of text
        long_text = "This is a test sentence. " * 50

        count = validator.count_tokens(long_text)

        # Rough estimate: 1 token ≈ 4 characters
        assert count > 200
        assert count < 400

    def test_validate_within_budget(self):
        """AC-T016.2: Validates prompt within budget."""
        validator = TokenValidator(max_tokens=4000)

        # Short prompt well under budget
        result = validator.validate("This is a short prompt.")

        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert result.token_count < 4000
        assert not result.truncated

    def test_validate_exceeds_budget(self):
        """AC-T016.2: Detects when prompt exceeds budget."""
        validator = TokenValidator(max_tokens=50)

        # Long prompt that exceeds small budget
        long_prompt = "This is a test sentence that will exceed the small token budget. " * 20

        result = validator.validate(long_prompt)

        assert isinstance(result, ValidationResult)
        assert not result.is_valid
        assert result.token_count > 50

    def test_validate_exactly_at_budget(self):
        """AC-T016.2: Handles prompt at exactly the budget."""
        validator = TokenValidator(max_tokens=4000)

        # Create a prompt that's close to 4000 tokens
        # Average word is ~1.3 tokens, so ~3000 words = ~4000 tokens
        prompt = "word " * 3000

        result = validator.validate(prompt)

        # Should be valid if at or slightly under
        assert isinstance(result, ValidationResult)

    def test_truncate_text(self):
        """AC-T016.3: Truncates text to fit budget."""
        validator = TokenValidator(max_tokens=4000)

        # Very long text
        long_text = "This is a word. " * 5000  # Way over budget

        truncated = validator.truncate(long_text, max_tokens=100)

        # Truncated text should fit in budget
        assert validator.count_tokens(truncated) <= 100

    def test_truncate_preserves_short_text(self):
        """AC-T016.3: Short text is not truncated."""
        validator = TokenValidator()

        short_text = "This is short."

        truncated = validator.truncate(short_text, max_tokens=1000)

        assert truncated == short_text

    def test_truncate_adds_marker(self):
        """AC-T016.3: Truncated text gets marker."""
        validator = TokenValidator()

        long_text = "Word " * 1000

        truncated = validator.truncate(long_text, max_tokens=50, add_marker=True)

        # Should have truncation marker
        assert "..." in truncated or "[truncated]" in truncated

    def test_validate_layer_breakdown(self):
        """AC-T016.2: Validates individual layer token counts."""
        validator = TokenValidator(max_tokens=4000)

        layer_breakdown = {
            "layer1_base_personality": 2000,
            "layer2_chapter": 300,
            "layer3_emotional_state": 150,
            "layer4_situation": 150,
            "layer5_context": 500,
            "layer6_modifications": 200,
        }

        result = validator.validate_breakdown(layer_breakdown)

        assert result.is_valid
        assert result.token_count == 3300

    def test_validate_breakdown_exceeds_budget(self):
        """AC-T016.2: Detects breakdown exceeding budget."""
        validator = TokenValidator(max_tokens=3000)

        layer_breakdown = {
            "layer1_base_personality": 2000,
            "layer2_chapter": 500,
            "layer3_emotional_state": 300,
            "layer4_situation": 200,
            "layer5_context": 500,
            "layer6_modifications": 200,
        }

        result = validator.validate_breakdown(layer_breakdown)

        assert not result.is_valid
        assert result.token_count == 3700  # Over 3000 budget

    def test_truncate_layers_to_fit(self):
        """AC-T016.3: Truncates layers proportionally to fit budget."""
        validator = TokenValidator(max_tokens=3000)

        layers = {
            "layer1_base_personality": "Base " * 600,  # ~600 tokens
            "layer2_chapter": "Chapter " * 300,
            "layer3_emotional_state": "Emotional " * 150,
            "layer4_situation": "Situation " * 150,
            "layer5_context": "Context " * 500,
            "layer6_modifications": "Modify " * 200,
        }

        truncated = validator.truncate_layers(layers, max_total=3000)

        # Verify total is now within budget
        total = sum(validator.count_tokens(text) for text in truncated.values())
        assert total <= 3000

    def test_layer_budgets(self):
        """AC-T016.2: Provides layer-specific budgets."""
        validator = TokenValidator(max_tokens=4000)

        budgets = validator.get_layer_budgets()

        assert "layer1_base_personality" in budgets
        assert budgets["layer1_base_personality"] == 2000
        assert budgets["layer2_chapter"] == 300
        assert budgets["layer5_context"] == 500


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_validation_result_valid(self):
        """ValidationResult for valid prompt."""
        result = ValidationResult(
            is_valid=True,
            token_count=2500,
            max_tokens=4000,
        )

        assert result.is_valid
        assert result.token_count == 2500
        assert not result.truncated

    def test_validation_result_invalid(self):
        """ValidationResult for invalid prompt."""
        result = ValidationResult(
            is_valid=False,
            token_count=5000,
            max_tokens=4000,
            error_message="Prompt exceeds token budget",
        )

        assert not result.is_valid
        assert result.error_message is not None

    def test_validation_result_truncated(self):
        """ValidationResult after truncation."""
        result = ValidationResult(
            is_valid=True,
            token_count=3900,
            max_tokens=4000,
            truncated=True,
            truncated_layers=["layer5_context"],
        )

        assert result.is_valid
        assert result.truncated
        assert "layer5_context" in result.truncated_layers


class TestTokenValidatorModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_token_validator_singleton(self):
        """AC-T016.1: get_token_validator returns singleton."""
        validator1 = get_token_validator()
        validator2 = get_token_validator()

        assert validator1 is validator2

    def test_default_budget(self):
        """AC-T016.2: Default budget is 4000."""
        validator = get_token_validator()

        assert validator.max_tokens == 4000
