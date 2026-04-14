-- Spec 213 PR 213-2: Add profile fields + backstory_cache table + RLS hardening
-- Applied via Supabase MCP after PR review (NOT applied by this agent).
--
-- Sections:
--   1. user_profiles extension (FR-1a)
--   2. backstory_cache table (FR-12)
--   3. backstory_cache RLS — admin-only via service_role bypass (FR-12)
--   4. user_profiles RLS hardening (FR-7 + TP.2)
--
-- ROLLBACK at end of file (see trailing comment block).

-- ============================================================================
-- 1. user_profiles extension (FR-1a)
-- ============================================================================
-- name: net-new personalization field (not on any prior column)
-- occupation: net-new on DB+ORM (already on UserOnboardingProfile Pydantic model)
-- age: SMALLINT, CHECK ensures 18-99 range; net-new on DB+ORM

-- VARCHAR(100) matches the ORM (String(100) in nikita/db/models/profile.py)
-- so DB and ORM agree on max length. Prior DDL used unbounded TEXT which
-- would silently accept rows exceeding the ORM contract (QA iter-1 F3).
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS name VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS occupation VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS age SMALLINT;

-- Add CHECK constraint for age (matches FR-1a DDL intent, guards DB layer)
-- Note: IF NOT EXISTS is not supported for constraints; guard with DO block
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'check_user_profiles_age_range'
          AND conrelid = 'user_profiles'::regclass
    ) THEN
        ALTER TABLE user_profiles
            ADD CONSTRAINT check_user_profiles_age_range
            CHECK (age IS NULL OR (age BETWEEN 18 AND 99));
    END IF;
END;
$$;

-- Index for age-based queries (analytics / matching)
CREATE INDEX IF NOT EXISTS idx_user_profiles_age
    ON user_profiles (age)
    WHERE age IS NOT NULL;

-- ============================================================================
-- 2. backstory_cache table (FR-12)
-- ============================================================================
-- Admin-only cache: maps segment key → generated BackstoryOption list
-- PK: cache_key (TEXT) — NOT UUID; cache semantics, key encodes segment

CREATE TABLE IF NOT EXISTS backstory_cache (
    cache_key        TEXT        PRIMARY KEY,
    scenarios        JSONB       NOT NULL,
    venues_used      JSONB       NOT NULL DEFAULT '[]'::jsonb,
    ttl_expires_at   TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for TTL sweep (cleanup expired entries)
CREATE INDEX IF NOT EXISTS idx_backstory_cache_ttl
    ON backstory_cache (ttl_expires_at);

-- ============================================================================
-- 3. backstory_cache RLS — admin-only (FR-12)
-- ============================================================================
-- is_admin() helper is NOT defined in this codebase.
-- Use USING (false) / WITH CHECK (false) to block all authenticated access.
-- Service_role token bypasses RLS entirely (standard Supabase pattern).

ALTER TABLE backstory_cache ENABLE ROW LEVEL SECURITY;

-- Block all authenticated access; service_role bypasses RLS
CREATE POLICY "backstory_cache_admin_only" ON backstory_cache
    FOR ALL
    TO authenticated
    USING (false)
    WITH CHECK (false);

-- QA iter-1 F5 defense-in-depth: explicit deny for anon role.
-- RLS default-deny already covers anon when no permissive policy matches,
-- but making the intent explicit removes ambiguity and surfaces in policy
-- audits (``SELECT * FROM pg_policies WHERE tablename = 'backstory_cache'``).
CREATE POLICY "backstory_cache_anon_denied" ON backstory_cache
    FOR ALL
    TO anon
    USING (false)
    WITH CHECK (false);

-- ============================================================================
-- 4. user_profiles RLS hardening (FR-7 + TP.2)
-- ============================================================================
-- UPDATE: add WITH CHECK to prevent id-swap attacks
-- (subquery form for auth.uid() avoids per-row function eval overhead)

DROP POLICY IF EXISTS "Users update own profile" ON user_profiles;
CREATE POLICY "Users update own profile" ON user_profiles
    FOR UPDATE
    TO authenticated
    USING (id = (SELECT auth.uid()))
    WITH CHECK (id = (SELECT auth.uid()));

-- DELETE: explicit subquery form (semantically equivalent; matches policy name)
DROP POLICY IF EXISTS "Users delete own profile" ON user_profiles;
CREATE POLICY "Users delete own profile" ON user_profiles
    FOR DELETE
    TO authenticated
    USING (id = (SELECT auth.uid()));

-- ============================================================================
-- ROLLBACK (down migration — execute manually if needed):
-- ============================================================================
-- DROP INDEX IF EXISTS idx_user_profiles_age;
-- ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS check_user_profiles_age_range;
-- ALTER TABLE user_profiles
--     DROP COLUMN IF EXISTS name,
--     DROP COLUMN IF EXISTS occupation,
--     DROP COLUMN IF EXISTS age;
--
-- -- Drop policies BEFORE dropping the table to keep piecemeal rollbacks clean:
-- DROP POLICY IF EXISTS "backstory_cache_anon_denied" ON backstory_cache;
-- DROP POLICY IF EXISTS "backstory_cache_admin_only" ON backstory_cache;
-- DROP INDEX IF EXISTS idx_backstory_cache_ttl;
-- DROP TABLE IF EXISTS backstory_cache;
--
-- -- Restore original UPDATE policy (without WITH CHECK) if needed:
-- DROP POLICY IF EXISTS "Users update own profile" ON user_profiles;
-- CREATE POLICY "Users update own profile" ON user_profiles
--     FOR UPDATE TO authenticated USING (id = auth.uid());
--
-- DROP POLICY IF EXISTS "Users delete own profile" ON user_profiles;
-- CREATE POLICY "Users delete own profile" ON user_profiles
--     FOR DELETE TO authenticated USING (id = auth.uid());
