"""Move extensions to dedicated schema and add pending_registrations table.

Revision ID: 0006
Revises: 0005
Create Date: 2025-12-01

T18: Extensions Schema + pending_registrations (MEDIUM)
- Creates extensions schema
- Moves vector and pg_trgm extensions out of public schema
- Creates pending_registrations table for Telegram auth flow
- Adds index and TTL cleanup function

Reference: Supabase Advisor extension_in_public warning
Note: Extensions in public schema can conflict with user-defined objects
and create security concerns.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move extensions and create pending_registrations table."""
    # AC-T18.1: Create extensions schema
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")

    # AC-T18.2: Move vector extension to extensions schema
    # Note: This may fail if the extension is in use by columns
    # In that case, we need to handle this differently
    op.execute(
        """
        DO $$
        BEGIN
            -- Check if vector extension exists in public
            IF EXISTS (
                SELECT 1 FROM pg_extension e
                JOIN pg_namespace n ON e.extnamespace = n.oid
                WHERE e.extname = 'vector' AND n.nspname = 'public'
            ) THEN
                ALTER EXTENSION vector SET SCHEMA extensions;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                -- If move fails (e.g., dependent objects), log and continue
                RAISE NOTICE 'Could not move vector extension: %', SQLERRM;
        END $$;
        """
    )

    # AC-T18.3: Move pg_trgm extension to extensions schema
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension e
                JOIN pg_namespace n ON e.extnamespace = n.oid
                WHERE e.extname = 'pg_trgm' AND n.nspname = 'public'
            ) THEN
                ALTER EXTENSION pg_trgm SET SCHEMA extensions;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not move pg_trgm extension: %', SQLERRM;
        END $$;
        """
    )

    # AC-T18.4: Update search_path to include extensions schema
    op.execute(
        """
        ALTER DATABASE postgres SET search_path TO public, extensions;
        """
    )

    # AC-T18.5: Create pending_registrations table
    # This replaces the in-memory dict in auth.py
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_registrations (
            telegram_id BIGINT PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '10 minutes')
        )
        """
    )

    # AC-T18.6: Create index for expiry cleanup
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pending_registrations_expires_at
        ON pending_registrations(expires_at)
        """
    )

    # AC-T18.7: Create cleanup function for expired registrations
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_registrations()
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM pending_registrations
            WHERE expires_at < now();
        END;
        $$;
        """
    )

    # AC-T18.8: Enable RLS on pending_registrations (no user access needed)
    # Only service role should access this table
    op.execute("ALTER TABLE pending_registrations ENABLE ROW LEVEL SECURITY")

    # No policies needed - service role bypasses RLS
    # Anon/authenticated users should not access this table


def downgrade() -> None:
    """Remove pending_registrations and move extensions back."""
    # Drop cleanup function
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_registrations()")

    # Drop pending_registrations
    op.execute("DROP TABLE IF EXISTS pending_registrations")

    # Move extensions back to public (if they exist in extensions)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension e
                JOIN pg_namespace n ON e.extnamespace = n.oid
                WHERE e.extname = 'vector' AND n.nspname = 'extensions'
            ) THEN
                ALTER EXTENSION vector SET SCHEMA public;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not move vector extension back: %', SQLERRM;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension e
                JOIN pg_namespace n ON e.extnamespace = n.oid
                WHERE e.extname = 'pg_trgm' AND n.nspname = 'extensions'
            ) THEN
                ALTER EXTENSION pg_trgm SET SCHEMA public;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not move pg_trgm extension back: %', SQLERRM;
        END $$;
        """
    )

    # Note: We don't drop the extensions schema as it may be used by other things
