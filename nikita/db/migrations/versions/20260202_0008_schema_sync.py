"""Schema sync migration - Add all missing tables and columns.

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-02

This migration syncs the database schema with all SQLAlchemy models.
Uses IF NOT EXISTS pattern for idempotency (cloud Supabase may already have some tables).

Missing tables (17):
- generated_prompts (Spec 029)
- conversation_threads (Spec 012)
- nikita_thoughts (Spec 012)
- engagement_state (Spec 014)
- engagement_history (Spec 014)
- user_profiles (Spec 017)
- user_backstories (Spec 017)
- venue_cache (Spec 017)
- onboarding_states (Spec 017)
- user_social_circles (Spec 035)
- user_narrative_arcs (Spec 035)
- scheduled_events (Spec 011)
- scheduled_touchpoints (Spec 025)
- job_executions (Spec 031)
- telegram_link_codes (Spec 033)
- audit_logs (Spec 041)
- error_logs (Spec 041)

Missing columns in users table (7):
- cached_voice_prompt, cached_voice_prompt_at, cached_voice_context
- onboarding_status, onboarding_profile, onboarded_at, onboarding_call_id

Missing columns in conversations table (8):
- status, processing_attempts, processing_started_at, processed_at
- last_message_at, extracted_entities, conversation_summary, emotional_tone

Missing columns in daily_summaries table (4):
- summary_text, key_moments, emotional_tone, engagement_score, updated_at
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name
                AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add all missing tables and columns."""
    # =========================================================================
    # PHASE 1: Create enum type for engagement states
    # =========================================================================
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'engagement_state_enum') THEN
                CREATE TYPE engagement_state_enum AS ENUM (
                    'calibrating', 'in_zone', 'drifting', 'clingy', 'distant', 'out_of_zone'
                );
            END IF;
        END
        $$;
        """
    )

    # =========================================================================
    # PHASE 2: Add missing columns to users table
    # =========================================================================
    if not column_exists("users", "cached_voice_prompt"):
        op.add_column("users", sa.Column("cached_voice_prompt", sa.Text(), nullable=True))

    if not column_exists("users", "cached_voice_prompt_at"):
        op.add_column(
            "users",
            sa.Column("cached_voice_prompt_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not column_exists("users", "cached_voice_context"):
        op.add_column(
            "users", sa.Column("cached_voice_context", postgresql.JSONB(), nullable=True)
        )

    if not column_exists("users", "onboarding_status"):
        op.add_column(
            "users",
            sa.Column(
                "onboarding_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
        )

    if not column_exists("users", "onboarding_profile"):
        op.add_column(
            "users",
            sa.Column(
                "onboarding_profile", postgresql.JSONB(), nullable=True, server_default="{}"
            ),
        )

    if not column_exists("users", "onboarded_at"):
        op.add_column(
            "users", sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True)
        )

    if not column_exists("users", "onboarding_call_id"):
        op.add_column("users", sa.Column("onboarding_call_id", sa.Text(), nullable=True))

    # Add check constraint for onboarding_status (idempotent)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'check_onboarding_status_values'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT check_onboarding_status_values
                CHECK (onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped'));
            END IF;
        END
        $$;
        """
    )

    # Fix telegram_id column type (BigInteger instead of Integer for IDs > 2^31)
    op.execute(
        """
        ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT USING telegram_id::BIGINT;
        """
    )

    # =========================================================================
    # PHASE 3: Add missing columns to conversations table
    # =========================================================================
    if not column_exists("conversations", "status"):
        op.add_column(
            "conversations",
            sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        )

    if not column_exists("conversations", "processing_attempts"):
        op.add_column(
            "conversations",
            sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"),
        )

    if not column_exists("conversations", "processing_started_at"):
        op.add_column(
            "conversations",
            sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not column_exists("conversations", "processed_at"):
        op.add_column(
            "conversations",
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not column_exists("conversations", "last_message_at"):
        op.add_column(
            "conversations",
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not column_exists("conversations", "extracted_entities"):
        op.add_column(
            "conversations",
            sa.Column("extracted_entities", postgresql.JSONB(), nullable=True),
        )

    if not column_exists("conversations", "conversation_summary"):
        op.add_column(
            "conversations", sa.Column("conversation_summary", sa.Text(), nullable=True)
        )

    if not column_exists("conversations", "emotional_tone"):
        op.add_column(
            "conversations", sa.Column("emotional_tone", sa.Text(), nullable=True)
        )

    # =========================================================================
    # PHASE 4: Add missing columns to daily_summaries table
    # =========================================================================
    if not column_exists("daily_summaries", "summary_text"):
        op.add_column(
            "daily_summaries", sa.Column("summary_text", sa.Text(), nullable=True)
        )

    if not column_exists("daily_summaries", "key_moments"):
        op.add_column(
            "daily_summaries",
            sa.Column("key_moments", postgresql.JSONB(), nullable=True),
        )

    if not column_exists("daily_summaries", "emotional_tone"):
        op.add_column(
            "daily_summaries", sa.Column("emotional_tone", sa.Text(), nullable=True)
        )

    if not column_exists("daily_summaries", "engagement_score"):
        op.add_column(
            "daily_summaries",
            sa.Column("engagement_score", sa.Numeric(3, 2), nullable=True),
        )

    if not column_exists("daily_summaries", "updated_at"):
        op.add_column(
            "daily_summaries",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # =========================================================================
    # PHASE 5: Create missing tables (in dependency order)
    # =========================================================================

    # --- generated_prompts (Spec 029) ---
    if not table_exists("generated_prompts"):
        op.create_table(
            "generated_prompts",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "conversation_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("prompt_content", sa.Text(), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=False),
            sa.Column("generation_time_ms", sa.Float(), nullable=False),
            sa.Column("meta_prompt_template", sa.String(100), nullable=False),
            sa.Column("platform", sa.String(10), nullable=False, server_default="text"),
            sa.Column("context_snapshot", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_generated_prompts_user_id", "generated_prompts", ["user_id"]
        )
        op.create_index(
            "ix_generated_prompts_conversation_id",
            "generated_prompts",
            ["conversation_id"],
        )

    # --- conversation_threads (Spec 012) ---
    if not table_exists("conversation_threads"):
        op.create_table(
            "conversation_threads",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("thread_type", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "source_conversation_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.Text(), nullable=False, server_default="open"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_conversation_threads_user_id", "conversation_threads", ["user_id"]
        )

    # --- nikita_thoughts (Spec 012) ---
    if not table_exists("nikita_thoughts"):
        op.create_table(
            "nikita_thoughts",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("thought_type", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "source_conversation_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("psychological_context", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_nikita_thoughts_user_id", "nikita_thoughts", ["user_id"])

    # --- engagement_state (Spec 014) ---
    if not table_exists("engagement_state"):
        op.create_table(
            "engagement_state",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column(
                "state",
                sa.String(20),  # Use String instead of Enum to avoid creation issues
                nullable=False,
                server_default="calibrating",
            ),
            sa.Column(
                "calibration_score",
                sa.Numeric(3, 2),
                nullable=False,
                server_default="0.50",
            ),
            sa.Column(
                "consecutive_in_zone", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "consecutive_clingy_days",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "consecutive_distant_days",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "multiplier", sa.Numeric(3, 2), nullable=False, server_default="0.90"
            ),
            sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=True),
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

    # --- engagement_history (Spec 014) ---
    if not table_exists("engagement_history"):
        op.create_table(
            "engagement_history",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "from_state",
                sa.String(20),  # Use String instead of Enum to avoid creation issues
                nullable=True,
            ),
            sa.Column(
                "to_state",
                sa.String(20),  # Use String instead of Enum to avoid creation issues
                nullable=False,
            ),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("calibration_score", sa.Numeric(3, 2), nullable=True),
            sa.Column("clinginess_score", sa.Numeric(3, 2), nullable=True),
            sa.Column("neglect_score", sa.Numeric(3, 2), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_engagement_history_user_id", "engagement_history", ["user_id"]
        )

    # --- user_profiles (Spec 017) ---
    if not table_exists("user_profiles"):
        op.create_table(
            "user_profiles",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("location_city", sa.String(100), nullable=True),
            sa.Column("location_country", sa.String(100), nullable=True),
            sa.Column("life_stage", sa.String(50), nullable=True),
            sa.Column("social_scene", sa.String(50), nullable=True),
            sa.Column("primary_interest", sa.String(100), nullable=True),
            sa.Column("drug_tolerance", sa.Integer(), nullable=False, server_default="3"),
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
            sa.CheckConstraint(
                "drug_tolerance BETWEEN 1 AND 5", name="check_drug_tolerance_range"
            ),
        )

    # --- user_backstories (Spec 017) ---
    if not table_exists("user_backstories"):
        op.create_table(
            "user_backstories",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                unique=True,
                nullable=False,
            ),
            sa.Column("venue_name", sa.String(200), nullable=True),
            sa.Column("venue_city", sa.String(100), nullable=True),
            sa.Column("scenario_type", sa.String(50), nullable=True),
            sa.Column("how_we_met", sa.Text(), nullable=True),
            sa.Column("the_moment", sa.Text(), nullable=True),
            sa.Column("unresolved_hook", sa.Text(), nullable=True),
            sa.Column("nikita_persona_overrides", postgresql.JSONB(), nullable=True),
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

    # --- venue_cache (Spec 017) ---
    if not table_exists("venue_cache"):
        op.create_table(
            "venue_cache",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("city", sa.String(100), nullable=False),
            sa.Column("scene", sa.String(50), nullable=False),
            sa.Column(
                "venues", postgresql.JSONB(), nullable=False, server_default="[]"
            ),
            sa.Column(
                "fetched_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now() + interval '30 days'"),
            ),
            sa.UniqueConstraint("city", "scene", name="uq_venue_cache_city_scene"),
        )

    # --- onboarding_states (Spec 017) ---
    if not table_exists("onboarding_states"):
        op.create_table(
            "onboarding_states",
            sa.Column("telegram_id", sa.BigInteger(), primary_key=True, nullable=False),
            sa.Column(
                "current_step", sa.String(30), nullable=False, server_default="location"
            ),
            sa.Column(
                "collected_answers",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column(
                "started_at",
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

    # --- user_social_circles (Spec 035) ---
    if not table_exists("user_social_circles"):
        op.create_table(
            "user_social_circles",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("friend_name", sa.String(100), nullable=False),
            sa.Column("friend_role", sa.String(50), nullable=False),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("occupation", sa.String(100), nullable=True),
            sa.Column("personality", sa.Text(), nullable=True),
            sa.Column("relationship_to_nikita", sa.Text(), nullable=True),
            sa.Column(
                "storyline_potential",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "trigger_conditions",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "adapted_traits",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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

    # --- user_narrative_arcs (Spec 035) ---
    if not table_exists("user_narrative_arcs"):
        op.create_table(
            "user_narrative_arcs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("template_name", sa.String(100), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("current_stage", sa.String(20), nullable=False, server_default="setup"),
            sa.Column("stage_progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "conversations_in_arc", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("max_conversations", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("current_description", sa.Text(), nullable=True),
            sa.Column(
                "involved_characters",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "emotional_impact",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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

    # --- scheduled_events (Spec 011) ---
    if not table_exists("scheduled_events"):
        op.create_table(
            "scheduled_events",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "source_conversation_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("platform", sa.String(20), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("content", postgresql.JSONB(), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
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
        # Partial index for pending events
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scheduled_events_due
            ON scheduled_events (status, scheduled_at)
            WHERE status = 'pending';
            """
        )

    # --- scheduled_touchpoints (Spec 025) ---
    if not table_exists("scheduled_touchpoints"):
        op.create_table(
            "scheduled_touchpoints",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("trigger_type", sa.String(20), nullable=False),
            sa.Column(
                "trigger_context",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("message_content", sa.Text(), nullable=False, server_default=""),
            sa.Column("delivery_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("skipped", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("skip_reason", sa.String(100), nullable=True),
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
        # Partial index for due touchpoints
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scheduled_touchpoints_due
            ON scheduled_touchpoints (delivered, skipped, delivery_at)
            WHERE delivered = false AND skipped = false;
            """
        )

    # --- job_executions (Spec 031) ---
    if not table_exists("job_executions"):
        op.create_table(
            "job_executions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("job_name", sa.String(50), nullable=False, index=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="running"),
            sa.Column("result", postgresql.JSONB(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
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

    # --- telegram_link_codes (Spec 033) ---
    if not table_exists("telegram_link_codes"):
        op.create_table(
            "telegram_link_codes",
            sa.Column("code", sa.String(6), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )

    # --- audit_logs (Spec 041) ---
    # NOTE: RLS intentionally DISABLED - admin-only table accessed exclusively via
    # service_role key through backend API (GET /admin/audit-logs). Never exposed
    # to anon key or client-side queries. Same applies to error_logs below.
    if not table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "admin_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column("admin_email", sa.Text(), nullable=False),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("resource_type", sa.String(100), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True
            ),
            sa.Column(
                "details", postgresql.JSONB(), nullable=False, server_default="{}"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    # --- error_logs (Spec 041) ---
    if not table_exists("error_logs"):
        op.create_table(
            "error_logs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("level", sa.String(20), nullable=False, server_default="error"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("source", sa.String(200), nullable=False),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("stack_trace", sa.Text(), nullable=True),
            sa.Column(
                "context", postgresql.JSONB(), nullable=False, server_default="{}"
            ),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_error_logs_level", "error_logs", ["level"])
        op.create_index("ix_error_logs_source", "error_logs", ["source"])
        op.create_index("ix_error_logs_user_id", "error_logs", ["user_id"])


def downgrade() -> None:
    """Remove all tables and columns added in this migration."""
    # Drop tables in reverse order (respecting FK dependencies)
    tables_to_drop = [
        "error_logs",
        "audit_logs",
        "telegram_link_codes",
        "job_executions",
        "scheduled_touchpoints",
        "scheduled_events",
        "user_narrative_arcs",
        "user_social_circles",
        "onboarding_states",
        "venue_cache",
        "user_backstories",
        "user_profiles",
        "engagement_history",
        "engagement_state",
        "nikita_thoughts",
        "conversation_threads",
        "generated_prompts",
    ]

    for table in tables_to_drop:
        if table_exists(table):
            op.drop_table(table)

    # Remove columns from daily_summaries
    for col in ["updated_at", "engagement_score", "emotional_tone", "key_moments", "summary_text"]:
        if column_exists("daily_summaries", col):
            op.drop_column("daily_summaries", col)

    # Remove columns from conversations
    for col in [
        "emotional_tone",
        "conversation_summary",
        "extracted_entities",
        "last_message_at",
        "processed_at",
        "processing_started_at",
        "processing_attempts",
        "status",
    ]:
        if column_exists("conversations", col):
            op.drop_column("conversations", col)

    # Remove columns from users
    for col in [
        "onboarding_call_id",
        "onboarded_at",
        "onboarding_profile",
        "onboarding_status",
        "cached_voice_context",
        "cached_voice_prompt_at",
        "cached_voice_prompt",
    ]:
        if column_exists("users", col):
            op.drop_column("users", col)

    # Remove constraint
    op.execute(
        """
        ALTER TABLE users DROP CONSTRAINT IF EXISTS check_onboarding_status_values;
        """
    )

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS engagement_state_enum;")
