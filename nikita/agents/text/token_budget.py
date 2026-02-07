"""Combined Token Budget Manager for text agent context tiers.

Spec 030: Text Agent Message History and Continuity
Spec 041 T2.8: Two-tier token estimation (fast for truncation, accurate for validation)

Tasks: T5.1 (TokenBudgetManager), T5.2 (Truncation Priority)

Manages token allocation across 4 context tiers:
1. History (3000 tokens) - Message history for continuity
2. Today (500 tokens) - Daily summary and key moments
3. Threads (400 tokens) - Open conversation threads
4. Last Conversation (300 tokens) - Summary of prior session

Total Target: 4100 tokens
Hard Cap: 6150 tokens

Truncation Priority (lowest priority first):
1. Last Conversation - truncated first
2. Threads - truncated second
3. Today - truncated third
4. History - truncated last (highest priority, preserves min 10 turns)
"""

import logging
from dataclasses import dataclass
from typing import Any

from nikita.context.utils.token_counter import get_token_estimator

logger = logging.getLogger(__name__)

# Token budgets per tier
TIER_BUDGETS = {
    "history": 3000,
    "today": 500,
    "threads": 400,
    "last_conversation": 300,
}

# Total budget constraints
TARGET_BUDGET = 4100  # Recommended total
HARD_CAP = 6150  # Never exceed

# Minimum history to preserve (10 turns * ~30 tokens avg)
MIN_HISTORY_TOKENS = 100


@dataclass
class TierContent:
    """Content for each context tier.

    Attributes:
        history: Message history content.
        today: Today's summary and key moments.
        threads: Open conversation threads.
        last_conversation: Summary of last conversation.
    """

    history: str = ""
    today: str = ""
    threads: str = ""
    last_conversation: str = ""


@dataclass
class TokenUsage:
    """Token usage breakdown by tier.

    Attributes:
        history_tokens: Tokens used by history tier.
        today_tokens: Tokens used by today tier.
        threads_tokens: Tokens used by threads tier.
        last_conversation_tokens: Tokens used by last conversation tier.
        total_tokens: Total tokens across all tiers.
        truncated: Whether any tier was truncated.
        truncation_info: Details about what was truncated.
        truncated_history: Truncated history content.
        truncated_today: Truncated today content.
        truncated_threads: Truncated threads content.
        truncated_last_conversation: Truncated last conversation content.
    """

    history_tokens: int = 0
    today_tokens: int = 0
    threads_tokens: int = 0
    last_conversation_tokens: int = 0
    total_tokens: int = 0
    truncated: bool = False
    truncation_info: dict[str, Any] | None = None
    truncated_history: str = ""
    truncated_today: str = ""
    truncated_threads: str = ""
    truncated_last_conversation: str = ""


class TokenBudgetManager:
    """Manages token allocation across context tiers.

    Enforces tier budgets and hard cap, truncating lower-priority
    tiers first when over budget.

    Truncation priority (truncated first to last):
    1. last_conversation (lowest priority)
    2. threads
    3. today
    4. history (highest priority, min tokens preserved)

    Example:
        manager = TokenBudgetManager()
        content = TierContent(
            history="conversation history...",
            today="today's summary...",
            threads="open threads...",
            last_conversation="last time we talked...",
        )
        result = manager.allocate(content)
        print(f"Total: {result.total_tokens} tokens")
        print(f"History: {result.truncated_history}")
    """

    def __init__(
        self,
        history_budget: int = TIER_BUDGETS["history"],
        today_budget: int = TIER_BUDGETS["today"],
        threads_budget: int = TIER_BUDGETS["threads"],
        last_conversation_budget: int = TIER_BUDGETS["last_conversation"],
        hard_cap: int = HARD_CAP,
    ):
        """Initialize TokenBudgetManager.

        Args:
            history_budget: Max tokens for history tier (default 3000).
            today_budget: Max tokens for today tier (default 500).
            threads_budget: Max tokens for threads tier (default 400).
            last_conversation_budget: Max tokens for last conversation (default 300).
            hard_cap: Absolute maximum total tokens (default 6150).
        """
        self.history_budget = history_budget
        self.today_budget = today_budget
        self.threads_budget = threads_budget
        self.last_conversation_budget = last_conversation_budget
        self.hard_cap = hard_cap

    def _estimate_tokens(self, text: str | None, accurate: bool = False) -> int:
        """Estimate token count for text.

        Spec 041 T2.8: Uses two-tier estimation:
        - Fast (default): Character ratio for quick estimates (~100x faster)
        - Accurate: tiktoken encoding for precise budget validation

        Args:
            text: Text to estimate.
            accurate: If True, use tiktoken for precise count.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        estimator = get_token_estimator()
        return estimator.estimate(text, accurate=accurate)

    def _truncate_to_budget(
        self,
        text: str,
        token_budget: int,
        tier_name: str,
    ) -> tuple[str, int, bool]:
        """Truncate text to fit within token budget.

        Spec 041 T2.8: Uses fast estimation during truncation,
        accurate estimation for final returned token count.

        Args:
            text: Text to truncate.
            token_budget: Maximum tokens allowed.
            tier_name: Name of tier (for logging).

        Returns:
            Tuple of (truncated_text, actual_tokens, was_truncated).
        """
        if not text:
            return "", 0, False

        # Use fast estimate for initial check
        current_tokens = self._estimate_tokens(text, accurate=False)

        if current_tokens <= token_budget:
            # Use accurate count for return value
            actual_tokens = self._estimate_tokens(text, accurate=True)
            return text, actual_tokens, False

        # Calculate max characters for budget (~4 chars per token)
        chars_per_token = 4
        max_chars = int(token_budget * chars_per_token)

        # Truncate with ellipsis
        truncated = text[:max_chars - 3] + "..." if max_chars > 3 else text[:max_chars]

        # Use accurate count for final token calculation
        actual_tokens = self._estimate_tokens(truncated, accurate=True)

        logger.info(
            f"Truncated {tier_name} from ~{current_tokens} to {actual_tokens} tokens"
        )

        return truncated, actual_tokens, True

    def allocate(self, content: TierContent) -> TokenUsage:
        """Allocate tokens across tiers, enforcing budgets.

        First applies per-tier budgets, then enforces hard cap
        by truncating lowest-priority tiers first.

        Args:
            content: Content for each tier.

        Returns:
            TokenUsage with truncated content and token counts.
        """
        truncation_info: dict[str, Any] = {}
        truncated = False

        # Step 1: Apply per-tier budgets
        history_text, history_tokens, history_truncated = self._truncate_to_budget(
            content.history, self.history_budget, "history"
        )
        if history_truncated:
            truncated = True
            truncation_info["history"] = {
                "original_tokens": self._estimate_tokens(content.history),
                "truncated_to": history_tokens,
            }

        today_text, today_tokens, today_truncated = self._truncate_to_budget(
            content.today, self.today_budget, "today"
        )
        if today_truncated:
            truncated = True
            truncation_info["today"] = {
                "original_tokens": self._estimate_tokens(content.today),
                "truncated_to": today_tokens,
            }

        threads_text, threads_tokens, threads_truncated = self._truncate_to_budget(
            content.threads, self.threads_budget, "threads"
        )
        if threads_truncated:
            truncated = True
            truncation_info["threads"] = {
                "original_tokens": self._estimate_tokens(content.threads),
                "truncated_to": threads_tokens,
            }

        last_conv_text, last_conv_tokens, last_conv_truncated = self._truncate_to_budget(
            content.last_conversation, self.last_conversation_budget, "last_conversation"
        )
        if last_conv_truncated:
            truncated = True
            truncation_info["last_conversation"] = {
                "original_tokens": self._estimate_tokens(content.last_conversation),
                "truncated_to": last_conv_tokens,
            }

        # Step 2: Check total against hard cap
        total = history_tokens + today_tokens + threads_tokens + last_conv_tokens

        if total > self.hard_cap:
            logger.warning(
                f"Total tokens {total} exceeds hard cap {self.hard_cap}, "
                "applying priority truncation"
            )
            truncated = True

            # Truncation order: last_conv -> threads -> today -> history
            excess = total - self.hard_cap

            # 1. Truncate last_conversation first
            if excess > 0 and last_conv_tokens > 0:
                reduction = min(excess, last_conv_tokens)
                new_budget = max(0, last_conv_tokens - reduction)
                last_conv_text, last_conv_tokens, _ = self._truncate_to_budget(
                    last_conv_text, new_budget, "last_conversation (priority)"
                )
                excess -= reduction
                truncation_info["last_conversation_priority"] = {
                    "reduced_by": reduction,
                    "new_tokens": last_conv_tokens,
                }

            # 2. Truncate threads second
            if excess > 0 and threads_tokens > 0:
                reduction = min(excess, threads_tokens)
                new_budget = max(0, threads_tokens - reduction)
                threads_text, threads_tokens, _ = self._truncate_to_budget(
                    threads_text, new_budget, "threads (priority)"
                )
                excess -= reduction
                truncation_info["threads_priority"] = {
                    "reduced_by": reduction,
                    "new_tokens": threads_tokens,
                }

            # 3. Truncate today third
            if excess > 0 and today_tokens > 0:
                reduction = min(excess, today_tokens)
                new_budget = max(0, today_tokens - reduction)
                today_text, today_tokens, _ = self._truncate_to_budget(
                    today_text, new_budget, "today (priority)"
                )
                excess -= reduction
                truncation_info["today_priority"] = {
                    "reduced_by": reduction,
                    "new_tokens": today_tokens,
                }

            # 4. Truncate history last (preserve minimum)
            if excess > 0 and history_tokens > MIN_HISTORY_TOKENS:
                # Don't go below minimum
                max_reduction = history_tokens - MIN_HISTORY_TOKENS
                reduction = min(excess, max_reduction)
                new_budget = max(MIN_HISTORY_TOKENS, history_tokens - reduction)
                history_text, history_tokens, _ = self._truncate_to_budget(
                    history_text, new_budget, "history (priority)"
                )
                truncation_info["history_priority"] = {
                    "reduced_by": reduction,
                    "new_tokens": history_tokens,
                    "min_preserved": MIN_HISTORY_TOKENS,
                }

        # Recalculate total after priority truncation
        total = history_tokens + today_tokens + threads_tokens + last_conv_tokens

        if truncated:
            logger.info(
                f"Token allocation complete: {total} total "
                f"(history={history_tokens}, today={today_tokens}, "
                f"threads={threads_tokens}, last_conv={last_conv_tokens})"
            )

        return TokenUsage(
            history_tokens=history_tokens,
            today_tokens=today_tokens,
            threads_tokens=threads_tokens,
            last_conversation_tokens=last_conv_tokens,
            total_tokens=total,
            truncated=truncated,
            truncation_info=truncation_info if truncation_info else None,
            truncated_history=history_text,
            truncated_today=today_text,
            truncated_threads=threads_text,
            truncated_last_conversation=last_conv_text,
        )
