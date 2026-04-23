-- Spec 214 FR-11c T1.1: portal_bridge_tokens table (resolves auth-M-A / plan D1).
--
-- Purpose: opaque single-use bridge tokens that route Telegram `/start`
-- entries into an authenticated portal session at /onboarding/auth.
--
-- Distinct from `auth_bridge_tokens` (5-min post-OTP bridge). The two
-- coexist by design; do NOT merge. See
-- nikita/db/models/portal_bridge_token.py for rationale.
--
-- RLS: admin + service_role only. Tokens are minted and consumed by
-- the backend service role exclusively (Telegram bot → portal auth).
-- No end-user has reason to SELECT or manipulate this table directly.

CREATE TABLE IF NOT EXISTS portal_bridge_tokens (
    token       TEXT PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason      TEXT NOT NULL CHECK (reason IN ('resume', 're-onboard')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_portal_bridge_tokens_user
    ON portal_bridge_tokens (user_id, consumed_at);

ALTER TABLE portal_bridge_tokens ENABLE ROW LEVEL SECURITY;

-- Single combined policy covers SELECT/INSERT/UPDATE/DELETE. The
-- WITH CHECK mirrors the USING clause so admin/service_role cannot
-- accidentally escalate-via-update (see .claude/rules/testing.md
-- DB Migration Checklist).
--
-- NOTE: production asyncpg pool connects as role 'postgres' which
-- bypasses RLS entirely. This policy gates PostgREST anon/authenticated
-- surfaces (future admin UI) and documents ownership intent.
CREATE POLICY "admin_and_service_role_only"
    ON portal_bridge_tokens
    FOR ALL
    USING (is_admin() OR auth.role() = 'service_role')
    WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- Hourly prune of expired rows. Keeps the table from growing unbounded
-- while preserving a short audit trail for recently consumed tokens.
-- Retention semantics: the prune treats consumed and unconsumed tokens
-- identically once expires_at has passed; both are removed at expires_at
-- + 6h. There is no longer-term forensic store for consumed tokens; if
-- one is ever needed it should land in a separate audit table, not by
-- relaxing this prune.
--
-- Idempotency: a second application of this migration must not fail
-- on duplicate jobname. The Supabase MCP migration applier runs as a
-- role without DELETE privilege on cron.job, so use the cron.unschedule()
-- API wrapped in a DO block.
--
-- Exception scope: pg_cron does not raise a stable SQLSTATE for "job
-- name not registered" (the expected first-apply path), so we catch
-- WHEN OTHERS. The leak is bounded in practice: any latent failure
-- (missing extension, revoked privilege, schema drift) re-throws on
-- the immediately following cron.schedule(...) call, which has no
-- exception handler.
DO $do_block$
BEGIN
    PERFORM cron.unschedule('portal_bridge_tokens_prune');
EXCEPTION WHEN OTHERS THEN
    NULL;
END
$do_block$;

SELECT cron.schedule(
    'portal_bridge_tokens_prune',
    '0 * * * *',
    $cron$
      DELETE FROM portal_bridge_tokens
       WHERE expires_at < now() - INTERVAL '6 hours';
    $cron$
);
