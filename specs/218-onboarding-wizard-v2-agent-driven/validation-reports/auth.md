# GATE 2: Auth Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md`
**Brief cross-ref**: `~/.claude/plans/immutable-wondering-gray.md` §23.7, §23.9, §24-R1
**Timestamp**: 2026-05-09
**Validator**: sdd-auth-validator

## Verdict

**FAIL**

GATE 2 PASS criterion = 0 CRITICAL + 0 HIGH. Two HIGH findings block.

## Severity Counts

CRITICAL=0 HIGH=2 MEDIUM=3 LOW=1

## Auth Flow Analysis

- **Primary Method**: Authenticated session inherited from Spec 216-A Telegram-first signup (JWT). Spec 218 wizard is the second step post-auth.
- **Session Type**: JWT (per project pattern, `nikita/api/dependencies/auth.py`); spec relies on existing middleware but does not explicitly cite it.
- **Token Handling**: Implicit reuse of existing JWT validation; not surfaced in spec.

## Findings

### HIGH-1: Wizard route protection not explicitly specified (Check 1)

**Category**: Protected Resources
**Location**: spec.md (whole spec)
**Issue**: Spec 218 references "authenticated user" only once (AC-001-001) and assumes the wizard sits behind Spec 216-A's auth gate. The two new server surfaces this spec implies — `/onboarding/answer` (envelope submission) and `/onboarding/state` (replay hydration) — are NEVER explicitly required to enforce JWT middleware. FR-002, FR-016, FR-017 all assume per-user state; if the routes were unauthenticated, every persistence/idempotency invariant collapses.
**Recommendation**: Add an explicit FR or NFR Security clause: "All `/onboarding/*` routes MUST require a valid JWT (Authorization: Bearer) and MUST resolve `user_id` from the JWT `sub` claim — never from request body — before reading or writing onboarding_profile. Unauthenticated requests MUST return 401." Reference `nikita/api/dependencies/auth.py:get_current_user_id` as the reuse pattern.

### HIGH-2: Per-user agent-decorator rate limit not surfaced in spec (Check 5a)

**Category**: Security Measures / Rate Limiting
**Location**: spec.md NFR section vs brief §23.9
**Issue**: Brief §23.9 mandates "Decorator agent calls — per-user 30 rpm via existing `nikita/api/middleware/rate_limit.py:answer_rate_limit` (preserve)". The spec.md NFR section enumerates Performance, Security, Cost, Scalability, Availability, Accessibility, Observability, Privacy — but contains NO rate-limit clause. Without it, an authenticated user can churn the LLM-backed `/answer` endpoint to exhaust Phase-2 cost ceiling AND burn token budget on a refresh-loop, even though FR-017 caches envelopes by state_hash. The cost guard ($0.10 Phase-2 ceiling) is a budget cap, not a request-rate cap; both are required.
**Recommendation**: Add NFR Security clause: "POST `/onboarding/answer` and the agent-decorator path MUST enforce a per-user rate limit of 30 requests/minute, reusing `nikita/api/middleware/rate_limit.py:answer_rate_limit`. Phone-demo trigger MUST enforce a per-user lifetime cap of 1 outbound call (already in FR-011 — restate as a rate limit so it lands in the limiter inventory)." Also cite the existing backstory limiter as preserved.

### MEDIUM-1: Server-side consent persistence not mandated (Check 2)

**Category**: Regulatory / TCPA evidence trail
**Location**: FR-009, AC-003-003
**Issue**: FR-009 mandates a 1-tap consent modal and that "Only on explicit `yes` does system fire an outbound voice call." AC-003-003 says "When the BE receives consent, Then exactly one outbound call is initiated". Neither requirement explicitly mandates **persisting the consent record server-side with timestamp + user_id + phone_e164** for TCPA audit-trail purposes. If a regulator or carrier challenge arises, "the FE sent a flag" is insufficient evidence. The phone_demo_calls table (referenced in §23.7 as the unique-constraint source) should hold the consent timestamp.
**Recommendation**: Add to FR-009: "Server MUST persist a consent record (user_id, phone_e164, consent_granted_at, ip_address, user_agent) before initiating the outbound call. The same DB row enforces the FR-011 single-fire unique constraint."

### MEDIUM-2: Phone E.164 validation library not specified (Check 3)

**Category**: Security / Input Validation
**Location**: NFR Security
**Issue**: NFR Security states "Phone numbers MUST be normalized to E.164 before storage; no raw user input persisted in phone slot." Normalization is stated; validation that the input IS a valid phone before normalization (libphonenumber-style country-code + length checks) is not. Without explicit library mandate, a developer could implement a regex E.164 stub that accepts garbage like `+10000000000`, allowing voice-provider abuse vectors.
**Recommendation**: Add NFR Security clause: "Phone input MUST be validated via libphonenumber (or equivalent) at the BE boundary, rejecting numbers that fail country-code + length + carrier-line-type checks. Invalid numbers MUST return 422 with FE inline error per FR-015."

### MEDIUM-3: Phase handoff atomic-transaction guarantee not stated (Check 6)

**Category**: Authorization / State Integrity
**Location**: FR-002, AC-001-004, R3 mitigation
**Issue**: FR-002 says `phase_2_started_at` is persisted "at the moment Phase 1 completes, before Phase 2's first turn is rendered." AC-001-004 says it is persisted "before the first Phase 2 envelope is emitted." R3 mitigation says "BE writes `phase_2_started_at` BEFORE first Phase 2 envelope." None of these state that the timestamp write occurs **in the same DB transaction** as the final Phase 1 slot acceptance. A two-statement non-transactional sequence is open to a window where the final Phase-1 slot is committed, the request crashes, and the user resumes with all Phase 1 slots filled but no `phase_2_started_at` — Risk R3 partially regresses.
**Recommendation**: Strengthen FR-002: "Persisting `phase_2_started_at` MUST occur in the same DB transaction as the final Phase 1 slot acceptance write (atomic). If either fails, both roll back."

### LOW-1: Backstory generation rate limiter not enumerated (Check 5d)

**Category**: Security Measures / Rate Limiting
**Location**: spec.md NFR
**Issue**: Brief §23.9 lists "Backstory generation: existing limiter" but spec.md does not enumerate that the existing limiter is preserved. Minor surface gap; the tasks-phase implementor should not be left to infer this.
**Recommendation**: Add a sentence to NFR Security or Scalability: "Backstory-generation per-user rate limit (existing) MUST be preserved unchanged."

## Role & Permission Matrix

Spec 218 is a single-role flow (authenticated end user editing own onboarding_profile). No admin/multi-role surface.

| Resource | Role | Access | Notes |
|---|---|---|---|
| `/onboarding/answer` POST | authenticated user | self-row R/W | NEEDS EXPLICIT FR (HIGH-1) |
| `/onboarding/state` GET | authenticated user | self-row read | NEEDS EXPLICIT FR (HIGH-1) |
| Phone-demo trigger | authenticated user | once per lifetime (FR-011) | covered |
| Backstory generation | authenticated user | self-only (existing) | not restated in spec (LOW-1) |

## Protected Resources

| Resource | Auth Required | Allowed Roles | Source |
|---|---|---|---|
| Wizard pages `/onboarding/*` | YES (implicit) | self user | NOT EXPLICITLY STATED — HIGH-1 |
| `/onboarding/answer` | YES (implicit) | self user | NOT EXPLICITLY STATED — HIGH-1 |
| `/onboarding/state` | YES (implicit) | self user | NOT EXPLICITLY STATED — HIGH-1 |
| Voice outbound call trigger | YES + opt-in consent | self user | FR-009/FR-011 partial (MEDIUM-1) |

## Security Checklist

- [✗] Rate limiting on agent-decorator endpoint — NOT IN SPEC (HIGH-2)
- [✓] Per-user lifetime cap on phone-demo call — FR-011
- [✓] Per-user Phase-2 cost ceiling — NFR Cost ($0.10)
- [✗] Server-side consent record for TCPA — NOT IN SPEC (MEDIUM-1)
- [~] E.164 normalization — STATED but validation library unspecified (MEDIUM-2)
- [✓] Prompt-injection structural separation — NFR Security + R1 + `_sanitize_for_prompt`
- [✓] Slot persistence sanitization boundary — NFR Security (R1 mitigation bullet 4)
- [~] Phase handoff atomicity — NOT EXPLICITLY TRANSACTIONAL (MEDIUM-3)
- [✓] Voice provider credential reuse — Assumption A2 + pattern-scout
- [✓] GDPR Art 6 cited as easter-egg cut reason — Out-of-Scope + Privacy + Regulatory sections
- [✓] Idempotency for outbound calls — FR-017 + brief §23.7 (DB unique constraint)
- [✓] Idempotency for envelope generation — FR-017 (refresh-safe; no token re-spend)

## Recommendations (ordered by severity)

1. **[HIGH-1]** Add explicit FR-Security clause requiring all `/onboarding/*` server routes to enforce JWT validation and resolve `user_id` from JWT `sub` claim, never from request body. Reuse `nikita/api/dependencies/auth.py:get_current_user_id`.

2. **[HIGH-2]** Add NFR Security clause enumerating the per-user 30 rpm rate limit on `/onboarding/answer`, FR-011 single-fire phone-call cap as a limiter inventory entry, and preserved backstory generation limiter. Reference `nikita/api/middleware/rate_limit.py:answer_rate_limit`.

3. **[MEDIUM-1]** Strengthen FR-009 to mandate server-side consent record persistence (user_id, phone_e164, consent_granted_at, ip_address, user_agent) BEFORE outbound call initiation. Doubles as the FR-011 unique-constraint row.

4. **[MEDIUM-2]** Add NFR Security clause mandating libphonenumber-style validation (country code + length + carrier line-type) at BE boundary; reject invalid input with 422 + inline error per FR-015.

5. **[MEDIUM-3]** Strengthen FR-002 to require `phase_2_started_at` write occurs in the same DB transaction as the final Phase 1 slot acceptance write (atomic-or-rollback).

6. **[LOW-1]** Add a single line to NFR Security/Scalability stating the existing backstory-generation per-user limiter is preserved unchanged.

## Notes for Coordinator

- Findings 1, 5, 6 are spec-surface gaps where the brief already encodes the right answer (§23.9 / §23.7 / R3). Promotion from brief into spec.md is mostly textual editing — likely <30 min.
- Finding 2 (server-side consent) is genuinely net-new TCPA hardening; check with product whether the existing `phone_demo_calls` table schema can absorb consent fields, or whether a sibling `phone_consent_records` table is preferred.
- Finding 4 (libphonenumber) interacts with the data-layer validator's persistence-validator review of FR-017 idempotency — coordinate so both validators reference the same E.164 contract.
- HIGH-1 in particular is the kind of finding that, if waived ("auth is implicit"), produces a downstream IDOR vulnerability where a request body's `user_id` is trusted; spec needs the explicit clause to prevent that path during tasks-phase implementation.
