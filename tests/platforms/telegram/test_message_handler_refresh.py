"""Tests for message handler conversation refresh fix (Spec 038 T1.1).

Verifies that conversation.messages is refreshed after append_message()
so the agent receives the latest message list including the just-appended
user message.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.platforms.telegram.message_handler import MessageHandler


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for MessageHandler."""
    user_repo = AsyncMock()
    conversation_repo = AsyncMock()
    text_agent_handler = AsyncMock()
    response_delivery = AsyncMock()
    bot = AsyncMock()
    rate_limiter = None
    scoring_service = AsyncMock()
    profile_repo = AsyncMock()
    backstory_repo = AsyncMock()

    # Configure default user
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    user.game_status = "active"
    user.relationship_score = 50
    user.metrics = MagicMock()
    user.metrics.intimacy = 50
    user.metrics.passion = 50
    user.metrics.trust = 50
    user.metrics.secureness = 50
    user.engagement_state = None
    user.last_interaction_at = None
    user_repo.get_by_telegram_id.return_value = user
    user_repo.get.return_value = user

    # Configure onboarding complete
    profile_repo.get_by_user_id.return_value = MagicMock()  # Has profile
    backstory_repo.get_by_user_id.return_value = MagicMock()  # Has backstory

    return {
        "user_repo": user_repo,
        "conversation_repo": conversation_repo,
        "text_agent_handler": text_agent_handler,
        "response_delivery": response_delivery,
        "bot": bot,
        "rate_limiter": rate_limiter,
        "scoring_service": scoring_service,
        "profile_repo": profile_repo,
        "backstory_repo": backstory_repo,
        "user": user,
    }


@pytest.mark.asyncio
async def test_messages_refreshed_after_append(mock_dependencies):
    """Verify conversation.messages is refreshed from DB after append_message.

    AC-1.1.1: After append_message(), the conversation object should be
    refreshed so messages includes the just-appended user message.
    """
    deps = mock_dependencies
    conversation_repo = deps["conversation_repo"]

    # Create a conversation mock that tracks refresh calls
    conversation = MagicMock()
    conversation.id = uuid4()
    conversation.status = "active"
    initial_messages = [{"role": "user", "content": "old message"}]
    conversation.messages = initial_messages

    # Set up the session mock on the conversation_repo
    session_mock = AsyncMock()
    conversation_repo.session = session_mock

    # After refresh, messages should include new message
    async def fake_refresh(obj):
        obj.messages = [
            {"role": "user", "content": "old message"},
            {"role": "user", "content": "test message"},
        ]

    session_mock.refresh = fake_refresh
    conversation_repo.get_active_conversation.return_value = conversation

    # Configure agent handler to return a response
    decision_mock = MagicMock()
    decision_mock.should_respond = True
    decision_mock.response = "Hi there!"
    decision_mock.delay_seconds = 0
    deps["text_agent_handler"].handle.return_value = decision_mock

    # Create the handler
    handler = MessageHandler(
        user_repository=deps["user_repo"],
        conversation_repository=conversation_repo,
        text_agent_handler=deps["text_agent_handler"],
        response_delivery=deps["response_delivery"],
        bot=deps["bot"],
        rate_limiter=deps["rate_limiter"],
        scoring_service=deps["scoring_service"],
        profile_repository=deps["profile_repo"],
        backstory_repository=deps["backstory_repo"],
    )

    # Create a mock telegram message
    message = MagicMock()
    message.from_.id = 12345
    message.text = "test message"
    message.chat.id = 12345

    # Call handle
    await handler.handle(message)

    # Verify append_message was called (at least once for user message)
    assert conversation_repo.append_message.called

    # Verify session.refresh was called on conversation
    # The refresh should have been called after append_message
    # We verify by checking that the handler got messages with the new content
    call_args = deps["text_agent_handler"].handle.call_args
    passed_messages = call_args.kwargs.get("conversation_messages")

    # After refresh, messages should include the new message
    assert passed_messages is not None
    assert len(passed_messages) == 2
    assert passed_messages[-1]["content"] == "test message"


@pytest.mark.asyncio
async def test_agent_receives_latest_messages(mock_dependencies):
    """Verify agent receives message list including just-appended user message.

    AC-1.1.3: The agent should receive fresh message list, not stale snapshot.
    """
    deps = mock_dependencies
    conversation_repo = deps["conversation_repo"]

    # Create conversation with initial messages
    conversation = MagicMock()
    conversation.id = uuid4()
    conversation.status = "active"
    conversation.messages = []

    # Set up session mock
    session_mock = AsyncMock()
    conversation_repo.session = session_mock

    # Track what messages the agent receives
    received_messages = []

    async def capture_messages(*args, **kwargs):
        received_messages.append(kwargs.get("conversation_messages", []))
        decision = MagicMock()
        decision.should_respond = True
        decision.response = "Response"
        decision.delay_seconds = 0
        return decision

    deps["text_agent_handler"].handle.side_effect = capture_messages

    # After refresh, add the user message
    async def fake_refresh(obj):
        obj.messages = [{"role": "user", "content": "Hello Nikita!"}]

    session_mock.refresh = fake_refresh
    conversation_repo.get_active_conversation.return_value = conversation

    handler = MessageHandler(
        user_repository=deps["user_repo"],
        conversation_repository=conversation_repo,
        text_agent_handler=deps["text_agent_handler"],
        response_delivery=deps["response_delivery"],
        bot=deps["bot"],
        rate_limiter=deps["rate_limiter"],
        scoring_service=deps["scoring_service"],
        profile_repository=deps["profile_repo"],
        backstory_repository=deps["backstory_repo"],
    )

    message = MagicMock()
    message.from_.id = 12345
    message.text = "Hello Nikita!"
    message.chat.id = 12345

    await handler.handle(message)

    # Agent should have received the message that was appended
    assert len(received_messages) == 1
    agent_messages = received_messages[0]
    assert len(agent_messages) == 1
    assert agent_messages[0]["content"] == "Hello Nikita!"
