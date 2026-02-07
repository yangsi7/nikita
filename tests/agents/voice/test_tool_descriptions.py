"""Tests for server tool descriptions (Spec 032: US-2).

TDD tests for T2.1-T2.5: Tool descriptions with WHEN/HOW/RETURNS/ERROR format.
"""

import pytest
from nikita.agents.voice.server_tools import (
    TOOL_DESCRIPTION_GET_CONTEXT,
    TOOL_DESCRIPTION_GET_MEMORY,
    TOOL_DESCRIPTION_SCORE_TURN,
    TOOL_DESCRIPTION_UPDATE_MEMORY,
)


class TestGetMemoryDescription:
    """T2.1: get_memory tool description tests."""

    def test_description_exists(self):
        """TOOL_DESCRIPTION_GET_MEMORY constant exists."""
        assert TOOL_DESCRIPTION_GET_MEMORY is not None
        assert isinstance(TOOL_DESCRIPTION_GET_MEMORY, str)
        assert len(TOOL_DESCRIPTION_GET_MEMORY) > 100

    def test_has_when_section(self):
        """AC-T2.1.1: WHEN section present."""
        desc = TOOL_DESCRIPTION_GET_MEMORY.upper()
        assert "WHEN" in desc, "Missing WHEN section"

    def test_has_how_section(self):
        """AC-T2.1.2: HOW section present."""
        desc = TOOL_DESCRIPTION_GET_MEMORY.upper()
        assert "HOW" in desc, "Missing HOW section"

    def test_has_error_section(self):
        """AC-T2.1.3: ERROR section present."""
        desc = TOOL_DESCRIPTION_GET_MEMORY.upper()
        assert "ERROR" in desc, "Missing ERROR section"

    def test_includes_examples(self):
        """AC-T2.1.4: Examples included."""
        desc = TOOL_DESCRIPTION_GET_MEMORY.lower()
        # Should include example use cases
        assert any(word in desc for word in ["remember", "recall", "birthday", "example"]), \
            "Missing examples in description"

    def test_mentions_memory_search(self):
        """Description mentions searching memory."""
        desc = TOOL_DESCRIPTION_GET_MEMORY.lower()
        assert "search" in desc or "memory" in desc or "memories" in desc


class TestGetContextDescription:
    """T2.2: get_context tool description tests."""

    def test_description_exists(self):
        """TOOL_DESCRIPTION_GET_CONTEXT constant exists."""
        assert TOOL_DESCRIPTION_GET_CONTEXT is not None
        assert isinstance(TOOL_DESCRIPTION_GET_CONTEXT, str)

    def test_emphasizes_call_start(self):
        """AC-T2.2.1: 'Use at the START of each call' emphasized."""
        desc = TOOL_DESCRIPTION_GET_CONTEXT.upper()
        assert "START" in desc, "Should emphasize use at call START"

    def test_describes_returned_context(self):
        """AC-T2.2.2: Describes what context is returned."""
        desc = TOOL_DESCRIPTION_GET_CONTEXT.lower()
        assert any(word in desc for word in ["chapter", "relationship", "mood", "context"]), \
            "Should describe returned context"

    def test_explains_refresh(self):
        """AC-T2.2.3: Explains when to refresh context."""
        desc = TOOL_DESCRIPTION_GET_CONTEXT.lower()
        # Should mention long calls or refreshing
        assert any(word in desc for word in ["refresh", "long", "minutes"]), \
            "Should explain when to refresh"


class TestScoreTurnDescription:
    """T2.3: score_turn tool description tests."""

    def test_description_exists(self):
        """TOOL_DESCRIPTION_SCORE_TURN constant exists."""
        assert TOOL_DESCRIPTION_SCORE_TURN is not None
        assert isinstance(TOOL_DESCRIPTION_SCORE_TURN, str)

    def test_emphasizes_emotional_exchanges(self):
        """AC-T2.3.1: 'Use after emotional exchanges' emphasized."""
        desc = TOOL_DESCRIPTION_SCORE_TURN.lower()
        assert any(word in desc for word in ["emotional", "meaningful", "important", "after"]), \
            "Should emphasize use after emotional exchanges"

    def test_explains_what_gets_scored(self):
        """AC-T2.3.2: Explains what gets scored."""
        desc = TOOL_DESCRIPTION_SCORE_TURN.lower()
        assert any(word in desc for word in ["intimacy", "passion", "trust", "score", "metrics"]), \
            "Should explain what metrics are scored"

    def test_documents_error_handling(self):
        """AC-T2.3.3: Error handling documented."""
        desc = TOOL_DESCRIPTION_SCORE_TURN.upper()
        assert "ERROR" in desc, "Should document error handling"


class TestUpdateMemoryDescription:
    """T2.4: update_memory tool description tests."""

    def test_description_exists(self):
        """TOOL_DESCRIPTION_UPDATE_MEMORY constant exists."""
        assert TOOL_DESCRIPTION_UPDATE_MEMORY is not None
        assert isinstance(TOOL_DESCRIPTION_UPDATE_MEMORY, str)

    def test_emphasizes_new_information(self):
        """AC-T2.4.1: 'Use when user shares NEW information' emphasized."""
        desc = TOOL_DESCRIPTION_UPDATE_MEMORY.upper()
        assert "NEW" in desc, "Should emphasize NEW information"

    def test_has_examples_of_what_to_store(self):
        """AC-T2.4.2: Examples of what to store."""
        desc = TOOL_DESCRIPTION_UPDATE_MEMORY.lower()
        assert any(word in desc for word in ["job", "hobby", "name", "preference", "fact"]), \
            "Should have examples of what to store"

    def test_explains_confidence_or_importance(self):
        """AC-T2.4.3: Explains importance/confidence levels."""
        desc = TOOL_DESCRIPTION_UPDATE_MEMORY.lower()
        # Should mention importance or what to prioritize
        assert any(word in desc for word in ["important", "significant", "personal", "meaningful"]), \
            "Should explain importance criteria"


class TestAllDescriptionsFormat:
    """T2.5: Integration tests for tool description format."""

    def test_all_descriptions_non_empty(self):
        """AC-T2.5.1: All descriptions are non-empty."""
        descriptions = [
            TOOL_DESCRIPTION_GET_CONTEXT,
            TOOL_DESCRIPTION_GET_MEMORY,
            TOOL_DESCRIPTION_SCORE_TURN,
            TOOL_DESCRIPTION_UPDATE_MEMORY,
        ]
        for desc in descriptions:
            assert desc is not None
            assert len(desc) > 50, "Description too short"

    def test_all_descriptions_valid_strings(self):
        """AC-T2.5.1: All descriptions are valid strings."""
        descriptions = [
            TOOL_DESCRIPTION_GET_CONTEXT,
            TOOL_DESCRIPTION_GET_MEMORY,
            TOOL_DESCRIPTION_SCORE_TURN,
            TOOL_DESCRIPTION_UPDATE_MEMORY,
        ]
        for desc in descriptions:
            assert isinstance(desc, str)
            # Should not have unescaped special characters that break JSON
            # (no actual JSON validation needed, just string check)

    def test_descriptions_have_consistent_structure(self):
        """AC-T2.5.2: Format consistency verified."""
        descriptions = [
            TOOL_DESCRIPTION_GET_MEMORY,
            TOOL_DESCRIPTION_SCORE_TURN,
            TOOL_DESCRIPTION_UPDATE_MEMORY,
        ]
        for desc in descriptions:
            desc_upper = desc.upper()
            # All should have WHEN/HOW/ERROR or similar structure
            sections_found = sum([
                "WHEN" in desc_upper,
                "HOW" in desc_upper or "USE" in desc_upper,
                "ERROR" in desc_upper or "RETURN" in desc_upper,
            ])
            assert sections_found >= 2, f"Description missing standard sections: {desc[:100]}..."

    def test_descriptions_reasonable_length(self):
        """Tool descriptions should be concise but complete."""
        descriptions = [
            TOOL_DESCRIPTION_GET_CONTEXT,
            TOOL_DESCRIPTION_GET_MEMORY,
            TOOL_DESCRIPTION_SCORE_TURN,
            TOOL_DESCRIPTION_UPDATE_MEMORY,
        ]
        for desc in descriptions:
            # Should be between 100-2000 characters
            assert 100 < len(desc) < 2000, f"Description length {len(desc)} out of range"
