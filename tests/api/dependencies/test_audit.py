"""Tests for audit logging middleware - T1.2 Spec 034.

TDD: Write tests FIRST, then implement.
Uses mocking for unit tests (fast, isolated).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestAuditAdminAction:
    """Test audit_admin_action function."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_audit_log_created_on_user_view(self, mock_session):
        """AC-1.2.1: Audit log entry created when admin views user data."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()
        user_id = uuid4()

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="view",
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            session=mock_session,
        )

        # Verify session.add was called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

        # Verify the log entry has correct values
        assert result.action == "view"
        assert result.resource_type == "user"
        assert result.resource_id == user_id

    @pytest.mark.asyncio
    async def test_audit_log_captures_admin_id(self, mock_session):
        """AC-1.2.2: Audit log captures admin ID correctly."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="test@silent-agents.com",
            action="view",
            resource_type="conversation",
            resource_id=uuid4(),
            user_id=uuid4(),
            session=mock_session,
        )

        assert result.admin_id == admin_id
        assert result.admin_email == "test@silent-agents.com"

    @pytest.mark.asyncio
    async def test_audit_log_captures_resource_info(self, mock_session):
        """AC-1.2.3: Audit log captures resource type and ID."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()
        resource_id = uuid4()

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="view",
            resource_type="generated_prompt",
            resource_id=resource_id,
            user_id=uuid4(),
            session=mock_session,
        )

        assert result.resource_type == "generated_prompt"
        assert result.resource_id == resource_id

    @pytest.mark.asyncio
    async def test_audit_log_with_details(self, mock_session):
        """Audit log can include optional details."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()
        details = {"query_params": {"page": 1, "limit": 50}}

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="list",
            resource_type="conversations",
            resource_id=None,
            user_id=uuid4(),
            session=mock_session,
            details=details,
        )

        assert result.details == details

    @pytest.mark.asyncio
    async def test_audit_log_without_resource_id(self, mock_session):
        """Audit log works for list actions without specific resource ID."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()
        user_id = uuid4()

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="list",
            resource_type="users",
            resource_id=None,
            user_id=user_id,
            session=mock_session,
        )

        assert result.resource_id is None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_audit_log_default_empty_details(self, mock_session):
        """Audit log defaults details to empty dict when not provided."""
        from nikita.api.dependencies.audit import audit_admin_action

        admin_id = uuid4()

        result = await audit_admin_action(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="view",
            resource_type="user",
            resource_id=uuid4(),
            user_id=uuid4(),
            session=mock_session,
        )

        assert result.details == {}

    @pytest.mark.asyncio
    async def test_audit_log_logging_called(self, mock_session):
        """Audit action logs to Python logger."""
        from nikita.api.dependencies.audit import audit_admin_action

        with patch("nikita.api.dependencies.audit.logger") as mock_logger:
            await audit_admin_action(
                admin_id=uuid4(),
                admin_email="admin@silent-agents.com",
                action="view",
                resource_type="user",
                resource_id=uuid4(),
                user_id=uuid4(),
                session=mock_session,
            )

            mock_logger.info.assert_called_once()


class TestAuditLogModel:
    """Test AuditLog SQLAlchemy model."""

    def test_audit_log_model_fields(self):
        """AuditLog model has all required fields."""
        from nikita.db.models.audit_log import AuditLog

        admin_id = uuid4()
        resource_id = uuid4()
        user_id = uuid4()

        log = AuditLog(
            admin_id=admin_id,
            admin_email="admin@silent-agents.com",
            action="view",
            resource_type="user",
            resource_id=resource_id,
            user_id=user_id,
            details={"test": "value"},
        )

        assert log.admin_id == admin_id
        assert log.admin_email == "admin@silent-agents.com"
        assert log.action == "view"
        assert log.resource_type == "user"
        assert log.resource_id == resource_id
        assert log.user_id == user_id
        assert log.details == {"test": "value"}

    def test_audit_log_default_details(self):
        """AuditLog defaults details to empty dict."""
        from nikita.db.models.audit_log import AuditLog

        log = AuditLog(
            admin_id=uuid4(),
            admin_email="admin@silent-agents.com",
            action="view",
            resource_type="user",
        )

        # Default is set via mapped_column default
        assert log.details == {}

    def test_audit_log_nullable_fields(self):
        """AuditLog allows nullable resource_id and user_id."""
        from nikita.db.models.audit_log import AuditLog

        log = AuditLog(
            admin_id=uuid4(),
            admin_email="admin@silent-agents.com",
            action="list",
            resource_type="users",
            resource_id=None,
            user_id=None,
        )

        assert log.resource_id is None
        assert log.user_id is None
