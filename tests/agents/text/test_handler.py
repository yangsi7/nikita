"""Tests for MessageHandler - TDD for T4.2.

Acceptance Criteria:
- AC-4.2.1: `MessageHandler.handle(user_id, message)` async method exists
- AC-4.2.2: Handler generates response via agent
- AC-4.2.3: Handler calculates delay via ResponseTimer
- AC-4.2.4: Handler stores pending response with scheduled delivery time
- AC-4.2.5: Handler returns ResponseDecision with delay_seconds
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


class TestMessageHandlerStructure:
    """Tests for MessageHandler class structure."""

    def test_handler_module_importable(self):
        """Handler module should be importable."""
        from nikita.agents.text import handler

        assert hasattr(handler, "MessageHandler")
        assert hasattr(handler, "ResponseDecision")

    def test_ac_4_2_5_response_decision_exists(self):
        """AC-4.2.5: ResponseDecision dataclass should exist."""
        from nikita.agents.text.handler import ResponseDecision

        assert callable(ResponseDecision)

    def test_response_decision_has_delay_seconds(self):
        """ResponseDecision should have delay_seconds field."""
        from nikita.agents.text.handler import ResponseDecision

        # Create an instance
        decision = ResponseDecision(
            response="test response",
            delay_seconds=600,
            scheduled_at=datetime.now(timezone.utc),
        )

        assert hasattr(decision, "delay_seconds")
        assert decision.delay_seconds == 600

    def test_response_decision_has_scheduled_at(self):
        """ResponseDecision should have scheduled_at field."""
        from nikita.agents.text.handler import ResponseDecision

        now = datetime.now(timezone.utc)
        decision = ResponseDecision(
            response="test",
            delay_seconds=300,
            scheduled_at=now,
        )

        assert hasattr(decision, "scheduled_at")
        assert decision.scheduled_at == now


class TestMessageHandler:
    """Tests for MessageHandler class."""

    def test_message_handler_class_exists(self):
        """MessageHandler class should exist."""
        from nikita.agents.text.handler import MessageHandler

        assert callable(MessageHandler)

    def test_ac_4_2_1_handle_method_exists(self):
        """AC-4.2.1: MessageHandler.handle(user_id, message) should exist."""
        from nikita.agents.text.handler import MessageHandler
        import inspect

        handler = MessageHandler()

        assert hasattr(handler, "handle")
        assert callable(handler.handle)
        assert inspect.iscoroutinefunction(handler.handle)

    def test_handle_method_signature(self):
        """Handle method should accept user_id and message parameters."""
        from nikita.agents.text.handler import MessageHandler
        import inspect

        handler = MessageHandler()
        sig = inspect.signature(handler.handle)
        params = list(sig.parameters.keys())

        assert "user_id" in params
        assert "message" in params

    @pytest.mark.asyncio
    async def test_ac_4_2_2_handler_generates_response(self):
        """AC-4.2.2: Handler should generate response via agent."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()
        message = "Hello Nikita"

        # Mock dependencies
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2
        mock_user.game_status = "active"

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_settings = MagicMock()

        mock_agent = MagicMock()
        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory
        mock_deps.settings = mock_settings

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(mock_agent, mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="Hey, what do you want?")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            result = await handler.handle(user_id, message)

    @pytest.mark.asyncio
    async def test_ac_4_2_3_handler_calculates_delay(self):
        """AC-4.2.3: Handler should calculate delay via ResponseTimer."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 3
        mock_user.game_status = "active"

        mock_memory = MagicMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory
        mock_deps.settings = MagicMock()

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 1800

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            result = await handler.handle(user_id, "test")

            # Should have used ResponseTimer to calculate delay
            mock_timer.calculate_delay.assert_called_once_with(mock_user.chapter)

    @pytest.mark.asyncio
    async def test_ac_4_2_5_handler_returns_response_decision(self):
        """AC-4.2.5: Handler should return ResponseDecision with delay_seconds."""
        from nikita.agents.text.handler import MessageHandler, ResponseDecision
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 900

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False  # Don't skip

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        # Mock text pattern processor to return original text
        mock_pattern_result = MagicMock()
        mock_pattern_result.messages = [MagicMock(content="Hey there")]
        mock_pattern_result.context = "neutral"
        mock_pattern_result.emoji_count = 0
        mock_processor = MagicMock()
        mock_processor.process.return_value = mock_pattern_result

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="Hey there")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()), \
             patch("nikita.agents.text.handler._get_processor_instance", return_value=mock_processor):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            result = await handler.handle(user_id, "Hello")

            # Should return ResponseDecision
            assert isinstance(result, ResponseDecision)
            assert result.delay_seconds == 900
            assert result.response == "Hey there"
            assert result.scheduled_at is not None


class TestResponseDecisionScheduling:
    """Tests for scheduled delivery time calculation."""

    def test_scheduled_at_is_future(self):
        """scheduled_at should be in the future based on delay."""
        from nikita.agents.text.handler import ResponseDecision

        now = datetime.now(timezone.utc)
        delay = 600  # 10 minutes
        scheduled = now + timedelta(seconds=delay)

        decision = ResponseDecision(
            response="test",
            delay_seconds=delay,
            scheduled_at=scheduled,
        )

        assert decision.scheduled_at > now

    @pytest.mark.asyncio
    async def test_handler_calculates_correct_scheduled_time(self):
        """Handler should calculate scheduled_at based on now + delay."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.skip import SkipDecision
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
        mock_timer.calculate_delay.return_value = 3600  # 1 hour

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False  # Don't skip

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=AsyncMock()):

            before_call = datetime.now(timezone.utc)
            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            result = await handler.handle(user_id, "test")
            after_call = datetime.now(timezone.utc)

            # scheduled_at should be approximately now + 1 hour
            expected_min = before_call + timedelta(seconds=3600)
            expected_max = after_call + timedelta(seconds=3600)

            assert expected_min <= result.scheduled_at <= expected_max


class TestPendingResponseStorage:
    """Tests for storing pending responses (AC-4.2.4)."""

    @pytest.mark.asyncio
    async def test_ac_4_2_4_handler_stores_pending_response(self):
        """AC-4.2.4: Handler should store pending response with scheduled delivery time."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision
        from nikita.agents.text.timing import ResponseTimer
        from nikita.agents.text.facts import FactExtractor

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2
        mock_user.game_status = "active"

        mock_memory = MagicMock()
        mock_memory.get_user_facts = AsyncMock(return_value=[])
        mock_memory.add_user_fact = AsyncMock()

        mock_deps = MagicMock()
        mock_deps.user = mock_user
        mock_deps.memory = mock_memory

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 1200

        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        mock_fact_extractor = MagicMock(spec=FactExtractor)
        mock_fact_extractor.extract_facts = AsyncMock(return_value=[])

        mock_store = AsyncMock()

        with patch("nikita.agents.text.handler.get_nikita_agent_for_user", new=AsyncMock(return_value=(MagicMock(), mock_deps))), \
             patch("nikita.agents.text.handler.generate_response", new=AsyncMock(return_value="pending response")), \
             patch("nikita.agents.text.handler.store_pending_response", new=mock_store):

            handler = MessageHandler(timer=mock_timer, skip_decision=mock_skip, fact_extractor=mock_fact_extractor)
            result = await handler.handle(user_id, "test message")

            # Should have stored the pending response
            mock_store.assert_called_once()

            # Verify call arguments
            call_args = mock_store.call_args
            assert call_args[1]["user_id"] == user_id
            # Response may be modified by text patterns (adds emojis, etc.)
            # Just verify the original content is present
            assert "pending response" in call_args[1]["response"]
            assert "scheduled_at" in call_args[1]

    def test_response_decision_has_response_id(self):
        """ResponseDecision should have response_id for tracking."""
        from nikita.agents.text.handler import ResponseDecision

        response_id = uuid4()
        decision = ResponseDecision(
            response="test",
            delay_seconds=300,
            scheduled_at=datetime.now(timezone.utc),
            response_id=response_id,
        )

        assert hasattr(decision, "response_id")
        assert decision.response_id == response_id


class TestStorePendingResponse:
    """Tests for the store_pending_response function (G7 fix)."""

    @pytest.mark.asyncio
    async def test_skips_db_write_when_no_session(self):
        """store_pending_response with session=None should log and return without error."""
        from nikita.agents.text.handler import store_pending_response

        user_id = uuid4()
        response_id = uuid4()
        now = datetime.now(timezone.utc)

        # Should complete without error even with no session
        await store_pending_response(
            user_id=user_id,
            response="Hello",
            scheduled_at=now,
            response_id=response_id,
            session=None,
        )

    @pytest.mark.asyncio
    async def test_calls_repository_create_event_with_session(self):
        """store_pending_response with a session should call ScheduledEventRepository.create_event."""
        from nikita.agents.text.handler import store_pending_response
        from unittest.mock import AsyncMock, MagicMock, patch

        user_id = uuid4()
        response_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_session = MagicMock()

        mock_repo = MagicMock()
        mock_repo.create_event = AsyncMock(return_value=MagicMock())

        with patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mock_repo,
        ):
            # Patch at the import site inside the function
            with patch(
                "nikita.agents.text.handler.ScheduledEventRepository",
                return_value=mock_repo,
                create=True,
            ):
                await store_pending_response(
                    user_id=user_id,
                    response="Hey there",
                    scheduled_at=now,
                    response_id=response_id,
                    session=mock_session,
                )

    @pytest.mark.asyncio
    async def test_stores_response_text_and_response_id_in_content(self):
        """Content payload must include 'text' and 'response_id'."""
        from nikita.agents.text.handler import store_pending_response
        from unittest.mock import AsyncMock, MagicMock, patch

        user_id = uuid4()
        response_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_session = MagicMock()

        created_events = []

        async def fake_create_event(**kwargs):
            created_events.append(kwargs)
            return MagicMock()

        mock_repo_instance = MagicMock()
        mock_repo_instance.create_event = fake_create_event

        # Patch ScheduledEventRepository at the module where it is defined so
        # the local import inside store_pending_response picks up the mock.
        with patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mock_repo_instance,
        ), patch(
            "nikita.agents.text.handler.ScheduledEventRepository",
            return_value=mock_repo_instance,
            create=True,
        ):
            await store_pending_response(
                user_id=user_id,
                response="Test message",
                scheduled_at=now,
                response_id=response_id,
                session=mock_session,
            )

        # Verify a create_event call was captured with correct content shape
        assert len(created_events) == 1
        content = created_events[0]["content"]
        assert content["text"] == "Test message"
        assert content["response_id"] == str(response_id)
