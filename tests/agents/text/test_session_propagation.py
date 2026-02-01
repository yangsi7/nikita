"""Tests for session propagation in build_system_prompt (Spec 038 T2.2).

Verifies that build_system_prompt uses the provided session instead of
creating a new one, preventing FK constraint violations.

NOTE (2026-02): Updated to patch context_engine.router.generate_text_prompt
since context_engine v2 is now the production default.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_build_system_prompt_uses_provided_session():
    """Verify build_system_prompt uses provided session.

    AC-2.2.2: When session provided, use it directly without creating new.
    """
    from nikita.agents.text.agent import build_system_prompt

    # Create mocks
    memory = None
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    session = AsyncMock()
    session.commit = AsyncMock()
    conversation_id = uuid4()

    # Mock the context engine router's generate_text_prompt
    with patch(
        "nikita.context_engine.router.generate_text_prompt",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = "Test prompt"

        # Mock get_session_maker to track if it's called
        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session_maker:
            result = await build_system_prompt(
                memory=memory,
                user=user,
                user_message="Hello",
                conversation_id=conversation_id,
                session=session,
            )

            # When session is provided, get_session_maker should NOT be called
            mock_get_session_maker.assert_not_called()

            # generate_text_prompt should be called with the provided session
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[0][0] is session  # First arg is session


@pytest.mark.asyncio
async def test_build_system_prompt_creates_session_when_none():
    """Verify fallback creates session for backwards compatibility.

    AC-2.2.3: When session=None, create new session (backwards compat).
    """
    from nikita.agents.text.agent import build_system_prompt

    memory = None
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    conversation_id = uuid4()

    # Mock session factory
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session_maker = MagicMock()
    mock_session_maker.return_value.__aenter__ = AsyncMock(
        return_value=mock_session
    )
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "nikita.context_engine.router.generate_text_prompt",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = "Test prompt"

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mock_session_maker,
        ):
            result = await build_system_prompt(
                memory=memory,
                user=user,
                user_message="Hello",
                conversation_id=conversation_id,
                session=None,  # No session provided
            )

            # generate_text_prompt should be called with created session
            mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_logged_in_same_transaction():
    """Verify prompt is logged in same transaction as conversation.

    AC-2.2.4: When session is propagated, prompt logging happens
    in the same transaction (same session), preventing FK violations.
    """
    from nikita.agents.text.agent import build_system_prompt

    memory = None
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    session = AsyncMock()
    conversation_id = uuid4()

    # Track commit calls on the session
    session.commit = AsyncMock()

    with patch(
        "nikita.context_engine.router.generate_text_prompt",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = "Test prompt"

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session_maker:
            result = await build_system_prompt(
                memory=memory,
                user=user,
                user_message="Hello",
                conversation_id=conversation_id,
                session=session,
            )

            # Session commit should be called to persist the prompt log
            session.commit.assert_called()


@pytest.mark.asyncio
async def test_no_fk_violation_with_session():
    """Test that using propagated session prevents FK violations.

    This tests the actual behavior where prompt logging would fail
    if using a different session than the conversation.
    """
    from nikita.agents.text.agent import build_system_prompt

    memory = None
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    conversation_id = uuid4()

    # Create a session that tracks all operations
    session = AsyncMock()
    operations_log = []

    async def track_commit():
        operations_log.append("commit")

    session.commit = track_commit

    with patch(
        "nikita.context_engine.router.generate_text_prompt",
        new_callable=AsyncMock,
    ) as mock_generate:
        # Simulate generate_text_prompt adding to session
        async def generate_and_add(sess, user, user_message, conversation_id):
            operations_log.append(f"generate with session {id(sess)}")
            return "Test prompt"

        mock_generate.side_effect = generate_and_add

        with patch("nikita.db.database.get_session_maker"):
            result = await build_system_prompt(
                memory=memory,
                user=user,
                user_message="Hello",
                conversation_id=conversation_id,
                session=session,
            )

            # Should have used the same session
            assert len(operations_log) >= 1
            assert f"generate with session {id(session)}" in operations_log[0]
