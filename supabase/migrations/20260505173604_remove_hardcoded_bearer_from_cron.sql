-- Spec 216 EM-3b: Remove hardcoded Bearer secret from pg_cron HTTP jobs.
--
-- The 9 nikita-* cron jobs were registered with the TASK_AUTH_SECRET embedded
-- as a literal in `cron.schedule(... headers := '{"Authorization": "Bearer
-- S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0"}'::jsonb ...)`. Three of those
-- live in 20260418141500_cron_heartbeat_engine.sql (heartbeat-hourly,
-- generate-daily-arcs, touchpoints). Rotating the secret previously required
-- editing every literal and re-applying every migration — error-prone and a
-- security smell (the secret is grep-visible in the repo + DB dumps).
--
-- This migration moves the secret to a Postgres GUC (Grand Unified Config)
-- read at command time via `current_setting('app.task_auth_secret', true)`.
-- Operators set the GUC once via:
--
--     ALTER DATABASE postgres SET app.task_auth_secret = '<rotated-secret>';
--     SELECT pg_reload_conf();
--
-- After that, rotation is an `ALTER DATABASE ... SET ...` away — no migration
-- replay required. The cron commands re-read the current value on every
-- invocation, so a rotation propagates within one cron tick (max 5 min for
-- the most-frequent job).
--
-- DEPLOYMENT RUNBOOK:
--   1. Apply this migration. The 3 jobs are re-scheduled to read from the
--      GUC. If the GUC is unset, it returns NULL and the Authorization
--      header becomes 'Bearer ' (empty) — task endpoints reject this with
--      401 (verify_task_secret). To avoid an outage window, this migration
--      pre-seeds the GUC with the existing literal as a placeholder; the
--      coordinator will rotate the secret in a separate step.
--   2. Coordinator rotates: `ALTER DATABASE postgres SET app.task_auth_secret
--      = '<new>'` + Cloud Run env var update (TASK_AUTH_SECRET) + reload.
--   3. Verify the next cron tick succeeds (gcloud logging read the task
--      endpoint hit in /api/v1/tasks/heartbeat etc.).
--
-- This migration is IDEMPOTENT: cron.unschedule-then-schedule per job, and
-- ALTER DATABASE SET is naturally idempotent.

-- ---------------------------------------------------------------------------
-- Step 1: Pre-seed the GUC with the existing literal (placeholder, rotated
-- by coordinator post-merge). This prevents an outage window where the GUC
-- is unset and cron jobs send empty Bearer tokens.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  -- Use ALTER DATABASE so the GUC persists across connections. We cannot use
  -- current_database() inside ALTER DATABASE syntactically, so we read the
  -- name first via format/EXECUTE.
  EXECUTE format(
    'ALTER DATABASE %I SET app.task_auth_secret = %L',
    current_database(),
    'S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0'
  );
EXCEPTION WHEN insufficient_privilege THEN
  -- Supabase-managed Postgres may restrict ALTER DATABASE; in that case the
  -- GUC must be set out-of-band. Log and continue — the cron jobs will use
  -- whatever value `current_setting` returns at invocation time.
  RAISE NOTICE 'ALTER DATABASE skipped (insufficient_privilege); set app.task_auth_secret out-of-band';
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
-- Step 3: Verification — assert all 3 jobs use current_setting() and contain
-- no literal of the prior secret. Raises if any job slipped through.
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
