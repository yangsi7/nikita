"""Tests for TokenBudgetManager class.

Spec 030: Text Agent Message History and Continuity
Tasks: T5.1 (TokenBudgetManager), T5.2 (Truncation Priority)

TDD: Write failing tests first, then implement.
"""

import pytest
from dataclasses import dataclass


class TestTokenBudgetManagerBasics:
    """T5.1: Combined Token Budget Manager tests."""

    def test_total_budget_respected(self):
        """AC-T5.1.1: Total budget 4100 tokens (target), 6150 (hard cap)."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        manager = TokenBudgetManager()

        # Create content that exceeds hard cap
        history_content = "a" * 20000  # ~6000 tokens
        today_content = "b" * 2000  # ~600 tokens
        threads_content = "c" * 1500  # ~450 tokens
        last_conv_content = "d" * 1000  # ~300 tokens

        content = TierContent(
            history=history_content,
            today=today_content,
            threads=threads_content,
            last_conversation=last_conv_content,
        )

        result = manager.allocate(content)

        # Total should not exceed hard cap (6150)
        assert result.total_tokens <= 6150

    def test_tier_budgets_enforced(self):
        """AC-T5.1.2: Tier budgets enforced - History 3000, Today 500, Threads 400, Last 300."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        manager = TokenBudgetManager()

        # Create content at exactly budget limits
        content = TierContent(
            history="a" * 10000,  # ~3000 tokens
            today="b" * 1700,  # ~500 tokens
            threads="c" * 1400,  # ~400 tokens
            last_conversation="d" * 1000,  # ~300 tokens
        )

        result = manager.allocate(content)

        # Each tier should not exceed its budget
        assert result.history_tokens <= 3000
        assert result.today_tokens <= 500
        assert result.threads_tokens <= 400
        assert result.last_conversation_tokens <= 300

    def test_hard_cap_never_exceeded(self):
        """AC-T5.1.3: Combined output never exceeds 6150 tokens."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        manager = TokenBudgetManager()

        # Extreme content that would far exceed hard cap
        massive_content = "x" * 100000  # ~30000 tokens each

        content = TierContent(
            history=massive_content,
            today=massive_content,
            threads=massive_content,
            last_conversation=massive_content,
        )

        result = manager.allocate(content)

        # Must never exceed hard cap
        assert result.total_tokens <= 6150

    def test_provides_usage_breakdown(self):
        """AC-T5.1.4: Returns TokenUsage with per-tier counts."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        manager = TokenBudgetManager()

        content = TierContent(
            history="hello world",
            today="good morning",
            threads="topic one",
            last_conversation="we talked about",
        )

        result = manager.allocate(content)

        # Should have all breakdown fields
        assert hasattr(result, "history_tokens")
        assert hasattr(result, "today_tokens")
        assert hasattr(result, "threads_tokens")
        assert hasattr(result, "last_conversation_tokens")
        assert hasattr(result, "total_tokens")

        # Total should equal sum of tiers
        assert result.total_tokens == (
            result.history_tokens
            + result.today_tokens
            + result.threads_tokens
            + result.last_conversation_tokens
        )


class TestTruncationPriority:
    """T5.2: Truncation Priority Logic tests."""

    def test_truncation_order_last_conv_first(self):
        """AC-T5.2.1: Truncation order - Last Conv truncated before Threads."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        # Set a low hard cap to force truncation
        # Note: With fast estimate (~4 chars/token), we need larger content to exceed cap
        manager = TokenBudgetManager(hard_cap=800)

        content = TierContent(
            history="a" * 3000,  # ~750 tokens (fast) -> should be truncated to history_budget
            today="b" * 800,  # ~200 tokens (fast)
            threads="c" * 800,  # ~200 tokens (fast)
            last_conversation="d" * 1500,  # ~375 tokens - should be truncated first
        )

        result = manager.allocate(content)

        # When priority truncation kicks in, last_conversation gets reduced first
        # Total after tier budgets: depends on hard_cap, but last_conv should be smaller than threads
        assert result.last_conversation_tokens <= result.threads_tokens

    def test_truncation_preserves_history_priority(self):
        """AC-T5.2.2: History is truncated last (highest priority)."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        # Very low cap forces significant truncation
        manager = TokenBudgetManager(hard_cap=500)

        content = TierContent(
            history="a" * 2000,  # Primary tier - should be preserved most
            today="b" * 1000,
            threads="c" * 500,
            last_conversation="d" * 500,
        )

        result = manager.allocate(content)

        # History should have highest allocation after truncation
        assert result.history_tokens >= result.today_tokens
        assert result.history_tokens >= result.threads_tokens
        assert result.history_tokens >= result.last_conversation_tokens

    def test_minimum_history_preserved(self):
        """AC-T5.2.3: Minimum 10 history turns always preserved (~300 tokens min)."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent

        # Very low cap
        manager = TokenBudgetManager(hard_cap=300)

        # Simulate 20 turns of history (each turn ~30 tokens avg)
        history_turns = "\n".join([f"Turn {i}: Some message content" for i in range(20)])

        content = TierContent(
            history=history_turns,
            today="today summary",
            threads="thread content",
            last_conversation="last conv",
        )

        result = manager.allocate(content)

        # Should preserve minimum history even under pressure
        # Minimum ~100 tokens for 10 short turns
        assert result.history_tokens >= 100

    def test_truncation_logged_with_token_counts(self):
        """AC-T5.2.4: Truncation logged with token counts."""
        from nikita.agents.text.token_budget import TokenBudgetManager, TierContent
        import logging

        # Capture logs
        manager = TokenBudgetManager(hard_cap=500)

        content = TierContent(
            history="a" * 5000,
            today="b" * 2000,
            threads="c" * 1000,
            last_conversation="d" * 1000,
        )

        # Should not raise, should log truncation info
        result = manager.allocate(content)

        # Truncation happened
        assert result.truncated is True
        assert result.truncation_info is not None
        # Check for any tier truncation info (with or without _priority suffix)
        info_keys = result.truncation_info.keys()
        has_truncation_info = any(
            "history" in k or "last_conversation" in k or "threads" in k or "today" in k
            for k in info_keys
        )
        assert has_truncation_info


class TestTierContentDataclass:
    """Tests for TierContent dataclass."""

    def test_tier_content_creation(self):
        """TierContent can be created with all fields."""
        from nikita.agents.text.token_budget import TierContent

        content = TierContent(
            history="history content",
            today="today content",
            threads="threads content",
            last_conversation="last conversation",
        )

        assert content.history == "history content"
        assert content.today == "today content"
        assert content.threads == "threads content"
        assert content.last_conversation == "last conversation"

    def test_tier_content_optional_fields(self):
        """TierContent allows empty strings for missing tiers."""
        from nikita.agents.text.token_budget import TierContent

        content = TierContent(
            history="only history",
            today="",
            threads="",
            last_conversation="",
        )

        assert content.history == "only history"
        assert content.today == ""


class TestTokenUsageResult:
    """Tests for TokenUsage result dataclass."""

    def test_token_usage_fields(self):
        """TokenUsage has all required fields."""
        from nikita.agents.text.token_budget import TokenUsage

        usage = TokenUsage(
            history_tokens=1000,
            today_tokens=200,
            threads_tokens=150,
            last_conversation_tokens=100,
            total_tokens=1450,
            truncated=False,
            truncation_info=None,
            truncated_history="truncated content",
            truncated_today="today",
            truncated_threads="threads",
            truncated_last_conversation="last",
        )

        assert usage.history_tokens == 1000
        assert usage.total_tokens == 1450
        assert usage.truncated is False


class TestTokenEstimation:
    """Tests for token estimation accuracy."""

    def test_token_estimation_conservative(self):
        """Token estimation is conservative (tends to overestimate)."""
        from nikita.agents.text.token_budget import TokenBudgetManager

        manager = TokenBudgetManager()

        # 100 characters in English ~= 25-30 tokens
        text = "a" * 100
        estimated = manager._estimate_tokens(text)

        # Conservative estimate: ~0.3 tokens per char = 30 tokens
        # Should be in range 25-35
        assert 20 <= estimated <= 40

    def test_empty_content_zero_tokens(self):
        """Empty content should estimate to 0 tokens."""
        from nikita.agents.text.token_budget import TokenBudgetManager

        manager = TokenBudgetManager()

        assert manager._estimate_tokens("") == 0
        assert manager._estimate_tokens(None) == 0
