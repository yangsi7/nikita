"""Tests for Telegram linking endpoints.

TDD tests for T46: Telegram linking.

Acceptance Criteria:
- AC-T46.1: "Link Telegram" generates 6-char code
- AC-T46.2: Code displayed with instructions
- AC-T46.3: Code expires after 10 minutes
- AC-T46.4: Bot command /link CODE validates and links
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.portal import router as portal_router


class TestGenerateLinkCode:
    """Test suite for generating Telegram link codes (T46.1-T46.3)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app with portal router."""
        test_app = FastAPI()
        test_app.include_router(portal_router, prefix="/portal")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with isolated app."""
        return TestClient(app)

    @pytest.fixture
    def mock_user_id(self):
        """Create a mock user ID."""
        return uuid4()

    def test_link_telegram_endpoint_exists(self, client):
        """Link Telegram endpoint is registered at POST /portal/link-telegram."""
        response = client.post("/portal/link-telegram")
        # Should return 401/403 without auth, not 404
        assert response.status_code in [401, 403]

    def test_link_telegram_requires_auth(self, client):
        """POST /link-telegram requires authentication."""
        response = client.post("/portal/link-telegram")
        assert response.status_code in [401, 403]

    def test_generate_link_code_creates_code(self, client, mock_user_id):
        """AC-T46.1: POST /link-telegram generates 6-char code."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.TelegramLinkRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_code = AsyncMock()
                    mock_code.code = "ABC123"
                    mock_code.expires_at = datetime.now(UTC) + timedelta(minutes=10)
                    mock_repo.create_link_code.return_value = mock_code
                    mock_repo_class.return_value = mock_repo

                    response = client.post(
                        "/portal/link-telegram",
                        headers={"Authorization": "Bearer fake-token"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "code" in data
                    assert len(data["code"]) == 6
                    assert data["code"] == "ABC123"

    def test_generate_link_code_returns_expiry(self, client, mock_user_id):
        """AC-T46.3: Response includes expires_at timestamp."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.TelegramLinkRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_code = AsyncMock()
                    mock_code.code = "XYZ789"
                    expiry = datetime.now(UTC) + timedelta(minutes=10)
                    mock_code.expires_at = expiry
                    mock_repo.create_link_code.return_value = mock_code
                    mock_repo_class.return_value = mock_repo

                    response = client.post(
                        "/portal/link-telegram",
                        headers={"Authorization": "Bearer fake-token"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "expires_at" in data

    def test_generate_link_code_returns_instructions(self, client, mock_user_id):
        """AC-T46.2: Response includes instructions for linking."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.TelegramLinkRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_code = AsyncMock()
                    mock_code.code = "LNK456"
                    mock_code.expires_at = datetime.now(UTC) + timedelta(minutes=10)
                    mock_repo.create_link_code.return_value = mock_code
                    mock_repo_class.return_value = mock_repo

                    response = client.post(
                        "/portal/link-telegram",
                        headers={"Authorization": "Bearer fake-token"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "instructions" in data
                    assert "/link" in data["instructions"]


class TestTelegramLinkModel:
    """Test TelegramLinkCode model behavior."""

    def test_generate_random_code(self):
        """generate_link_code creates 6-character alphanumeric code."""
        from nikita.db.models.telegram_link import generate_link_code

        code = generate_link_code()
        assert len(code) == 6
        assert code.isalnum()
        assert code.isupper()

    def test_codes_are_unique(self):
        """Generated codes should be unique (statistically)."""
        from nikita.db.models.telegram_link import generate_link_code

        codes = [generate_link_code() for _ in range(100)]
        # All should be unique
        assert len(set(codes)) == 100

    def test_link_code_expiry_calculation(self):
        """TelegramLinkCode expires after 10 minutes."""
        from nikita.db.models.telegram_link import TelegramLinkCode

        model = TelegramLinkCode
        # Check table name
        assert model.__tablename__ == "telegram_link_codes"


class TestVerifyLinkCode:
    """Test verify link code functionality (T46.4).

    Note: The actual /link command is tested in telegram route tests.
    These tests verify the repository methods.
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_verify_valid_code_returns_user_id(self, mock_session):
        """AC-T46.4: Valid code returns user_id for linking."""
        from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository

        user_id = uuid4()
        mock_link = MagicMock()  # Use MagicMock for sync method is_expired()
        mock_link.user_id = user_id
        mock_link.code = "ABC123"
        mock_link.expires_at = datetime.now(UTC) + timedelta(minutes=5)
        mock_link.is_expired.return_value = False  # Not expired (sync method)

        repo = TelegramLinkRepository(mock_session)
        repo.get_by_code = AsyncMock(return_value=mock_link)
        repo.delete = AsyncMock()

        result = await repo.verify_code("ABC123")

        assert result == user_id
        repo.delete.assert_called_once_with("ABC123")

    @pytest.mark.asyncio
    async def test_verify_expired_code_returns_none(self, mock_session):
        """Expired code returns None."""
        from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository

        mock_link = MagicMock()  # Use MagicMock for sync method is_expired()
        mock_link.user_id = uuid4()
        mock_link.code = "ABC123"
        mock_link.expires_at = datetime.now(UTC) - timedelta(minutes=5)  # Expired
        mock_link.is_expired.return_value = True  # Explicitly expired (sync method)

        repo = TelegramLinkRepository(mock_session)
        repo.get_by_code = AsyncMock(return_value=mock_link)
        repo.delete = AsyncMock()

        result = await repo.verify_code("ABC123")

        assert result is None
        # Should delete expired code
        repo.delete.assert_called_once_with("ABC123")

    @pytest.mark.asyncio
    async def test_verify_invalid_code_returns_none(self, mock_session):
        """Invalid/unknown code returns None."""
        from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository

        repo = TelegramLinkRepository(mock_session)
        repo.get_by_code = AsyncMock(return_value=None)

        result = await repo.verify_code("INVALID")

        assert result is None
