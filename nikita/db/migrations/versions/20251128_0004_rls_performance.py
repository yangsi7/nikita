"""Fix RLS policy performance - use (select auth.uid()) pattern.

Revision ID: 0004
Revises: 0003
Create Date: 2025-12-01

T16: Fix RLS Performance (HIGH)
- Recreates all RLS policies with (select auth.uid()) instead of auth.uid()
- This optimization evaluates auth.uid() once per query instead of per row
- Affects 6 tables (message_embeddings already fixed in 0003)

Performance Impact: ~50-100x faster for large tables due to initplan optimization
Reference: Supabase Advisor auth_rls_initplan warning
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate RLS policies with (select auth.uid()) optimization."""
    # AC-T16.1: Fix users policy
    op.execute("DROP POLICY IF EXISTS users_own_data ON users")
    op.execute(
        """
        CREATE POLICY "users_own_data" ON users
        FOR ALL
        USING (id = (select auth.uid()))
        WITH CHECK (id = (select auth.uid()))
        """
    )

    # AC-T16.2: Fix user_metrics policy
    op.execute("DROP POLICY IF EXISTS user_metrics_own_data ON user_metrics")
    op.execute(
        """
        CREATE POLICY "user_metrics_own_data" ON user_metrics
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )

    # AC-T16.3: Fix user_vice_preferences policy
    op.execute(
        "DROP POLICY IF EXISTS vice_preferences_own_data ON user_vice_preferences"
    )
    op.execute(
        """
        CREATE POLICY "vice_preferences_own_data" ON user_vice_preferences
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )

    # AC-T16.4: Fix conversations policy
    op.execute("DROP POLICY IF EXISTS conversations_own_data ON conversations")
    op.execute(
        """
        CREATE POLICY "conversations_own_data" ON conversations
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )

    # AC-T16.5: Fix score_history policy
    op.execute("DROP POLICY IF EXISTS score_history_own_data ON score_history")
    op.execute(
        """
        CREATE POLICY "score_history_own_data" ON score_history
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )

    # AC-T16.6: Fix daily_summaries policy
    op.execute("DROP POLICY IF EXISTS daily_summaries_own_data ON daily_summaries")
    op.execute(
        """
        CREATE POLICY "daily_summaries_own_data" ON daily_summaries
        FOR ALL
        USING (user_id = (select auth.uid()))
        WITH CHECK (user_id = (select auth.uid()))
        """
    )

    # Note: message_embeddings already fixed in migration 0003


def downgrade() -> None:
    """Restore original RLS policies without optimization."""
    # Restore users policy
    op.execute("DROP POLICY IF EXISTS users_own_data ON users")
    op.execute(
        """
        CREATE POLICY "users_own_data" ON users
        FOR ALL
        USING (auth.uid() = id)
        WITH CHECK (auth.uid() = id)
        """
    )

    # Restore user_metrics policy
    op.execute("DROP POLICY IF EXISTS user_metrics_own_data ON user_metrics")
    op.execute(
        """
        CREATE POLICY "user_metrics_own_data" ON user_metrics
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Restore user_vice_preferences policy
    op.execute(
        "DROP POLICY IF EXISTS vice_preferences_own_data ON user_vice_preferences"
    )
    op.execute(
        """
        CREATE POLICY "vice_preferences_own_data" ON user_vice_preferences
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Restore conversations policy
    op.execute("DROP POLICY IF EXISTS conversations_own_data ON conversations")
    op.execute(
        """
        CREATE POLICY "conversations_own_data" ON conversations
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Restore score_history policy
    op.execute("DROP POLICY IF EXISTS score_history_own_data ON score_history")
    op.execute(
        """
        CREATE POLICY "score_history_own_data" ON score_history
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    # Restore daily_summaries policy
    op.execute("DROP POLICY IF EXISTS daily_summaries_own_data ON daily_summaries")
    op.execute(
        """
        CREATE POLICY "daily_summaries_own_data" ON daily_summaries
        FOR ALL
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )
