-- Spec 215 B2 (GH #336): Arm the heartbeat cost circuit breaker
--
-- Adds cost_usd to job_executions so JobExecutionRepository.get_today_cost_usd()
-- can sum daily LLM spend for the FR-014 ceiling check
-- (heartbeat_cost_circuit_breaker_usd_per_day, default $50/day).
--
-- Without this column the daily-arcs handler logged cost_breaker_degraded and
-- treated today_cost = $0, leaving Anthropic spend uncapped on flag-flip.
--
-- Apply via mcp__supabase__apply_migration post-merge — file alone does not
-- mutate the live DB. Existing rows default to NULL (read as 0 in SUM).
--
-- RLS: job_executions table inherits its existing policy set; this column
-- addition does not change row visibility. No new policy needed.

ALTER TABLE public.job_executions
    ADD COLUMN IF NOT EXISTS cost_usd numeric(10, 4);

COMMENT ON COLUMN public.job_executions.cost_usd IS
    'USD cost of this job execution (LLM API spend). Aggregated daily by '
    'JobExecutionRepository.get_today_cost_usd for FR-014 cost circuit breaker.';
