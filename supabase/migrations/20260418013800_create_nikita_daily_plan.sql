-- Spec 215 PR 215-A: Heartbeat Engine foundation — nikita_daily_plan table
-- Applied via Supabase MCP after PR review (NOT applied by this agent automatically).
--
-- Sections:
--   1. nikita_daily_plan table (FR-001/FR-002 — daily plan persistence)
--   2. Indexes (idempotency unique + cron query partial + observability)
--   3. RLS policies (FR-008 game-state respect, FR-015 PII protection)
--
-- ROLLBACK at end of file (see trailing comment block).
--
-- Source: plan.md T2.1 (with iter-2 GATE 2 fixes H-5, H-7, H-8, H-10, M-12, M-13, M-15)

-- ============================================================================
-- 1. nikita_daily_plan table
-- ============================================================================
-- Stores Nikita's LLM-generated daily emotional arc per user, used by the
-- /tasks/heartbeat handler to drive proactive touchpoints.
--
-- Phase 1 schema acknowledgment (Plan v4 R7): arc_json holds a discrete
-- step list (6-12 timestamped intentions). Phase 2 introduces a parallel
-- nikita_daily_intensity_state table for the continuous-distribution model;
-- this Phase 1 table is intentionally throwaway-compatible and will not be
-- extended by Phase 2.

CREATE TABLE IF NOT EXISTS public.nikita_daily_plan (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    -- plan_date validity range: lower bound rejects prehistoric/clock-skew
    -- writes; upper bound allows up to 14 days of forward-scheduling slack
    -- (Phase 2 backfill scenarios may write today + 7-14 days; the wider
    -- bound prevents false rejects at the timezone-skew boundary between
    -- Cloud Run UTC and Postgres UTC).
    plan_date       DATE         NOT NULL CHECK (plan_date BETWEEN '2020-01-01' AND CURRENT_DATE + INTERVAL '14 days'),
    arc_json        JSONB        NOT NULL,
    narrative_text  TEXT         NOT NULL,
    generated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    model_used      TEXT
);

-- ============================================================================
-- 2. Indexes
-- ============================================================================

-- Unique index for idempotency (FR-002 AC-FR2-002):
-- one plan per (user_id, plan_date); upsert via ON CONFLICT.
-- This index also serves the cron's "today's plan" lookup: the planner
-- queries by (user_id, plan_date) which uses the leading user_id of this
-- index efficiently. No separate plan_date-only index is needed
-- (plan.md AC-T2.1-007 originally proposed a partial index on plan_date
-- but Postgres requires IMMUTABLE predicates and CURRENT_DATE is STABLE,
-- so a partial form is not expressible; a full plan_date index would be
-- redundant with this composite for the cron access pattern).
CREATE UNIQUE INDEX IF NOT EXISTS idx_nikita_daily_plan_user_date
    ON public.nikita_daily_plan (user_id, plan_date);

-- Index on generated_at for cost/observability queries (M-13 fix).
-- The /tasks/generate-daily-arcs handler logs total LLM spend per day; this
-- index supports time-bucketed aggregation for the cost circuit breaker.
CREATE INDEX IF NOT EXISTS idx_nikita_daily_plan_generated_at
    ON public.nikita_daily_plan (generated_at DESC);

-- ============================================================================
-- 3. RLS policies
-- ============================================================================
-- H-5 fix: explicit per-verb policies + WITH CHECK clauses to prevent silent
-- privilege escalation. Service-role token bypasses RLS entirely (standard
-- Supabase pattern). DO NOT add a service_role policy here.

ALTER TABLE public.nikita_daily_plan ENABLE ROW LEVEL SECURITY;

-- Authenticated users: read own plans only (FR-015 PII protection)
CREATE POLICY nikita_daily_plan_select_own ON public.nikita_daily_plan
    FOR SELECT
    TO authenticated
    USING (user_id = (SELECT auth.uid()));

-- Authenticated users: deny all writes (only the service-role pg_cron
-- handler may insert/update/delete plans). Subquery form of auth.uid()
-- avoids per-row function eval overhead. WITH CHECK (false) closes the
-- silent-escalation gap that a missing WITH CHECK would create.
CREATE POLICY nikita_daily_plan_no_write_authenticated ON public.nikita_daily_plan
    FOR ALL
    TO authenticated
    USING (false)
    WITH CHECK (false);

-- Anon: deny everything. RLS default-deny already covers anon when no
-- permissive policy matches, but making the intent explicit removes
-- ambiguity and surfaces in policy audits
-- (SELECT * FROM pg_policies WHERE tablename = 'nikita_daily_plan').
CREATE POLICY nikita_daily_plan_no_anon ON public.nikita_daily_plan
    FOR ALL
    TO anon
    USING (false)
    WITH CHECK (false);

-- ============================================================================
-- ROLLBACK (down migration — execute manually if needed):
-- ============================================================================
-- DROP POLICY IF EXISTS nikita_daily_plan_no_anon ON public.nikita_daily_plan;
-- DROP POLICY IF EXISTS nikita_daily_plan_no_write_authenticated ON public.nikita_daily_plan;
-- DROP POLICY IF EXISTS nikita_daily_plan_select_own ON public.nikita_daily_plan;
-- DROP INDEX IF EXISTS idx_nikita_daily_plan_generated_at;
-- DROP INDEX IF EXISTS idx_nikita_daily_plan_user_date;
-- DROP TABLE IF EXISTS public.nikita_daily_plan;
