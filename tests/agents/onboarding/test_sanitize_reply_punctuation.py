"""Tests for sanitize_reply_punctuation (closes GH #494, Walk A1 L1).

Em-dashes leak into LLM-generated nikita_reply prose. The sanitizer
post-processes the reply BEFORE persistence + envelope build so users
never see ``—``. Per user-global rule (~/.claude/CLAUDE.md "Output
Style, Hard Rule"): em-dash forbidden in human-facing prose.
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.validators import sanitize_reply_punctuation


class TestEmDashScrubbed:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (
                "long pause — let it breathe",
                "long pause, let it breathe",
            ),
            (
                "Walker—nice name. tell me more.",
                "Walker, nice name. tell me more.",
            ),
            (
                "twenty-five — that's a vibe",
                "twenty-five, that's a vibe",
            ),
            # En-dash + figure-dash + horizontal-bar variants too
            (
                "she said – then paused",
                "she said, then paused",
            ),
            (
                "okay ‒ done",
                "okay, done",
            ),
            (
                "hmm ― interesting",
                "hmm, interesting",
            ),
            # Multiple in one reply
            (
                "first — then — finally",
                "first, then, finally",
            ),
        ],
    )
    def test_replaces_dash_variants_with_comma(
        self, raw: str, expected: str
    ) -> None:
        assert sanitize_reply_punctuation(raw) == expected


class TestPreservesNormalText:
    @pytest.mark.parametrize(
        "raw",
        [
            "no dashes here",
            "twenty-five",  # hyphen-minus (compound) preserved
            "I'll think about it",  # apostrophe untouched
            "well, well, well",  # commas untouched
            "",
        ],
    )
    def test_no_change_when_no_dashes(self, raw: str) -> None:
        assert sanitize_reply_punctuation(raw) == raw


class TestEdgeCases:
    def test_idempotent(self) -> None:
        s = "long pause, let it breathe"
        assert sanitize_reply_punctuation(s) == s
        # Apply twice
        once = sanitize_reply_punctuation("long pause — breathe")
        twice = sanitize_reply_punctuation(once)
        assert once == twice

    def test_collapses_double_comma_artifact(self) -> None:
        # If a reply already had a comma followed by an em-dash,
        # the substitution would yield ", ," which we collapse to ",".
        result = sanitize_reply_punctuation("hi, — there")
        assert result == "hi, there"
        assert ", ," not in result

    def test_tight_dash_no_whitespace(self) -> None:
        # Bare "a—b" with no whitespace still gets sanitized.
        result = sanitize_reply_punctuation("walker—nice")
        assert result == "walker, nice"
