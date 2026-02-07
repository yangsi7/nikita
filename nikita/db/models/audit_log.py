"""AuditLog model for tracking admin access to sensitive data.

Part of Spec 034 - Admin User Monitoring Dashboard.
CRITICAL: All admin data access must be logged for security compliance.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class AuditLog(Base):
    """Audit log entry for admin access to sensitive data.

    Tracks:
    - Which admin accessed data
    - What resource type and ID
    - Which user's data was accessed
    - When the access occurred
    - Optional metadata (query params, etc.)
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    admin_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    admin_email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    def __init__(self, **kwargs):
        """Initialize with default details if not provided."""
        if "details" not in kwargs:
            kwargs["details"] = {}
        super().__init__(**kwargs)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
