"""Tests for push notification subscription endpoints (Wave H1)."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4


@pytest.mark.asyncio
class TestPushSubscribe:
    """Test push subscription API endpoints."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    async def test_subscribe_stores_subscription(self, mock_session, mock_user_id):
        """POST /push-subscribe stores subscription data."""
        from nikita.api.routes.portal import subscribe_push, PushSubscriptionRequest

        request = PushSubscriptionRequest(
            endpoint="https://fcm.googleapis.com/fcm/send/test",
            keys={"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        )

        result = await subscribe_push(
            user_id=mock_user_id,
            session=mock_session,
            request=request,
        )

        assert result.success is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_unsubscribe_removes_subscription(self, mock_session, mock_user_id):
        """DELETE /push-subscribe removes subscription."""
        from nikita.api.routes.portal import unsubscribe_push

        result = await unsubscribe_push(
            user_id=mock_user_id,
            session=mock_session,
            endpoint="https://fcm.googleapis.com/fcm/send/test",
        )

        assert result.success is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_subscribe_upserts_on_conflict(self, mock_session, mock_user_id):
        """Subscribing with same endpoint updates keys."""
        from nikita.api.routes.portal import subscribe_push, PushSubscriptionRequest

        request = PushSubscriptionRequest(
            endpoint="https://fcm.googleapis.com/fcm/send/test",
            keys={"p256dh": "updated_key", "auth": "updated_auth"},
        )

        result = await subscribe_push(
            user_id=mock_user_id,
            session=mock_session,
            request=request,
        )

        assert result.success is True
        # Verify the SQL contains ON CONFLICT ... DO UPDATE
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "ON CONFLICT" in sql_text
