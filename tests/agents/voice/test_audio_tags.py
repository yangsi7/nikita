"""Tests for audio_tags module (Spec 108: V3 Voice Optimization).

Tests for:
- Tag definitions: all have required fields, count matches spec
- Chapter gating: Ch1 gets universal tags, Ch3 unlocks vulnerability, Ch5 gets all
- Forbidden tags: accent tags, shouts flagged
- First messages: each chapter has an audio tag, correct tag per spec
- Format instruction: non-empty, grouped by category
"""

import pytest


class TestAudioTagDefinitions:
    """Test ALL_AUDIO_TAGS registry."""

    def test_all_tags_have_required_fields(self):
        """Every tag must have name, display, description, min_chapter, category."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS

        for name, tag in ALL_AUDIO_TAGS.items():
            assert tag.name, f"Tag {name} missing name"
            assert tag.display, f"Tag {name} missing display"
            assert tag.description, f"Tag {name} missing description"
            assert 1 <= tag.min_chapter <= 5, f"Tag {name} has invalid min_chapter={tag.min_chapter}"
            assert tag.category in (
                "emotional", "delivery", "reaction",
            ), f"Tag {name} has invalid category={tag.category}"

    def test_tag_count_matches_spec(self):
        """Spec Section 3 defines 27 tags total (15 emotional + 5 delivery + 7 reaction)."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS

        assert len(ALL_AUDIO_TAGS) == 27

    def test_display_format_is_bracketed(self):
        """Display format must be [tagname]."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS

        for name, tag in ALL_AUDIO_TAGS.items():
            assert tag.display.startswith("["), f"Tag {name} display missing ["
            assert tag.display.endswith("]"), f"Tag {name} display missing ]"

    def test_no_forbidden_tags_in_catalog(self):
        """Forbidden tags must not appear in ALL_AUDIO_TAGS."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS, FORBIDDEN_TAGS

        for forbidden_name in FORBIDDEN_TAGS:
            assert forbidden_name not in ALL_AUDIO_TAGS, (
                f"Forbidden tag '{forbidden_name}' found in ALL_AUDIO_TAGS"
            )

    def test_core_tags_present(self):
        """Verify key tags from spec are present."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS

        expected = [
            "excited", "happy", "sad", "angry", "disappointed",
            "curious", "sarcastic", "nervous", "tired", "dismissive",
            "cheeky", "enthusiastic", "serious", "patient", "concerned",
            "whispers", "laughs", "laughs_softly", "chuckles",
            "laughs_hard", "sighs", "gasps", "hmm",
            "slow", "rushed", "hesitantly",
        ]
        for tag_name in expected:
            assert tag_name in ALL_AUDIO_TAGS, f"Expected tag '{tag_name}' not found"


class TestChapterGating:
    """Test chapter-based tag availability."""

    def test_chapter_1_gets_universal_tags_only(self):
        """Ch1 should only get tags with min_chapter=1."""
        from nikita.agents.voice.audio_tags import get_chapter_appropriate_tags

        tags = get_chapter_appropriate_tags(1)
        for tag in tags:
            assert tag.min_chapter <= 1, (
                f"Tag '{tag.name}' has min_chapter={tag.min_chapter} but was returned for Ch1"
            )

    def test_chapter_3_unlocks_vulnerability_tags(self):
        """Ch3 should unlock sad, nervous, whispers, hesitantly, quietly."""
        from nikita.agents.voice.audio_tags import get_chapter_appropriate_tags

        tags = get_chapter_appropriate_tags(3)
        tag_names = {t.name for t in tags}

        # These should be available at Ch3
        assert "sad" in tag_names
        assert "nervous" in tag_names
        assert "whispers" in tag_names
        assert "hesitantly" in tag_names

    def test_chapter_5_gets_all_tags(self):
        """Ch5 should get every tag in the catalog."""
        from nikita.agents.voice.audio_tags import ALL_AUDIO_TAGS, get_chapter_appropriate_tags

        tags = get_chapter_appropriate_tags(5)
        assert len(tags) == len(ALL_AUDIO_TAGS)

    def test_chapter_progression_monotonic(self):
        """Higher chapters must have >= tags than lower chapters."""
        from nikita.agents.voice.audio_tags import get_chapter_appropriate_tags

        prev_count = 0
        for chapter in range(1, 6):
            count = len(get_chapter_appropriate_tags(chapter))
            assert count >= prev_count, (
                f"Ch{chapter} has {count} tags but Ch{chapter-1} had {prev_count}"
            )
            prev_count = count

    def test_get_chapter_tag_names_returns_display_strings(self):
        """get_chapter_tag_names should return list of [tag] strings."""
        from nikita.agents.voice.audio_tags import get_chapter_tag_names

        names = get_chapter_tag_names(3)
        assert isinstance(names, list)
        assert len(names) > 0
        for name in names:
            assert name.startswith("[") and name.endswith("]")


class TestForbiddenTags:
    """Test forbidden tag detection."""

    def test_accent_tags_forbidden(self):
        """All accent tags must be forbidden."""
        from nikita.agents.voice.audio_tags import is_tag_forbidden

        assert is_tag_forbidden("French accent")
        assert is_tag_forbidden("US accent")
        assert is_tag_forbidden("Australian accent")
        assert is_tag_forbidden("British accent")

    def test_shouts_forbidden(self):
        """[shouts] is forbidden (Nikita's Max trauma)."""
        from nikita.agents.voice.audio_tags import is_tag_forbidden

        assert is_tag_forbidden("shouts")

    def test_singing_forbidden(self):
        """[singing] is forbidden."""
        from nikita.agents.voice.audio_tags import is_tag_forbidden

        assert is_tag_forbidden("singing")

    def test_valid_tags_not_forbidden(self):
        """Normal tags should not be flagged as forbidden."""
        from nikita.agents.voice.audio_tags import is_tag_forbidden

        assert not is_tag_forbidden("happy")
        assert not is_tag_forbidden("sighs")
        assert not is_tag_forbidden("chuckles")

    def test_forbidden_tags_have_reasons(self):
        """Each forbidden tag must have a reason string."""
        from nikita.agents.voice.audio_tags import FORBIDDEN_TAGS

        assert len(FORBIDDEN_TAGS) >= 6
        for tag_name, reason in FORBIDDEN_TAGS.items():
            assert isinstance(reason, str) and len(reason) > 0, (
                f"Forbidden tag '{tag_name}' missing reason"
            )


class TestFirstMessages:
    """Test chapter-specific first messages with audio tags."""

    def test_each_chapter_has_audio_tag(self):
        """Every first message must contain at least one [tag]."""
        from nikita.agents.voice.audio_tags import get_first_message

        for chapter in range(1, 6):
            msg = get_first_message(chapter, "TestUser")
            assert "[" in msg and "]" in msg, (
                f"Ch{chapter} first message has no audio tag: {msg}"
            )

    def test_chapter_1_uses_dismissive(self):
        """Ch1 first message should use [dismissive] tag."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(1, "Alex")
        assert "[dismissive]" in msg
        assert "Alex" in msg

    def test_chapter_2_uses_curious(self):
        """Ch2 first message should use [curious] tag."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(2, "Jordan")
        assert "[curious]" in msg
        assert "Jordan" in msg

    def test_chapter_3_uses_happy(self):
        """Ch3 first message should use [happy] tag."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(3, "Morgan")
        assert "[happy]" in msg
        assert "Morgan" in msg

    def test_chapter_4_uses_cheeky(self):
        """Ch4 first message should use [cheeky] tag."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(4, "Casey")
        assert "[cheeky]" in msg
        assert "Casey" in msg

    def test_chapter_5_uses_whispers(self):
        """Ch5 first message should use [whispers] tag."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(5, "Riley")
        assert "[whispers]" in msg
        assert "Riley" in msg

    def test_default_name_fallback(self):
        """None name should default to something reasonable."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(1, None)
        assert "[" in msg  # Still has audio tag
        assert len(msg) > 10  # Non-trivial message

    def test_invalid_chapter_returns_fallback(self):
        """Invalid chapter should return a valid message."""
        from nikita.agents.voice.audio_tags import get_first_message

        msg = get_first_message(99, "Test")
        assert len(msg) > 5


class TestFormatInstruction:
    """Test format_tag_instruction output."""

    def test_format_non_empty(self):
        """Format instruction should produce non-empty string."""
        from nikita.agents.voice.audio_tags import format_tag_instruction

        result = format_tag_instruction(3)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_format_includes_tag_syntax(self):
        """Output should include [tag] syntax examples."""
        from nikita.agents.voice.audio_tags import format_tag_instruction

        result = format_tag_instruction(3)
        assert "[" in result and "]" in result

    def test_format_groups_by_category(self):
        """Output should mention categories."""
        from nikita.agents.voice.audio_tags import format_tag_instruction

        result = format_tag_instruction(5)
        # Should reference at least emotional and reaction categories
        assert "emotional" in result.lower() or "emotion" in result.lower()
        assert "reaction" in result.lower() or "human" in result.lower()

    def test_format_chapter_1_fewer_tags_than_chapter_5(self):
        """Ch1 instruction should be shorter (fewer tags available)."""
        from nikita.agents.voice.audio_tags import format_tag_instruction

        ch1 = format_tag_instruction(1)
        ch5 = format_tag_instruction(5)
        assert len(ch1) < len(ch5)
