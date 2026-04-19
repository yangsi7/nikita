-- Spec 214 FR-11d (GH #353, AC-11d.3d / S6) — per-user daily LLM spend
-- ledger backing the ``CONVERSE_DAILY_LLM_CAP_USD`` rate limiter.
--
-- Accumulation pattern (decision D2): INSERT ... ON CONFLICT (user_id,
-- day) DO UPDATE SET spend_usd = spend_usd + EXCLUDED.spend_usd —
-- atomic per-user upsert under Postgres row-level lock.
--
-- Rollover: daily at 00:05 UTC via pg_cron ``llm_spend_ledger_rollover``
-- which DELETEs rows older than 30 days (archival + cost audit window).
--
-- RLS: admin / service_role only. Same rationale as the idempotency
-- cache — portal reads go through the backend service role.

CREATE TABLE IF NOT EXISTS llm_spend_ledger (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day DATE NOT NULL,
  spend_usd NUMERIC(10, 4) NOT NULL DEFAULT 0,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, day)
);

-- N2 QA iter-1: drop the standalone day-only index. The composite PK
-- (user_id, day) already serves the per-user-per-day point query; the
-- separate day index added no measurable value at current row volumes.
DROP INDEX IF EXISTS idx_llm_spend_ledger_day;

ALTER TABLE llm_spend_ledger ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_and_service_role_only"
  ON llm_spend_ledger;

-- I7 QA iter-1: explicit TO clause restricts policy evaluation to
-- authenticated + service_role principals. See companion migration
-- 20260419120000_llm_idempotency_cache.sql for rationale.
CREATE POLICY "admin_and_service_role_only"
  ON llm_spend_ledger FOR ALL
  TO authenticated, service_role
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- I8 QA iter-1: idempotent pg_cron registration. Rollover archives /
-- prunes rows older than 30 days at 00:05 UTC daily.
DELETE FROM cron.job WHERE jobname = 'llm_spend_ledger_rollover';
SELECT cron.schedule(
  'llm_spend_ledger_rollover',
  '5 0 * * *',
  $$DELETE FROM llm_spend_ledger
      WHERE day < current_date - interval '30 days';$$
);
