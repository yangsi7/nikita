---
title: "Spec 218 Slice 7 — Phone-Demo Wow + Supabase Realtime + Opt-In Modal"
spec: 218
slice: 7
lifecycle: living
pr: pending
---

# Slice 218-7: Phone-Demo Wow + Supabase Realtime + Opt-In Modal

## Scope

- DB migration `20260512120000_phone_demo_calls.sql` (spec §Entity 2 schema, RLS, ALTER PUBLICATION)
- BE module `nikita/agents/onboarding/v2/phone_demo.py` (~150 LOC): consent persistence + outbound call dispatch + idempotency
- Endpoints: `POST /api/v1/converse/onboarding/phone-demo/consent` + `POST /api/v1/converse/onboarding/phone-demo/end-call`
- Voice webhook piggyback: `post_call_transcription` handler in `nikita/api/routes/voice.py`
- FE: `portal/src/app/onboarding/v2/phone_demo_modal.tsx` (shadcn AlertDialog, default-skip)
- FE: `portal/src/app/onboarding/v2/phone_demo_takeover.tsx` (full-screen + Supabase Realtime)
- shadcn AlertDialog component: `portal/src/components/ui/alert-dialog.tsx`
- Tests: `tests/agents/onboarding/v2/test_phone_demo.py`, `tests/api/routes/test_phone_demo_endpoint.py`, `portal/src/__tests__/app/onboarding/v2/phone_demo_modal.test.tsx`

## Spec Requirements Addressed

| FR | Description |
|---|---|
| FR-009 | Phone-demo opt-in modal with server-side consent record (TCPA compliance) |
| FR-010 | Full-screen takeover + focus trap + aria-live + prefers-reduced-motion + "End early" button (post 5s) |
| FR-011 | Single-fire per user (UNIQUE constraint on `phone_demo_calls.user_id`) |

## Key Design Decisions

### Schema (spec §Entity 2 — authoritative)
Columns per spec: `consent_recorded_at` (not `consented_at`), `provider_call_id` (not `call_id`), `status` CHECK 8-value enum (not `call_status`). Insert RLS uses `WITH CHECK (user_id = (SELECT auth.uid()))` — subquery form for index performance.

### Idempotency (FR-017)
DB-level `ON CONFLICT (user_id) DO NOTHING RETURNING *`. Empty rowset → `inserted=False` → HTTP 409. No Python-side pre-check (eliminates race conditions).

### Webhook piggyback
At top of `post_call_transcription` block: query `phone_demo_calls WHERE provider_call_id = session_id`. If found: UPDATE `status`/`ended_at`/`cost_usd` via service-role, return early. Non-phone-demo calls unaffected.

### Supabase Realtime
`ALTER PUBLICATION supabase_realtime ADD TABLE phone_demo_calls;` in migration (required for `postgres_changes` events). FE subscribes with `event: 'UPDATE', filter: 'user_id=eq.<uid>'`. Polling FORBIDDEN.

### FR-010 "End early" button
`POST /onboarding/phone-demo/end-call` added to scope. Spec route table omits it but FR-010 says the button MUST abort the call gracefully — an endpoint is required.

## Reuse Locks

- All slice-2..6 shapes + decorator + route AS-IS
- `VoiceService.make_outbound_call` signature unchanged
- `message_history` hydrator from PR #588 reused

## LOC Estimate

~800 LOC (BE ~300, FE ~300, tests ~200)

## Post-Merge Gate (R8)

SUBAGENT SMOKE (~5 min) for phone-demo scenario + opt-in modal acceptance walk. Plus-alias `youwontgetmyname777+walkSlice7Phone@gmail.com` if walk needed.
