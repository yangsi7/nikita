"""Consolidate duplicate RLS policies.

Revision ID: 0005
Revises: 0004
Create Date: 2025-12-01

T17: Consolidate Duplicate Policies (HIGH)
- Removes overlapping SELECT policies on conversations
- Removes overlapping SELECT policies on user_vice_preferences
- Keeps single FOR ALL policy per table

Reference: Supabase Advisor multiple_permissive_policies warning
Note: The original migration created both "view own" and "manage own" policies
which overlap on SELECT operations. This migration ensures only one policy exists.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove any duplicate policies that may exist."""
    # AC-T17.1: Clean up conversations - remove any legacy duplicate policies
    # Note: These may or may not exist depending on database state
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own conversations\" ON conversations"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can manage own conversations\" ON conversations"
    )
    op.execute(
        "DROP POLICY IF EXISTS conversations_view_own ON conversations"
    )
    op.execute(
        "DROP POLICY IF EXISTS conversations_manage_own ON conversations"
    )

    # AC-T17.2: Clean up user_vice_preferences - remove any legacy duplicate policies
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own vice preferences\" ON user_vice_preferences"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can manage own vice preferences\" ON user_vice_preferences"
    )
    op.execute(
        "DROP POLICY IF EXISTS vice_preferences_view_own ON user_vice_preferences"
    )
    op.execute(
        "DROP POLICY IF EXISTS vice_preferences_manage_own ON user_vice_preferences"
    )

    # AC-T17.3: Verify single policy exists (policies created in 0004)
    # The conversations_own_data and vice_preferences_own_data policies
    # from migration 0004 handle all operations with FOR ALL clause

    # AC-T17.4: Clean up any other potential duplicate policies
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own profile\" ON users"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can update own profile\" ON users"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own metrics\" ON user_metrics"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own score history\" ON score_history"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own daily summaries\" ON daily_summaries"
    )
    op.execute(
        "DROP POLICY IF EXISTS \"Users can view own message embeddings\" ON message_embeddings"
    )


def downgrade() -> None:
    """No-op - we don't want to recreate duplicate policies."""
    # Downgrade is intentionally a no-op
    # The duplicate policies were a mistake, not a feature
    pass
