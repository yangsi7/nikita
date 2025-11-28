"""Tests for Fact Extraction Integration - TDD for T6.3.

Acceptance Criteria:
- AC-6.3.1: Handler calls FactExtractor after agent generates response
- AC-6.3.2: Extracted facts stored via memory.add_user_fact()
- AC-6.3.3: Facts include source_message reference
- AC-6.3.4: ResponseDecision includes facts_extracted list
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


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


class TestHandlerFactExtraction:
    """Tests for fact extraction in MessageHandler."""

    @pytest.mark.asyncio
    async def test_ac_6_3_1_handler_calls_fact_extractor(self):
        """AC-6.3.1: Handler calls FactExtractor after agent generates response."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()
        user_message = "I work at Tesla as an engineer"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="Nice, electric cars!")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            await handler.handle(user_id, user_message)

            # Verify FactExtractor.extract_facts was called
            mock_fact_extractor.extract_facts.assert_called_once()

    @pytest.mark.asyncio
    async def test_fact_extractor_receives_correct_arguments(self):
        """FactExtractor should receive user_message, nikita_response, and existing_facts."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()
        user_message = "I'm an engineer"
        nikita_response = "That's cool"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        existing_facts = ["User lives in California"]
        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock()
        mock_memory.get_user_facts = AsyncMock(return_value=existing_facts)

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value=nikita_response)), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            await handler.handle(user_id, user_message)

            # Verify arguments
            call_args = mock_fact_extractor.extract_facts.call_args
            assert call_args.kwargs["user_message"] == user_message
            assert call_args.kwargs["nikita_response"] == nikita_response
            assert call_args.kwargs["existing_facts"] == existing_facts

    @pytest.mark.asyncio
    async def test_ac_6_3_2_extracted_facts_stored_via_memory(self):
        """AC-6.3.2: Extracted facts stored via memory.add_user_fact()."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        # Mock extractor to return some facts
        extracted_facts = [
            ExtractedFact(
                fact="User works at Tesla",
                confidence=0.9,
                source="I work at Tesla",
                fact_type="explicit",
            ),
            ExtractedFact(
                fact="User is an engineer",
                confidence=0.85,
                source="I work at Tesla as an engineer",
                fact_type="explicit",
            ),
        ]

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=extracted_facts)

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            await handler.handle(user_id, "I work at Tesla as an engineer")

            # Verify add_user_fact was called for each fact
            assert mock_memory.add_user_fact.call_count == 2

            calls = mock_memory.add_user_fact.call_args_list
            assert calls[0][0] == ("User works at Tesla", 0.9)
            assert calls[1][0] == ("User is an engineer", 0.85)

    @pytest.mark.asyncio
    async def test_ac_6_3_4_response_includes_extracted_facts(self):
        """AC-6.3.4: ResponseDecision includes facts_extracted list."""
        from nikita.agents.text.handler import MessageHandler, ResponseDecision
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        extracted_facts = [
            ExtractedFact(
                fact="User works at Tesla",
                confidence=0.9,
                source="I work at Tesla",
                fact_type="explicit",
            ),
        ]

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=extracted_facts)

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="Nice!")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            result = await handler.handle(user_id, "I work at Tesla")

            # Response should include the extracted facts
            assert isinstance(result, ResponseDecision)
            assert len(result.facts_extracted) == 1
            assert result.facts_extracted[0].fact == "User works at Tesla"

    @pytest.mark.asyncio
    async def test_no_fact_extraction_when_skipped(self):
        """Should not extract facts when message is skipped."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 3

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True  # Skip this message

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            result = await handler.handle(user_id, "I work at Tesla")

            # Should not call fact extractor when skipped
            mock_fact_extractor.extract_facts.assert_not_called()
            assert result.facts_extracted == []


class TestHandlerWithDefaultFactExtractor:
    """Tests for handler creating default FactExtractor."""

    def test_handler_creates_fact_extractor_if_none(self):
        """Handler should create FactExtractor if none provided."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.facts import FactExtractor

        handler = MessageHandler()

        assert hasattr(handler, "fact_extractor")
        assert isinstance(handler.fact_extractor, FactExtractor)

    def test_handler_uses_provided_fact_extractor(self):
        """Handler should use provided FactExtractor."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.facts import FactExtractor

        custom_extractor = FactExtractor(min_confidence=0.7)
        handler = MessageHandler(fact_extractor=custom_extractor)

        assert handler.fact_extractor is custom_extractor


class TestFactExtractionWithEmptyResults:
    """Tests for handling empty fact extraction results."""

    @pytest.mark.asyncio
    async def test_empty_facts_handled_gracefully(self):
        """Handler should handle empty fact extraction results gracefully."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        # Return no facts
        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="Hello")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(
                timer=mock_timer,
                skip_decision=mock_skip,
                fact_extractor=mock_fact_extractor,
            )
            result = await handler.handle(user_id, "Hey")

            # Should not call add_user_fact
            mock_memory.add_user_fact.assert_not_called()
            # Response should have empty facts list
            assert result.facts_extracted == []
