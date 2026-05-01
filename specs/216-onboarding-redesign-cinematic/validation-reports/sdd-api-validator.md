# API Validation Report — ITERATION 2

**Spec:** `specs/216-onboarding-redesign-cinematic/` (subspecs 216-A, 216-B, 216-E)
**Validator:** sdd-api-validator
**Status:** **PASS**
**Timestamp:** 2026-04-29
**Iteration:** 2 (re-validation after iteration-1 fixes)

## Summary

| Severity | Iter 1 | Iter 2 | Δ |
|----------|-------:|-------:|--:|
| CRITICAL | 2 | **0** | −2 |
| HIGH     | 7 | **0** | −7 |
| MEDIUM   | 5 | 1 (carry — non-blocking) | −4 |
| LOW      | 3 | 1 (carry — non-blocking) | −2 |

PASS criteria met (0 CRITICAL + 0 HIGH). All prior CRITICAL and HIGH findings closed by additions to master `spec.md` §HTTP API Contracts and §Type System Anchors, plus per-subspec ACs (A1.9-A1.14, B1.13-B1.22, E1.9-E1.12).

No regressions detected. The HTTP/REST contract surface is now fully specified with named Pydantic v2 models, deterministic predicates, error envelopes, idempotency strategy, deprecation strategy, secret handling, and structured tool logging.

---

## Closure of Prior CRITICAL + HIGH Findings

| # | Iter 1 Severity | Subspec | Finding | Disposition | Evidence |
|---|------|---------|---------|-------------|----------|
| 1 | **CRITICAL** | 216-B | No named Pydantic v2 request/response models for `POST /api/v1/onboarding/answer`; no field-level constraints; no `response_model=` declared | **CLOSED** | Master spec L194-243 declares `AnswerRequest` (slot_kind: SlotKind, value: `Annotated[str, Field(min_length=0, max_length=2000)]`, turn_id: UUID4, conversation_id: UUID4 \| None) + `AnswerResponse` (output: `TurnOutput \| TurnFailure = Field(discriminator="kind")`, progress_pct: `Field(ge=0, le=100)`, is_complete, link_code, conversation_id, meta). Subspec B1.13 mandates `response_model=AnswerResponse` + `responses={...}` dict + OpenAPI metadata. |
| 2 | **CRITICAL** | 216-B | No `responses={...}` dict; no documented status-code mapping for failure modes; ambiguity on whether `TurnFailure`/`UnexpectedModelBehavior` should be 4xx/5xx vs 200 | **CLOSED** | Master spec L228-239 status-code table explicitly maps: happy path → 200, in-character refusal → 200 + `TurnFailure`, `UnexpectedModelBehavior` → 200 + registry fallback w/ `meta.fallback_reason="model_behavior_error"`, cost circuit → 200 + `meta.fallback_reason="cost_circuit"`, missing JWT → 401, body-validation → 422, rate limit → 429 + Retry-After, internal error → 500. B1.17 ratifies. |
| 3 | **HIGH** | 216-A | AC A1.9 idempotency was disjunction ("400 OR 302"), not deterministic predicate | **CLOSED** | A1.9 rewritten: deterministic predicate on `nikita-session` cookie presence; (a) cookie+valid → 302 `/dashboard`, (b) no/invalid cookie → 400 + `ErrorEnvelope(error="magic_link_consumed")`. Master spec L289-296 codifies exact predicate. Tests must exercise BOTH branches. |
| 4 | **HIGH** | 216-A | No error envelope shape; no enumerated error codes for magic-link failures | **CLOSED** | Master spec L262-281 declares `ErrorEnvelope(error: ErrorCode, detail: str, trace_id: str \| None)` + `ErrorCode` StrEnum table: `auth_required` (401), `magic_link_consumed`/`magic_link_expired`/`magic_link_invalid` (400), `rate_limit_exceeded` (429), `budget_exceeded` (internal/200), `internal_error` (500). L283 explicit no-stack-trace clause. |
| 5 | **HIGH** | 216-B | `UnexpectedModelBehavior` fallback response shape unspecified | **CLOSED** | Master spec L234 + B1.17: 200 + `AnswerResponse(output=TurnOutput from registry, meta={"fallback_reason":"model_behavior_error"})`. Cost-circuit variant uses `meta.fallback_reason="cost_circuit"`. Telemetry hook explicit. |
| 6 | **HIGH** | 216-B | No auth mechanism stated for `/api/v1/onboarding/answer` | **CLOSED** | Master spec L200 + B1.14: `Depends(require_auth_cookie)` reading `nikita-session` JWT cookie; missing/expired → 401 + `ErrorEnvelope(error="auth_required")`. Cookie-only, no Authorization header path. Cookie attributes (Secure, HttpOnly, SameSite=Lax, Path=/, Max-Age≥604800) declared L300-307 + AC A1.10. |
| 7 | **HIGH** | 216-B | No deprecation strategy for legacy `/converse` route | **CLOSED** | Master spec L309-323 + B1.16: 410 Gone shim with `Location: /api/v1/onboarding/answer` for ONE deploy cycle (~7 days), then deletion in subsequent PR. FE forced refresh via `Cache-Control: no-store` on portal HTML. |
| 8 | **HIGH** | 216-B | No idempotency strategy on state-mutating POST `/answer`; client retry would double-charge LLM and double-append history | **CLOSED** | Master spec L241 + B1.15: client-generated `turn_id: UUID4` per turn; server check-before-write — if `turn_id` exists in `conversation_jsonb` for `(user_id, conversation_id)`, return cached `AnswerResponse` (200, no re-execution). |
| 9 | **HIGH** | 216-E | Tool-failure surface to FE undefined; no structured log shape for telemetry | **CLOSED** | Master spec L325-341 + E1.9: structured Cloud Run log `{event: "agent_tool_call", tool_name, outcome ∈ {success, cache_hit, timeout, firecrawl_error, budget_exceeded}, duration_ms, cohort_cache_used, cost_usd_delta, traceparent}`. User-facing response remains 200 (graceful degradation). |
| 10 | **HIGH** | 216-E | `FIRECRAWL_API_KEY` secret-handling rules absent | **CLOSED** | Master spec L343-348 + E1.10: stored as Cloud Run secret env var (not committed `.env`); NEVER logged in plaintext; NEVER returned in any HTTP response or `ErrorEnvelope.detail`. Verified by `tests/agents/onboarding/test_firecrawl_secret_handling.py`. |

All 2 CRITICAL + 7 HIGH iteration-1 findings: **CLOSED**.

---

## Closure of Prior MEDIUM Findings (informational)

| # | Iter 1 | Subspec | Finding | Disposition |
|---|--------|---------|---------|-------------|
| M1 | MEDIUM | 216-A | Cookie flags not explicit | **CLOSED** — A1.10 + master L300-307 (HttpOnly, Secure, SameSite=Lax, Path=/, Max-Age ≥ 604800) |
| M2 | MEDIUM | 216-A | GET `/auth/confirm` side-effect not documented | **CLOSED** — Master L285-298 documents PKCE side-effect + idempotent-on-replay semantics |
| M3 | MEDIUM | 216-B | No OpenAPI metadata (tags, summary, description) | **CLOSED** — Master L243 + B1.13 |
| M4 | MEDIUM | 216-B | No per-user rate limit | **CLOSED** — B1.22 (30 turns/min, 429 + Retry-After) |
| M5 | MEDIUM | 216-E | Firecrawl timeout per-attempt vs cumulative ambiguous | **CLOSED** — E1.11 declares per-attempt; tools NOT in `ModelRetry` loop |
| M6 | MEDIUM | 216-E | `builtin_tools` vs `@agent.tool` conflated | **CLOSED** — E1.12 disambiguates: `WebSearchTool` via `builtin_tools=[prepared_web_search]`; 4 `fetch_*` via `@agent.tool` |
| M7 | MEDIUM | 216-E | `prepared_web_search` API verification deferred | **CARRIED FORWARD (LOW)** — E1.12 instructs verify-against-1.71.0; remains a planning-time check, non-blocking for spec PASS |

---

## Endpoint Inventory (post iteration-2)

| Method | Path | Request Model | Response Model | Auth | Status Codes |
|--------|------|---------------|----------------|------|--------------|
| POST | /api/v1/onboarding/answer | `AnswerRequest` | `AnswerResponse` (`response_model=`) | `Depends(require_auth_cookie)` (`nikita-session` JWT cookie) | 200 / 401 / 422 / 429 / 500 (documented in `responses={}`) |
| GET | /api/v1/onboarding/state | (query) | `StateResponse` | same | 200 / 401 |
| POST | /api/v1/onboarding/converse (deprecated shim) | — | `ErrorEnvelope` | n/a | 410 Gone + `Location` header (one deploy cycle) |
| GET | /auth/confirm | (token_hash query) | (Set-Cookie + redirect) | PKCE token_hash | 302 (replay w/ live session) / 400 (`magic_link_consumed`) / 200 (first valid click) |
| POST | /telegram/webhook (existing) | unchanged | unchanged | Telegram secret header | unchanged |

---

## Error Envelope Consistency

- ✓ Uniform `ErrorEnvelope(error: ErrorCode, detail: str, trace_id: str | None)` across new endpoints (master L262-269)
- ✓ `ErrorCode` StrEnum exhaustive (master L271-281)
- ✓ No stack-trace leakage clause explicit (master L283)
- ✓ Semantic codes (not generic `error`): `magic_link_consumed`, `auth_required`, `rate_limit_exceeded`, etc.

## Idempotency Audit

| Endpoint | Verb | Idempotency Strategy | Status |
|----------|------|----------------------|--------|
| /api/v1/onboarding/answer | POST | client `turn_id: UUID4` + server check-before-write on `conversation_jsonb` | ✓ |
| /auth/confirm | GET | deterministic cookie-presence predicate (302 vs 400) | ✓ |
| /api/v1/onboarding/converse | POST | 410 Gone shim (deprecated) | ✓ (sunset path) |
| /telegram/webhook | POST | existing (Telegram dedup) | ✓ |

## OpenAPI Surface

- ✓ `response_model=` mandated on `/answer` (B1.13) and implied on `/state`
- ✓ `responses={...}` documents non-200 paths (master L228-239)
- ✓ `tags=["onboarding"]` (master L243 + B1.13)
- ✓ `summary` + `description` populated (master L243)
- ✓ Deprecation marked via `deprecated=True` on legacy `/converse` shim (master L314)

---

## Remaining Non-Blocking Findings (carried forward, planning-phase)

| Severity | Subspec | Finding | Note |
|----------|---------|---------|------|
| LOW | 216-A | Open Q1 (`_send_bare_portal_auth_link` deletion vs retain) still pending | Document during planning (Phase 1.C); not a contract gap |
| LOW | 216-E | `prepared_web_search` API surface should be verified against Pydantic AI 1.71.0 `prepare_tools` docs at planning time | E1.12 already instructs the verification; non-blocking for spec PASS |

These do not block GATE 2 closure.

---

## Regression Check

Re-scanned all 11 categories of the API validation checklist against iteration-2 spec text. No new CRITICAL or HIGH findings introduced. The additions in master §HTTP API Contracts and §Type System Anchors are internally consistent with the subspec ACs (A1.9-A1.14, B1.13-B1.22, E1.9-E1.12). No drift between master and subspecs detected.

**No REGRESSION.**

---

## Verdict

**PASS** — 0 CRITICAL + 0 HIGH. All prior CRITICAL/HIGH findings closed. 2 LOW items carried forward as planning-phase items, non-blocking. Iteration-2 fixes have produced a complete and implementation-ready HTTP/REST contract surface for the new `POST /api/v1/onboarding/answer` endpoint plus the auth-confirm idempotency predicate, error envelope, deprecation strategy, and tool-failure log shape. Spec 216 subspecs A/B/E clear GATE 2 from this validator's perspective.
