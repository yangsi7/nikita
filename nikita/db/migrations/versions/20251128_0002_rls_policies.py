"""Add Row-Level Security policies for user data isolation.

Revision ID: 0002
Revises: 0001
Create Date: 2025-11-28

T10: Create RLS Policies Migration
- Enables RLS on all user-data tables
- Creates "own_data" policies for auth.uid() matching
- Service role bypasses RLS
- Anon role blocked from all operations
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable RLS and create policies."""
    # AC-T10.1: Enable RLS on users
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # AC-T10.3: Policy for users - own data only via auth.uid()
    op.execute(
        """
        CREATE POLICY "users_own_data" ON users
        FOR ALL
        USING (auth.uid() = id)
        WITH CHECK (auth.uid() = id)
        """
    )

    # AC-T10.1: Enable RLS on user_metrics
    op.execute("ALTER TABLE user_metrics ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for user_metrics - via user_id
    op.execute(
        """
        CREATE POLICY "user_metrics_own_data" ON user_metrics
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # AC-T10.1: Enable RLS on user_vice_preferences
    op.execute("ALTER TABLE user_vice_preferences ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for vice_preferences - via user_id
    op.execute(
        """
        CREATE POLICY "vice_preferences_own_data" ON user_vice_preferences
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # AC-T10.2: Enable RLS on conversations
    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for conversations - via user_id
    op.execute(
        """
        CREATE POLICY "conversations_own_data" ON conversations
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # AC-T10.2: Enable RLS on score_history
    op.execute("ALTER TABLE score_history ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for score_history - via user_id
    op.execute(
        """
        CREATE POLICY "score_history_own_data" ON score_history
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # AC-T10.2: Enable RLS on daily_summaries
    op.execute("ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for daily_summaries - via user_id
    op.execute(
        """
        CREATE POLICY "daily_summaries_own_data" ON daily_summaries
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # AC-T10.2: Enable RLS on message_embeddings
    op.execute("ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY")

    # AC-T10.4: Policy for message_embeddings - via user_id
    op.execute(
        """
        CREATE POLICY "message_embeddings_own_data" ON message_embeddings
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Note: AC-T10.5 (Service role bypass) is automatic in Supabase
    # The service_role key bypasses RLS by default

    # Note: AC-T10.6 (Anon blocked) is automatic when RLS is enabled
    # Anon role has no policies, so all operations are blocked


def downgrade() -> None:
    """Drop RLS policies and disable RLS."""
    # Drop policies
    op.execute("DROP POLICY IF EXISTS users_own_data ON users")
    op.execute("DROP POLICY IF EXISTS user_metrics_own_data ON user_metrics")
    op.execute(
        "DROP POLICY IF EXISTS vice_preferences_own_data ON user_vice_preferences"
    )
    op.execute("DROP POLICY IF EXISTS conversations_own_data ON conversations")
    op.execute("DROP POLICY IF EXISTS score_history_own_data ON score_history")
    op.execute("DROP POLICY IF EXISTS daily_summaries_own_data ON daily_summaries")
    op.execute(
        "DROP POLICY IF EXISTS message_embeddings_own_data ON message_embeddings"
    )

    # Disable RLS
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_metrics DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_vice_preferences DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conversations DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE score_history DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE daily_summaries DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE message_embeddings DISABLE ROW LEVEL SECURITY")
