-- Spec 216-D-migration: User profile inference + cache_key PII hashing
-- Applied via Supabase MCP after PR review (NOT applied by this agent).
--
-- Sections:
--   1. public.users new columns (D1.1, D1.2, D1.3, D1.10, D1.12)
--   2. CHECK constraints with idempotent DO-block guard (D1.11)
--   3. backstory_cache.cache_key sha256 backfill (D1.8, closes #446)
--
-- RLS: public.users already has RLS enabled (Spec 213 PR 213-2). New columns
-- inherit row-level scope automatically; no new policies required.
--
-- ROLLBACK at end of file (see trailing comment block).

-- ============================================================================
-- 1. public.users new columns (top-level — NOT JSONB-embedded per D1.10)
-- ============================================================================
-- big5_vector: 5 floats {O, C, E, A, N} + per-dim confidence dict, written
--   by per-turn claude-haiku-4-5 judge in 216-D-code (D1.5). Example shape:
--     {"O": 0.72, "C": 0.45, "E": 0.81, "A": 0.55, "N": 0.30,
--      "confidence": {"O": 0.85, "C": 0.6, "E": 0.9, "A": 0.5, "N": 0.4}}
--   No DB-level CHECK on shape; Pydantic validation in 216-D-code is the
--   write-side gate (TurnOutput excludes big5 per NR-05 hide-the-framework).
-- backstory_seed: ≤300 chars, persona-prose seed for backstory generation.
-- brand_resonance_signal: NUMERIC in [0, 1], cosine-similarity placeholder.
-- archetype_candidates: 3 LLM-picked archetype candidates (separate from
--   final backstory_pick), required for W4 walk G.6 verification (D1.12).
--   Example shape: [{"label": "the climber", "score": 0.72}, ...]

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS big5_vector JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS backstory_seed TEXT,
    ADD COLUMN IF NOT EXISTS brand_resonance_signal NUMERIC,
    ADD COLUMN IF NOT EXISTS archetype_candidates JSONB DEFAULT '[]'::jsonb;

-- ============================================================================
-- 2. CHECK constraints with idempotent DO-block guard (D1.11)
-- ============================================================================
-- PostgreSQL has no `ADD CONSTRAINT IF NOT EXISTS`. Guard via pg_constraint
-- lookup so re-running the migration is safe (matches canonical pattern at
-- 20260414213313_add_profile_fields_and_backstory_cache.sql:28-41).

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'check_users_backstory_seed_length'
          AND conrelid = 'public.users'::regclass
    ) THEN
        ALTER TABLE public.users
            ADD CONSTRAINT check_users_backstory_seed_length
            CHECK (backstory_seed IS NULL OR length(backstory_seed) <= 300);
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'check_users_brand_resonance_range'
          AND conrelid = 'public.users'::regclass
    ) THEN
        ALTER TABLE public.users
            ADD CONSTRAINT check_users_brand_resonance_range
            CHECK (brand_resonance_signal IS NULL
                   OR (brand_resonance_signal >= 0
                       AND brand_resonance_signal <= 1));
    END IF;
END;
$$;

-- ============================================================================
-- 3. backstory_cache.cache_key sha256 backfill (D1.8, closes #446)
-- ============================================================================
-- Walk W3 finding: cache_key contained raw lowercased city + occupation +
-- darkness as a pipe-delimited string (PII leak in primary key).
-- Hash existing rows to sha256-hex, leaving already-hashed rows untouched
-- via regex predicate (NOT length-based — raw keys can be ~60 chars and
-- accidentally match length 64).
--
-- Idempotent: re-running this UPDATE on already-hashed rows yields zero
-- matches via the `!~ '^[a-f0-9]{64}$'` predicate.

UPDATE public.backstory_cache
SET cache_key = encode(sha256(cache_key::bytea), 'hex')
WHERE cache_key IS NOT NULL
  AND cache_key !~ '^[a-f0-9]{64}$';

-- ============================================================================
-- ROLLBACK (down migration — execute manually if needed):
-- ============================================================================
-- ALTER TABLE public.users DROP CONSTRAINT IF EXISTS check_users_backstory_seed_length;
-- ALTER TABLE public.users DROP CONSTRAINT IF EXISTS check_users_brand_resonance_range;
-- ALTER TABLE public.users
--     DROP COLUMN IF EXISTS archetype_candidates,
--     DROP COLUMN IF EXISTS brand_resonance_signal,
--     DROP COLUMN IF EXISTS backstory_seed,
--     DROP COLUMN IF EXISTS big5_vector;
--
-- Note: backstory_cache.cache_key sha256 backfill is NOT reversible
-- (raw values irrecoverable). Rollback this section only by restoring
-- from a pre-migration snapshot of the backstory_cache table.
