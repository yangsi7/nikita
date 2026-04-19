-- Spec 214 FR-11d (GH #352, AC-11d.3c) — POST /converse idempotency cache.
-- Stores (user_id, turn_id) → cached response body + status for 5-minute
-- TTL; the endpoint short-circuits on cache HIT (no agent call, no rate-
-- limit decrement, no JSONB write, no LLM spend increment per M5).
--
-- Prune cadence: hourly via pg_cron job ``llm_idempotency_cache_prune``
-- which DELETEs rows older than 5 minutes (TTL).
--
-- RLS: admin / service_role only. Portal reads go through the backend
-- which uses the service role; direct browser access is not a supported
-- surface.

CREATE TABLE IF NOT EXISTS llm_idempotency_cache (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  turn_id UUID NOT NULL,
  response_body JSONB NOT NULL,
  status_code INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, turn_id)
);

CREATE INDEX IF NOT EXISTS idx_llm_idempotency_cache_created
  ON llm_idempotency_cache (created_at);

ALTER TABLE llm_idempotency_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_and_service_role_only"
  ON llm_idempotency_cache;

-- I7 QA iter-1: explicit TO clause restricts the policy to authenticated
-- + service_role principals. Without it, the USING check is evaluated
-- against the `anon` and `public` roles too — an unnecessary surface.
CREATE POLICY "admin_and_service_role_only"
  ON llm_idempotency_cache FOR ALL
  TO authenticated, service_role
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- I8 QA iter-1: idempotent pg_cron registration. Re-running the
-- migration replaces the prior schedule rather than failing on a
-- duplicate jobname. Hourly prune — delete rows older than 5 minutes.
DELETE FROM cron.job WHERE jobname = 'llm_idempotency_cache_prune';
SELECT cron.schedule(
  'llm_idempotency_cache_prune',
  '0 * * * *',
  $$DELETE FROM llm_idempotency_cache
      WHERE created_at < now() - interval '5 minutes';$$
);
