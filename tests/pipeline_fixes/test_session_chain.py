"""Tests for session propagation through handler chain (Spec 038 T2.3).

Verifies that session is passed from TelegramMessageHandler through
TextAgentHandler to build_system_prompt.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_session_flows_through_handler():
    """Verify session is passed from MessageHandler to deps.

    AC-2.3.2: Session should be passed to NikitaDeps during initialization.
    """
    from nikita.agents.text.handler import MessageHandler

    # Create mock session
    session = AsyncMock()

    # Create handler with mocks
    handler = MessageHandler()

    # Mock get_nikita_agent_for_user to capture deps
    captured_deps = []

    async def mock_get_agent(user_id):
        agent = MagicMock()
        user = MagicMock()
        user.game_status = "active"
        user.chapter = 1
        settings = MagicMock()

        from nikita.agents.text.deps import NikitaDeps

        deps = NikitaDeps(memory=None, user=user, settings=settings)
        captured_deps.append(deps)
        return agent, deps

    # Mock generate_response to return immediately
    with patch(
        "nikita.agents.text.handler.get_nikita_agent_for_user",
        side_effect=mock_get_agent,
    ):
        with patch(
            "nikita.agents.text.handler.generate_response",
            new_callable=AsyncMock,
            return_value="Response",
        ):
            # Call handle with session
            result = await handler.handle(
                user_id=uuid4(),
                message="Hello",
                conversation_messages=[],
                conversation_id=uuid4(),
                session=session,
            )

            # Verify session was set on deps
            assert len(captured_deps) == 1
            assert captured_deps[0].session is session


@pytest.mark.asyncio
async def test_no_new_sessions_created():
    """Verify no new sessions are created when session is provided.

    AC-2.3.3: When session is propagated, no new get_session_maker() calls.
    """
    from nikita.agents.text.agent import build_system_prompt

    user = MagicMock()
    user.id = uuid4()
    session = AsyncMock()
    session.commit = AsyncMock()

    # Track get_session_maker calls
    session_maker_calls = []

    def track_session_maker():
        session_maker_calls.append(1)
        return MagicMock()

    with patch(
        "nikita.context.template_generator.generate_system_prompt",
        new_callable=AsyncMock,
        return_value="Test prompt",
    ):
        with patch(
            "nikita.db.database.get_session_maker",
            side_effect=track_session_maker,
        ):
            await build_system_prompt(
                memory=None,
                user=user,
                user_message="Hello",
                conversation_id=uuid4(),
                session=session,  # Provided session
            )

            # No calls to get_session_maker when session provided
            assert len(session_maker_calls) == 0


@pytest.mark.asyncio
async def test_session_propagates_to_build_prompt():
    """Verify session propagates all the way to build_system_prompt.

    This tests that when deps.session is set, it gets passed to build_system_prompt.
    """
    from nikita.agents.text.agent import build_system_prompt

    session = AsyncMock()
    session.commit = AsyncMock()

    # Track what session generate_system_prompt receives
    received_sessions = []

    async def mock_generate_prompt(sess, user_id, **kwargs):
        received_sessions.append(sess)
        return "Test prompt"

    with patch(
        "nikita.context.template_generator.generate_system_prompt",
        side_effect=mock_generate_prompt,
    ):
        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_maker:
            user = MagicMock()
            user.id = uuid4()
            user.chapter = 1

            # Call build_system_prompt directly with session
            result = await build_system_prompt(
                memory=None,
                user=user,
                user_message="Hello",
                conversation_id=uuid4(),
                session=session,
            )

            # Session should have been passed to generate_system_prompt
            assert len(received_sessions) == 1
            assert received_sessions[0] is session
