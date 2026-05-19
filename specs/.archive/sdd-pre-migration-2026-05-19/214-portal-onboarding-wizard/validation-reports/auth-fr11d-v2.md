## Auth Validation Report — FR-11d Amendment

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d, lines 654-782)
**Branch:** `spec/214-fr11d-slot-filling-amendment` (commit 72e06d6)
**Status:** PASS (with 1 MEDIUM + 3 LOW findings; 0 CRITICAL, 0 HIGH)
**Timestamp:** 2026-04-23T00:00:00Z
**Validator:** sdd-auth-validator (FR-11d v2 re-validation)

---

### Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 1
- LOW: 3

PASS criteria met (0 CRITICAL + 0 HIGH). The FR-11d amendment's auth surface is sound. The existing `get_authenticated_user` dependency chain and JWT pattern from `nikita/api/dependencies/auth.py` are preserved on both `/converse` and `GET /conversation`. The two new wire fields (`link_code`, `link_expires_at`) are additive and null-safe. One MEDIUM finding covers a spec gap on the re-mint auth flow that could lead to an unprotected code-generation path if misread. Three LOW findings are clarifications around PII logging scope, link-code timing-safety, and the null-on-early-completion invariant.

---

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| B1 | MEDIUM | Session Management / Re-mint Auth | AC-11d.8 says the FE "re-runs `/converse` with the same conversation_history to re-mint a fresh code via the existing completion-gate path." This implies the re-mint happens through the normal `/converse` endpoint with the existing Bearer JWT — which is correct. However, the spec does not make this explicit. An implementor could misread it as a new unauthenticated GET-triggered re-mint path. The `GET /conversation` endpoint returns `link_code_expired=True` but has NO mint side-effect — minting only happens via `/converse` (authenticated, rate-limited, idempotency-keyed). This separation must be documented as a security invariant. If `GET /conversation` were ever given mint capability, it would bypass the rate-limiter and idempotency store. | spec.md L733 ("GET /conversation hydration response") | Add an explicit constraint sentence to AC-11d.8: "The `GET /conversation` endpoint MUST NOT mint a new code. `link_code_expired=True` is a FE signal to re-drive the existing `/converse` flow (which carries Bearer JWT + rate-limit + idempotency). `GET /conversation` is read-only; minting responsibility remains on `/converse` exclusively." |
| B2 | LOW | PII Handling — Logging Scope | The spec mandates the `testing.md` pre-PR grep gate against raw PII values in log format strings (name/age/occupation/phone). The existing `/converse` handler at L875-880 already logs `loc=` and `type=` from Pydantic `ValidationError` — never raw field values — and the comment notes this is "PII-safe." However, the FR-11d state reconstruction path (`build_state_from_conversation`) is new and will iterate over JSONB blobs containing name/age/phone. The spec does not explicitly prohibit logging reconstructed slot values in `state_reconstruction.py`. | spec.md L737-742 ("Conversation Persistence") | Add to AC-11d.1 or the Conversation Persistence subsection: "The reconstruction reducer (`build_state_from_conversation`) MUST NOT log individual slot values (name, age, occupation, phone). Log only slot-key names (e.g. `'location'`) and counts. Applies to the `elided_extracted` merge path as well." |
| B3 | LOW | Token Timing-Safety — `link_code` Exposure | `link_code` is a 6-char alphanumeric generated via `secrets.choice` (confirmed in `nikita/db/models/telegram_link.py:19-29` — uses `secrets` module, NOT `random`, alphabet = uppercase + digits, 36^6 ≈ 2.18 billion combinations). The code is returned in the wire response body and stored in `telegram_link_codes`. Wire delivery is HTTPS-only (Cloud Run + Vercel enforce TLS). Single-use semantics are per FR-11b `consumed_at` column. The spec at L726-731 says the field is null on non-terminal turns. One minor gap: the spec does not state that `link_code` MUST NOT be included in error logs or response bodies outside the terminal turn. The existing `extra="forbid"` on `ConverseResponse` prevents accidental field leakage via spoofed fields, but does not prevent an accidental logger call from emitting the minted code. | spec.md L724-731 ("Wire-Format Extension") | Add: "The `link_code` value MUST NOT appear in any server log (it is a single-use authentication credential). Log only the code's `expires_at` timestamp and whether minting succeeded. Client-side, the FE MUST NOT persist `link_code` to localStorage or sessionStorage — it should only live in the React state driving the `ClearanceGrantedCeremony` deep-link render." |
| B4 | LOW | Null-Age Rejection — FinalForm Validator Spec | AC-11d.3 states "`FinalForm` declares all 6 slots as non-optional + a `@model_validator(mode="after")` for cross-field rules (age ≥ 18 enforced via `MIN_USER_AGE`)." The slot table at L666-673 shows `identity` as `IdentityExtraction(name?, age?, occupation?)` with "Yes (≥1 sub-field)" required. This means a user could satisfy the `identity` slot with name-only (age=None). The `@model_validator` applies after `FinalForm` validates the `identity` slot as present, but `age` being None means the `age >= MIN_USER_AGE` check would either error with a `TypeError` or silently skip. The spec must clarify whether null `age` is treated as completion-blocking or only invalid ages are rejected. | spec.md L679 ("Completion Criteria — FinalForm") | Add a clarifying sentence: "The `age >= 18` cross-field validator in `FinalForm` MUST treat `null age` as non-blocking (identity slot is completable with name-only), NOT as an under-18 rejection. Under-18 is only triggered when `age` is explicitly provided and `age < 18`. The existing `ValidationError` age-18 in-character reply (`_VALIDATION_REJECT_AGE_REPLY`) applies only to the explicit `age < 18` case, not to `age=None`." This is consistent with the existing `IdentityExtraction` schema that marks `age` optional, but must be explicitly stated in `FinalForm`'s validator docstring. |

---

### Auth Flow Analysis

**Primary Method:** Supabase JWT (Bearer token), validated via `get_authenticated_user` dependency (`nikita/api/dependencies/auth.py`)
**Session Type:** Stateless JWT — no server-side session; identity derived per-request from JWT sub claim
**Token Handling:** JWT validated and decoded in `_decode_jwt`; `get_authenticated_user` returns `AuthenticatedUser(id, email)` with user_id used as the scoping key for all DB reads

Both `/converse` (POST, L751-753) and `GET /conversation` (L702-703) carry `current_user: AuthenticatedUser = Depends(get_authenticated_user)` — confirmed in live code. FR-11d does not alter these dependencies. The re-mint path via GET `/conversation` is read-only (returns expired signal); re-minting routes through `/converse` (authenticated, rate-limited).

---

### Role & Permission Matrix

FR-11d adds no new roles. The existing two-tier model applies:

| Resource | `user` (JWT) | `admin` | Notes |
|----------|-------------|---------|-------|
| POST `/converse` | READ/WRITE own data | N/A | `get_authenticated_user` dep; rate-limited (20 rpm/user, 30 rpm/IP, $2/day) |
| GET `/conversation` | READ own data | N/A | `get_authenticated_user` dep; read-only |
| `telegram_link_codes` row | READ (own code via /converse response) | N/A | No direct API to list/read codes; code returned on terminal turn only |
| `WizardSlots` state | READ/WRITE own JSONB | N/A | Scoped to `current_user.id`; no cross-user read |

`user_metadata` is never consulted for admin checks (confirmed in `api/CLAUDE.md`). Admin claim requires `app_metadata.role == "admin"` (service-role-only, not client-writable). FR-11d endpoints do not use admin deps.

---

### Protected Resources

| Resource | Auth Required | Allowed Roles | Notes |
|----------|--------------|---------------|-------|
| POST `/onboarding/converse` | Yes (Bearer JWT) | Authenticated user | Rate-limited; idempotency via `Idempotency-Key` header or `turn_id` body |
| GET `/onboarding/conversation` | Yes (Bearer JWT) | Authenticated user | Read-only; no mint side-effect |
| `telegram_link_codes` table | Implicit via app-layer | User's own code only | No direct REST exposure; code surfaces only in terminal `/converse` response |
| `users.onboarding_profile` JSONB | App-layer scoped | User's own record | `repo.get(current_user.id)` — no UUID param in URL; RLS `auth.uid() = id` enforces at DB layer |

Cross-user JSONB reads: not possible. Both `GET /conversation` (L710: `repo.get(current_user.id)`) and `/converse` (deps scoped to `current_user.id`) use the authenticated user's own ID. No user_id accepted from the request body (the `/converse` docstring at L738 explicitly states "Body MUST NOT carry `user_id` (extra='forbid' at schema level)").

---

### Security Checklist

- [✓] Rate limiting on login — SPECIFIED. `/converse` has 20 rpm/user, 30 rpm/IP, $2/day LLM spend cap (AC-T2.5.4, L749). `GET /conversation` is read-only with no rate limit (acceptable — no LLM cost).
- [✓] Account lockout policy — N/A for this feature. Auth is Supabase-managed; lockout applies at the Supabase Auth layer, not in-app.
- [✓] Session invalidation on logout — N/A for this endpoint. Stateless JWT; invalidation handled by Supabase token expiry.
- [✓] CSRF protection — SPECIFIED. CORS `extra="forbid"` on request body; Bearer JWT in header (not cookie) means no CSRF surface for these endpoints.
- [✓] Security headers (CSP, HSTS) — N/A for this validator scope. Handled at Cloud Run / Vercel layer, not FR-11d-specific.
- [✓] Single-use link code — SPECIFIED. `consumed_at IS NULL` filter on GET lookup (L733); FR-11b semantics preserved.
- [✓] Link code TTL — SPECIFIED. 10-minute TTL in `telegram_link_codes` model (expires_at = utc_now() + 10 min, confirmed in `telegram_link.py:102`).
- [✓] Cryptographically safe code generation — CONFIRMED. `secrets.choice` (not `random`) with 36-char alphabet, 6 chars → ~2.18B combinations. Brute-force infeasible within 10-min TTL given rate-limiting.
- [~] Link-code logging prohibition — NOT SPECIFIED. See finding B3.
- [~] Re-mint auth invariant (GET read-only) — IMPLICIT but not explicit. See finding B1 (MEDIUM).
- [~] Null-age vs under-18 rejection distinction — AMBIGUOUS. See finding B4.
- [~] PII logging guard on reconstruction path — NOT SPECIFIED. See finding B2.

---

### Recommendations

1. **(MEDIUM — B1) Mint-only-via-/converse invariant**: Add one sentence to AC-11d.8 stating `GET /conversation` MUST NOT mint link codes. This is already the intended design but the spec wording invites misreading. Cost: one spec sentence.

2. **(LOW — B2) Reconstruction PII logging guard**: Add a logging constraint to the state_reconstruction spec section. Implementor must not log slot values (name/age/phone) from the JSONB reduction path — only key names and counts. Prevents accidental PII leakage to Cloud Run logs during debugging.

3. **(LOW — B3) link_code log/storage prohibition**: Explicitly prohibit server-side logging of the `link_code` value and FE-side persistence to localStorage/sessionStorage. The code is a single-use auth credential; accidental logging would expose it to anyone with Cloud Logging read access.

4. **(LOW — B4) Null-age gate semantics in FinalForm**: Clarify that `age=None` inside a filled `identity` slot does NOT trigger the under-18 in-character reply. The `@model_validator` MUST only fire on explicit `age < 18`. This prevents the incorrect path where a user who gives only their name gets the age-rejection error. The existing `IdentityExtraction` schema (age optional) and the handler's `_is_age_under_18_error` check must be aligned on this — spec the intended semantic explicitly.

---

### Conclusion

**PASS.** The FR-11d amendment is auth-safe. It:

1. Preserves the existing `get_authenticated_user` JWT dep on both new-behavior endpoints, confirmed in live code at L702-703 and L751-753.
2. Scopes all JSONB reads to `current_user.id` — no URL-embedded user ID, no cross-user read possible.
3. Routes the sole mint operation through `/converse` (authenticated, rate-limited, idempotency-keyed), not through the read-only `GET /conversation`.
4. Uses `secrets.choice` for code generation (not `random`), 10-min TTL, single-use `consumed_at` semantics — all confirmed in `telegram_link.py`.
5. Does not add any new roles, admin capabilities, or unauthenticated endpoints.

The 4 findings are clarification-only spec edits. None require architectural change. B1 (MEDIUM) is the most important to address as it encodes a security invariant that the spec currently leaves implicit.
