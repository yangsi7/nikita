# GATE 2: API Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (553 lines)
**Validator**: sdd-api-validator
**Timestamp**: 2026-05-09
**Brief cross-ref**: `~/.claude/plans/immutable-wondering-gray.md` §5, §23.1, §23.4, §23.5, §23.10

## Verdict
FAIL

## Severity Counts
CRITICAL=0 HIGH=4 MEDIUM=5 LOW=2

---

## Findings

### HIGH-1 — No HTTP route surface specified at all (FR-004 / FR-015 / FR-016)
**Category**: Route Schemas & Contracts
**Location**: spec.md FR-004 (L61-65), FR-015 (L127-131), FR-016 (L133-137)
**Issue**: Spec describes a "typed response envelope" emitted "for every wizard turn" and "BE-strict validation per component" but never specifies the HTTP method + path of the endpoint that emits the envelope. There is no `POST /onboarding/answer`, no `GET /onboarding/state`, no `/api/v1/...` reference, no FastAPI route signature, no Pydantic request/response model name. Planning cannot proceed without the route inventory because every other concern (idempotency keys, status codes, error envelope, CORS) is route-scoped.
**Recommendation**: Add a "Route Contract" section enumerating each endpoint: method, path (with `/api/v1/onboarding/...` prefix per existing convention), request model name, response model name (the envelope union), success status code, error status codes. At minimum: `POST /api/v1/onboarding/answer`, `GET /api/v1/onboarding/state`, `POST /api/v1/onboarding/phone-demo/consent` (separate from /answer per FR-009 modal), and the Realtime channel name for `phone_demo_calls` (FR-010).

### HIGH-2 — Envelope union shape names not enumerated (FR-004 + FR-005)
**Category**: Route Schemas & Contracts / OpenAPI Alignment
**Location**: FR-005 (L67-71)
**Issue**: FR-005 names 8 shape categories in prose ("short text input, long text input, single-select choice, multi-chip selection, numeric slider, calendar/date picker, phone-number input, completion celebration") but does NOT define the discriminator field name (e.g., `kind`, `type`, `component`), the per-shape required field set, or the discriminator literal values. The brief's §23.1 "8-component lock" is referenced but not inlined. A discriminated-union envelope without declared discriminator + per-variant required fields is not implementable as a Pydantic v2 `Field(..., discriminator=...)`.
**Recommendation**: Inline the per-shape contract as a table: `kind` literal | required fields | optional fields | example. e.g., `short_text` | `kind, prompt, slot, max_length` | `placeholder, helper_text, dictation_enabled` | …. Cite `nikita/api/schemas/onboarding.py:206-216` (the existing precedent the spec already references in Intelligence Evidence) as the schema pattern.

### HIGH-3 — No /state route contract for refresh-resume (FR-016)
**Category**: Route Schemas & Contracts
**Location**: FR-016 (L133-137), AC-005-001/002/003 (L268-271)
**Issue**: FR-016 mandates state-replay-from-conversation-log but does not specify the endpoint. AC-005-003 says "the same envelope is re-served from cache (no LLM token re-spend)" — this implies a GET endpoint that returns `{cumulative_state, last_envelope}` but the contract is left implicit. Planning cannot decide between `GET /onboarding/state` (returning state + last envelope) vs. `GET /onboarding/resume` (returning only the next envelope to render).
**Recommendation**: Add an explicit FR or sub-section defining the read endpoint: `GET /api/v1/onboarding/state` → `OnboardingStateResponse{slots: WizardSlots, last_envelope: Envelope, phase: Literal["phase_1", "phase_2", "complete"], phase_2_started_at: datetime | None, turn_count: int}`. State the authority rule from FR-016 (log wins on mismatch) here too.

### HIGH-4 — Idempotency mechanism specified by behavior but not by header/contract (FR-017)
**Category**: Idempotency
**Location**: FR-017 (L139-143), AC-005-003 (L271)
**Issue**: FR-017 specifies cache-key composition (`user_id + target_slot + state_hash` for envelope, `user_id + slot + prior_state_hash` for firecrawl) but does NOT specify how the key is conveyed across the HTTP boundary. Three options are left unspecified: (a) `Idempotency-Key` request header (RFC 7240), (b) server-derived from request body + auth context, (c) state_hash echoed in response and required in subsequent request. Without picking one, the FE/BE contract is ambiguous and replay-after-network-blip semantics are undefined.
**Recommendation**: Pick one and document. Recommended: server-derived key (`user_id` from JWT + `target_slot` + `state_hash` computed from cumulative slots) — no client header required, consistent with the existing `nikita/onboarding/idempotency.py` pattern referenced in Intelligence Evidence. Document that a retried `POST /answer` with the same payload returns the same envelope (200, not 201) without re-running the agent.

---

### MEDIUM-1 — Error envelope shape not specified (FR-015)
**Category**: Error Response Shapes
**Location**: FR-015 (L127-131), AC-001-003 (L207)
**Issue**: FR-015 says "FE inline error display is the only acceptable user-facing error path" and AC-001-003 says "FE displays an inline error" but the wire shape is unspecified. Is the error returned as HTTP 422 with `{"error": "<code>", "detail": "<message>"}`? Is it returned as HTTP 200 with an envelope of kind `error_inline`? The contract decision changes FE handling significantly. Consistency with project convention (`{"error": "<code>", "detail": "<message>"}` envelope per backend memory) needs to be stated.
**Recommendation**: Add a sub-section: validation failures from BE-strict validation return HTTP 422 with project-standard envelope `{"error": "<semantic_code>", "detail": "<message>", "field": "<slot_name>"}`; FE renders inline. List the semantic codes (e.g., `slot_value_invalid`, `age_below_minimum`, `phone_invalid_format`, `phase_2_premature_complete`).

### MEDIUM-2 — Realtime subscription channel name + auth not specified (FR-010, AC-003-004)
**Category**: Streaming / SSE / Realtime
**Location**: FR-010 (L97-101), AC-003-004 (L240)
**Issue**: AC-003-004 says "FE receives a status update via real-time subscription (NOT polling)" and the brief §23.5 explicitly killed polling in favor of Realtime on `phone_demo_calls`. Spec does not specify: (a) Supabase Realtime channel name, (b) RLS policy gating subscription to the user's own row, (c) event payload shape (`call.ringing`, `call.ended`, `call.failed`), (d) the 30s ceiling timeout owner (FE clock vs. BE deadline event).
**Recommendation**: Add a "Realtime Contract" sub-section: channel = `phone_demo_calls`, filter = `user_id = auth.uid()`, payload shape, and explicit BE-emits-deadline-event vs. FE-clock decision (recommended: BE writes a `call.timeout` row at 30s so FE has a single source of truth).

### MEDIUM-3 — HTTP status codes not specified for any operation
**Category**: HTTP Status Code Correctness
**Location**: spec.md (none)
**Issue**: No success or error status codes documented for any of the implied endpoints. POST /answer success could be 200 (replay) or 201 (new envelope); FR-017 idempotency replay should be 200. Phone-demo consent that triggers a call could be 202 Accepted (call dispatched async) or 200 with envelope. Force-skip on per-user-single-fire (AC-003-005) needs a documented status (200 with skip envelope vs. 409 Conflict).
**Recommendation**: Tabulate the operation × status-code × condition matrix. Recommended: POST /answer = 200 always (envelope returned, even on replay); 422 for validation failure; 429 for cost-cap exceeded; 503 for LLM provider degraded with last-good fallback.

### MEDIUM-4 — Phone-demo consent endpoint vs. /answer multiplexing not decided (FR-009)
**Category**: HTTP Verb Semantics / Route Schemas
**Location**: FR-009 (L91-95), AC-003-001 to AC-003-006 (L237-242)
**Issue**: FR-009's "1-tap consent modal" with yes/skip outcomes is a state-mutating action with side effects (outbound call dispatch on `yes`). It is unclear whether this rides on the existing `POST /answer` endpoint with a special slot value (e.g., slot=`phone_demo_consent`, value=`yes`) or whether it has its own endpoint (`POST /onboarding/phone-demo/consent`). The single-fire constraint (FR-011) is easier to enforce with a dedicated endpoint + DB unique constraint.
**Recommendation**: Make the choice explicit. Recommended: dedicated `POST /api/v1/onboarding/phone-demo/consent` with body `{"consent": "yes" | "skip"}`, returns 202 Accepted on `yes` (call dispatched, FE expects Realtime event), 200 on `skip` (envelope for next slot). Single-fire enforced by `UNIQUE(user_id)` on `phone_demo_calls` table.

### MEDIUM-5 — Atomic supersession of v1 routes (FR-018) not enumerated
**Category**: Versioning
**Location**: FR-018 (L145-149)
**Issue**: FR-018 mandates atomic deletion of legacy 217 modules but does not list the specific HTTP routes being deleted. The brief §23.10 PR roadmap presumably enumerates the v1 routes; spec should mirror that list so the planner knows the exact route inventory being replaced (vs. a parallel v2 prefix). Spec is silent on whether the new envelope union routes reuse the v1 paths or land on `/api/v2/onboarding/...`.
**Recommendation**: Inline the v1 route deletion list (e.g., `POST /api/v1/portal-onboarding/turn`, `GET /api/v1/portal-onboarding/state` — placeholder names; the spec author should pull the actual list from the brief). State explicitly that v2 takes the same `/api/v1/onboarding/...` prefix (atomic replacement, no v2 namespace) since FR-018 is bulldoze + zero retained users.

---

### LOW-1 — CORS allowlist not referenced (NFR-Security)
**Category**: CORS & Cookies
**Location**: NFR-Security (L161-166)
**Issue**: NFR-Security covers prompt injection, sanitization, and TCPA but does not reference the existing CORS allowlist (`nikita-mygirl.com` canonical per `.claude/rules/vercel-cors-canonical.md`). Adding new routes under `/api/v1/onboarding/...` should be pre-flighted against the existing CORS list. Likely a no-op (same origin set), but should be acknowledged.
**Recommendation**: Add a one-liner under NFR-Security: "All new routes inherit the existing apex-canonical CORS allowlist; no allowlist mutation required."

### LOW-2 — Idempotency key derivation involves `state_hash` but state_hash format not specified
**Category**: OpenAPI Alignment / Idempotency
**Location**: FR-017 (L139-143)
**Issue**: `prior_state_hash` is referenced as a cache key component but the canonical hash function (e.g., `sha256(canonical_json(slots))` vs. `hash(tuple(sorted(slots.items())))`) is not specified. Planner-time decision but worth nailing now to avoid a Walk-B6 cache-miss-because-hash-changed-on-trivial-reorder bug.
**Recommendation**: Specify: `state_hash = sha256(json.dumps(slots, sort_keys=True, default=str))[:16]` or equivalent canonical form. Document in FR-017.

---

## Route Coverage

| Route | Verb | Request shape | Response shape | Status |
|-------|------|---------------|----------------|--------|
| (implied) /api/v1/onboarding/answer | POST | NOT SPECIFIED — likely `{slot, value}` | NOT SPECIFIED — implied envelope union (FR-004 + FR-005, 8 shapes named in prose only) | NOT SPECIFIED |
| (implied) /api/v1/onboarding/state | GET | (none, JWT) | NOT SPECIFIED — implied `{slots, last_envelope, phase, phase_2_started_at}` per FR-016 | NOT SPECIFIED |
| (implied) /api/v1/onboarding/phone-demo/consent | POST | NOT SPECIFIED — likely `{consent: yes/skip}` | NOT SPECIFIED — likely envelope or 202 ack | NOT SPECIFIED |
| (implied) Supabase Realtime channel `phone_demo_calls` | SUB | (filter on user_id) | NOT SPECIFIED — likely `{event: ringing/ended/failed/timeout, ...}` | NOT SPECIFIED |

---

## Error Envelope Consistency

- ✗ Uniform error shape across endpoints — NOT SPECIFIED (FR-015 says "inline display" but no wire shape)
- ✗ Stack-trace leakage — NOT SPECIFIED (no error contract at all)
- ✗ Semantic error codes — NOT SPECIFIED (codes like `slot_value_invalid` not enumerated)

## Idempotency Audit

| Endpoint | Verb | Idempotency Strategy | Status |
|----------|------|----------------------|--------|
| /answer | POST | server-derived `user_id + target_slot + state_hash` per FR-017 (mechanism: not stated; recommended server-derived) | ✗ Mechanism not specified |
| /phone-demo/consent | POST | DB UNIQUE(user_id) per FR-011 + FR-017 (single-fire) | ✓ Constraint named |
| Phase 2 firecrawl call | (server-internal) | cache key `user_id + slot + prior_state_hash` per FR-017 | ✓ Documented (server-internal) |
| Backstory generation | (server-internal) | "existing pattern" per FR-017 | ✓ Documented (deferred to existing) |

## OpenAPI Surface

- ✗ `response_model=` on every route — N/A (no routes specified)
- ✗ `responses={}` documents non-200 paths — NOT SPECIFIED
- ✗ `tags=` present for grouping — NOT SPECIFIED (recommended: `tags=["onboarding-v2"]`)
- ✗ `summary` + `description` populated — N/A

---

## Recommendations (ordered by severity)

1. **HIGH-1** — Add a "Route Contract" section enumerating every HTTP endpoint by method + path + request model + response model + status codes. Without this, planning cannot proceed; FR-004/FR-015/FR-016 reference "envelopes" but never anchor them to a route.
2. **HIGH-2** — Inline the 8-shape discriminated-union table: discriminator field name, per-shape required/optional fields, example payload. Reference `nikita/api/schemas/onboarding.py:206-216` as the precedent.
3. **HIGH-3** — Add `GET /api/v1/onboarding/state` contract explicitly with response shape `{slots, last_envelope, phase, phase_2_started_at, turn_count}` per FR-016.
4. **HIGH-4** — Pick the idempotency key transport mechanism (recommended: server-derived) and document the response semantics for replay (200 OK, same envelope, no LLM re-spend per AC-005-003).
5. **MEDIUM-1** — Standardize the validation error envelope: HTTP 422 + `{"error", "detail", "field"}`; enumerate semantic error codes.
6. **MEDIUM-2** — Document the Realtime channel contract: name, RLS filter, event shape, BE-emits-timeout-event decision (recommended).
7. **MEDIUM-3** — Tabulate the HTTP status code matrix (200/201/202/422/429/503) per operation.
8. **MEDIUM-4** — Decide /answer-multiplexed vs. dedicated `/phone-demo/consent` endpoint (recommended: dedicated, 202 Accepted on `yes`).
9. **MEDIUM-5** — Inline the list of v1 routes being deleted under FR-018 atomic supersession; confirm v2 reuses the v1 prefix (no `/api/v2`).
10. **LOW-1** — Add CORS allowlist no-op acknowledgement under NFR-Security.
11. **LOW-2** — Specify `state_hash` canonical form (recommended: `sha256(json.dumps(slots, sort_keys=True))[:16]`).

---

## Summary

The spec is rich on functional behavior, persona/UX intent, and risk-mitigation reasoning, but the API contract surface is almost entirely implicit. Six of the eight validation checks (envelope union shape names, /answer route contract, /state route contract, idempotency header/transport, error envelope, CORS) returned NOT SPECIFIED. The phone-demo Realtime path (check 4) is correctly mandated as Realtime not polling (FR-010 + AC-003-004 + brief §23.5) but the channel/RLS/event-shape are unspecified. Versioning (check 7) is correctly identified as atomic v1 supersession but the v1 route deletion list is not inlined.

This gates planning. The brief presumably contains the missing detail (per Intelligence Evidence, the brief is 833 lines with §23.1 8-component lock and §23.10 PR roadmap), but the spec must inline enough of it that an implementer doesn't have to load the brief to know the route surface. Recommend a Phase-3 spec amendment adding a "Route & Schema Contract" section before re-running GATE 2.

VERDICT: FAIL — CRITICAL=0 HIGH=4 MEDIUM=5 LOW=2
