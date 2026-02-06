"""Token counting utilities using tiktoken.

Provides accurate token counting for Claude-compatible models.

Spec 041 T2.8: Two-tier token estimation
- Fast: Character ratio (~4 chars per token) for quick estimates
- Accurate: tiktoken encoding for precise counts

Use TokenEstimator.estimate_fast() for hot paths (message loading loops)
Use TokenEstimator.estimate_accurate() for final budget calculations
"""

import logging
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)

# Claude uses the same tokenizer as cl100k_base (GPT-4 compatible)
# This is the closest available encoding for Claude models
DEFAULT_ENCODING = "cl100k_base"

# Fast estimation: ~4 characters per token (conservative)
# Based on empirical testing with English text
CHARS_PER_TOKEN = 4


@lru_cache(maxsize=1)
def _get_encoder() -> tiktoken.Encoding:
    """Get the tiktoken encoder (cached singleton).

    Returns:
        tiktoken Encoding instance.
    """
    return tiktoken.get_encoding(DEFAULT_ENCODING)


class TokenEstimator:
    """Two-tier token estimation for performance-sensitive contexts.

    Spec 041 T2.8: Provides fast (char ratio) and accurate (tiktoken) methods.

    Fast estimation is ~100x faster but less accurate (±20%).
    Accurate estimation uses tiktoken but has ~0.5ms overhead per call.

    Usage:
        estimator = TokenEstimator()

        # Hot path (loading 100 messages)
        total = sum(estimator.estimate_fast(m) for m in messages)

        # Final budget check
        precise = estimator.estimate_accurate(final_text)

    Typical performance:
        - estimate_fast: ~0.001ms per call
        - estimate_accurate: ~0.5ms per call (first call ~5ms for encoder init)
    """

    def __init__(self):
        """Initialize TokenEstimator with lazy encoder loading."""
        self._encoder: tiktoken.Encoding | None = None

    @property
    def encoder(self) -> tiktoken.Encoding:
        """Get encoder (lazy initialization)."""
        if self._encoder is None:
            self._encoder = _get_encoder()
        return self._encoder

    def estimate_fast(self, text: str | None) -> int:
        """Fast token estimate using character ratio.

        Uses ~4 characters per token ratio (conservative for English).
        Suitable for:
        - Loading many messages in a loop
        - Initial budget checks before detailed analysis
        - Cases where ±20% accuracy is acceptable

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count (may be ±20% off accurate count).
        """
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN

    def estimate_accurate(self, text: str | None) -> int:
        """Accurate token count using tiktoken.

        Uses cl100k_base encoding (Claude-compatible).
        Suitable for:
        - Final budget calculations before truncation
        - Validating context fits within limits
        - Cases where precision matters

        Args:
            text: Text to count tokens for.

        Returns:
            Accurate token count (or fallback to fast if tiktoken fails).
        """
        if not text:
            return 0
        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken failed, falling back to fast estimate: {e}")
            return self.estimate_fast(text)

    def estimate(self, text: str | None, accurate: bool = False) -> int:
        """Estimate tokens with mode selection.

        Args:
            text: Text to estimate tokens for.
            accurate: If True, use tiktoken; if False, use char ratio.

        Returns:
            Token count estimate.
        """
        if accurate:
            return self.estimate_accurate(text)
        return self.estimate_fast(text)


# Global singleton for convenience
_token_estimator: TokenEstimator | None = None


def get_token_estimator() -> TokenEstimator:
    """Get global TokenEstimator singleton.

    Returns:
        TokenEstimator instance.
    """
    global _token_estimator
    if _token_estimator is None:
        _token_estimator = TokenEstimator()
    return _token_estimator


def estimate_tokens_fast(text: str | None) -> int:
    """Quick token estimate using character ratio.

    Convenience function using global estimator.

    Args:
        text: Text to estimate.

    Returns:
        Estimated token count.
    """
    return get_token_estimator().estimate_fast(text)


def estimate_tokens_accurate(text: str | None) -> int:
    """Accurate token count using tiktoken.

    Convenience function using global estimator.

    Args:
        text: Text to count.

    Returns:
        Accurate token count.
    """
    return get_token_estimator().estimate_accurate(text)


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
