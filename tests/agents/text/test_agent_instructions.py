"""Tests for agent-level @agent.instructions decorators (GH #201).

Covers the two new decorators added in GH #201:
- add_vulnerability_gate — mirrors system_prompt.j2:411-426 on fallback path
- add_chapter_examples — serializes curated examples for chapter

Both must skip when ctx.deps.generated_prompt is set (pipeline owns prompt).
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def ctx_without_generated_prompt():
    """RunContext mock where pipeline path is INACTIVE (fallback path)."""
    ctx = MagicMock()
    ctx.deps.generated_prompt = None
    ctx.deps.user.chapter = 1
    ctx.deps.psyche_state = None
    return ctx


@pytest.fixture
def ctx_with_generated_prompt():
    """RunContext mock where pipeline path is ACTIVE."""
    ctx = MagicMock()
    ctx.deps.generated_prompt = "## PIPELINE OWNS THIS PROMPT"
    ctx.deps.user.chapter = 1
    return ctx


class TestAddVulnerabilityGate:
    """add_vulnerability_gate decorator — injects structured level 0-5 block."""

    def test_skips_when_generated_prompt_is_set(self, ctx_with_generated_prompt):
        """When pipeline path is active, skip to avoid ~80 tokens of dupe."""
        from nikita.agents.text.persona import add_vulnerability_gate

        result = add_vulnerability_gate(ctx_with_generated_prompt)
        assert result == ""

    def test_injects_level_0_for_chapter_1(self, ctx_without_generated_prompt):
        """Ch1 → level 0 → 'Surface facts only' directive."""
        from nikita.agents.text.persona import add_vulnerability_gate

        ctx_without_generated_prompt.deps.user.chapter = 1
        result = add_vulnerability_gate(ctx_without_generated_prompt)
        assert "0/5" in result
        assert "Surface facts only" in result

    def test_injects_level_5_for_chapter_5(self, ctx_without_generated_prompt):
        """Ch5 → level 5 → 'Complete transparency' directive."""
        from nikita.agents.text.persona import add_vulnerability_gate

        ctx_without_generated_prompt.deps.user.chapter = 5
        result = add_vulnerability_gate(ctx_without_generated_prompt)
        assert "5/5" in result
        assert "Complete transparency" in result


class TestAddChapterExamples:
    """add_chapter_examples decorator — serializes curated Ch-keyed examples."""

    def test_skips_when_generated_prompt_is_set(self, ctx_with_generated_prompt):
        """Pipeline owns examples too (implicitly via its own prompt)."""
        from nikita.agents.text.persona import add_chapter_examples

        result = add_chapter_examples(ctx_with_generated_prompt)
        assert result == ""

    def test_serializes_ch1_examples_as_markdown(
        self, ctx_without_generated_prompt
    ):
        """Examples render as a clearly-delimited list for the LLM."""
        from nikita.agents.text.persona import (
            CHAPTER_EXAMPLE_RESPONSES,
            add_chapter_examples,
        )

        ctx_without_generated_prompt.deps.user.chapter = 1
        result = add_chapter_examples(ctx_without_generated_prompt)
        # Header present
        assert "Example" in result or "examples" in result.lower()
        # At least one Ch1 response string appears in the serialized output
        first = CHAPTER_EXAMPLE_RESPONSES[1][0]["response"]
        assert first in result, (
            f"Expected first Ch1 response in output, got: {result[:200]!r}"
        )

    def test_uses_chapter_specific_examples_not_fallback(
        self, ctx_without_generated_prompt
    ):
        """Ch3 output contains Ch3 examples, not Ch1 examples."""
        from nikita.agents.text.persona import (
            CHAPTER_EXAMPLE_RESPONSES,
            add_chapter_examples,
        )

        ctx_without_generated_prompt.deps.user.chapter = 3
        result = add_chapter_examples(ctx_without_generated_prompt)
        ch3_first = CHAPTER_EXAMPLE_RESPONSES[3][0]["response"]
        assert ch3_first in result
