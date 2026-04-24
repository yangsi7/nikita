-- Spec 215 PR-F1a §9.1 + §7.2 — Telegram-first signup data layer.
--
-- Renames the legacy `pending_registrations` table to `telegram_signup_sessions`,
-- renames OTP-era columns to neutral signup-state names, expands the state
-- domain for the new FSM (awaiting_email → code_sent → magic_link_sent →
-- completed), adds magic-link tracking columns, and enables service-role-only
-- RLS.
--
-- Per .claude/rules/testing.md DB Migration Checklist:
--   - ENABLE RLS + service-role policy with WITH CHECK clause.
--   - chat_id retained verbatim (FR-11c routing dependency, data-layer H1).
--   - Existing columns RENAMED, not duplicated (data-layer H2).
--
-- Per spec §7.2.1: every FSM transition is a CAS UPDATE asserting the prior
-- state. The CHECK constraint enforces the closed domain at the DB level.

BEGIN;

-- 1. Rename the table. chat_id column is preserved verbatim.
ALTER TABLE IF EXISTS pending_registrations
    RENAME TO telegram_signup_sessions;

-- 2. Rename OTP-era columns to neutral signup-state names.
ALTER TABLE telegram_signup_sessions
    RENAME COLUMN otp_state TO signup_state;
ALTER TABLE telegram_signup_sessions
    RENAME COLUMN otp_attempts TO attempts;

-- 3. Drop the old CHECK constraint (if it exists; legacy table may have used
--    a NOT NULL DEFAULT only) and recreate over the new closed domain.
--    The legacy domain was {'pending','code_sent','verified','expired'};
--    the new domain is {'awaiting_email','code_sent','magic_link_sent',
--    'completed'}. Backfill happens before the new constraint goes live.
DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT con.conname INTO constraint_name
      FROM pg_constraint con
      JOIN pg_class      cls ON cls.oid = con.conrelid
     WHERE cls.relname = 'telegram_signup_sessions'
       AND con.contype = 'c'
       AND pg_get_constraintdef(con.oid) ILIKE '%signup_state%';
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE telegram_signup_sessions DROP CONSTRAINT %I',
                       constraint_name);
    END IF;
END $$;

-- 4. Backfill any existing rows to the new domain. Per spec §9.2 these 5
--    in-flight dev rows will be destructively reset post-deploy; for the
--    purposes of the migration they map cleanly to 'awaiting_email'.
UPDATE telegram_signup_sessions
   SET signup_state = 'awaiting_email'
 WHERE signup_state NOT IN ('awaiting_email','code_sent','magic_link_sent','completed');

-- 5. Apply the new closed domain CHECK.
ALTER TABLE telegram_signup_sessions
    ADD CONSTRAINT telegram_signup_sessions_signup_state_check
    CHECK (signup_state IN ('awaiting_email','code_sent','magic_link_sent','completed'));

-- 6. Update the column default to the new initial state.
ALTER TABLE telegram_signup_sessions
    ALTER COLUMN signup_state SET DEFAULT 'awaiting_email';

-- 7. ADD COLUMNs for magic-link tracking.
--    Storage contract (data-layer H5): magic_link_token stores ONLY the
--    hashed_token returned by supabase.auth.admin.generate_link, NEVER the
--    raw action_link query-string token. The action_link itself is delivered
--    via Telegram and not stored server-side after dispatch.
ALTER TABLE telegram_signup_sessions
    ADD COLUMN IF NOT EXISTS magic_link_token   TEXT       NULL,
    ADD COLUMN IF NOT EXISTS magic_link_sent_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS verification_type  TEXT       NULL,
    ADD COLUMN IF NOT EXISTS last_attempt_at    TIMESTAMPTZ NULL;

ALTER TABLE telegram_signup_sessions
    ADD CONSTRAINT telegram_signup_sessions_verification_type_check
    CHECK (verification_type IS NULL OR verification_type IN ('email','signup','magiclink','recovery'));

COMMENT ON COLUMN telegram_signup_sessions.magic_link_token IS
    'STORAGE CONTRACT (Spec 215 data-layer H5): stores ONLY the hashed_token '
    'returned by supabase.auth.admin.generate_link — NEVER the raw action_link '
    'query-string token. Hashed_token is opaque to the user; the action_link '
    'itself is delivered via Telegram and not stored server-side.';

-- 8. RLS — service-role only. End users cannot SELECT/INSERT/UPDATE/DELETE
--    pending signup state directly.
ALTER TABLE telegram_signup_sessions ENABLE ROW LEVEL SECURITY;

-- Drop any pre-existing legacy policy that may have been carried over from
-- the rename (defensive — pending_registrations did not have a policy in
-- the baseline, but be idempotent).
DO $$
DECLARE
    pol_name text;
BEGIN
    FOR pol_name IN
        SELECT policyname FROM pg_policies
         WHERE schemaname = 'public'
           AND tablename = 'telegram_signup_sessions'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON telegram_signup_sessions', pol_name);
    END LOOP;
END $$;

-- Service-role-only ALL policy. WITH CHECK mirrors USING to prevent
-- privilege escalation via UPDATE (per .claude/rules/testing.md).
-- NOTE: production asyncpg pool connects as role 'postgres' which bypasses
-- RLS entirely; this policy gates PostgREST anon/authenticated surfaces
-- and documents ownership intent.
CREATE POLICY "service_role_only"
    ON telegram_signup_sessions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMIT;
