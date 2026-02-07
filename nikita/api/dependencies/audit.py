"""Audit logging middleware for admin data access.

Part of Spec 034 - Admin User Monitoring Dashboard.
CRITICAL: All admin access to sensitive user data must be logged.

Usage:
    @router.get("/admin/users/{user_id}")
    async def get_user(
        user_id: UUID,
        admin: AdminUser = Depends(get_current_admin_user),
        session: AsyncSession = Depends(get_async_session),
    ):
        # Log the access
        await audit_admin_action(
            admin_id=admin.id,
            admin_email=admin.email,
            action="view",
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            session=session,
        )
        # ... rest of endpoint
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def audit_admin_action(
    admin_id: UUID,
    admin_email: str,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    user_id: UUID | None,
    session: AsyncSession,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Log an admin action for audit trail.

    CRITICAL: Call this for ALL admin access to sensitive data.

    Args:
        admin_id: UUID of the admin performing the action
        admin_email: Email of the admin (for quick reference)
        action: Type of action (view, list, export, etc.)
        resource_type: Type of resource accessed (user, conversation, etc.)
        resource_id: Specific resource ID if applicable
        user_id: ID of user whose data was accessed
        session: Database session
        details: Optional additional context (query params, etc.)

    Returns:
        Created AuditLog entry

    Example:
        await audit_admin_action(
            admin_id=admin.id,
            admin_email=admin.email,
            action="view",
            resource_type="conversation",
            resource_id=conversation_id,
            user_id=user_id,
            session=session,
            details={"include_messages": True},
        )
    """
    log_entry = AuditLog(
        admin_id=admin_id,
        admin_email=admin_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        details=details or {},
    )

    session.add(log_entry)
    await session.commit()

    logger.info(
        "Admin audit: %s %s %s (admin=%s, user=%s)",
        action,
        resource_type,
        resource_id or "list",
        admin_email,
        user_id,
    )

    return log_entry
