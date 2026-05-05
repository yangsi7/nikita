-- Spec 216 EM-3b: Remove hardcoded Bearer secret from pg_cron HTTP jobs.
--
-- ============================================================================
-- WHAT THIS MIGRATION CHANGES
-- ============================================================================
--
-- The 3 nikita-* cron jobs registered in
-- `supabase/migrations/20260418141500_cron_heartbeat_engine.sql` (heartbeat-
-- hourly, generate-daily-arcs, touchpoints) embedded the TASK_AUTH_SECRET as
-- a literal Bearer token in the `headers` argument to `net.http_post(...)`.
-- The literal was grep-visible in the repo + DB dumps and could only be
-- rotated by editing every migration and re-applying — error-prone and a
-- security smell.
--
-- This migration re-schedules those 3 jobs to read the secret from a
-- Postgres GUC at command time:
--
--     coalesce(current_setting('app.task_auth_secret', true), '')
--
-- After this migration applies, rotation is `ALTER DATABASE postgres SET
-- app.task_auth_secret = '<new>'` away. The cron commands re-read the GUC
-- on every invocation, so a rotation propagates within one cron tick (max
-- 5 min for the most-frequent job, `nikita-touchpoints`).
--
-- ============================================================================
-- SCOPE: WHICH JOBS ARE COVERED HERE
-- ============================================================================
--
-- This migration re-schedules ONLY the 3 jobs whose
-- `cron.schedule(..., headers := '{"Authorization": "Bearer <literal>"}'...)`
-- form is grep-visible in repo migrations:
--
--     nikita-heartbeat-hourly
--     nikita-generate-daily-arcs
--     nikita-touchpoints
--
-- The prior version of this migration's header claimed "9 nikita-* cron
-- jobs"; that count came from the upstream comment in
-- `20260418141500_cron_heartbeat_engine.sql:4` referencing jobs registered
-- out-of-band (via Supabase MCP / dashboard). Examples cited at `:26`
-- include `nikita-deliver`, `nikita-decay`, `nikita-summary`. Those out-of-
-- band jobs are NOT visible to this migration — verifying their command
-- text requires DB access (e.g.,
-- `SELECT jobname, command FROM cron.job WHERE jobname LIKE 'nikita-%'`).
-- They likely embed the SAME literal and need the same substitution. That
-- enumeration + backfill is tracked under GH #521 (operator must enumerate
-- prod cron.job and apply the same `current_setting('app.task_auth_secret',
-- true)` substitution to any HTTP-posting job that still embeds the
-- literal).
--
-- The verification block at the end of this migration inspects ONLY the 3
-- in-scope jobs. Operators must additionally enumerate `nikita-%` jobs
-- post-apply (see POST-APPLY VERIFICATION step 1).
--
-- ============================================================================
-- DEPLOYMENT RUNBOOK (operator action REQUIRED before applying)
-- ============================================================================
--
-- !!! THIS MIGRATION DOES NOT WRITE THE SECRET !!!
--
-- The Postgres GUC `app.task_auth_secret` MUST be set OUT-OF-BAND BEFORE
-- this migration applies, otherwise Step 1 (pre-flight) raises and the
-- migration aborts before unscheduling any job. Run ONE of the following
-- methods, picking whichever your env supports:
--
--   1. Supabase Dashboard → Database → Database settings → Custom postgres
--      config:
--        Add row: `app.task_auth_secret = '<rotated_value>'`
--        Save and reload. Confirm via SQL Editor:
--          SELECT current_setting('app.task_auth_secret', true);
--        returns the value (open a NEW SQL tab — existing connections
--        do not refresh ALTER DATABASE-set GUCs).
--
--   2. SQL Editor (Supabase Dashboard → SQL Editor) — run as the database
--      owner role:
--        ALTER DATABASE postgres SET app.task_auth_secret = '<rotated_value>';
--        SELECT pg_reload_conf();
--      Then OPEN A NEW QUERY TAB and run
--        SELECT current_setting('app.task_auth_secret', true);
--      to confirm. ALTER DATABASE-set GUCs only apply to NEW connections.
--
--   3. `gcloud sql connect` (or psql via direct connection string), as a
--      role with ALTER DATABASE privilege:
--        ALTER DATABASE postgres SET app.task_auth_secret = '<rotated_value>';
--        SELECT pg_reload_conf();
--      Reconnect (\q + relaunch) before verifying with current_setting().
--
-- After setting the GUC, run the migration. If Step 1 raises, fix the GUC
-- and re-run.
--
-- ============================================================================
-- POST-APPLY VERIFICATION (operator action REQUIRED after applying)
-- ============================================================================
--
-- 1. Confirm all 3 in-scope jobs were re-scheduled with the GUC pattern AND
--    audit any out-of-band nikita-% jobs for the same literal:
--      SELECT jobname, command
--      FROM cron.job
--      WHERE jobname LIKE 'nikita-%'
--      ORDER BY jobname;
--    For each row, `command` should contain
--    `current_setting('app.task_auth_secret', true)` and NO Bearer literal.
--    Any `nikita-*` row that still contains a Bearer literal → file a
--    follow-up issue + apply the same `cron.unschedule` + `cron.schedule`
--    substitution that this migration applies for the 3 in-scope jobs.
--
-- 2. GUC scope vs cron worker connection lifecycle: pg_cron's bgworker
--    opens fresh connections per tick to run scheduled commands. ALTER
--    DATABASE ... SET sets a per-database default that NEW connections
--    pick up. Therefore the worker picks up the new GUC on the next tick
--    after `ALTER DATABASE ... SET` + `pg_reload_conf()` — there is NO
--    need to restart the cron worker. If you observe the cron worker
--    sending stale-secret requests (401 from /api/v1/tasks/...), force a
--    refresh by running `SELECT pg_reload_conf();` again, or in the
--    pathological case bounce the bgworker via `pg_cancel_backend(pid)`
--    on the cron-worker backend (see `pg_stat_activity WHERE
--    application_name = 'pg_cron'`).
--
-- 3. Confirm propagation by reading the next cron-tick HTTP request from
--    Cloud Run logs:
--      gcloud logging read --project=gcp-transcribe-test \
--        'resource.type=cloud_run_revision AND
--         resource.labels.service_name=nikita-api AND
--         httpRequest.requestUrl=~"/api/v1/tasks/touchpoints"' \
--        --limit=2 --freshness=10m
--    Look for HTTP 200 (not 401). 401 means the GUC was unset or stale.
--
-- 4. ROTATION (post-merge, ongoing): to rotate the secret, issue
--      ALTER DATABASE postgres SET app.task_auth_secret = '<new>';
--      SELECT pg_reload_conf();
--    AND update the Cloud Run env var `TASK_AUTH_SECRET` to match. Do NOT
--    re-apply this migration. The rotation propagates to the cron worker
--    on the next tick.
--
-- ============================================================================
-- ROLLBACK
-- ============================================================================
--
-- If verification fails (Step 3 below raises) or the cron worker rejects
-- the GUC pattern in your env, you have two recovery paths:
--
--   (a) IDEMPOTENT RE-RUN — preferred. Fix the GUC value (or check for
--       privilege issues on `ALTER DATABASE`), then re-apply this
--       migration. The migration is idempotent end-to-end:
--         - Step 1 pre-flight check is read-only
--         - Step 2 cron.unschedule + cron.schedule replace existing jobs
--           (cron.schedule is upsert-by-name)
--         - Step 3 verification is read-only
--       No DB state from a partial prior run blocks a re-apply.
--
--   (b) RESTORE PRIOR LITERAL FORM — break-glass only. Re-run the literal
--       `cron.schedule(...)` blocks from
--       `supabase/migrations/20260418141500_cron_heartbeat_engine.sql:35-90`
--       (after `cron.unschedule(...)` of the same job names) to fall back.
--       This re-introduces the literal in the running DB but unblocks
--       deploys; track follow-up to rotate the secret + re-apply this
--       migration.
--
-- A standalone rollback SQL file is intentionally NOT shipped: it would
-- contain the literal verbatim. The literal is captured ONCE in the prior
-- migration (already in git history) and (a) is preferred.
--
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Step 1: Pre-flight — fail loudly if the GUC is unset.
-- Short-circuits BEFORE any cron.unschedule so a misconfigured deploy does
-- not leave jobs in a half-applied state.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  guc_value text;
BEGIN
  guc_value := current_setting('app.task_auth_secret', true);
  IF guc_value IS NULL OR length(guc_value) = 0 THEN
    RAISE EXCEPTION
      'GUC app.task_auth_secret is not set; run: ALTER DATABASE postgres SET app.task_auth_secret = ''<rotated_value>''; SELECT pg_reload_conf(); in a NEW connection BEFORE applying this migration. See migration header DEPLOYMENT RUNBOOK for full instructions.';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Step 2: Re-schedule the 3 heartbeat-engine cron jobs to read the secret
-- from current_setting() instead of hardcoding it. Same schedules + URLs as
-- 20260418141500_cron_heartbeat_engine.sql.
-- ---------------------------------------------------------------------------

DO $$
BEGIN
  PERFORM cron.unschedule('nikita-heartbeat-hourly')
  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nikita-heartbeat-hourly');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  PERFORM cron.unschedule('nikita-generate-daily-arcs')
  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nikita-generate-daily-arcs');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  PERFORM cron.unschedule('nikita-touchpoints')
  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nikita-touchpoints');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

SELECT cron.schedule(
    'nikita-heartbeat-hourly',
    '0 * * * *',
    $cron$
    SELECT net.http_post(
        url := 'https://nikita-api-1040094048579.us-central1.run.app/api/v1/tasks/heartbeat',
        body := '{}'::jsonb,
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || coalesce(current_setting('app.task_auth_secret', true), ''),
            'Content-Type', 'application/json'
        )
    );
    $cron$
);

SELECT cron.schedule(
    'nikita-generate-daily-arcs',
    '0 5 * * *',
    $cron$
    SELECT net.http_post(
        url := 'https://nikita-api-1040094048579.us-central1.run.app/api/v1/tasks/generate-daily-arcs',
        body := '{}'::jsonb,
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || coalesce(current_setting('app.task_auth_secret', true), ''),
            'Content-Type', 'application/json'
        )
    );
    $cron$
);

SELECT cron.schedule(
    'nikita-touchpoints',
    '*/5 * * * *',
    $cron$
    SELECT net.http_post(
        url := 'https://nikita-api-1040094048579.us-central1.run.app/api/v1/tasks/touchpoints',
        body := '{}'::jsonb,
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || coalesce(current_setting('app.task_auth_secret', true), ''),
            'Content-Type', 'application/json'
        )
    );
    $cron$
);

-- ---------------------------------------------------------------------------
-- Step 3: Verification — assert all 3 in-scope jobs use current_setting()
-- and contain no literal of the prior secret. Raises if any job slipped
-- through.
--
-- NOTE: This block inspects ONLY the 3 in-scope jobs. Operators MUST also
-- run the post-apply Step 1 query to enumerate all `nikita-%` jobs and
-- audit out-of-band ones for the same literal.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  bad_jobs text[];
BEGIN
  SELECT array_agg(jobname) INTO bad_jobs
  FROM cron.job
  WHERE jobname IN ('nikita-heartbeat-hourly', 'nikita-generate-daily-arcs', 'nikita-touchpoints')
    AND (command NOT LIKE '%current_setting(%app.task_auth_secret%' OR command LIKE '%S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0%');

  IF bad_jobs IS NOT NULL THEN
    RAISE EXCEPTION 'cron jobs still contain hardcoded secret or missing current_setting(): %', bad_jobs;
  END IF;
END $$;
