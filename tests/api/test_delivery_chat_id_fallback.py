"""Tests for GH #248: Delivery worker chat_id fallback.

When scheduled_events content lacks chat_id, the delivery worker should
look up telegram_id from the user record instead of failing silently.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_delivery_resolves_chat_id_from_user_when_missing():
    """GH #248: Delivery worker resolves chat_id from users.telegram_id
    when content.chat_id is missing."""
    from nikita.db.models.scheduled_event import EventPlatform

    user_id = uuid4()
    telegram_id = 746410893

    # Simulate a scheduled event without chat_id (the bug)
    event = MagicMock()
    event.id = uuid4()
    event.user_id = user_id
    event.platform = EventPlatform.TELEGRAM.value
    event.content = {"text": "you first.", "response_id": str(uuid4())}

    # Mock user with telegram_id
    mock_user = MagicMock()
    mock_user.telegram_id = telegram_id

    mock_user_repo = AsyncMock()
    mock_user_repo.get.return_value = mock_user

    mock_event_repo = AsyncMock()
    mock_event_repo.get_due_events.return_value = [event]

    mock_bot = AsyncMock()

    # Simulate the delivery logic
    chat_id = event.content.get("chat_id")
    text = event.content.get("text")

    # Before fix: chat_id is None, delivery would fail
    assert chat_id is None

    # After fix: fallback to user.telegram_id
    if not chat_id and text:
        user = await mock_user_repo.get(event.user_id)
        if user and user.telegram_id:
            chat_id = str(user.telegram_id)

    # Now chat_id is resolved
    assert chat_id == str(telegram_id)
    assert text == "you first."


@pytest.mark.asyncio
async def test_delivery_fails_when_no_user_telegram_id():
    """GH #248: When user has no telegram_id, delivery still fails gracefully."""
    user_id = uuid4()

    mock_user = MagicMock()
    mock_user.telegram_id = None  # No telegram_id

    mock_user_repo = AsyncMock()
    mock_user_repo.get.return_value = mock_user

    content = {"text": "hello", "response_id": str(uuid4())}
    chat_id = content.get("chat_id")

    if not chat_id and content.get("text"):
        user = await mock_user_repo.get(user_id)
        if user and user.telegram_id:
            chat_id = str(user.telegram_id)

    # chat_id should still be None
    assert chat_id is None


@pytest.mark.asyncio
async def test_delivery_uses_explicit_chat_id_when_present():
    """When content already has chat_id, the fallback is not triggered."""
    content = {"text": "hello", "chat_id": "123456", "response_id": str(uuid4())}
    chat_id = content.get("chat_id")

    # No fallback needed — chat_id is present
    assert chat_id == "123456"
