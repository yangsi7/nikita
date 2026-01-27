"""Tests for ViceProcessingStage message pairing logic.

Spec 037 US-5: Vice Processing Fix - Message Pairing Edge Cases.
Fixes H-4: Non-alternating messages handled correctly.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.vice_processing import ViceProcessingStage


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def pipeline_context():
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


class TestMessagePairing:
    """Tests for _extract_exchanges() message pairing logic.

    AC-T4.1: 8 tests for message pairing edge cases.
    """

    def test_alternating_messages(self, mock_session):
        """Test standard alternating user→assistant pattern."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm good!"},
        ]

        exchanges = stage._extract_exchanges(messages)

        assert len(exchanges) == 2
        assert exchanges[0] == ("Hello", "Hi there!")
        assert exchanges[1] == ("How are you?", "I'm good!")

    def test_non_alternating_multiple_user_messages(self, mock_session):
        """AC-T4.1.2: Handle multiple consecutive user messages."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Response to both"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # First user message paired with assistant
        assert len(exchanges) == 1
        assert exchanges[0] == ("First message", "Response to both")

    def test_nikita_only_messages_skipped(self, mock_session):
        """AC-T4.1.3: Handle nikita-only message sequences."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "assistant", "content": "Hello!"},
            {"role": "assistant", "content": "You there?"},
            {"role": "user", "content": "Yes!"},
            {"role": "assistant", "content": "Great!"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # Only the user→assistant pair should be extracted
        assert len(exchanges) == 1
        assert exchanges[0] == ("Yes!", "Great!")

    def test_single_message_conversation(self, mock_session):
        """AC-T4.1.6: Handle single-message conversations."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "Hello?"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # No pair found
        assert len(exchanges) == 0

    def test_role_variants_nikita_and_assistant(self, mock_session):
        """AC-T2.8.4: Both 'assistant' and 'nikita' roles recognized."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "Test 1"},
            {"role": "nikita", "content": "Response 1"},
            {"role": "user", "content": "Test 2"},
            {"role": "assistant", "content": "Response 2"},
        ]

        exchanges = stage._extract_exchanges(messages)

        assert len(exchanges) == 2
        assert exchanges[0] == ("Test 1", "Response 1")
        assert exchanges[1] == ("Test 2", "Response 2")

    def test_empty_content_messages_skipped(self, mock_session):
        """AC-T4.1.5: Handle empty content messages."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},  # Empty
            {"role": "assistant", "content": "Real response"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # Empty assistant message skipped, paired with next
        assert len(exchanges) == 1
        assert exchanges[0] == ("Hello", "Real response")

    def test_whitespace_only_content_skipped(self, mock_session):
        """Test whitespace-only messages are skipped."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user", "content": "   "},  # Whitespace only
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Real message"},
            {"role": "assistant", "content": "Real response"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # First user message skipped (whitespace only)
        assert len(exchanges) == 1
        assert exchanges[0] == ("Real message", "Real response")

    def test_missing_role_field(self, mock_session):
        """Test messages without role field."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"content": "No role"},
            {"role": "user", "content": "Valid user"},
            {"role": "assistant", "content": "Valid response"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # Message without role is skipped
        assert len(exchanges) == 1
        assert exchanges[0] == ("Valid user", "Valid response")

    def test_missing_content_field(self, mock_session):
        """Test messages without content field."""
        stage = ViceProcessingStage(mock_session)
        messages = [
            {"role": "user"},  # No content
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Valid"},
            {"role": "assistant", "content": "Response 2"},
        ]

        exchanges = stage._extract_exchanges(messages)

        # First user message skipped (no content = empty string = falsy)
        assert len(exchanges) == 1
        assert exchanges[0] == ("Valid", "Response 2")


class TestViceProcessingStage:
    """Tests for ViceProcessingStage execution."""

    @pytest.mark.asyncio
    async def test_stage_properties(self, mock_session):
        """AC-T2.8.1, AC-T2.8.2: Verify stage properties."""
        stage = ViceProcessingStage(mock_session)

        assert stage.name == "vice_processing"
        assert stage.is_critical is False
        assert stage.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_context_manager_used(self, mock_session, pipeline_context):
        """AC-T1.4.1: Verify context manager pattern used."""
        stage = ViceProcessingStage(mock_session)

        mock_conv = MagicMock()
        mock_conv.id = pipeline_context.conversation_id
        mock_conv.user_id = pipeline_context.user_id
        mock_conv.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        mock_vice_service = AsyncMock()
        mock_vice_service.__aenter__ = AsyncMock(return_value=mock_vice_service)
        mock_vice_service.__aexit__ = AsyncMock(return_value=False)
        mock_vice_service.process_conversation = AsyncMock(
            return_value={"signals_detected": 1}
        )

        # Patch at the source module where ViceService is imported
        with patch(
            "nikita.engine.vice.service.ViceService",
            return_value=mock_vice_service,
        ):
            result = await stage.execute(pipeline_context, mock_conv)

        assert result.success is True
        assert result.data == 1
        mock_vice_service.__aenter__.assert_called_once()
        mock_vice_service.__aexit__.assert_called_once()
