"""Add rate_limits table for DB-backed rate limiting.

Revision ID: 0007
Revises: 0006
Create Date: 2025-12-05

SEC-02: Database-backed rate limiting (HIGH priority)
- Creates rate_limits table for persistent rate limit tracking
- Adds composite unique index for (user_id, window)
- Adds expiration index for cleanup
- Creates cleanup function for expired rate limit records
- Enables RLS (service role only)

This replaces the in-memory InMemoryCache with database persistence,
enabling rate limiting across multiple Cloud Run instances.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create rate_limits table and cleanup function."""
    # Create rate_limits table
    # Note: 'window' is a reserved keyword in PostgreSQL, so we quote it
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            "window" VARCHAR(50) NOT NULL,
            count BIGINT NOT NULL DEFAULT 0,
            expires_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_rate_limit_user_window UNIQUE (user_id, "window")
        )
        """
    )

    # Create index on user_id for faster lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_rate_limits_user_id
        ON rate_limits(user_id)
        """
    )

    # Create index on expires_at for cleanup queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_rate_limits_expires_at
        ON rate_limits(expires_at)
        """
    )

    # Create cleanup function for expired rate limit records
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_rate_limits()
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM rate_limits
            WHERE expires_at < now();
        END;
        $$;
        """
    )

    # Enable RLS (service role only - no user access)
    op.execute("ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY")

    # No policies needed - service role bypasses RLS
    # Anon/authenticated users should not directly access rate_limits


def downgrade() -> None:
    """Remove rate_limits table and cleanup function."""
    # Drop cleanup function
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_rate_limits()")

    # Drop rate_limits table (CASCADE to drop dependent indexes)
    op.execute("DROP TABLE IF EXISTS rate_limits CASCADE")
