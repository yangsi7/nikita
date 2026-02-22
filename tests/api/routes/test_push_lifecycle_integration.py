"""Integration tests for push subscription lifecycle.

Tests the full subscribe/unsubscribe cycle via route handlers with
mocked DB session.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from nikita.api.routes.portal import (
    PushSubscriptionRequest,
    subscribe_push,
    unsubscribe_push,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """Create mock async session that tracks SQL executed."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPushSubscriptionLifecycle:
    """Integration tests for the push subscription full lifecycle."""

    async def test_subscribe_then_unsubscribe_lifecycle(self, mock_session, user_id):
        """POST subscribe -> verify stored -> DELETE unsubscribe -> verify removed."""
        endpoint = "https://fcm.googleapis.com/fcm/send/test-endpoint-123"

        # Step 1: Subscribe
        request = PushSubscriptionRequest(
            endpoint=endpoint,
            keys={"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        )
        subscribe_result = await subscribe_push(
            user_id=user_id,
            session=mock_session,
            request=request,
        )
        assert subscribe_result.success is True
        assert mock_session.execute.call_count == 1
        assert mock_session.commit.call_count == 1

        # Verify SQL contains INSERT
        subscribe_sql = str(mock_session.execute.call_args[0][0])
        assert "INSERT" in subscribe_sql

        mock_session.execute.reset_mock()
        mock_session.commit.reset_mock()

        # Step 2: Unsubscribe
        unsubscribe_result = await unsubscribe_push(
            user_id=user_id,
            session=mock_session,
            endpoint=endpoint,
        )
        assert unsubscribe_result.success is True
        assert mock_session.execute.call_count == 1
        assert mock_session.commit.call_count == 1

        # Verify SQL contains DELETE
        unsubscribe_sql = str(mock_session.execute.call_args[0][0])
        assert "DELETE" in unsubscribe_sql

    async def test_subscribe_upsert_same_endpoint(self, mock_session, user_id):
        """POST twice with same endpoint, different keys -> upsert (ON CONFLICT)."""
        endpoint = "https://fcm.googleapis.com/fcm/send/same-endpoint"

        # First subscribe
        request1 = PushSubscriptionRequest(
            endpoint=endpoint,
            keys={"p256dh": "key_v1", "auth": "auth_v1"},
        )
        result1 = await subscribe_push(
            user_id=user_id,
            session=mock_session,
            request=request1,
        )
        assert result1.success is True

        # Second subscribe with same endpoint, different keys
        request2 = PushSubscriptionRequest(
            endpoint=endpoint,
            keys={"p256dh": "key_v2", "auth": "auth_v2"},
        )
        result2 = await subscribe_push(
            user_id=user_id,
            session=mock_session,
            request=request2,
        )
        assert result2.success is True

        # Both calls should use ON CONFLICT upsert
        for call in mock_session.execute.call_args_list:
            sql_text = str(call[0][0])
            assert "ON CONFLICT" in sql_text

    async def test_subscribe_requires_valid_payload(self, mock_session, user_id):
        """Subscribe with missing keys should still work (empty string defaults)."""
        request = PushSubscriptionRequest(
            endpoint="https://fcm.googleapis.com/fcm/send/minimal",
            keys={},
        )
        result = await subscribe_push(
            user_id=user_id,
            session=mock_session,
            request=request,
        )
        assert result.success is True

        # Verify empty string defaults for missing keys
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["p256dh"] == ""
        assert params["auth"] == ""
