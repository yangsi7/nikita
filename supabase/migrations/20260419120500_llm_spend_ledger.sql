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

CREATE INDEX IF NOT EXISTS idx_llm_spend_ledger_day
  ON llm_spend_ledger (day);

ALTER TABLE llm_spend_ledger ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_and_service_role_only"
  ON llm_spend_ledger;

CREATE POLICY "admin_and_service_role_only"
  ON llm_spend_ledger FOR ALL
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- Rollover: archive/prune rows older than 30 days at 00:05 UTC daily.
SELECT cron.schedule(
  'llm_spend_ledger_rollover',
  '5 0 * * *',
  $$DELETE FROM llm_spend_ledger
      WHERE day < current_date - interval '30 days';$$
);
