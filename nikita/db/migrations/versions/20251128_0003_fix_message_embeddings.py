"""Fix message_embeddings table - add missing user_id column.

Revision ID: 0003
Revises: 0002
Create Date: 2025-12-01

T15: Fix message_embeddings Schema (CRITICAL)
- Adds user_id column to message_embeddings (FK to users)
- Backfills user_id from conversations.user_id
- Adds NOT NULL constraint after backfill
- Creates index for RLS performance

Migration Drift Fix: The initial schema migration (0001) had user_id in code,
but the actual Supabase database does not have this column. This migration
corrects the drift.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user_id column to message_embeddings and backfill from conversations."""
    # AC-T15.1: Add user_id column (nullable initially for backfill)
    op.execute(
        """
        ALTER TABLE message_embeddings
        ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE
        """
    )

    # AC-T15.2: Backfill user_id from conversations table
    op.execute(
        """
        UPDATE message_embeddings me
        SET user_id = c.user_id
        FROM conversations c
        WHERE me.conversation_id = c.id
        AND me.user_id IS NULL
        """
    )

    # AC-T15.3: Add NOT NULL constraint (after backfill)
    # Only if there are no NULL values remaining
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM message_embeddings WHERE user_id IS NULL
            ) THEN
                ALTER TABLE message_embeddings
                ALTER COLUMN user_id SET NOT NULL;
            END IF;
        END $$;
        """
    )

    # AC-T15.4: Create index for RLS performance
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_message_embeddings_user_id
        ON message_embeddings(user_id)
        """
    )

    # AC-T15.5: Update RLS policy to use the new column with optimized pattern
    # First drop the old broken policy
    op.execute(
        "DROP POLICY IF EXISTS message_embeddings_own_data ON message_embeddings"
    )

    # Create new policy with (select auth.uid()) optimization
    op.execute(
        """
        CREATE POLICY "message_embeddings_own_data" ON message_embeddings
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )


def downgrade() -> None:
    """Remove user_id column from message_embeddings."""
    # Restore original policy (broken, but matches 0002 state)
    op.execute(
        "DROP POLICY IF EXISTS message_embeddings_own_data ON message_embeddings"
    )
    op.execute(
        """
        CREATE POLICY "message_embeddings_own_data" ON message_embeddings
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Drop index
    op.execute("DROP INDEX IF EXISTS ix_message_embeddings_user_id")

    # Drop column
    op.execute("ALTER TABLE message_embeddings DROP COLUMN IF EXISTS user_id")
