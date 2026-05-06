-- Spec 216 EM-3b (revised 2026-05-06): Remove hardcoded Bearer secret from
-- pg_cron HTTP jobs by reading TASK_AUTH_SECRET from Supabase Vault on every
-- tick.
--
-- ============================================================================
-- WHY THIS REPLACED THE PRIOR ALTER-DATABASE / GUC PATTERN
-- ============================================================================
--
-- The prior version of this migration (commit c0d6bbf, 2026-05-05) re-scheduled
-- 3 cron jobs to read the secret from a Postgres GUC named
-- `app.task_auth_secret`. Pre-flight required the GUC to be set out-of-band
-- before applying.
--
-- Live test (2026-05-06) confirmed Supabase platform GATES `ALTER DATABASE
-- postgres SET app.<custom>` to internal roles only; the `postgres` role
-- (including the service-role-key path) returns
-- `permission denied to set parameter "app.task_auth_secret"`. The
-- supautils-allowed list (https://supabase.com/docs/guides/database/custom-postgres-config)
-- enumerates the supported `app.*` overrides; `app.task_auth_secret` is NOT
-- in that list. Outcome: the GUC pattern is unreachable programmatically;
-- it requires Dashboard → Database settings → Custom postgres config
-- (manual step), which violates the "do it yourself" requirement.
--
-- Solution: switch to Supabase Vault (`vault.create_secret` /
-- `vault.decrypted_secrets` view). Vault is SQL-only, no Dashboard
-- dependency, role-permission consistent with the postgres role used by
-- pg_cron, and rotation-friendly (single `vault.update_secret` call
-- propagates to the next cron tick).
--
-- ============================================================================
-- WHAT THIS MIGRATION CHANGES
-- ============================================================================
--
-- Re-schedules every cron job whose command embeds a literal
-- `Authorization: Bearer S7fBv...` (the rotated-2026-05-06 prior literal)
-- so it reads the bearer from the Vault entry named `task_auth_secret`
-- on each tick:
--
--   headers := jsonb_build_object(
--     'Authorization', 'Bearer ' ||
--       (SELECT decrypted_secret FROM vault.decrypted_secrets
--        WHERE name = 'task_auth_secret'),
--     'Content-Type', 'application/json'
--   )
--
-- Coverage = ALL 11 nikita-* / nikita_* / psyche-* HTTP cron jobs
-- (post-2026-05-06 audit; the prior 3-job scope was incomplete):
--
--   nikita-cleanup, nikita-decay, nikita-deliver,
--   nikita-generate-daily-arcs, nikita-heartbeat-hourly,
--   nikita-process-conversations, nikita-refresh-voice-prompts,
--   nikita-summary, nikita-touchpoints,
--   nikita_handoff_greeting_backstop, psyche-batch-daily.
--
-- Non-HTTP jobs (cron-cleanup, portal_bridge_tokens_prune,
-- cleanup-pipeline-events) are untouched.
--
-- ============================================================================
-- DEPLOYMENT RUNBOOK
-- ============================================================================
--
-- BEFORE applying this migration:
--   1. Add the secret to Vault (one-time): in psql or Supabase SQL Editor,
--      SELECT vault.create_secret('<task_auth_secret_value>', 'task_auth_secret',
--                                 'pg_cron HTTP auth Bearer');
--      Verify: SELECT length(decrypted_secret) FROM vault.decrypted_secrets
--              WHERE name = 'task_auth_secret';   -- must be > 0
--
--   2. Confirm the same value is in Cloud Run env TASK_AUTH_SECRET (via
--      Secret Manager nikita-task-auth-secret). The cron tick sends what
--      Vault returns; the BE compares against env. If mismatch -> 401.
--      Live trap (2026-05-06): a trailing newline in `gcloud secrets
--      versions add --data-file=...` causes a 1-byte mismatch. Use
--      `tr -d '\n' < secret.txt > secret.notrailing.txt` before adding.
--
-- After applying:
--   3. Verify no cron job still has a Bearer literal:
--      SELECT jobname FROM cron.job
--      WHERE command LIKE '%Bearer S%' AND command NOT LIKE '%vault.decrypted_secrets%';
--      Must return 0 rows.
--
--   4. Wait one cron tick (60s for nikita_handoff_greeting_backstop, max
--      300s for the */5 jobs). Verify in net._http_response:
--      SELECT status_code, count(*) FROM net._http_response
--      WHERE created > now() - interval '5 minutes' GROUP BY 1;
--      Expect status_code=200; ZERO 401.
--
-- Rotation (post-merge):
--   1. Update Secret Manager: gcloud secrets versions add
--      nikita-task-auth-secret --data-file=secret.notrailing.txt
--   2. Force Cloud Run rev: gcloud run services update nikita-api
--      --update-secrets=TASK_AUTH_SECRET=nikita-task-auth-secret:latest
--   3. Update Vault: SELECT vault.update_secret(id, '<new>')
--      FROM vault.decrypted_secrets WHERE name = 'task_auth_secret';
--   4. (optional) Destroy old secret versions: gcloud secrets versions
--      destroy <N> --secret=nikita-task-auth-secret
--   5. Verify net._http_response status_code=200 within 300s.
--
-- ============================================================================
-- IDEMPOTENCY
-- ============================================================================
--
-- cron.unschedule + cron.schedule REPLACE jobs by jobname. Re-running this
-- migration is safe: jobs are unscheduled then re-created with identical
-- command text. No DB state from a prior partial run blocks re-apply.
--
-- The pre-flight check (Step 1) only verifies Vault holds the secret. If
-- the Vault entry is missing, Step 1 RAISEs and the migration aborts
-- BEFORE touching cron.

-- ---------------------------------------------------------------------------
-- Step 1: Pre-flight — fail loudly if Vault is missing the secret.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  vault_len int;
BEGIN
  SELECT length(decrypted_secret)
    INTO vault_len
    FROM vault.decrypted_secrets
    WHERE name = 'task_auth_secret'
    LIMIT 1;
  IF vault_len IS NULL OR vault_len = 0 THEN
    RAISE EXCEPTION
      'Vault entry "task_auth_secret" missing or empty. Add it via SELECT vault.create_secret(''<value>'', ''task_auth_secret'', ''pg_cron HTTP auth Bearer'') BEFORE applying. See migration header DEPLOYMENT RUNBOOK.';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Step 2: Re-schedule every HTTP cron job to read the bearer from Vault.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  jobs jsonb := jsonb_build_array(
    jsonb_build_object('name','nikita-cleanup',                  'schedule','30 * * * *',     'path','cleanup'),
    jsonb_build_object('name','nikita-decay',                    'schedule','0 * * * *',      'path','decay'),
    jsonb_build_object('name','nikita-deliver',                  'schedule','*/5 * * * *',    'path','deliver'),
    jsonb_build_object('name','nikita-generate-daily-arcs',      'schedule','0 5 * * *',      'path','generate-daily-arcs'),
    jsonb_build_object('name','nikita-heartbeat-hourly',         'schedule','0 * * * *',      'path','heartbeat'),
    jsonb_build_object('name','nikita-process-conversations',    'schedule','*/5 * * * *',    'path','process-conversations'),
    jsonb_build_object('name','nikita-refresh-voice-prompts',    'schedule','0 */6 * * *',    'path','refresh-voice-prompts'),
    jsonb_build_object('name','nikita-summary',                  'schedule','0 */6 * * *',    'path','summary'),
    jsonb_build_object('name','nikita-touchpoints',              'schedule','*/5 * * * *',    'path','touchpoints'),
    jsonb_build_object('name','nikita_handoff_greeting_backstop','schedule','* * * * *',      'path','retry-handoff-greetings'),
    jsonb_build_object('name','psyche-batch-daily',              'schedule','15 3 * * *',     'path','psyche-batch')
  );
  job jsonb;
  cmd text;
BEGIN
  FOR job IN SELECT jsonb_array_elements(jobs) LOOP
    BEGIN
      PERFORM cron.unschedule((job->>'name'));
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    cmd := format($S$
    SELECT net.http_post(
        url := 'https://nikita-api-1040094048579.us-central1.run.app/api/v1/tasks/%s',
        body := '{}'::jsonb,
        headers := jsonb_build_object(
          'Authorization', 'Bearer ' || (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'task_auth_secret'),
          'Content-Type', 'application/json'
        )
    );
    $S$, job->>'path');

    PERFORM cron.schedule(job->>'name', job->>'schedule', cmd);
  END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- Step 3: Verify no Bearer literal remains in any cron command.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  literal_count int;
BEGIN
  SELECT count(*)
    INTO literal_count
    FROM cron.job
    WHERE command LIKE '%Bearer S%'
      AND command NOT LIKE '%vault.decrypted_secrets%';
  IF literal_count > 0 THEN
    RAISE EXCEPTION
      '% cron job(s) still embed a Bearer literal post-migration; expected 0. Inspect: SELECT jobname, command FROM cron.job WHERE command LIKE ''%%Bearer S%%'' AND command NOT LIKE ''%%vault.decrypted_secrets%%'';',
      literal_count;
  END IF;
END $$;
