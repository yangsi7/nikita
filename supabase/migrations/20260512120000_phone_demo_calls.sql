-- Migration: phone_demo_calls table for Spec 218 FR-009/FR-010/FR-011
-- Schema source: spec §Entity 2 (GATE-2 passed audit)
-- PR-218-7 atomic: table + RLS + Realtime publication

CREATE TABLE IF NOT EXISTS phone_demo_calls (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL UNIQUE
                                  REFERENCES auth.users(id) ON DELETE CASCADE,
  phone_e164          text        NOT NULL,
  consent_recorded_at timestamptz NOT NULL,
  consent_source      text        NOT NULL DEFAULT 'phone_demo_optin',
  client_ip           inet,
  user_agent          text,
  provider_call_id    text,
  status              text        NOT NULL
                                  CHECK (status IN (
                                    'pending',
                                    'ringing',
                                    'in_progress',
                                    'ended_success',
                                    'ended_busy',
                                    'ended_no_answer',
                                    'ended_error',
                                    'ceiling_timeout'
                                  )),
  created_at          timestamptz NOT NULL DEFAULT now(),
  ended_at            timestamptz,
  cost_usd            numeric(8,4)
);

-- Indexes
CREATE INDEX IF NOT EXISTS phone_demo_calls_user_id_idx
  ON phone_demo_calls (user_id);

CREATE INDEX IF NOT EXISTS phone_demo_calls_provider_call_id_idx
  ON phone_demo_calls (provider_call_id)
  WHERE provider_call_id IS NOT NULL;

-- RLS (MANDATORY per .claude/rules/testing.md DB Migration Checklist)
ALTER TABLE phone_demo_calls ENABLE ROW LEVEL SECURITY;

-- Owner can SELECT their own row (Supabase Realtime requires SELECT policy)
CREATE POLICY phone_demo_calls_owner_select ON phone_demo_calls
  FOR SELECT
  USING (user_id = (SELECT auth.uid()));

-- Owner can INSERT their own row (consent recording)
-- WITH CHECK enforces user_id matches authenticated user
CREATE POLICY phone_demo_calls_owner_insert ON phone_demo_calls
  FOR INSERT
  WITH CHECK (user_id = (SELECT auth.uid()));

-- No UPDATE policy for users: status updates come from voice-provider webhook
-- via service-role key (admin-only path). User cannot self-escalate.
-- No DELETE policy for users: audit trail preservation (FR-009 TCPA compliance).

-- Supabase Realtime: FE subscribes to status updates (FR-010)
-- Required: table must be added to supabase_realtime publication for
-- postgres_changes events to fire.
ALTER PUBLICATION supabase_realtime ADD TABLE phone_demo_calls;
