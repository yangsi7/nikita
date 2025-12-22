"""Tests for ResponseDecision facts_extracted field.

NOTE: Fact extraction was moved from handler to post-processing pipeline (spec 012).
See nikita/context/post_processor.py for the extraction logic.
See tests/context/test_post_processor.py for comprehensive extraction tests.

This file only tests the ResponseDecision.facts_extracted field contract.
"""

import pytest
from datetime import datetime, timezone


class TestResponseDecisionFacts:
    """Tests for facts_extracted field in ResponseDecision."""

    def test_ac_6_3_4_response_decision_has_facts_extracted(self):
        """AC-6.3.4: ResponseDecision should have facts_extracted list."""
        from nikita.agents.text.handler import ResponseDecision

        decision = ResponseDecision(
            response="test response",
            delay_seconds=600,
            scheduled_at=datetime.now(timezone.utc),
        )

        assert hasattr(decision, "facts_extracted")

    def test_facts_extracted_default_empty_list(self):
        """facts_extracted should default to empty list."""
        from nikita.agents.text.handler import ResponseDecision

        decision = ResponseDecision(
            response="test",
            delay_seconds=300,
            scheduled_at=datetime.now(timezone.utc),
        )

        assert decision.facts_extracted == []

    def test_facts_extracted_can_contain_facts(self):
        """facts_extracted should be able to contain ExtractedFact objects."""
        from nikita.agents.text.handler import ResponseDecision
        from nikita.agents.text.facts import ExtractedFact

        facts = [
            ExtractedFact(
                fact="User works at Tesla",
                confidence=0.9,
                source="I work at Tesla",
                fact_type="explicit",
            ),
        ]

        decision = ResponseDecision(
            response="test",
            delay_seconds=300,
            scheduled_at=datetime.now(timezone.utc),
            facts_extracted=facts,
        )

        assert len(decision.facts_extracted) == 1
        assert decision.facts_extracted[0].fact == "User works at Tesla"
