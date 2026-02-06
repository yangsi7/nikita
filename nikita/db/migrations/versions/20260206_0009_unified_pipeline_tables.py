"""Unified pipeline tables - memory_facts + ready_prompts.

Revision ID: 0009
Revises: 0008
Create Date: 2026-02-06

Spec 042: Unified Pipeline Refactor
- T0.1: Create memory_facts and ready_prompts tables
- T0.2: Create IVFFlat + unique indexes
- T0.7: Add RLS policies
"""

from alembic import op


# revision identifiers
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── memory_facts table ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_facts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            graph_type TEXT NOT NULL CHECK (graph_type IN ('user', 'relationship', 'nikita')),
            fact TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
            embedding vector(1536) NOT NULL,
            metadata JSONB DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            superseded_by UUID REFERENCES memory_facts(id) ON DELETE SET NULL,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── ready_prompts table ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS ready_prompts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            platform TEXT NOT NULL CHECK (platform IN ('text', 'voice')),
            prompt_text TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            context_snapshot JSONB,
            pipeline_version TEXT NOT NULL,
            generation_time_ms REAL NOT NULL,
            is_current BOOLEAN NOT NULL DEFAULT TRUE,
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── Indexes (T0.2) ─────────────────────────────────────────────────

    # IVFFlat index for semantic search on memory_facts.embedding
    # lists=50 works on empty tables with pgvector 0.5+
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_facts_embedding_cosine
        ON memory_facts
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
    """)

    # Composite index for filtered lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_facts_user_graph_active
        ON memory_facts (user_id, graph_type, created_at DESC)
        WHERE is_active = TRUE
    """)

    # Partial unique index: only one current prompt per user/platform
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ready_prompts_current
        ON ready_prompts (user_id, platform)
        WHERE is_current = TRUE
    """)

    # Index for history lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ready_prompts_user_created
        ON ready_prompts (user_id, created_at DESC)
    """)

    # ── RLS Policies (T0.7) ────────────────────────────────────────────

    # memory_facts RLS
    op.execute("ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY memory_facts_user_select ON memory_facts
        FOR SELECT USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY memory_facts_user_insert ON memory_facts
        FOR INSERT WITH CHECK (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY memory_facts_user_update ON memory_facts
        FOR UPDATE USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY memory_facts_user_delete ON memory_facts
        FOR DELETE USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY memory_facts_service_role ON memory_facts
        FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE)
    """)

    # ready_prompts RLS
    op.execute("ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY ready_prompts_user_select ON ready_prompts
        FOR SELECT USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY ready_prompts_user_insert ON ready_prompts
        FOR INSERT WITH CHECK (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY ready_prompts_user_update ON ready_prompts
        FOR UPDATE USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY ready_prompts_user_delete ON ready_prompts
        FOR DELETE USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY ready_prompts_service_role ON ready_prompts
        FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE)
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS memory_facts_service_role ON memory_facts")
    op.execute("DROP POLICY IF EXISTS memory_facts_user_delete ON memory_facts")
    op.execute("DROP POLICY IF EXISTS memory_facts_user_update ON memory_facts")
    op.execute("DROP POLICY IF EXISTS memory_facts_user_insert ON memory_facts")
    op.execute("DROP POLICY IF EXISTS memory_facts_user_select ON memory_facts")

    op.execute("DROP POLICY IF EXISTS ready_prompts_service_role ON ready_prompts")
    op.execute("DROP POLICY IF EXISTS ready_prompts_user_delete ON ready_prompts")
    op.execute("DROP POLICY IF EXISTS ready_prompts_user_update ON ready_prompts")
    op.execute("DROP POLICY IF EXISTS ready_prompts_user_insert ON ready_prompts")
    op.execute("DROP POLICY IF EXISTS ready_prompts_user_select ON ready_prompts")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_ready_prompts_user_created")
    op.execute("DROP INDEX IF EXISTS idx_ready_prompts_current")
    op.execute("DROP INDEX IF EXISTS idx_memory_facts_user_graph_active")
    op.execute("DROP INDEX IF EXISTS idx_memory_facts_embedding_cosine")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS ready_prompts")
    op.execute("DROP TABLE IF EXISTS memory_facts")
