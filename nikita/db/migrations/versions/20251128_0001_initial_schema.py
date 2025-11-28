"""Initial schema for Nikita database.

Revision ID: 0001
Revises: None
Create Date: 2025-11-28

T9: Create Initial Migration
- Creates all 6 core tables
- Creates message_embeddings with pgvector
- Sets up foreign keys with CASCADE
- Creates performance indexes
- Adds check constraints
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial schema."""
    # Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # AC-T9.1: Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), unique=True, nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "relationship_score",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="50.00",
        ),
        sa.Column("chapter", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("boss_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("days_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_interaction_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "game_status", sa.String(20), nullable=False, server_default="active"
        ),
        sa.Column("graphiti_group_id", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column(
            "notifications_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # AC-T9.5: Check constraints
        sa.CheckConstraint("chapter BETWEEN 1 AND 5", name="check_chapter_range"),
        sa.CheckConstraint(
            "boss_attempts BETWEEN 0 AND 3", name="check_boss_attempts_range"
        ),
        sa.CheckConstraint(
            "game_status IN ('active', 'boss_fight', 'game_over', 'won')",
            name="check_game_status_values",
        ),
    )

    # AC-T9.4: Performance indexes
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_game_status", "users", ["game_status"])

    # AC-T9.1: Create user_metrics table
    op.create_table(
        "user_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "intimacy", sa.Numeric(5, 2), nullable=False, server_default="50.00"
        ),
        sa.Column(
            "passion", sa.Numeric(5, 2), nullable=False, server_default="50.00"
        ),
        sa.Column("trust", sa.Numeric(5, 2), nullable=False, server_default="50.00"),
        sa.Column(
            "secureness", sa.Numeric(5, 2), nullable=False, server_default="50.00"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # AC-T9.1: Create user_vice_preferences table
    op.create_table(
        "user_vice_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("intensity_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "engagement_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"
        ),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # AC-T9.5: Check constraint
        sa.CheckConstraint(
            "intensity_level BETWEEN 1 AND 5", name="check_intensity_level_range"
        ),
    )

    op.create_index(
        "ix_user_vice_preferences_user_id", "user_vice_preferences", ["user_id"]
    )

    # AC-T9.1: Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column(
            "messages", postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.Column("score_delta", sa.Numeric(5, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_boss_fight", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("chapter_at_time", sa.Integer(), nullable=True),
        sa.Column("elevenlabs_session_id", sa.Text(), nullable=True),
        sa.Column("transcript_raw", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # AC-T9.4: Performance indexes for conversations
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index(
        "ix_conversations_user_started", "conversations", ["user_id", "started_at"]
    )

    # AC-T9.1: Create score_history table
    op.create_table(
        "score_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("event_details", postgresql.JSONB(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_score_history_user_id", "score_history", ["user_id"])
    op.create_index(
        "ix_score_history_user_recorded",
        "score_history",
        ["user_id", "recorded_at"],
    )

    # AC-T9.1: Create daily_summaries table
    op.create_table(
        "daily_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("score_start", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_end", sa.Numeric(5, 2), nullable=True),
        sa.Column("decay_applied", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "conversations_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("nikita_summary_text", sa.Text(), nullable=True),
        sa.Column("key_events", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_daily_summaries_user_id", "daily_summaries", ["user_id"])
    op.create_index(
        "ix_daily_summaries_user_date", "daily_summaries", ["user_id", "date"]
    )

    # AC-T9.2: Create message_embeddings table with pgvector
    op.create_table(
        "message_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Add vector column separately (Alembic doesn't support vector type directly)
    op.execute(
        "ALTER TABLE message_embeddings ADD COLUMN embedding vector(1536)"
    )

    op.create_index(
        "ix_message_embeddings_user_id", "message_embeddings", ["user_id"]
    )
    op.create_index(
        "ix_message_embeddings_conversation_id",
        "message_embeddings",
        ["conversation_id"],
    )

    # Create HNSW index for vector similarity search
    op.execute(
        """
        CREATE INDEX ix_message_embeddings_embedding
        ON message_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Drop all tables in reverse order (AC-T9.7: Reversible)."""
    op.drop_table("message_embeddings")
    op.drop_table("daily_summaries")
    op.drop_table("score_history")
    op.drop_table("conversations")
    op.drop_table("user_vice_preferences")
    op.drop_table("user_metrics")
    op.drop_table("users")
