## Auth Validation Report (Iter 2)

**Spec:** specs/218-onboarding-wizard-v2-agent-driven/spec.md
**Status:** PASS
**Timestamp:** 2026-05-09T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

### Re-check of Iter-1 Findings

| Iter-1 Finding | Severity | Resolved? | Evidence |
|---|---|---|---|
| HIGH-1: Wizard route JWT protection | HIGH | RESOLVED | FR-019 (lines 223-227) explicitly requires JWT on `/onboarding/answer` and `/onboarding/state`; anonymous → HTTP 401; FE redirect to `/login`. Reinforced in Route Inventory table (line 693) "JWT required (FR-019)" for both routes. |
| HIGH-2: 30 rpm rate limit | HIGH | RESOLVED | NFR Security (line 262) declares "The `/onboarding/answer` decorator-agent endpoint MUST be rate-limited to 30 requests per minute per user (existing `nikita/api/middleware/rate_limit.py:answer_rate_limit` pattern)". Mirrored in Route Inventory (line 693) "30 rpm/user" + status code 429 (line 798). |
| MEDIUM-1: TCPA server-side consent record | MEDIUM | RESOLVED | FR-009 (lines 119-121) declares server-side consent record fields `(user_id, phone_e164, consented_at, consent_source='phone_demo_optin', client_ip, user_agent)` in same transaction as outbound call request; failed write blocks call. Schema confirms in `phone_demo_calls` table (lines 643-648) with consent_recorded_at, consent_source, client_ip, user_agent columns. |
| MEDIUM-2: libphonenumber explicit | MEDIUM | RESOLVED | NFR Security (line 260): "Phone numbers MUST be normalized to E.164 AND validated by the `libphonenumber` library (or equivalent) BEFORE persistence. Invalid numbers MUST be rejected at the BE boundary with HTTP 422 + inline error". Echoed in FR-005 (line 83) phone shape uses libphonenumber, and consent endpoint 422 status (line 833). |
| MEDIUM-3: Atomic-transaction phase handoff | MEDIUM | RESOLVED | FR-002 (lines 54-58) declares: "The handoff timestamp write MUST occur in the SAME database transaction as the final Phase 1 slot acceptance (atomic; either both succeed or both fail)." |

### Auth Flow Analysis

**Primary Method:** JWT (existing Supabase Auth via Spec 216-A Telegram-first signup)
**Session Type:** JWT bearer token via Supabase Auth middleware
**Token Handling:** SPECIFIED — middleware-enforced on `/onboarding/answer`, `/onboarding/state`, `/onboarding/phone-demo/consent`; FE verifies presence pre-mount

### Security Checklist
- [✓] Rate limiting on wizard endpoint — 30 rpm/user (NFR Security + Route Inventory + 429 status)
- [✓] Phone-demo lifetime cap — DB UNIQUE constraint on `phone_demo_calls.user_id` (FR-011 + entity schema)
- [✓] Server-side consent record — FR-009 explicit fields + atomic with call initiation
- [✓] libphonenumber validation — NFR Security + 422 boundary
- [✓] RLS posture on `phone_demo_calls` — owner_select + owner_insert + no UPDATE/DELETE for users (lines 657-666)
- [✓] Prompt-injection sanitization — `_sanitize_for_prompt` boundary helper (NFR Security + R1)
- [✓] CORS canonical apex only — NFR Security line 265
- [✓] Cost guards — Phase 2 $0.10, total $0.50 hard ceiling
- [✓] Atomic phase handoff transaction — FR-002 explicit

### Verdict

All 5 iter-1 findings resolved with explicit, locatable spec text. Auth/security posture is complete for Phase 5 planning.

VERDICT: PASS — CRITICAL=0 HIGH=0 MEDIUM=0 LOW=0
