"""SQLAlchemy model for context_packages table (Spec 021, T004).

Stores pre-computed context packages as JSONB for fast retrieval.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class ContextPackageModel(Base):
    """SQLAlchemy model for context_packages table.

    Stores pre-computed context packages with automatic expiration.
    Uses JSONB for flexible schema and efficient querying.
    """

    __tablename__ = "context_packages"

    # Primary key - auto-increment bigint
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign key to users table
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        unique=True,  # One package per user
        index=True,
    )

    # The context package data as JSONB
    package: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(hours=24),
    )

    # Note: Indexes are created in the migration, not here
    # - idx_context_packages_user_id (unique)
    # - idx_context_packages_expires (user_id, expires_at DESC)
    # - idx_context_packages_gin (JSONB GIN)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ContextPackageModel(id={self.id}, user_id={self.user_id}, "
            f"expires_at={self.expires_at})>"
        )
