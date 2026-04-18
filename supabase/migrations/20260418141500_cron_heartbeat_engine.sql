-- Spec 215 PR 215-E: Register pg_cron jobs for heartbeat engine + close GH #335.
--
-- THREE scheduled HTTP POSTs from pg_cron → Cloud Run task endpoints
-- (mirrors the format of all 9 existing nikita-* cron jobs):
--
--   nikita-heartbeat-hourly       — POST /api/v1/tasks/heartbeat            (00 of every hour)
--   nikita-generate-daily-arcs    — POST /api/v1/tasks/generate-daily-arcs  (05:00 UTC daily)
--   nikita-touchpoints            — POST /api/v1/tasks/touchpoints          (every 5 min) [closes GH #335]
--
-- B1/GH #335 context: TouchpointEngine writes rows to the `touchpoints` table
-- via evaluate_and_schedule_for_user; deliver_due_touchpoints() drains that
-- table via _send_telegram_message; route /api/v1/tasks/touchpoints exists
-- but had NO cron registered in prod (cron.job query 2026-04-18: 9 jobs, none
-- of them this one). Heartbeat fan-out and ALL other touchpoint producers
-- currently land in a queue with no consumer. Registering this cron alongside
-- the heartbeat crons closes the standing bug in one shot.
--
-- The two heartbeat endpoints are auth-gated (verify_task_secret) and no-op
-- + return 200 {"status":"disabled","reason":"feature_flag_off"} until
-- HEARTBEAT_ENGINE_ENABLED is flipped to true in Cloud Run env. The
-- nikita-touchpoints endpoint has its own dispatch logic (no flag gate);
-- it will start delivering touchpoints immediately after this migration
-- applies — that is the desired behavior (closes B1).
--
-- The hardcoded Bearer token + URL match the pattern of the 9 existing crons
-- (e.g., nikita-deliver, nikita-decay, nikita-summary). Backfilling all
-- crons (including these two) into auth.secrets / vault and a templated
-- migration helper is tracked separately as a hygiene cleanup.
--
-- IDEMPOTENCY: cron.schedule will overwrite an existing job with the same
-- name, but it returns the new jobid each time, which is fine. To guard
-- against double-scheduling on accidental re-apply, we cron.unschedule
-- first if exists.

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
        headers := '{"Authorization": "Bearer S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0", "Content-Type": "application/json"}'::jsonb
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
        headers := '{"Authorization": "Bearer S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0", "Content-Type": "application/json"}'::jsonb
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
        headers := '{"Authorization": "Bearer S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0", "Content-Type": "application/json"}'::jsonb
    );
    $cron$
);
