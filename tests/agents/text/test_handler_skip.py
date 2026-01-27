"""Tests for Skip Logic Integration with MessageHandler - TDD for T5.2.

Acceptance Criteria:
- AC-5.2.1: Handler checks `SkipDecision.should_skip()` before agent.run()
- AC-5.2.2: Skipped messages logged with reason
- AC-5.2.3: Skip state stored so consecutive messages don't all skip
- AC-5.2.4: Next message after skip processes normally
- AC-5.2.5: ResponseDecision.should_respond = False when skipped
"""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="function")

from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import logging


class TestSkipDecisionIntegration:
    """Tests for skip decision integration with handler."""

    def test_response_decision_has_should_respond(self):
        """ResponseDecision should have should_respond field."""
        from nikita.agents.text.handler import ResponseDecision

        # When skipped
        decision = ResponseDecision(
            response="",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=False,
        )

        assert hasattr(decision, "should_respond")
        assert decision.should_respond is False

    def test_response_decision_should_respond_default_true(self):
        """ResponseDecision.should_respond should default to True."""
        from nikita.agents.text.handler import ResponseDecision

        decision = ResponseDecision(
            response="test",
            delay_seconds=600,
            scheduled_at=datetime.now(timezone.utc),
        )

        # Default should be True (normal response)
        assert decision.should_respond is True

    def test_ac_5_2_5_response_decision_false_when_skipped(self):
        """AC-5.2.5: ResponseDecision.should_respond = False when skipped."""
        from nikita.agents.text.handler import ResponseDecision

        skipped_decision = ResponseDecision(
            response="",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=False,
            skip_reason="Chapter 1 random skip",
        )

        assert skipped_decision.should_respond is False
        assert skipped_decision.skip_reason is not None

    def test_response_decision_has_skip_reason(self):
        """ResponseDecision should have skip_reason field."""
        from nikita.agents.text.handler import ResponseDecision

        decision = ResponseDecision(
            response="",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=False,
            skip_reason="Random skip based on chapter 1 probability",
        )

        assert hasattr(decision, "skip_reason")
        assert "chapter 1" in decision.skip_reason.lower()


class TestHandlerSkipDecision:
    """Tests for handler using SkipDecision."""

    @pytest.mark.asyncio
    async def test_ac_5_2_1_handler_checks_skip_before_agent(self):
        """AC-5.2.1: Handler checks SkipDecision.should_skip() before agent.run()."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_memory = MagicMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False  # Don't skip
        mock_skip.last_was_skipped = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            await handler.handle(user_id, "Hello")

            # Should have called should_skip with the chapter
            mock_skip.should_skip.assert_called_once_with(mock_user.chapter)

    @pytest.mark.asyncio
    async def test_handler_skips_agent_when_should_skip_true(self):
        """When should_skip returns True, handler should not call agent."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.timing import ResponseTimer

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_timer = MagicMock(spec=ResponseTimer)

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True  # Skip this message
        mock_skip.last_was_skipped = True

        mock_generate = AsyncMock(return_value="response")

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=mock_generate), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip)
            result = await handler.handle(user_id, "Hello")

            # Should NOT have called generate_response when skipping
            mock_generate.assert_not_called()

            # Should return decision with should_respond=False
            assert result.should_respond is False

    @pytest.mark.asyncio
    async def test_ac_5_2_5_skipped_response_decision(self):
        """AC-5.2.5: When skipped, ResponseDecision.should_respond = False."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.timing import ResponseTimer

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True  # Skip
        mock_skip.last_was_skipped = True

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(skip_decision=mock_skip)
            result = await handler.handle(user_id, "Hello")

            assert result.should_respond is False
            assert result.response == ""
            assert result.delay_seconds == 0


class TestSkipLogging:
    """Tests for skip logging (AC-5.2.2)."""

    @pytest.mark.asyncio
    async def test_ac_5_2_2_skipped_messages_logged(self, caplog):
        """AC-5.2.2: Skipped messages should be logged with reason."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True
        mock_skip.last_was_skipped = True

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(skip_decision=mock_skip)

            with caplog.at_level(logging.INFO):
                result = await handler.handle(user_id, "Hello Nikita")

            # Should have logged the skip
            assert any("skip" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_skip_reason_in_response_decision(self):
        """Skip reason should be included in ResponseDecision."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True
        mock_skip.last_was_skipped = True

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(skip_decision=mock_skip)
            result = await handler.handle(user_id, "Hello")

            # Skip reason should be set
            assert result.skip_reason is not None
            assert "chapter" in result.skip_reason.lower()


class TestConsecutiveSkipState:
    """Tests for consecutive skip state management (AC-5.2.3, AC-5.2.4)."""

    @pytest.mark.asyncio
    async def test_ac_5_2_3_skip_state_stored(self):
        """AC-5.2.3: Skip state stored so consecutive messages don't all skip."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        # Use real SkipDecision to test state tracking
        skip_decision = SkipDecision()

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(skip_decision=skip_decision)

            # Handler should use the same SkipDecision instance across calls
            assert handler.skip_decision is skip_decision

    @pytest.mark.asyncio
    async def test_ac_5_2_4_next_message_after_skip_processes(self):
        """AC-5.2.4: Next message after skip processes normally."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_memory = MagicMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 600

        # Mock skip: first call skips, second call doesn't
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.side_effect = [True, False]  # Skip first, process second
        mock_skip.last_was_skipped = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        mock_generate = AsyncMock(return_value="response text")

        # Mock text pattern processor to return original text
        mock_pattern_result = MagicMock()
        mock_pattern_result.messages = [MagicMock(content="response text")]
        mock_pattern_result.context = "neutral"
        mock_pattern_result.emoji_count = 0
        mock_processor = MagicMock()
        mock_processor.process.return_value = mock_pattern_result

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=mock_generate), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler._get_processor_instance", return_value=mock_processor):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)

            # First message - skipped
            result1 = await handler.handle(user_id, "First message")
            assert result1.should_respond is False

            # Second message - processed normally
            result2 = await handler.handle(user_id, "Second message")
            assert result2.should_respond is True
            assert result2.response == "response text"

            # generate_response should only have been called once (for second message)
            assert mock_generate.call_count == 1


class TestSkipDoesNotStore:
    """Tests to verify skipped messages don't store pending responses.
    """

    @pytest.mark.asyncio
    async def test_skipped_message_not_stored(self):
        """Skipped messages should not call store_pending_response."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        mock_deps = MagicMock()
        mock_deps.user = mock_user

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True
        mock_skip.last_was_skipped = True

        mock_store = AsyncMock()

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler.store_pending_response", new=mock_store):

            handler = MessageHandler(skip_decision=mock_skip)
            await handler.handle(user_id, "Hello")

            # store_pending_response should NOT have been called
            mock_store.assert_not_called()


class TestHandlerWithDefaultSkip:
    """Tests for handler creating default SkipDecision."""

    def test_handler_creates_skip_decision_if_none(self):
        """Handler should create SkipDecision if none provided."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        handler = MessageHandler()

        assert handler.skip_decision is not None
        assert isinstance(handler.skip_decision, SkipDecision)

    def test_handler_uses_provided_skip_decision(self):
        """Handler should use provided SkipDecision."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        custom_skip = SkipDecision()
        handler = MessageHandler(skip_decision=custom_skip)

        assert handler.skip_decision is custom_skip
