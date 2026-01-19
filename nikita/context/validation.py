"""Token Validation for Hierarchical Prompt Composition (Spec 021, T016).

Validates and manages token budgets for the 6-layer prompt system.
Uses tiktoken for accurate token counting with Claude-compatible tokenizer.

Layer budgets:
- Layer 1: Base Personality (~2000 tokens)
- Layer 2: Chapter Layer (~300 tokens)
- Layer 3: Emotional State (~150 tokens)
- Layer 4: Situation (~150 tokens)
- Layer 5: Context Injection (~500 tokens)
- Layer 6: On-the-Fly Modifications (~200 tokens)
Total target: ~3300 tokens, max: 4000 tokens
"""

import logging
from dataclasses import dataclass, field

import tiktoken

logger = logging.getLogger(__name__)


# Default layer budgets (tokens)
LAYER_BUDGETS = {
    "layer1_base_personality": 2000,
    "layer2_chapter": 300,
    "layer3_emotional_state": 150,
    "layer4_situation": 150,
    "layer5_context": 500,
    "layer6_modifications": 200,
}

# Total budget
DEFAULT_MAX_TOKENS = 4000

# Encoding for Claude-compatible tokenization
# Using cl100k_base (GPT-4/Claude-compatible)
ENCODING_NAME = "cl100k_base"


@dataclass
class ValidationResult:
    """Result of token validation.

    Attributes:
        is_valid: Whether the prompt is within budget.
        token_count: Total token count.
        max_tokens: Maximum allowed tokens.
        truncated: Whether any truncation was applied.
        truncated_layers: List of layers that were truncated.
        error_message: Error message if validation failed.
    """

    is_valid: bool
    token_count: int
    max_tokens: int
    truncated: bool = False
    truncated_layers: list[str] = field(default_factory=list)
    error_message: str | None = None


class TokenValidator:
    """Validator for prompt token counts.

    Uses tiktoken for accurate token counting compatible with Claude.
    Provides validation and truncation for the 6-layer prompt system.

    Attributes:
        max_tokens: Maximum total tokens allowed.
        _encoding: Tiktoken encoding instance.
        _layer_budgets: Budget per layer.
    """

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        layer_budgets: dict[str, int] | None = None,
    ) -> None:
        """Initialize TokenValidator.

        Args:
            max_tokens: Maximum total tokens allowed.
            layer_budgets: Optional custom budgets per layer.
        """
        self.max_tokens = max_tokens
        self._layer_budgets = layer_budgets or LAYER_BUDGETS.copy()

        # Initialize tiktoken encoding
        try:
            self._encoding = tiktoken.get_encoding(ENCODING_NAME)
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}. Using fallback.")
            self._encoding = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for.

        Returns:
            Token count.
        """
        if not text:
            return 0

        if self._encoding is not None:
            return len(self._encoding.encode(text))

        # Fallback: estimate ~4 characters per token
        return len(text) // 4

    def validate(self, prompt: str) -> ValidationResult:
        """Validate a prompt's token count.

        Args:
            prompt: Full prompt text.

        Returns:
            ValidationResult with validation status.
        """
        token_count = self.count_tokens(prompt)
        is_valid = token_count <= self.max_tokens

        return ValidationResult(
            is_valid=is_valid,
            token_count=token_count,
            max_tokens=self.max_tokens,
            error_message=None if is_valid else f"Prompt exceeds budget: {token_count} > {self.max_tokens}",
        )

    def validate_breakdown(self, layer_breakdown: dict[str, int]) -> ValidationResult:
        """Validate token breakdown by layer.

        Args:
            layer_breakdown: Dict mapping layer names to token counts.

        Returns:
            ValidationResult with validation status.
        """
        total_tokens = sum(layer_breakdown.values())
        is_valid = total_tokens <= self.max_tokens

        return ValidationResult(
            is_valid=is_valid,
            token_count=total_tokens,
            max_tokens=self.max_tokens,
            error_message=None if is_valid else f"Total tokens exceed budget: {total_tokens} > {self.max_tokens}",
        )

    def truncate(
        self,
        text: str,
        max_tokens: int,
        add_marker: bool = False,
    ) -> str:
        """Truncate text to fit within token budget.

        Args:
            text: Text to truncate.
            max_tokens: Maximum tokens allowed.
            add_marker: Whether to add truncation marker.

        Returns:
            Truncated text.
        """
        if not text:
            return text

        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        # Truncate by encoding and decoding
        if self._encoding is not None:
            tokens = self._encoding.encode(text)

            # Leave room for marker if needed
            target_tokens = max_tokens - (3 if add_marker else 0)
            truncated_tokens = tokens[:target_tokens]

            truncated = self._encoding.decode(truncated_tokens)
        else:
            # Fallback: truncate by characters
            target_chars = max_tokens * 4 - (10 if add_marker else 0)
            truncated = text[:target_chars]

        if add_marker:
            truncated = truncated.rstrip() + "..."

        logger.warning(f"Truncated text from {current_tokens} to {self.count_tokens(truncated)} tokens")
        return truncated

    def truncate_layers(
        self,
        layers: dict[str, str],
        max_total: int | None = None,
    ) -> dict[str, str]:
        """Truncate layers proportionally to fit total budget.

        Args:
            layers: Dict mapping layer names to text.
            max_total: Maximum total tokens (default: self.max_tokens).

        Returns:
            Dict with truncated layer texts.
        """
        max_total = max_total or self.max_tokens

        # Calculate current totals
        current_counts = {name: self.count_tokens(text) for name, text in layers.items()}
        total = sum(current_counts.values())

        if total <= max_total:
            return layers

        # Calculate reduction ratio
        ratio = max_total / total

        # Truncate each layer proportionally
        truncated_layers: dict[str, str] = {}
        for name, text in layers.items():
            target_tokens = int(current_counts[name] * ratio)
            truncated_layers[name] = self.truncate(text, target_tokens)

        return truncated_layers

    def get_layer_budgets(self) -> dict[str, int]:
        """Get the configured layer budgets.

        Returns:
            Dict mapping layer names to token budgets.
        """
        return self._layer_budgets.copy()


# Module-level singleton for efficiency
_default_validator: TokenValidator | None = None


def get_token_validator() -> TokenValidator:
    """Get the singleton TokenValidator instance.

    Returns:
        Cached TokenValidator instance.
    """
    global _default_validator
    if _default_validator is None:
        _default_validator = TokenValidator()
    return _default_validator


def count_tokens(text: str) -> int:
    """Convenience function to count tokens.

    Args:
        text: Text to count tokens for.

    Returns:
        Token count.
    """
    return get_token_validator().count_tokens(text)


def validate_prompt(prompt: str) -> ValidationResult:
    """Convenience function to validate a prompt.

    Args:
        prompt: Prompt text to validate.

    Returns:
        ValidationResult.
    """
    return get_token_validator().validate(prompt)
