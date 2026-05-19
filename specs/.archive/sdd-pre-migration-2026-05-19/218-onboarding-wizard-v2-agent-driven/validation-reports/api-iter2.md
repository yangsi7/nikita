# GATE 2: API Validation Report (Iter 2) — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (1008 lines)
**Validator**: sdd-api-validator
**Iteration**: 2 (re-validation of iter-1 findings)
**Timestamp**: 2026-05-09
**Iter-1 verdict**: FAIL (CRITICAL=0 HIGH=4 MEDIUM=5 LOW=2)

## Verdict
PASS

## Severity Counts
CRITICAL=0 HIGH=0 MEDIUM=0 LOW=2

---

## Iter-1 Finding Resolution

### HIGH-1 — HTTP route surface — RESOLVED ✓
**Where addressed**: spec.md §"HTTP Route Contract" → "Route Inventory" table (L688-697).
**Verification**: Table lists method + path + purpose + auth + rate limit for all 4 surfaces:
- `POST /onboarding/answer` — JWT, 30 rpm/user
- `GET /onboarding/state` — JWT, no rate limit
- `POST /onboarding/phone-demo/consent` — JWT, 1/lifetime/user
- Realtime `phone_demo_calls` channel — JWT + RLS filter

The table also explicitly states "NO polling endpoint exists" (L698). All 4 routes have full request/response sub-sections downstream. PASS.

### HIGH-2 — Discriminated-union envelope schema — RESOLVED ✓
**Where addressed**: spec.md §"Envelope Discriminated Union" (L700-775).
**Verification**: All 8 shapes are enumerated with required fields and discriminator field `component`:
1. `text_short` — slot, prompt, placeholder, max_chars, dictation
2. `text_long` — slot, prompt, placeholder, max_chars, dictation
3. `single_select` — slot, prompt, options[2..8] with {value, label, blurb}
4. `chip_multi` — slot, prompt, options, min_pick, max_pick
5. `slider` — slot, prompt, min_val, max_val, step, labels
6. `calendar` — slot, prompt, min_date, max_date
7. `phone` — slot, prompt, default_country, demo_call_after_submit
8. `complete` — next_route, backstory_preview

Discriminator (`component`) explicit; per-shape required fields enumerated; JSON example payloads provided. PASS.

### HIGH-3 — `GET /onboarding/state` contract — RESOLVED ✓
**Where addressed**: spec.md §"GET /onboarding/state" (L802-814).
**Verification**: Response body declared with shape `{phase, slots, last_envelope, conversation_summary[]}`. Status codes 200 OK, 401 Unauthorized listed. FR-016 authority rule (log wins on mismatch) preserved at L170-172. PASS.

### HIGH-4 — Idempotency HTTP transport — RESOLVED ✓
**Where addressed**: FR-017 (L176-177) + §"POST /onboarding/answer" (L789).
**Verification**: FR-017 explicitly states "The HTTP transport MUST use a request-derived idempotency key (computed server-side from `(user_id, target_slot, state_hash)`) — clients do NOT need to send an explicit `Idempotency-Key` header; the server derives the key deterministically from session + state." Reinforced at L789: "No `Idempotency-Key` header is required from the client. The server derives idempotency from `(user_id, target_slot, state_hash)` per FR-017." PASS.

### MEDIUM-1 — Error envelope wire shape — RESOLVED ✓
**Where addressed**: spec.md §"Error Envelope Wire Shape" (L852-866).
**Verification**: JSON shape declared: `{error: {code, message, field}, recovery_envelope}`. FR-015 inline-error path preserved; recovery envelope optional fallback path explicit. PASS.

### MEDIUM-2 — Realtime channel name + RLS filter + event payload — RESOLVED ✓
**Where addressed**: §"Realtime channel `phone_demo_calls`" (L838-849) + Entity 2 §"Realtime subscription" (L669).
**Verification**: All 3 components covered:
- Channel name: `phone_demo_calls` (L842)
- RLS filter: `user_id=eq.${userId}` + RLS policies at L659-666
- Event payload: "full `phone_demo_calls` row post-update (Postgres CDC default). FE consumes `status` field transitions" (L849)

Status enum on `phone_demo_calls.status` declared (L649) covers transitions. PASS.

### MEDIUM-3 — HTTP status codes — RESOLVED ✓
**Where addressed**: per-route status code lists.
**Verification**:
- POST /onboarding/answer (L793-799): 200, 401, 422, 429, 500
- GET /onboarding/state (L814): 200, 401
- POST /onboarding/phone-demo/consent (L830-835): 201, 409, 422, 503

Status codes are semantically appropriate (409 for FR-011 single-fire conflict; 503 for voice-provider exhaustion; 422 for libphonenumber validation). PASS.

### MEDIUM-4 — Phone-demo consent endpoint — RESOLVED ✓
**Where addressed**: §"POST /onboarding/phone-demo/consent" (L816-835).
**Verification**: Dedicated endpoint declared (NOT multiplexed on /answer). Request body `{phone_e164, consent}`, response `{call_id, status}`, status codes documented. Single-fire enforced via DB UNIQUE on `phone_demo_calls.user_id` (Entity 2 L642) + 409 Conflict response. PASS.

### MEDIUM-5 — v1 route inventory in FR-018 — RESOLVED ✓
**Where addressed**: FR-018 (L194-214).
**Verification**: v1 BE routes/handlers explicitly enumerated (L196-203):
- `POST /onboarding/answer` v1 (emission-union dispatch)
- `GET /onboarding/state` v1
- `nikita/agents/onboarding/conversation_agent.py` (legacy + emission)
- `conversation_prompts.py`, `converse_contracts.py`, `answer_contracts.py`
- `agent_emission_state.py`, `sidecar_persistence.py`, `bare_token_fallback.py`

v1 FE modules listed (L205-212). v1 tests listed (L214). Atomic delete-and-replace in same PR explicitly required (L218). PASS.

---

## Carry-Forward LOW Findings

### LOW-1 — CORS allowlist acknowledgement
**Status**: ADDRESSED in NFR-Security L265 — "CORS allowlist MUST contain only the canonical apex domain `nikita-mygirl.com`". Resolved.

### LOW-2 — `state_hash` canonical form
**Status**: PARTIALLY ADDRESSED — FR-017 L186 says "`state_hash` MUST be a stable hash function of the cumulative `WizardSlots` state (e.g., SHA-256 of canonical JSON)". The "e.g." leaves the canonical form (sort_keys, encoding, truncation length) underspecified. Recommend documenting the exact form (e.g., `sha256(json.dumps(slots, sort_keys=True, default=str))[:16]`) at plan time. Non-blocking.

### LOW-3 (NEW) — `complete` envelope auth/idempotency edge case
**Severity**: LOW
**Category**: HTTP Status Code Correctness
**Location**: Route Contract §"POST /onboarding/answer" L793-799
**Issue**: The `complete` envelope shape (L770-775) is emitted as a terminal turn. If the user retries POST /answer after the wizard is already `complete`, the spec doesn't explicitly state whether the response is 200 (replay the complete envelope) or 409 Conflict (terminal state). Idempotency rule (`(user_id, target_slot, state_hash)`) likely yields 200 + replayed envelope, which is fine, but could be made explicit.
**Recommendation**: Add a one-liner at L799 noting that POST /answer after `phase=complete` returns 200 with the cached `complete` envelope.

---

## Route Coverage

| Route | Verb | Request shape | Response shape | Status codes |
|-------|------|---------------|----------------|--------------|
| /onboarding/answer | POST | `{turn_id, slot, value}` | Envelope discriminated union (8 shapes) | 200, 401, 422, 429, 500 |
| /onboarding/state | GET | (none, JWT) | `{phase, slots, last_envelope, conversation_summary[]}` | 200, 401 |
| /onboarding/phone-demo/consent | POST | `{phone_e164, consent}` | `{call_id, status}` | 201, 409, 422, 503 |
| Realtime `phone_demo_calls` | SUB | filter `user_id=eq.${uid}` | full row CDC payload | n/a (RLS-gated) |

## Error Envelope Consistency

- ✓ Uniform error shape across endpoints — `{error: {code, message, field}, recovery_envelope}` (L854-864)
- ✓ Stack-trace leakage — Wire shape carries no internal exception text
- ✓ Semantic error codes — `error.code` field declared (machine-readable); enumeration deferred to plan time (acceptable)

## Idempotency Audit

| Endpoint | Verb | Idempotency Strategy | Status |
|----------|------|----------------------|--------|
| /onboarding/answer | POST | server-derived `(user_id, target_slot, state_hash)` (FR-017 L176-177) | ✓ Mechanism specified |
| /onboarding/phone-demo/consent | POST | DB UNIQUE(user_id) on `phone_demo_calls` (FR-011 + Entity 2 L642) | ✓ Constraint declared |
| Phase 2 firecrawl call | (server-internal) | cache key `(user_id, slot, prior_state_hash)` (FR-017) | ✓ Documented |
| Backstory generation | (server-internal) | "existing pattern (preserved)" (FR-017) | ✓ Deferred to existing |

## OpenAPI Surface

- ✓ `response_model=` implied per route (envelope union for /answer; explicit shape for /state and /consent)
- ✓ `responses={}` documents non-200 paths — status codes enumerated per route
- ⚠ `tags=` not declared in spec — recommend `tags=["onboarding-v2"]` at plan time (LOW, non-blocking)
- ⚠ `summary` + `description` — defer to plan (non-blocking for spec gate)

---

## Summary

All 4 HIGH and all 5 MEDIUM iter-1 findings are resolved. The spec now contains a complete "HTTP Route Contract" section (L685-866) with route inventory, per-shape envelope schema, request/response bodies, status codes, error envelope wire shape, and Realtime channel contract. Idempotency mechanism is server-derived (no client header), consistent with the existing `nikita/onboarding/idempotency.py` pattern. v1 supersession surface (FR-018) is enumerated atomically.

Two LOW carry-forward items (`state_hash` canonical form precision; `complete` envelope retry semantics) are non-blocking and deferable to plan-time.

VERDICT: PASS — CRITICAL=0 HIGH=0 MEDIUM=0 LOW=2
