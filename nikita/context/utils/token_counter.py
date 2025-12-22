"""Token counting utilities using tiktoken.

Provides accurate token counting for Claude-compatible models.
"""

import logging
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)

# Claude uses the same tokenizer as cl100k_base (GPT-4 compatible)
# This is the closest available encoding for Claude models
DEFAULT_ENCODING = "cl100k_base"


@lru_cache(maxsize=1)
def _get_encoder() -> tiktoken.Encoding:
    """Get the tiktoken encoder (cached singleton).

    Returns:
        tiktoken Encoding instance.
    """
    return tiktoken.get_encoding(DEFAULT_ENCODING)


def count_tokens(text: str) -> int:
    """Count tokens in a text string using tiktoken.

    Uses cl100k_base encoding which is compatible with Claude models.
    Falls back to character estimation if tiktoken fails.

    Args:
        text: The text to count tokens for.

    Returns:
        Number of tokens in the text.
    """
    if not text:
        return 0

    try:
        encoder = _get_encoder()
        return len(encoder.encode(text))
    except Exception as e:
        logger.warning(f"tiktoken failed, falling back to estimate: {e}")
        # Fallback: 1 token ≈ 4 characters
        return len(text) // 4


class TokenCounter:
    """Token counting utility with budget enforcement.

    Provides token counting and budget checking for context engineering.
    """

    def __init__(self, budget: int = 4000):
        """Initialize TokenCounter.

        Args:
            budget: Maximum token budget (default 4000).
        """
        self.budget = budget
        self._encoder = _get_encoder()

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count.

        Returns:
            Token count.
        """
        return count_tokens(text)

    def count_multiple(self, texts: list[str]) -> int:
        """Count total tokens across multiple texts.

        Args:
            texts: List of text strings.

        Returns:
            Total token count.
        """
        return sum(count_tokens(t) for t in texts)

    def fits_budget(self, text: str, margin: int = 0) -> bool:
        """Check if text fits within budget.

        Args:
            text: Text to check.
            margin: Extra margin to reserve (default 0).

        Returns:
            True if text fits within budget minus margin.
        """
        return count_tokens(text) <= (self.budget - margin)

    def remaining(self, used: int) -> int:
        """Calculate remaining tokens.

        Args:
            used: Tokens already used.

        Returns:
            Remaining tokens in budget.
        """
        return max(0, self.budget - used)

    def truncate_to_budget(self, text: str, margin: int = 100) -> str:
        """Truncate text to fit within budget.

        Truncates from the end, trying to break at sentence boundaries.

        Args:
            text: Text to truncate.
            margin: Buffer to leave (default 100).

        Returns:
            Truncated text that fits budget.
        """
        target_tokens = self.budget - margin
        current_tokens = count_tokens(text)

        if current_tokens <= target_tokens:
            return text

        # Estimate characters to keep (rough)
        ratio = target_tokens / current_tokens
        estimated_chars = int(len(text) * ratio * 0.95)  # 5% safety margin

        truncated = text[:estimated_chars]

        # Try to break at sentence boundary
        last_period = truncated.rfind(". ")
        last_newline = truncated.rfind("\n")
        break_point = max(last_period, last_newline)

        if break_point > estimated_chars * 0.8:  # Only if we keep 80%+
            truncated = truncated[: break_point + 1]

        # Verify fits
        while count_tokens(truncated) > target_tokens and len(truncated) > 100:
            truncated = truncated[: int(len(truncated) * 0.9)]

        return truncated.rstrip() + "..."
